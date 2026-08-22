"""Availability entity for Techlan ARM-OPS."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TechlanDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: TechlanDataUpdateCoordinator = entry.runtime_data
    async_add_entities([TechlanAvailabilitySensor(coordinator)])


class TechlanAvailabilitySensor(CoordinatorEntity[TechlanDataUpdateCoordinator], BinarySensorEntity):
    _attr_name = "ARM-OPS доступность"
    _attr_unique_id = f"{DOMAIN}_availability"
    _attr_device_class = "connectivity"
    _attr_device_info = {
        "identifiers": {(DOMAIN, "arm_ops")},
        "name": "ARM-OPS / Techlan",
        "manufacturer": "Techlan",
        "model": "ServerSkif WebSocket proxy",
    }

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success
