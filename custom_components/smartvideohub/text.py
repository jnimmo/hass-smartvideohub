import logging

from homeassistant.components.text import TextEntity, TextMode, ENTITY_ID_FORMAT
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
    if dev.model == MODEL_STREAMING:
        async_add_entities(
            [
                StreamingInputDevice(
                    hass,
                    dev,
                    "stream_key",
                    deviceInfo
                )
            ],
            True,
        )

class StreamingInputDevice(TextEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hass,
        dev,
        translation_key,
        deviceInfo
    ):
        """Initialize new zone."""
        self._dev = dev
        self._attr_translation_key = translation_key
        self._attr_mode = TextMode.TEXT
        self._attr_unique_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            dev.attrs.get("Unique ID")+"/"+translation_key,
            hass=hass,
        )
        self._attr_available = False
        self._attr_device_info = deviceInfo
        self._attr_native_value = None
        dev.add_update_callback(self.update_callback)

    def update_callback(self, output_id=0):
        """Called when data is received by pySmartVideoHub"""
        self.update()
        self.schedule_update_ha_state(False)

    def update(self):
        if self._attr_translation_key == "stream_key":
            self._attr_native_value = self._dev.stream_set.get("Stream Key")
            self._attr_available = self._dev.stream_state.get("Status") == "Idle"

    async def async_set_value(self, value: str) -> None:
        """Update the value."""
        self._attr_native_value = value
        if self._attr_translation_key == "stream_key":
            self._dev.set_stream_key(value)
        self.async_write_ha_state()