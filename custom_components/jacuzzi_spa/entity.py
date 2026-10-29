"""Base entity for Jacuzzi Spa."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JacuzziSpaCoordinator


class JacuzziSpaEntity(CoordinatorEntity[JacuzziSpaCoordinator]):
    """Common device linkage for all Jacuzzi Spa entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JacuzziSpaCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Jacuzzi",
            model="RS485 Spa",
        )
