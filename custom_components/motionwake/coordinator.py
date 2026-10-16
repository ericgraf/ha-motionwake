"""DataUpdateCoordinator fetching state from the MotionWake tablet.

Merges /status (authoritative) with /settings, /browser and
/update/status so entities can read a single flat dict. The extra
endpoints are best-effort: if one fails, the rest still refresh.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import MotionWakeClient, MotionWakeError
from .const import SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__package__)


class MotionWakeCoordinator(DataUpdateCoordinator[dict]):
    """Polls the MotionWake tablet's state endpoints."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MotionWakeClient,
        config_entry=None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="motionwake_status",
            config_entry=config_entry,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            data = await self.client.get_status()
        except MotionWakeError as err:
            raise UpdateFailed(f"MotionWake status unavailable: {err}") from err
        # Best-effort additions (a failure here keeps the core state fresh).
        try:
            data.update(await self.client.get_settings())
        except MotionWakeError:
            pass
        try:
            data["browser"] = await self.client.get_browser()
        except MotionWakeError:
            pass
        try:
            data["update"] = await self.client.get_update_status()
        except MotionWakeError:
            pass
        return data
