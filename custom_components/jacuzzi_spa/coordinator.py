"""Data update coordinator for Jacuzzi Spa."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL_SECONDS
from .lib import ConnectionStates, JacuzziSpaWifi

_LOGGER = logging.getLogger(__name__)


class JacuzziSpaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Owns the spa TCP client and exposes a snapshot for entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.host: str = entry.data[CONF_HOST]
        self.port: int = entry.data[CONF_PORT]
        self.spa = JacuzziSpaWifi(self.host, self.port)
        self.spa.log = _LOGGER
        self._listen_task: asyncio.Task | None = None
        self._connection_task: asyncio.Task | None = None

    async def async_start(self) -> None:
        """Connect and start background listen / reconnect loops."""
        await self.spa.connect()
        if not self.spa.connected:
            raise UpdateFailed(f"Could not connect to spa at {self.host}:{self.port}")

        self._listen_task = self.hass.async_create_background_task(
            self.spa.listen(),
            name=f"{DOMAIN}_listen",
        )
        self._connection_task = self.hass.async_create_background_task(
            self.spa.check_connection_status(),
            name=f"{DOMAIN}_connection",
        )
        # Allow a few status frames before first entity update.
        for _ in range(25):
            if self.spa.settemp not in (None, 0.0):
                break
            await asyncio.sleep(0.2)
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Stop background tasks and disconnect."""
        for task in (self._listen_task, self._connection_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._listen_task = None
        self._connection_task = None
        try:
            await self.spa.disconnect()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Error during spa disconnect", exc_info=True)

    def _snapshot(self) -> dict[str, Any]:
        spa = self.spa
        light_on = bool(spa.light_status[0]) if spa.light_status else False
        pump1 = int(spa.pump_status[1]) if len(spa.pump_status) > 1 else 0
        pump2 = int(spa.pump_status[2]) if len(spa.pump_status) > 2 else 0
        connected = bool(spa.connected) and spa.connection_state == ConnectionStates.Connected
        return {
            "connected": connected,
            "connection_state": spa.connection_state.name
            if spa.connection_state is not None
            else "Unknown",
            "curtemp": spa.curtemp,
            "settemp": spa.settemp,
            "tempscale": spa.tempscale,
            "heatstate": spa.heatstate,
            "heatmode": spa.heatmode,
            "pump1": pump1,
            "pump2": pump2,
            "light_on": light_on,
            "light_mode": spa.lightMode,
            "light_brightness": spa.lightBrightness,
            "encrypted": bool(spa.encrypted_comm),
        }

    async def _async_update_data(self) -> dict[str, Any]:
        if not self.spa.connected:
            # check_connection_status() will reconnect in the background.
            raise UpdateFailed("Spa not connected")
        return self._snapshot()

    async def async_set_temperature(self, temperature: float) -> None:
        """Set spa target temperature."""
        await self.spa.send_temp_change(temperature)
        # Encrypted controllers adjust asynchronously via button presses.
        task = self.spa.encrypted_settemp_task
        if task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=45)
            except asyncio.TimeoutError:
                _LOGGER.warning("Timed out waiting for temperature adjust task")
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Temperature adjust task ended with error", exc_info=True)
        await self.async_request_refresh()

    async def async_set_pump(self, pump: int, on: bool) -> None:
        """Turn a pump on (low/first speed) or off."""
        target = 1 if on else 0
        await self.spa.change_pump(pump, target)
        await self.async_request_refresh()

    async def async_set_light(self, on: bool) -> None:
        """Turn lights on or off by toggling until desired state."""
        # Encrypted boards toggle off <-> color-cycle via Light 1 button.
        for _ in range(6):
            current = bool(self.spa.light_status[0]) if self.spa.light_status else False
            if current == on:
                break
            await self.spa.change_light(0)
            await asyncio.sleep(0.3)
        await self.async_request_refresh()
