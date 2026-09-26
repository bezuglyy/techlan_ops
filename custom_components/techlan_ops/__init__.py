"""Native Home Assistant integration for SecurARM (control domain).

Управление разделами идёт через сервисы ``arm_part``/``disarm_part`` и
switch-сущности. После команды интеграция **дожидается подтверждения по
состоянию раздела** (код 24 «Взят» / 109 «Снят») в пределах настраиваемого
таймаута; при неудаче делается одна повторная попытка, затем возвращается
понятная ошибка. Каждая команда попадает в аудит-событие ``techlan_ops_command``
с результатом.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, HomeAssistantError, ServiceCall

from ._shared.shared_api import TechlanApiError, TechlanCommandError
from ._shared.shared_entities import async_get_or_create_device, configuration_url
from .const import (
    ARM_CONFIRM_CODES,
    CONF_BASE_URL,
    CONF_COMMAND_TIMEOUT,
    CONF_SCAN_INTERVAL,
    CONF_SELECTED_LOOPS,
    CONF_WS_PATH,
    CONFIRM,
    CONFIG_MINOR_VERSION,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WS_PATH,
    DEVICE_MODEL,
    DEVICE_NAME,
    DISARM_CONFIRM_CODES,
    DOMAIN,
    INTEGRATION_VERSION,
    PARENT_IDENTIFIER,
    PLATFORMS,
)
from .coordinator import TechlanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

type TechlanConfigEntry = ConfigEntry[TechlanDataUpdateCoordinator]

# Ключи, добавленные после первой версии схемы (используются миграцией).
_MIGRATION_DEFAULTS: dict = {
    CONF_WS_PATH: DEFAULT_WS_PATH,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
    CONF_SELECTED_LOOPS: [],
    CONF_COMMAND_TIMEOUT: DEFAULT_COMMAND_TIMEOUT,
}


def _register_services(hass: HomeAssistant) -> None:
    """Register control services once for the integration domain."""
    if hass.services.has_service(DOMAIN, "arm_part"):
        return

    schema = vol.Schema(
        {
            vol.Required("pku", description="Номер ПКУ"): vol.Coerce(int),
            vol.Required("part", description="Номер раздела"): vol.Coerce(int),
            vol.Required(
                CONFIRM, default=False, description="Подтверждение команды"
            ): vol.Coerce(bool),
        }
    )

    async def get_coordinator() -> TechlanDataUpdateCoordinator:
        for entry in hass.config_entries.async_entries(DOMAIN):
            runtime_data = getattr(entry, "runtime_data", None)
            if runtime_data is not None:
                return runtime_data
        raise HomeAssistantError("Интеграция SecurARM ещё не загружена")

    def audit(
        action: str,
        call: ServiceCall,
        *,
        result: str,
        attempts: int = 0,
        error: str = "",
    ) -> None:
        """Log and fire an event for every manual arm/disarm command."""
        user_id = getattr(call.context, "user_id", None) or "unknown"
        _LOGGER.warning(
            "Techlan ARM command '%s': pku=%s part=%s user=%s result=%s attempts=%s",
            action,
            call.data.get("pku"),
            call.data.get("part"),
            user_id,
            result,
            attempts,
        )
        hass.bus.async_fire(
            f"{DOMAIN}_command",
            {
                "action": action,
                "pku": call.data.get("pku"),
                "part": call.data.get("part"),
                "user_id": user_id,
                "result": result,
                "attempts": attempts,
                "error": error,
            },
        )

    async def _control(action: str, call: ServiceCall) -> None:
        if not call.data[CONFIRM]:
            raise HomeAssistantError("Для управления требуется confirm: true")
        coordinator = await get_coordinator()
        pku = int(call.data["pku"])
        part = int(call.data["part"])
        target = ARM_CONFIRM_CODES if action == "arm" else DISARM_CONFIRM_CODES
        try:
            attempts = await coordinator.client.async_control_and_confirm(
                action,
                pku,
                part,
                target_codes=target,
                confirm_timeout=coordinator.command_timeout,
            )
        except (TechlanCommandError, TechlanApiError) as exc:
            audit(action, call, result="error", error=str(exc))
            verb = "взять" if action == "arm" else "снять"
            raise HomeAssistantError(
                f"Не удалось {verb} раздел ПКУ {pku}/{part}: {exc}"
            ) from exc
        audit(action, call, result="ok", attempts=attempts)
        await coordinator.async_request_refresh()

    async def handle_arm(call: ServiceCall) -> None:
        await _control("arm", call)

    async def handle_disarm(call: ServiceCall) -> None:
        await _control("disarm", call)

    hass.services.async_register(DOMAIN, "arm_part", handle_arm, schema)
    hass.services.async_register(DOMAIN, "disarm_part", handle_disarm, schema)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the SecurARM integration."""
    _register_services(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: TechlanConfigEntry) -> bool:
    """Migrate config entry schema (options get new keys with defaults)."""
    if entry.version > 1:
        # Unknown future schema — do not touch it.
        return False
    if entry.version == 1 and entry.minor_version < CONFIG_MINOR_VERSION:
        options = dict(entry.options)
        merged = {**entry.data, **entry.options}
        for key, default in _MIGRATION_DEFAULTS.items():
            if key not in merged:
                options[key] = default
        hass.config_entries.async_update_entry(
            entry, options=options, minor_version=CONFIG_MINOR_VERSION
        )
        _LOGGER.info(
            "SecurARM migrated to minor version %s", CONFIG_MINOR_VERSION
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TechlanConfigEntry) -> bool:
    """Set up SecurARM from a config entry."""
    _register_services(hass)
    if entry.title != "Techlan ARM":
        hass.config_entries.async_update_entry(entry, title="Techlan ARM")
    coordinator = TechlanDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_on_unload(coordinator.async_shutdown)
    _register_parent_device(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _register_parent_device(
    hass: HomeAssistant,
    entry: TechlanConfigEntry,
    coordinator: TechlanDataUpdateCoordinator,
) -> None:
    """Create the parent device before entities so via_device_id resolves."""
    base_url = {**entry.data, **entry.options}.get(CONF_BASE_URL, "")
    coordinator.parent_identifier = (DOMAIN, PARENT_IDENTIFIER)
    coordinator.configuration_url = configuration_url(base_url)
    parent = async_get_or_create_device(
        hass,
        entry,
        {coordinator.parent_identifier},
        name=DEVICE_NAME,
        model=DEVICE_MODEL,
        sw_version=INTEGRATION_VERSION,
        configuration_url=coordinator.configuration_url,
    )
    coordinator.parent_device_id = parent.id


async def _async_update_listener(
    hass: HomeAssistant, entry: TechlanConfigEntry
) -> None:
    """Reload the coordinator/entities after connection options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: TechlanConfigEntry) -> bool:
    """Unload SecurARM and close the persistent connection."""
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is not None:
        await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
