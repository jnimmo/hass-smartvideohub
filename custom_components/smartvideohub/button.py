import logging

from homeassistant.components.button import ENTITY_ID_FORMAT, ButtonEntity
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
                StreamingButtonDevice(
                    hass,
                    dev,
                    "reboot",
                    deviceInfo
                )
            ],
            True,
        )

class StreamingButtonDevice(ButtonEntity):
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
        self._attr_unique_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            dev.attrs.get("Unique ID", "")+"/"+translation_key,
            hass=hass,
        )
        self._attr_device_info = deviceInfo

    async def async_press(self) -> None:
        """Update the current selected option."""
        self._dev.reboot()
