"""Sensor platform for Jacuzzi Spa."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import JacuzziSpaCoordinator
from .entity import JacuzziSpaEntity

HEAT_STATE_MAP = {
    0: "idle",
    1: "heating",
    2: "heat_waiting",
}


@dataclass(frozen=True, kw_only=True)
class JacuzziSensorEntityDescription(SensorEntityDescription):
    """Describes a Jacuzzi sensor."""

    value_fn: Callable[[dict], StateType]


def _temp_unit(data: dict) -> str:
    if data.get("tempscale") == 1:
        return UnitOfTemperature.CELSIUS
    return UnitOfTemperature.FAHRENHEIT


SENSORS: tuple[JacuzziSensorEntityDescription, ...] = (
    JacuzziSensorEntityDescription(
        key="curtemp",
        name="Current temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("curtemp"),
    ),
    JacuzziSensorEntityDescription(
        key="settemp",
        name="Setpoint temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("settemp"),
    ),
    JacuzziSensorEntityDescription(
        key="connection_state",
        name="Connection state",
        value_fn=lambda d: d.get("connection_state"),
    ),
    JacuzziSensorEntityDescription(
        key="heatstate",
        name="Heat state",
        value_fn=lambda d: HEAT_STATE_MAP.get(d.get("heatstate"), str(d.get("heatstate"))),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jacuzzi Spa sensors."""
    coordinator: JacuzziSpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        JacuzziSpaSensor(coordinator, description) for description in SENSORS
    )


class JacuzziSpaSensor(JacuzziSpaEntity, SensorEntity):
    """A Jacuzzi spa sensor."""

    entity_description: JacuzziSensorEntityDescription

    def __init__(
        self,
        coordinator: JacuzziSpaCoordinator,
        description: JacuzziSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        data = self.coordinator.data or {}
        return self.entity_description.value_fn(data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.device_class == SensorDeviceClass.TEMPERATURE:
            return _temp_unit(self.coordinator.data or {})
        return self.entity_description.native_unit_of_measurement

    @property
    def available(self) -> bool:
        # Connection sensor stays available so you can see disconnects.
        if self.entity_description.key == "connection_state":
            return True
        return bool((self.coordinator.data or {}).get("connected"))
