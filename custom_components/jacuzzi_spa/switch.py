"""Switch platform for Jacuzzi Spa pumps and lights."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JacuzziSpaCoordinator
from .entity import JacuzziSpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jacuzzi Spa switches."""
    coordinator: JacuzziSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JacuzziPumpSwitch(coordinator, pump=1, name="Pump 1", key="pump1"),
            JacuzziPumpSwitch(coordinator, pump=2, name="Pump 2", key="pump2"),
            JacuzziLightSwitch(coordinator),
        ]
    )


class JacuzziPumpSwitch(JacuzziSpaEntity, SwitchEntity):
    """Switch for a spa jet pump."""

    def __init__(
        self,
        coordinator: JacuzziSpaCoordinator,
        *,
        pump: int,
        name: str,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._pump = pump
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"

    @property
    def is_on(self) -> bool:
        return bool((self.coordinator.data or {}).get(self._key, 0))

    @property
    def available(self) -> bool:
        return bool((self.coordinator.data or {}).get("connected"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_pump(self._pump, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_pump(self._pump, False)


class JacuzziLightSwitch(JacuzziSpaEntity, SwitchEntity):
    """Switch for spa lights (on = color cycle / off)."""

    _attr_name = "Lights"

    def __init__(self, coordinator: JacuzziSpaCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_lights"

    @property
    def is_on(self) -> bool:
        return bool((self.coordinator.data or {}).get("light_on"))

    @property
    def available(self) -> bool:
        return bool((self.coordinator.data or {}).get("connected"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_light(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_light(False)
