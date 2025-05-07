"""
Support for interfacing with Black Magic Smart Video Hub.
"""
from __future__ import annotations

import logging
import asyncio

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerState,
    MediaPlayerEntityFeature,
    MediaPlayerDeviceClass,
    ENTITY_ID_FORMAT,
)
from homeassistant.helpers.entity import async_generate_entity_id, DeviceInfo


from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up SmartVideoHub Device"""
    dev = hass.data[DOMAIN][config_entry.entry_id]['client']

    deviceInfo = DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name= dev.name,
        manufacturer="BlackMagic Design",
        model=dev.model
    )
    if dev.model == MODEL_VIDEOHUB:
        _LOGGER.info("Adding %i outputs", len(dev.get_outputs()))
        async_add_entities(
            [
                SmartVideoHubOutput(
                    hass,
                    dev,
                    dev.attrs.get("Unique ID"),
                    output_number,
                    output,
                    deviceInfo,
                    hide_default_inputs=config_entry.data.get(CONF_HIDE_DEFAULT_INPUTS, False),
                )
                for output_number, output in dev.get_outputs().items()
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
        deviceInfo,
        hide_default_inputs=False,
    ):
        """Initialize new zone."""
        _LOGGER.info("Adding SmartVideoHub output %i", output_number)
        self._smartvideohub = smartvideohub
        self._output_id = output_number
        self._output_name = output.get("name", "Output %d" % output_number)
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
        self._attr_device_info = deviceInfo
        smartvideohub.add_update_callback(self.update_callback)

    def update(self):
        """Retrieve latest state."""
        self._output_name = self._smartvideohub.get_outputs()[self._output_id].get("name")
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
