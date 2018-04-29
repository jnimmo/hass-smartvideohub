"""
Support for interfacing with Black Magic Smart Video Hub.
"""
import logging
import asyncio
from os import path

import voluptuous as vol

from homeassistant.const import (ATTR_ENTITY_ID, CONF_HOST, CONF_PORT,
                                 STATE_OFF, STATE_ON, STATE_UNKNOWN, CONF_NAME)
from homeassistant.config import load_yaml_config_file
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_state_change
from homeassistant.components.media_player import (
    DOMAIN, MediaPlayerDevice, MEDIA_PLAYER_SCHEMA, PLATFORM_SCHEMA,
    SUPPORT_VOLUME_MUTE, SUPPORT_SELECT_SOURCE, SUPPORT_TURN_ON,
    SUPPORT_TURN_OFF, SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP, ENTITY_ID_FORMAT)
from homeassistant.helpers.entity import async_generate_entity_id

DATA_SMARTVIDEOHUB = 'smartvideohub'

CONF_HIDE_DEFAULT_INPUTS = 'hide_default_inputs'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): cv.port,
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_HIDE_DEFAULT_INPUTS, default=False): cv.boolean,
})

_LOGGER = logging.getLogger(__name__)



# pylint: disable=unused-argument
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Monoprice 6-zone amplifier platform."""
    port = config.get(CONF_PORT)
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    hide_default_inputs = config.get(CONF_HIDE_DEFAULT_INPUTS)

    smartvideohub = None
    from custom_components.pyvideohub import SmartVideoHub

    _LOGGER.info('Establishing connection with SmartVideoHub at %s:%i', host, port)
    if not smartvideohub:
        smartvideohub = SmartVideoHub(host, port, hass.loop)
        smartvideohub.connect()

    _LOGGER.info('Adding %i outputs', len(smartvideohub.get_outputs()))

    while not smartvideohub.is_initialised:
        _LOGGER.info('Waiting for connection to Videohub')
        smartvideohub.connect()
        yield from asyncio.sleep(5, hass.loop)

    _LOGGER.debug(repr(smartvideohub.get_outputs()))
    async_add_devices([SmartVideoHubOutput(hass, smartvideohub, name, output_number, output,
                                           hide_default_inputs=hide_default_inputs)
                       for output_number, output in smartvideohub.get_outputs().items()])

    return True


class SmartVideoHubOutput(MediaPlayerDevice):
    """Representation of a a Monoprice amplifier zone."""

    # pylint: disable=too-many-public-methods

    def __init__(self, hass, smartvideohub, entity_prefix, output_number, output,
                 hide_default_inputs=False):
        _LOGGER.info('Adding SmartVideoHub output %i', output_number)
        """Initialize new zone."""
        self._smartvideohub = smartvideohub
        self._output_id = output_number
        self._output_name = output['name']
        self._source_name = smartvideohub.get_input_name(output['input'])
        self._source_id = output['input']
        self._connected = smartvideohub.connected
        self._hide_default_inputs = hide_default_inputs
        self._source_list = smartvideohub.get_input_list(self._hide_default_inputs)
        self._state = None
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_prefix + ' output ' + str(self._output_id), hass=hass
        )
        smartvideohub.add_update_callback(self.update_callback)

    def update(self):
        """Retrieve latest state."""
        if not self._smartvideohub.connected:
            self._smartvideohub.connect()

        self._output_name = self._smartvideohub.get_outputs()[self._output_id]['name']
        self._source_id = self._smartvideohub.get_selected_input(self._output_id)
        self._source_name = self._smartvideohub.get_input_name(self._source_id)
        self._source_list = self._smartvideohub.get_input_list(self._hide_default_inputs)

    @property
    def name(self):
        """Return the name of the zone."""
        return self._output_name

    @property
    def state(self):
        """Return the state of the zone."""
        if self._connected:
            return self._source_name
        else:
            return STATE_UNKNOWN

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_SELECT_SOURCE

    @property
    def source(self):
        """"Return the current input source of the device."""
        return self._source_name

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_list

    def select_source(self, source):
        """Set input source."""
        return self._smartvideohub.set_input_by_name(self._output_id, source)

    def update_callback(self, output_id=0):
        """Called when data is received by pySmartVideoHub"""
        if output_id == 0 | output_id == self._output_id:
            _LOGGER.info("SmartVideoHub sent a status update for output %i", output_id)
            self.update()
            self.schedule_update_ha_state(False)

    def should_poll(self):
        return not self._connected
