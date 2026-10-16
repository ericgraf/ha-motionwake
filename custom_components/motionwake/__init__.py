"""The MotionWake integration for Home Assistant.

Controls a sideloaded Fire-tablet app that idle-sleeps the screen and wakes
it on camera motion, over the app's local HTTP API.

Entity surface per tablet:
  switch  monitor (start/stop)
  button  wake / sleep / reload / restart / OTA update (if configured)
  number  threshold, check_seconds, idle_minutes   (applied live)
  text    dashboard_url                             (applied live + opens)
  sensor  screen_state, last_motion, idle_seconds, version,
          auto_start, adb_tcp, update_state

Service:
  motionwake.set_settings — batch-apply settings for one or more tablets
"""

from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv, service
from homeassistant.helpers.update_coordinator import UpdateFailed

from .client import MotionWakeClient, MotionWakeError
from .const import CONF_ENTRY_ID, CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN
from .coordinator import MotionWakeCoordinator

_LOGGER = logging.getLogger(__package__)

PLATFORMS = [
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.TEXT,
]

CONF_THRESHOLD = "threshold"
CONF_CHECK_SECONDS = "check_seconds"
CONF_IDLE_MINUTES = "idle_minutes"
CONF_DASHBOARD_URL = "dashboard_url"

SET_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTRY_ID): cv.string,
        vol.Optional(CONF_THRESHOLD): vol.Coerce(float),
        vol.Optional(CONF_CHECK_SECONDS): vol.Coerce(int),
        vol.Optional(CONF_IDLE_MINUTES): vol.Coerce(int),
        vol.Optional(CONF_DASHBOARD_URL): cv.string,
    }
)


def _get_client(hass: HomeAssistant, entry_id: str):
    coords = hass.data.get(DOMAIN, {})
    coord: MotionWakeCoordinator | None = coords.get(entry_id)
    if coord is None:
        raise ServiceValidationError(
            f"Unknown {DOMAIN} entry: {entry_id} "
            f"(known: {', '.join(coords) or 'none'})"
        )
    return coord


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

    # Global service (registered once per setup; idempotent replacement).
    async def _set_settings(call: ServiceCall) -> None:
        coord = _get_client(hass, call.data[CONF_ENTRY_ID])
        payload = {
            k: call.data.get(k)
            for k in (CONF_THRESHOLD, CONF_CHECK_SECONDS, CONF_IDLE_MINUTES)
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        try:
            if payload:
                await coord.client.set_settings(payload)
            if call.data.get(CONF_DASHBOARD_URL):
                await coord.client.set_browser(str(call.data[CONF_DASHBOARD_URL]))
        except MotionWakeError as err:
            raise ServiceValidationError(str(err)) from err
        try:
            await coord.async_refresh()
        except UpdateFailed:
            pass

    service.async_register_admin_service(
        hass, DOMAIN, "set_settings", _set_settings, SET_SETTINGS_SCHEMA
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(session.close)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    coords = hass.data.get(DOMAIN, {})
    if entry.entry_id in coords and len(coords) <= 1:
        hass.services.async_remove(DOMAIN, "set_settings")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle migration of old config entries (v1 is current)."""
    _LOGGER.debug("Migration to version %s is a no-op for v1", entry.version)
    return True
