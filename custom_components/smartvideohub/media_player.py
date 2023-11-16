"""
Support for interfacing with Black Magic Smart Video Hub.
"""
from __future__ import annotations

import logging
import asyncio

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerDeviceClass,
    PLATFORM_SCHEMA,
    ENTITY_ID_FORMAT,
)
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

DATA_SMARTVIDEOHUB = "smartvideohub"

CONF_HIDE_DEFAULT_INPUTS = "hide_default_inputs"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_HIDE_DEFAULT_INPUTS, default=False): cv.boolean,
    }
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Monoprice 6-zone amplifier platform."""
    port = config.get(CONF_PORT)
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    hide_default_inputs = config.get(CONF_HIDE_DEFAULT_INPUTS)

    smartvideohub = None
    from .pyvideohub import SmartVideoHub

    _LOGGER.info("Establishing connection with SmartVideoHub at %s:%i", host, port)
    if not smartvideohub:
        smartvideohub = SmartVideoHub(host, port, hass.loop)
        smartvideohub.start()

    _LOGGER.info("Adding %i outputs", len(smartvideohub.get_outputs()))

    while not smartvideohub.is_initialised:
        _LOGGER.info("Waiting for connection to Videohub")
        await asyncio.sleep(2)

    _LOGGER.debug(repr(smartvideohub.get_outputs()))
    async_add_entities(
        [
            SmartVideoHubOutput(
                hass,
                smartvideohub,
                name,
                output_number,
                output,
                hide_default_inputs=hide_default_inputs,
            )
            for output_number, output in smartvideohub.get_outputs().items()
        ],
        True,
    )


class SmartVideoHubOutput(MediaPlayerEntity):
    """Representation of a a Monoprice amplifier zone."""

    # pylint: disable=too-many-public-methods
    _attr_supported_features = MediaPlayerEntityFeature.SELECT_SOURCE
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER

    def __init__(
        self,
        hass,
        smartvideohub,
        entity_prefix,
        output_number,
        output,
        hide_default_inputs=False,
    ):
        """Initialize new zone."""
        _LOGGER.info("Adding SmartVideoHub output %i", output_number)
        self._smartvideohub = smartvideohub
        self._output_id = output_number
        self._output_name = output["name"]
        self._attr_source_source_name = smartvideohub.get_input_name(output_number)
        self._source_id = output["input"]
        self._connected = smartvideohub.connected
        self._hide_default_inputs = hide_default_inputs
        self._attr_source_list = smartvideohub.get_input_list(self._hide_default_inputs)
        self._attr_unique_id = f"smartvideohub_output_{self._output_id}"
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            entity_prefix + " output " + str(self._output_id),
            hass=hass,
        )
        smartvideohub.add_update_callback(self.update_callback)

    def update(self):
        """Retrieve latest state."""
        self._output_name = self._smartvideohub.get_outputs()[self._output_id]["name"]
        self._source_id = self._smartvideohub.get_selected_input(self._output_id)
        self._attr_source = self._smartvideohub.get_input_name(self._source_id)
        self._attr_source_list = self._smartvideohub.get_input_list(
            self._hide_default_inputs
        )

    @property
    def name(self):
        """Return the name of the zone."""
        return self._output_name

    @property
    def state(self):
        """Return the state of the zone."""
        if self._connected:
            return "playing"
        else:
            return "off"

    @property
    def media_title(self) -> str | None:
        """Title of current playing media."""
        return self._attr_source

    def select_source(self, source):
        """Set input source."""
        return self._smartvideohub.set_input_by_name(self._output_id, source)

    def update_callback(self, output_id=0):
        """Called when data is received by pySmartVideoHub"""
        if output_id == 0 | output_id == self._output_id:
            _LOGGER.info("SmartVideoHub sent a status update for output %i", output_id)
            self.update()
            self.schedule_update_ha_state(False)
