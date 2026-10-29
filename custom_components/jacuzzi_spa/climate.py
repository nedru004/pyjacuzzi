"""Climate platform for Jacuzzi Spa."""

from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
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
    """Set up Jacuzzi Spa climate entity."""
    coordinator: JacuzziSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JacuzziSpaClimate(coordinator)])


class JacuzziSpaClimate(JacuzziSpaEntity, ClimateEntity):
    """Spa temperature climate entity."""

    _attr_name = "Temperature"
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT

    def __init__(self, coordinator: JacuzziSpaCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_climate"

    @property
    def temperature_unit(self) -> str:
        data = self.coordinator.data or {}
        if data.get("tempscale") == 1:
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    @property
    def min_temp(self) -> float:
        return 80.0 if self.temperature_unit == UnitOfTemperature.FAHRENHEIT else 26.0

    @property
    def max_temp(self) -> float:
        return 104.0 if self.temperature_unit == UnitOfTemperature.FAHRENHEIT else 40.0

    @property
    def current_temperature(self) -> float | None:
        temp = (self.coordinator.data or {}).get("curtemp")
        return float(temp) if temp not in (None, 0) else None

    @property
    def target_temperature(self) -> float | None:
        temp = (self.coordinator.data or {}).get("settemp")
        return float(temp) if temp not in (None, 0) else None

    @property
    def hvac_action(self) -> HVACAction | None:
        heatstate = (self.coordinator.data or {}).get("heatstate")
        if heatstate:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def available(self) -> bool:
        return bool((self.coordinator.data or {}).get("connected"))

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.async_set_temperature(float(temperature))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """HVAC mode is always heat for this spa."""
        return
