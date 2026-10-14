"""Action buttons: wake, sleep, and reload the dashboard."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import MotionWakeError
from .const import DOMAIN
from .entity import MotionWakeEntity

_LOGGER = logging.getLogger(__package__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up button entities."""
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MotionWakeButton(
                coord, "wake", "Wake display", "mdi:power", lambda c: c.wake()
            ),
            MotionWakeButton(
                coord, "sleep", "Sleep display", "mdi:moon", lambda c: c.sleep()
            ),
            MotionWakeButton(
                coord,
                "reload",
                "Reload dashboard",
                "mdi:web-refresh",
                lambda c: c.reload_dashboard(),
            ),
        ]
    )


class MotionWakeButton(MotionWakeEntity, ButtonEntity):
    """A one-shot action button that talks to the tablet."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coord, key: str, name: str, icon: str, action) -> None:
        super().__init__(coord)
        self._client = coord.client
        self._attr_translation_key = key
        self._attr_name = name
        self._attr_icon = icon
        self._action = action

    async def async_press(self) -> None:
        """Fire the action."""
        try:
            await self._action(self._client)
        except MotionWakeError as err:
            raise HomeAssistantError(f"MotionWake action failed: {err}") from err
        await self.coordinator.async_refresh()
