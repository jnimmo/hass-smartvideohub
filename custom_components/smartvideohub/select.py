import logging

from homeassistant.components.select import ENTITY_ID_FORMAT, SelectEntity
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
                StreamingSelectDevice(
                    hass,
                    dev,
                    "platform",
                    deviceInfo
                ),
                StreamingSelectDevice(
                    hass,
                    dev,
                    "quality_level",
                    deviceInfo
                ),
                StreamingSelectDevice(
                    hass,
                    dev,
                    "video_mode",
                    deviceInfo
                )
            ],
            True,
        )
    elif dev.model == MODEL_TERANEX:
        async_add_entities(
            [
                StreamingSelectDevice(
                    hass,
                    dev,
                    "lut",
                    deviceInfo
                )
            ],
            True,
        )

class StreamingSelectDevice(SelectEntity):
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
        dev.add_update_callback(self.update_callback)

    def update(self):
        """Retrieve latest state."""
        if self._attr_translation_key == "platform":
            self._attr_current_option = self._dev.stream_set.get("Current Platform")
            self._attr_options = self._dev.stream_set.get("Available Default Platforms").split(", ") + \
                                 self._dev.stream_set.get("Available Custom Platforms").split(", ")
            self._attr_available = self._dev.stream_state.get("Status") == "Idle" and self._dev.connected
        elif self._attr_translation_key == "video_mode":
            self._attr_current_option = self._dev.stream_set.get("Video Mode")
            self._attr_options = self._dev.stream_set.get("Available Video Modes").split(", ")
            self._attr_available = self._dev.stream_state.get("Status") == "Idle" and self._dev.connected
        elif self._attr_translation_key == "quality_level":
            self._attr_current_option = self._dev.stream_set.get("Current Quality Level")
            self._attr_options = self._dev.stream_set.get("Available Quality Levels").split(", ")
            self._attr_available = self._dev.stream_state.get("Status") == "Idle" and self._dev.connected
        elif self._attr_translation_key == "lut":
            self._attr_options = ["none"]
            self._attr_options.extend(["Lut %d" % x for x in range(int(self._dev.teranex_set.get("Number of LUTs")))])
            self._attr_current_option = self._dev.teranex_set.get("Lut selection", "none")
            self._attr_available = self._dev.connected

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""
        self._attr_current_option = option
        if self._attr_translation_key == "platform":
            self._dev.set_stream_platform(option)
        elif self._attr_translation_key == "video_mode":
            self._dev.set_video_mode(option)
        elif self._attr_translation_key == "quality_level":
            self._dev.set_quality_level(option)
        elif self._attr_translation_key == "lut":
            self._dev.set_lut(option)
        self.async_write_ha_state()

    def update_callback(self, output_id=0):
        """Called when data is received by pySmartVideoHub"""
        self.update()
        self.schedule_update_ha_state(False)
