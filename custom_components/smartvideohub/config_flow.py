# config_flow.py
from __future__ import annotations

import logging
import asyncio

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_HOST, CONF_PORT, DEFAULT_PORT
from .pyvideohub import SmartVideoHub

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int
})

_LOGGER = logging.getLogger(__name__)

async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    client = SmartVideoHub(
        data[CONF_HOST],
        data[CONF_PORT],
        loop=hass.loop
    )
    await client.connect()

    try:
        await client.initialised.wait()

        return {"title": client.name}

    except Exception as e:
        client.stop()
        _LOGGER.error("Communication Error: %s: %s", e.__class__.__name__, str(e))
        raise ValueError("communication_error") from e


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Huawei UPS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)

            except (ConnectionError, ConnectionRefusedError):
                errors["base"] = "cannot_connect"
            except ValueError as e:
                if str(e) == "communication_error":
                    errors["base"] = "communication_error"
                else:
                    errors["base"] = "unknown"
                    _LOGGER.error("Unexcepted error %s: %s", e.__class__.__name__, e)
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.error("Unexcepted error %s: %s", e.__class__.__name__, e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors
        )
