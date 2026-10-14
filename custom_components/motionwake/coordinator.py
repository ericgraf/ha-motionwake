"""DataUpdateCoordinator fetching /status from the MotionWake tablet."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import MotionWakeClient, MotionWakeError
from .const import SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__package__)


class MotionWakeCoordinator(DataUpdateCoordinator[dict]):
    """Polls GET /status on the tablet."""

    config_entry = None

    def __init__(self, hass: HomeAssistant, client: MotionWakeClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="motionwake_status",
            update_interval=SCAN_INTERVAL_SECONDS,
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.get_status()
        except MotionWakeError as err:
            raise UpdateFailed(f"MotionWake status unavailable: {err}") from err
