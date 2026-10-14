"""Status sensors: screen state and last-motion age."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MotionWakeEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensor entities."""
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScreenStateSensor(coord, entry), LastMotionSensor(coord, entry)])


class ScreenStateSensor(MotionWakeEntity, SensorEntity):
    """awake / dreaming / asleep — the tablet's display state."""

    _attr_name = "Screen state"
    _attr_translation_key = "screen_state"

    @property
    def state(self) -> str | None:
        data = self.coordinator.data or {}
        return str(data.get("screen_state"))


class LastMotionSensor(MotionWakeEntity, SensorEntity):
    """Seconds since the camera last saw motion."""

    _attr_name = "Last motion (s)"
    _attr_translation_key = "last_motion"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        raw = data.get("last_motion_age_ms")
        if raw is None:
            return None
        try:
            return round(float(raw) / 1000.0, 1)
        except (TypeError, ValueError):
            return None
