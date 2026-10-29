"""Config flow for Jacuzzi Spa."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_HOST, DEFAULT_PORT, DOMAIN
from .lib import JacuzziSpaWifi

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
    }
)


async def validate_input(data: dict[str, Any]) -> dict[str, Any]:
    """Validate host/port by opening a short TCP connection to the spa bridge."""
    spa = JacuzziSpaWifi(data[CONF_HOST], data[CONF_PORT])
    try:
        ok = await asyncio.wait_for(spa.connect(), timeout=8)
    except Exception as err:
        _LOGGER.debug("Connection validation failed: %s", err)
        raise ConnectionError from err

    if not ok or not spa.connected:
        raise ConnectionError("Spa bridge did not accept the connection")

    title = f"Jacuzzi Spa ({data[CONF_HOST]})"
    try:
        await spa.disconnect()
    except Exception:  # noqa: BLE001
        pass
    return {"title": title}


class JacuzziSpaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jacuzzi Spa."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(user_input)
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during config validation")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
