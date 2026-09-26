"""Config flow for native SecurARM integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.core import HomeAssistant

from .api import TechlanApiClient, TechlanApiError
from ._shared.shared_api import CannotConnectError, url_is_valid
from .const import (
    CONF_ARM_ID,
    CONF_BASE_URL,
    CONF_COMMAND_TIMEOUT,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SELECTED_LOOPS,
    CONF_WS_PATH,
    CONFIG_MINOR_VERSION,
    DEFAULT_ARM_ID,
    DEFAULT_BASE_URL,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WS_PATH,
    DOMAIN,
)


async def _validate(hass: HomeAssistant, data: dict[str, str]) -> None:
    if not url_is_valid(
        data.get(CONF_BASE_URL, ""), data.get(CONF_WS_PATH, DEFAULT_WS_PATH)
    ):
        raise CannotConnectError
    client = TechlanApiClient(
        data[CONF_BASE_URL].rstrip("/"),
        data[CONF_ARM_ID],
        data[CONF_PASSWORD],
        data.get(CONF_WS_PATH, DEFAULT_WS_PATH),
    )
    try:
        await client.async_validate()
    except TechlanApiError as exc:
        raise CannotConnectError from exc


class TechlanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle setup from Home Assistant UI."""

    VERSION = 1
    MINOR_VERSION = CONFIG_MINOR_VERSION

    async def _loop_schema(self, data: dict, selected: list[str] | None = None):
        client = TechlanApiClient(
            data[CONF_BASE_URL],
            data[CONF_ARM_ID],
            data[CONF_PASSWORD],
            data.get(CONF_WS_PATH, DEFAULT_WS_PATH),
        )
        loops = await client.async_discover_loops()
        options = [{"value": item["key"], "label": item["label"]} for item in loops]
        return vol.Schema(
            {
                vol.Optional(
                    CONF_SELECTED_LOOPS, default=selected or []
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return TechlanOptionsFlow()

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_BASE_URL: user_input[CONF_BASE_URL].rstrip("/"),
                CONF_ARM_ID: user_input[CONF_ARM_ID].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            await self.async_set_unique_id(data[CONF_BASE_URL])
            self._abort_if_unique_id_configured()
            try:
                await _validate(self.hass, data)
            except (CannotConnectError, ValueError, TypeError):
                errors["base"] = "cannot_connect"
            else:
                self._pending_data = data
                return await self.async_step_select_loops()

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Required(CONF_ARM_ID, default=DEFAULT_ARM_ID): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_loops(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        data = self._pending_data
        if user_input is not None:
            data[CONF_SELECTED_LOOPS] = list(user_input.get(CONF_SELECTED_LOOPS, []))
            return self.async_create_entry(title="SecurARM", data=data)
        try:
            schema = await self._loop_schema(data)
        except TechlanApiError:
            return self.async_abort(reason="cannot_connect")
        return self.async_show_form(step_id="select_loops", data_schema=schema)


class TechlanOptionsFlow(config_entries.OptionsFlow):
    """Allow changing ARM connection parameters after setup."""

    async def _loop_schema(self, data: dict, selected: list[str] | None = None):
        client = TechlanApiClient(
            data[CONF_BASE_URL],
            data[CONF_ARM_ID],
            data[CONF_PASSWORD],
            data.get(CONF_WS_PATH, DEFAULT_WS_PATH),
        )
        loops = await client.async_discover_loops()
        options = [{"value": item["key"], "label": item["label"]} for item in loops]
        return vol.Schema(
            {
                vol.Optional(
                    CONF_SELECTED_LOOPS, default=selected or []
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            data = {
                CONF_BASE_URL: user_input[CONF_BASE_URL].rstrip("/"),
                CONF_ARM_ID: user_input[CONF_ARM_ID].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD]
                or current.get(CONF_PASSWORD, ""),
                CONF_WS_PATH: "/" + user_input[CONF_WS_PATH].lstrip("/"),
                CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                CONF_COMMAND_TIMEOUT: int(user_input[CONF_COMMAND_TIMEOUT]),
                CONF_SELECTED_LOOPS: list(
                    user_input.get(
                        CONF_SELECTED_LOOPS, current.get(CONF_SELECTED_LOOPS, [])
                    )
                ),
            }
            try:
                if data[CONF_SCAN_INTERVAL] < 5 or data[CONF_SCAN_INTERVAL] > 3600:
                    raise CannotConnectError
                if data[CONF_COMMAND_TIMEOUT] < 5 or data[CONF_COMMAND_TIMEOUT] > 600:
                    raise CannotConnectError
                await _validate(self.hass, data)
            except (CannotConnectError, ValueError, TypeError):
                errors["base"] = "cannot_connect"
            else:
                # Persist all option values through the OptionsFlow result;
                # returning an empty result makes Home Assistant replace the
                # saved options with {}.
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_BASE_URL: data[CONF_BASE_URL],
                        CONF_ARM_ID: data[CONF_ARM_ID],
                        CONF_PASSWORD: data[CONF_PASSWORD],
                        CONF_WS_PATH: data[CONF_WS_PATH],
                        CONF_SCAN_INTERVAL: data[CONF_SCAN_INTERVAL],
                        CONF_COMMAND_TIMEOUT: data[CONF_COMMAND_TIMEOUT],
                        CONF_SELECTED_LOOPS: data[CONF_SELECTED_LOOPS],
                    },
                )

        try:
            loop_schema = await self._loop_schema(
                current, current.get(CONF_SELECTED_LOOPS, [])
            )
            loop_field = loop_schema.schema
        except TechlanApiError:
            loop_field = {
                vol.Optional(
                    CONF_SELECTED_LOOPS, default=current.get(CONF_SELECTED_LOOPS, [])
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=[], multiple=True)
                )
            }
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BASE_URL, default=current.get(CONF_BASE_URL, DEFAULT_BASE_URL)
                ): str,
                vol.Required(
                    CONF_ARM_ID, default=current.get(CONF_ARM_ID, DEFAULT_ARM_ID)
                ): str,
                vol.Optional(CONF_PASSWORD, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(
                    CONF_WS_PATH, default=current.get(CONF_WS_PATH, DEFAULT_WS_PATH)
                ): str,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=int(current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                vol.Required(
                    CONF_COMMAND_TIMEOUT,
                    default=int(
                        current.get(CONF_COMMAND_TIMEOUT, DEFAULT_COMMAND_TIMEOUT)
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=600)),
                **loop_field,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
