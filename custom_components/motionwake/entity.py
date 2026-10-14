"""Shared base entity for MotionWake."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MotionWakeCoordinator


class MotionWakeEntity(CoordinatorEntity[MotionWakeCoordinator]):
    """Common base: coordinator plumbing + device metadata."""

    _attr_has_entity_name = True

    def __init__(self, coord: MotionWakeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coord)
        self.config_entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Identify the MotionWake tablet as a single device."""
        entry = self.config_entry
        unique_id = entry.unique_id or "motionwake"
        host = entry.data.get("host", "tablet")
        return DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=f"MotionWake {host}",
            manufacturer="Amazon",
            model="Fire tablet (MotionWake)",
        )
