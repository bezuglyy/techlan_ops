"""PKU summary sensors for Techlan ARM-OPS."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ALARM_STATE_CODES, DOMAIN, STATE_NAMES
from .coordinator import TechlanDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: TechlanDataUpdateCoordinator = entry.runtime_data
    await coordinator.async_config_entry_first_refresh()
    entities = [TechlanPkuSensor(coordinator, entry, pku) for pku in sorted(coordinator.data.get("pkus", {}))]
    for pku, item in coordinator.data.get("pkus", {}).items():
        for part, details in item.get("parts", {}).items():
            entities.append(TechlanPartSensor(coordinator, entry, pku, int(part), details))
    async_add_entities(entities)


class TechlanPkuSensor(CoordinatorEntity[TechlanDataUpdateCoordinator], SensorEntity):
    """One compact sensor per PKU; details are exposed as attributes."""

    _attr_icon = "mdi:shield-home-outline"

    def __init__(self, coordinator: TechlanDataUpdateCoordinator, entry: ConfigEntry, pku: int) -> None:
        super().__init__(coordinator)
        self._pku = pku
        self._attr_unique_id = f"{DOMAIN}_pku_{pku}"
        self._attr_name = f"Скиф ПКУ {pku}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"pku_{pku}")},
            "name": f"Скиф ПКУ {pku}",
            "manufacturer": "Techlan",
            "model": "ServerSkif PKU",
            "via_device": (DOMAIN, "arm_ops"),
        }

    @property
    def native_value(self) -> str:
        return "online" if self.coordinator.last_update_success else "offline"

    @property
    def extra_state_attributes(self) -> dict:
        item = self.coordinator.data.get("pkus", {}).get(self._pku, {})
        return {"pku": self._pku, "part_count": item.get("part_count", 0), "parts": item.get("parts", {})}


class TechlanPartSensor(CoordinatorEntity[TechlanDataUpdateCoordinator], SensorEntity):
    """State entity for one ARM security/fire section."""

    def __init__(self, coordinator: TechlanDataUpdateCoordinator, entry: ConfigEntry, pku: int, part: int, details: dict) -> None:
        super().__init__(coordinator)
        self._pku = pku
        self._part = part
        self._description = str(details.get("description") or "").strip()
        self._attr_unique_id = f"{DOMAIN}_pku_{pku}_part_{part}"
        self._attr_name = self._name()
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"pku_{pku}")},
            "name": f"Скиф ПКУ {pku}",
            "manufacturer": "Techlan",
            "model": "ServerSkif PKU",
            "via_device": (DOMAIN, "arm_ops"),
        }

    def _name(self) -> str:
        return self._description or "Без названия"

    def _details(self) -> dict:
        return self.coordinator.data.get("pkus", {}).get(self._pku, {}).get("parts", {}).get(self._part, {})

    @property
    def native_value(self) -> str:
        code = int(self._details().get("state_code", -1))
        return STATE_NAMES.get(code, "Тревога" if code in ALARM_STATE_CODES else f"Состояние {code}")

    @property
    def icon(self) -> str:
        details = self._details()
        code = int(details.get("state_code", -1))
        text = f"{self._description} {STATE_NAMES.get(code, '')}".lower()
        if code in ALARM_STATE_CODES:
            if any(word in text for word in ("пожар", "дым", "температур", "затоп")):
                return "mdi:shield-fire-outline"
            return "mdi:shield-alert-outline"
        if code in {109, 119} or "снят" in text:
            return "mdi:shield-off-outline"
        return "mdi:shield-check-outline"

    @property
    def extra_state_attributes(self) -> dict:
        details = self._details()
        return {
            "pku": self._pku,
            "part": self._part,
            "description": self._description,
            "state_code": details.get("state_code"),
        }


class TechlanLoopSensor(CoordinatorEntity[TechlanDataUpdateCoordinator], SensorEntity):
    """State sensor for a configured ServerSkif loop (ШС)."""

    def __init__(self, coordinator: TechlanDataUpdateCoordinator, entry: ConfigEntry, pku: int, part: int, sh: int, details: dict) -> None:
        super().__init__(coordinator)
        self._pku, self._part, self._sh = pku, part, sh
        self._description = str(details.get("description") or "").strip()
        self._attr_unique_id = f"{DOMAIN}_pku_{pku}_part_{part}_sh_{sh}"
        self._attr_name = self._description or f"ШС {sh >> 8}/{sh & 0xFF}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"pku_{pku}")},
            "name": f"Скиф ПКУ {pku}",
            "manufacturer": "Techlan",
            "model": "ServerSkif PKU",
            "via_device": (DOMAIN, "arm_ops"),
        }

    def _details(self) -> dict:
        return self.coordinator.data.get("pkus", {}).get(self._pku, {}).get("parts", {}).get(self._part, {}).get("loops", {}).get(self._sh, {})

    @property
    def native_value(self) -> str:
        code = int(self._details().get("state_code", -1))
        return STATE_NAMES.get(code, "Тревога" if code in ALARM_STATE_CODES else f"Состояние {code}")

    @property
    def icon(self) -> str:
        code = int(self._details().get("state_code", -1))
        if code in ALARM_STATE_CODES:
            return "mdi:alarm-light-outline"
        if code in {36, 119}:
            return "mdi:alert-outline"
        return "mdi:transit-connection-variant"

    @property
    def extra_state_attributes(self) -> dict:
        return {"pku": self._pku, "part": self._part, "sh": self._sh, "sh_number": f"{self._sh >> 8}/{self._sh & 0xFF}", "description": self._description, "state_code": self._details().get("state_code")}
