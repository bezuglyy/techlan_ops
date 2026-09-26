"""Availability entity for SecurARM."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ._shared.shared_entities import build_device_info
from .const import DEVICE_MODEL, DEVICE_NAME, DOMAIN, INTEGRATION_VERSION
from .coordinator import TechlanDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: TechlanDataUpdateCoordinator = entry.runtime_data
    async_add_entities([TechlanAvailabilitySensor(coordinator)])


class TechlanAvailabilitySensor(
    CoordinatorEntity[TechlanDataUpdateCoordinator], BinarySensorEntity
):
    """Service entity: SecurARM reachability (diagnostic)."""

    _attr_has_entity_name = True
    _attr_translation_key = "availability"
    _attr_unique_id = f"{DOMAIN}_availability"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TechlanDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = build_device_info(
            identifiers={coordinator.parent_identifier},
            name=DEVICE_NAME,
            model=DEVICE_MODEL,
            sw_version=INTEGRATION_VERSION,
            configuration_url=coordinator.configuration_url,
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success
