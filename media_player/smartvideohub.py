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

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): cv.port,
    vol.Required(CONF_NAME): cv.string,
})

_LOGGER = logging.getLogger(__name__)



# pylint: disable=unused-argument
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Monoprice 6-zone amplifier platform."""
    port = config.get(CONF_PORT)
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)

    smartvideohub = None
    from custom_components.pyvideohub import SmartVideoHub

    _LOGGER.info('Establishing connection with SmartVideoHub at %s:%i',host,port)
    if not smartvideohub:
        smartvideohub = SmartVideoHub(host, port, hass.loop)
        smartvideohub.start()

    _LOGGER.info('Adding %i outputs',len(smartvideohub.get_outputs()))

    while not smartvideohub.is_initialised:
        yield from asyncio.sleep(2,hass.loop)

    _LOGGER.debug(repr(smartvideohub.get_outputs()))
    async_add_devices([SmartVideoHubOutput(hass, smartvideohub, name, output_number, output)
                 for output_number, output in smartvideohub.get_outputs().items()])

    return True


class SmartVideoHubOutput(MediaPlayerDevice):
    """Representation of a a Monoprice amplifier zone."""

    # pylint: disable=too-many-public-methods

    def __init__(self, hass, smartvideohub, entity_prefix, output_number, output):
        _LOGGER.info('Adding SmartVideoHub output %i',output_number)
        """Initialize new zone."""
        self._smartvideohub = smartvideohub
        self._output_id = output_number
        self._output_name = output['name']
        self._source_name = smartvideohub.get_input_name(output_number)
        self._source_id = output['input']
        self._connected = smartvideohub.connected
        self._source_list = smartvideohub.get_input_list()
        self._state = None
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, entity_prefix + ' output ' + str(self._output_id), hass=hass
        )
        smartvideohub.add_update_callback(self.update_callback)

    def update(self):
        """Retrieve latest state."""
        self._connected = self._smartvideohub.connected
        if self._connected:
            self._output_name = self._smartvideohub.get_outputs()[self._output_id]['name']
            self._source_id = self._smartvideohub.get_selected_input(self._output_id)
            self._source_name = self._smartvideohub.get_input_name(self._source_id)
            self._source_list = self._smartvideohub.get_input_list()


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

    def update_callback(self):
        """Called when data is received by pySmartVideoHub"""
        _LOGGER.info("SmartVideoHub sent a status update.")
        self.update()
        self.schedule_update_ha_state()

    def should_poll(self):
        return False
