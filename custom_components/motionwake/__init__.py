"""The MotionWake integration for Home Assistant.

Controls a sideloaded Fire-tablet app that idle-sleeps the screen and wakes
it on camera motion, over the app's local HTTP API.
"""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .client import MotionWakeClient, MotionWakeError
from .const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN
from .coordinator import MotionWakeCoordinator

_LOGGER = logging.getLogger(__package__)

PLATFORMS = [Platform.SWITCH, Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MotionWake from a config entry."""
    host = entry.data[CONF_HOST]
    port = int(entry.data[CONF_PORT])
    token = entry.data[CONF_TOKEN]

    session = aiohttp.ClientSession()
    client = MotionWakeClient(session, host, port, token)
    coordinator = MotionWakeCoordinator(hass, client, entry)

    try:
        await coordinator.async_refresh()
    except MotionWakeError as err:
        session.close()
        raise ConfigEntryNotReady(f"MotionWake unavailable: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(session.close)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle migration of old config entries (v1 is current)."""
    _LOGGER.debug("Migration to version %s is a no-op for v1", entry.version)
    return True
