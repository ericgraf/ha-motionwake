"""Status sensors: screen state, motion age, app version, OTA state, etc."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
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
    async_add_entities(
        [
            ScreenStateSensor(coord, entry),
            LastMotionSensor(coord, entry),
            IdleSecondsSensor(coord, entry),
            VersionSensor(coord, entry),
            AutoStartSensor(coord, entry),
            AdbTcpSensor(coord, entry),
            UpdateStateSensor(coord, entry),
        ]
    )


class _SimpleSensor(MotionWakeEntity, SensorEntity):
    """Base for flat key/value sensors off the merged coordinator data."""

    def __init__(self, coord, entry, key: str, name: str, icon: str) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"sensor_{key}"
        self._key = key
        self._attr_name = name
        self._attr_icon = icon

    @property
    def state(self) -> str | None:
        data = self.coordinator.data or {}
        value = data.get(self._key)
        if value is None or value == "":
            return None
        return str(value)


class ScreenStateSensor(MotionWakeEntity, SensorEntity):
    """awake / dreaming / asleep — the tablet's display state."""

    _attr_name = "Screen state"
    _attr_translation_key = "screen_state"

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_screen_state"

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

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_last_motion"

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


class IdleSecondsSensor(MotionWakeEntity, SensorEntity):
    """Seconds the screen has been idle (counts up to the idle limit)."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "idle_seconds"
    _attr_name = "Idle time (s)"

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_idle_seconds"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        raw = data.get("idle_ms")
        if raw is None:
            return None
        try:
            return round(float(raw) / 1000.0, 1)
        except (TypeError, ValueError):
            return None


class VersionSensor(MotionWakeEntity, SensorEntity):
    """MotionWake app version on the tablet."""

    _attr_translation_key = "version"
    _attr_name = "App version"
    _attr_icon = "mdi:tag"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_version"

    @property
    def state(self) -> str | None:
        data = self.coordinator.data or {}
        return str(data.get("version"))


class AutoStartSensor(MotionWakeEntity, SensorEntity):
    """Whether the monitor auto-starts at boot (state: on / off).

    The app currently reports this but only accepts the other settings
    writes; it will become a real switch once the app exposes it.
    """

    _attr_translation_key = "auto_start"
    _attr_name = "Auto start"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_auto_start"

    @property
    def state(self) -> str | None:
        data = self.coordinator.data or {}
        return "on" if data.get("auto_start") else "off"


class AdbTcpSensor(MotionWakeEntity, SensorEntity):
    """LAN ADB transport port (service.adb.tcp.port) — empty means the
    host must re-run `adb tcpip 5555` over USB after a reboot."""

    _attr_translation_key = "adb_tcp"
    _attr_name = "ADB TCP"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_adb_tcp"

    @property
    def state(self) -> str | None:
        data = self.coordinator.data or {}
        value = data.get("adb_tcp")
        return str(value) if value else None


class UpdateStateSensor(MotionWakeEntity, SensorEntity):
    """OTA self-update state: none (never) | pending (installing) | applied."""

    _attr_translation_key = "update_state"
    _attr_name = "Update state"
    _attr_icon = "mdi:package-up"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_update_state"

    @property
    def state(self) -> str | None:
        data = self.coordinator.data or {}
        update = data.get("update") or {}
        return str(update.get("state"))


# _SimpleSensor is reserved for future flat sensors; keep the alias so
# subclasses can reference it without import surprises.
SimpleSensor = _SimpleSensor
