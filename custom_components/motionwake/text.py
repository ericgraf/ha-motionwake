"""Text entity for the dashboard URL the tablet opens on wake/boot."""

from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity, TextMode
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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the MotionWake text entities."""
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DashboardUrlText(coord, entry)])


class DashboardUrlText(MotionWakeEntity, TextEntity):
    """The HA dashboard (or any URL) the tablet loads on wake/boot.

    Setting the value re-points the tablet and opens the page immediately.
    """

    _attr_translation_key = "dashboard_url"
    _attr_name = "Dashboard URL"
    _attr_icon = "mdi:monitor-dashboard"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_pattern = r"^[a-z][a-z0-9+.-]*://\S+"
    _attr_mode = TextMode.TEXT

    def __init__(self, coord, entry) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_dashboard_url"
        self._client = coord.client

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        browser = data.get("browser") or {}
        url = browser.get("url")
        return url if isinstance(url, str) else None

    async def async_set_value(self, value: str) -> None:
        """Store the new dashboard URL on the tablet."""
        try:
            await self._client.set_browser(value)
        except MotionWakeError as err:
            raise HomeAssistantError(f"MotionWake browser URL failed: {err}") from err
        try:
            await self.coordinator.async_refresh()
        except UpdateFailed:
            pass
