"""WebSocket-клиент ServerSkif через прокси ARM WebSocket (операции интеграции).

Общая механика постоянного соединения/лимитов — в ``_shared/shared_api.py``
(канонический источник — ``tools/ha-shared/shared_api.py``).

``securarm`` — управляющая интеграция: помимо чтения снимка она умеет
отправлять команды ``controlPart_Arm``/``controlPart_DisArm``. Подтверждение
команды выполняется по состоянию раздела (коды 24/109) в ``__init__.py``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ._shared.shared_api import (
    PersistentTechlanClient,
    TechlanApiError,
    TechlanCommandError,
    format_loop_label,
    loop_key,
    parse_loop_keys,
    state_confirms,
    websocket_url,
)

__all__ = [
    "TechlanApiClient",
    "TechlanApiError",
    "TechlanCommandError",
    "websocket_url",
]


class TechlanApiClient(PersistentTechlanClient):
    """ServerSkif API client for securarm (read + control)."""

    # --- discovery (config flow selector) ------------------------------------

    async def async_discover_loops(self) -> list[dict[str, Any]]:
        """Discover loop (ШС) choices grouped by section for the HA selector."""
        return await self.async_run(self._discover_loops_sync)

    def _discover_loops_sync(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        pkus = [
            int(item) for item in (self.request_sync("getListPKU").get("ret") or [])
        ]
        for pku in pkus:
            parts = [
                int(item)
                for item in (
                    self.request_sync("getListParts", pku=pku).get("ret") or []
                )
            ]
            for part in parts:
                shs = [
                    int(item)
                    for item in (
                        self.request_sync(
                            "getListPartSh", pku=pku, extra={"req": part}
                        ).get("ret")
                        or []
                    )
                ]
                descriptions: list[str] = []
                if shs:
                    descriptions = [
                        str(item)
                        for item in (
                            self.request_sync(
                                "getShDescription", pku=pku, extra={"req": shs}
                            ).get("ret")
                            or []
                        )
                    ]
                for sh, description in zip(shs, descriptions or [""] * len(shs)):
                    result.append(
                        {
                            "key": loop_key(pku, part, sh),
                            "pku": pku,
                            "part": part,
                            "sh": sh,
                            "description": description,
                            "label": format_loop_label(pku, part, sh, description),
                        }
                    )
        return result

    # --- snapshot -------------------------------------------------------------

    async def async_fetch_snapshot(
        self, selected_loops: list[str] | None = None
    ) -> dict[str, Any]:
        """Fetch PKU/part state over the persistent session."""
        return await self.async_run(self._fetch_snapshot_sync, selected_loops)

    def _fetch_snapshot_sync(
        self, selected_loops: list[str] | None = None
    ) -> dict[str, Any]:
        pkus = [
            int(item) for item in (self.request_sync("getListPKU").get("ret") or [])
        ]
        if not pkus:
            raise TechlanApiError("ServerSkif returned no PKU")
        selected = None if selected_loops is None else parse_loop_keys(selected_loops)
        if selected is not None:
            pkus = sorted({pku for pku, _part, _sh in selected})
        parts: dict[int, list[int]] = {}
        descriptions: dict[tuple[int, int], str] = {}
        states: dict[int, dict[int, int]] = {pku: {} for pku in pkus}
        # Query one PKU at a time. ServerSkif emits unsolicited state messages,
        # so sequential requests avoid response interleaving.
        for pku in pkus:
            if selected is None:
                part_list = [
                    int(item)
                    for item in (
                        self.request_sync("getListParts", pku=pku).get("ret") or []
                    )
                ]
            else:
                part_list = sorted(
                    {
                        part
                        for selected_pku, part, _sh in selected
                        if selected_pku == pku
                    }
                )
            parts[pku] = part_list
            if part_list:
                description_message = self.request_sync(
                    "getPartDescription", pku=pku, extra={"req": part_list}
                )
                for part, description in zip(
                    part_list, description_message.get("ret") or []
                ):
                    descriptions[(pku, part)] = str(description)
                state_message = self.request_sync(
                    "getPartState", pku=pku, extra={"req": part_list}
                )
                states[pku] = {
                    part: int(state)
                    for part, state in zip(part_list, state_message.get("ret") or [])
                }
        snapshot: dict[str, Any] = {
            "available": True,
            "pkus": {},
            "updated_at": time.time(),
        }
        for pku in pkus:
            snapshot["pkus"][pku] = {
                "part_count": len(parts.get(pku, [])),
                "parts": {
                    part: {
                        "description": descriptions.get((pku, part), ""),
                        "state_code": state,
                        "loops": {},
                    }
                    for part, state in states.get(pku, {}).items()
                },
            }
        return snapshot

    async def async_validate(self) -> None:
        """Validate URL, authentication and at least one PKU."""
        await self.async_fetch_snapshot()

    # --- control --------------------------------------------------------------

    async def async_get_part_state(self, pku: int, part: int) -> int | None:
        """Read the current state code of a single section."""
        message = await self.async_request(
            "getPartState", pku=int(pku), extra={"req": [int(part)]}
        )
        values = message.get("ret") or []
        try:
            return int(values[0]) if values else None
        except (TypeError, ValueError):
            return None

    async def async_control_part(self, action: str, pku: int, part: int) -> None:
        """Send one protected arm/disarm command to a section."""
        if action not in {"arm", "disarm"}:
            raise TechlanApiError("Unsupported section control action")
        command_name = "controlPart_Arm" if action == "arm" else "controlPart_DisArm"
        await self.async_send_command(
            {"funct": command_name, "pku": int(pku), "part": int(part)}
        )

    async def async_control_and_confirm(
        self,
        action: str,
        pku: int,
        part: int,
        *,
        target_codes: frozenset[int],
        confirm_timeout: float,
        poll_interval: float = 1.0,
        retries: int = 1,
    ) -> int:
        """Send a command, then wait for the state confirmation (24/109).

        Retries once if the first command is not confirmed. Returns the number
        of attempts made; raises ``TechlanCommandError`` on failure.
        """
        attempts = 0
        max_attempts = 1 + max(0, int(retries))
        last_state: int | None = None
        while attempts < max_attempts:
            attempts += 1
            await self.async_control_part(action, pku, part)
            deadline = time.monotonic() + max(0.0, float(confirm_timeout))
            while True:
                last_state = await self.async_get_part_state(pku, part)
                if state_confirms(last_state, target_codes):
                    return attempts
                if time.monotonic() >= deadline:
                    break
                await asyncio.sleep(poll_interval)
        raise TechlanCommandError(
            f"Команда {action} для ПКУ {pku}/{part} не подтверждена "
            f"(состояние {last_state})"
        )
