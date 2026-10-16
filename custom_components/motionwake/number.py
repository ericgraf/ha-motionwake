"""Configurable number entities: threshold, check interval, idle limit.

All three are applied live by the app (POST /settings triggers its
SharedPreferences listener, which updates the camera immediately).
"""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import UpdateFailed

from .client import MotionWakeError
from .const import DOMAIN
from .entity import MotionWakeEntity

_LOGGER = logging.getLogger(__package__)

PARALLEL_UPDATES = 1

#: (key, min, max, step, int-valued, icon)
_NUMBER_DEFS = [
    ("threshold", 0.5, 15.0, 0.1, False, "mdi:target-account"),
    ("check_seconds", 2, 30, 1, True, "mdi:timer-sync"),
    ("idle_minutes", 1, 1440, 1, True, "mdi:alarm-sleep"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the MotionWake number entities."""
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MotionWakeNumber(coord, entry, key, mn, mx, step, is_int, icon)
        for key, mn, mx, step, is_int, icon in _NUMBER_DEFS
    )


class MotionWakeNumber(MotionWakeEntity, NumberEntity):
    """A MotionWake setting, exposed as a native number entity."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coord,
        entry,
        key: str,
        min_v: float,
        max_v: float,
        step: float,
        is_int: bool,
        icon: str,
    ) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_num_{key}"
        self._attr_translation_key = key
        self._attr_name = key.replace("_", " ").title()
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = (
            "s" if key == "check_seconds" else "min" if key == "idle_minutes" else None
        )
        self._key = key
        self._is_int = is_int
        self._client = coord.client

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        raw = data.get(self._key)
        if raw is None:
            return None
        try:
            return int(raw) if self._is_int else float(raw)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Apply the new setting to the tablet (live)."""
        payload = {self._key: int(value) if self._is_int else float(value)}
        try:
            await self._client.set_settings(payload)
        except MotionWakeError as err:
            raise HomeAssistantError(f"MotionWake setting failed: {err}") from err
        try:
            await self.coordinator.async_refresh()
        except UpdateFailed:
            pass
