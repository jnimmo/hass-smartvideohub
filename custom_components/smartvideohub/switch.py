import logging

from homeassistant.components.switch import ENTITY_ID_FORMAT, SwitchEntity, SwitchDeviceClass
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
                StreamingSwitchDevice(
                    hass,
                    dev,
                    "streaming",
                    deviceInfo
                )
            ],
            True,
        )

class StreamingSwitchDevice(SwitchEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:ip"

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
        dev.add_update_callback(self.update_callback)

    @property
    def is_on(self):
        """Retrieve latest state."""
        if self._attr_translation_key == "streaming":
            if self._dev.stream_state.get("Status") == "Idle":
                return False
            else:
                return True

        self._attr_available = self._dev.connected

    async def async_turn_on(self) -> None:
        """Update the current selected option."""
        if self._attr_translation_key == "streaming":
            self._dev.set_steam_state(True)
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Update the current selected option."""
        if self._attr_translation_key == "streaming":
            self._dev.set_steam_state(False)
        self.async_write_ha_state()

    def update_callback(self, output_id=0):
        """Called when data is received by pySmartVideoHub"""
        self.schedule_update_ha_state(False)
