"""Motion monitoring on/off switch (maps to the app's start/stop)."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import MotionWakeError
from .const import DOMAIN
from .entity import MotionWakeEntity

_LOGGER = logging.getLogger(__package__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the MotionWake entities for this config entry."""
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MotionWakeSwitch(coord, entry)])


class MotionWakeSwitch(MotionWakeEntity, SwitchEntity):
    """Turn the motion monitor (idle-sleep + motion-wake) on and off.

    ON  -> monitoring active (sleeps the screen after the idle limit,
          wakes it on camera motion).
    OFF -> monitoring paused (screen left alone, no wake on motion).
    """

    _attr_name = "Motion monitoring"
    _attr_translation_key = "monitor"

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_monitor"
        self._client = coord.client

    @property
    def available(self) -> bool:
        """Availability = coordinator has data AND monitor reachable."""
        data = self.coordinator.data
        return bool(data) and data.get("running") is not None

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return bool(data.get("running"))

    async def async_turn_on(self, **kwargs) -> None:
        """Start monitoring."""
        try:
            await self._client.start()
        except MotionWakeError as err:
            raise HomeAssistantError(f"MotionWake start failed: {err}") from err
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Stop monitoring."""
        try:
            await self._client.stop()
        except MotionWakeError as err:
            raise HomeAssistantError(f"MotionWake stop failed: {err}") from err
        await self.coordinator.async_refresh()
