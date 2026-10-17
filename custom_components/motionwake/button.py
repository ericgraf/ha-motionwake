"""Action buttons: wake, sleep, reload, restart, OTA update."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import UpdateFailed

from .client import MotionWakeError
from .const import CONF_UPDATE_SOURCE, DOMAIN
from .entity import MotionWakeEntity

_LOGGER = logging.getLogger(__package__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up button entities."""
    coord = hass.data[DOMAIN][entry.entry_id]
    buttons = [
        MotionWakeButton(
            coord, entry, "wake", "Wake display", "mdi:power", lambda c: c.wake()
        ),
        MotionWakeButton(
            coord, entry, "sleep", "Sleep display", "mdi:moon", lambda c: c.sleep()
        ),
        MotionWakeButton(
            coord,
            entry,
            "reload",
            "Reload dashboard",
            "mdi:web-refresh",
            lambda c: c.reload_dashboard(),
        ),
        MotionWakeButton(
            coord,
            entry,
            "restart",
            "Restart service",
            "mdi:restart",
            lambda c: c.shutdown(),
            post_refresh_wait=(1, 4, 9, 16),
        ),
    ]
    source = (entry.data.get(CONF_UPDATE_SOURCE) or "").strip()
    if source:
        async def _ota(client) -> dict:
            if source.startswith("cmd:"):
                # Host-driven OTA (the proven channel on the Fire builds in
                # this fleet: pm's file-context broker accepts shell-uid
                # streamed installs but rejects app-uid file installs).
                # Runs a shell command inside the HA host, e.g.:
                #   cmd:ssh calvin 'cd /home/egraf/scripts/firetablet-app &&
                #     ./scripts/ota-update.sh C'
                cmd = source[len("cmd:"):].strip()
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                try:
                    out, _ = await asyncio.wait_for(proc.communicate(), timeout=900)
                except asyncio.TimeoutError:
                    proc.kill()
                    raise HomeAssistantError(
                        "OTA command timed out (900 s)"
                    ) from None
                tail = out.decode(errors="replace").strip()
                if proc.returncode != 0:
                    _LOGGER.warning("OTA command rc=%s — %s", proc.returncode, tail[-500:])
                    raise HomeAssistantError(
                        f"OTA command exited {proc.returncode}: {tail[-300:]}"
                    )
                _LOGGER.info("OTA command OK — %s", tail[-300:])
                return {"ok": True, "via": "command"}
            # In-app channel: fetch the APK (http(s) URL or local file) and
            # POST the raw bytes to the tablet's /update endpoint (works on
            # builds where pm's broker is permissive).
            apk = await client.fetch_apk(source)
            return await client.post_update(apk)

        buttons.append(
            MotionWakeButton(
                coord,
                entry,
                "update",
                "Update app (OTA)",
                "mdi:package-up",
                _ota,
                post_refresh_wait=(3, 8, 16, 30),
            )
        )
    async_add_entities(buttons)


class MotionWakeButton(MotionWakeEntity, ButtonEntity):
    """A one-shot action button that talks to the tablet."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coord,
        entry,
        key: str,
        name: str,
        icon: str,
        action,
        post_refresh_wait: tuple[int, ...] = (),
    ) -> None:
        super().__init__(coord, entry)
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._client = coord.client
        self._attr_translation_key = key
        self._attr_name = name
        self._attr_icon = icon
        self._action = action
        self._refresh_waits = post_refresh_wait

    async def async_press(self) -> None:
        """Fire the action, then best-effort re-poll the (possibly rebooting) app."""
        try:
            await self._action(self._client)
        except MotionWakeError as err:
            raise HomeAssistantError(f"MotionWake action failed: {err}") from err
        if not self._refresh_waits:
            await self._safe_refresh()
            return
        # After a restart/OTA the service comes back after a few seconds;
        # retry the refresh until it answers (or give up silently).
        for delay in self._refresh_waits:
            await asyncio.sleep(delay)
            if await self._safe_refresh():
                break

    async def _safe_refresh(self) -> bool:
        """Refresh coordinator state; return True on success."""
        try:
            await self.coordinator.async_refresh()
            return True
        except UpdateFailed:
            return False
        except MotionWakeError:
            return False
