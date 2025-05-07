from homeassistant.components.device_tracker import config_entry
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
)
from homeassistant.core import HomeAssistant
from .pyvideohub import SmartVideoHub
from .const import *

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    smartvideohub = SmartVideoHub(config_entry.data[CONF_HOST], config_entry.data[CONF_PORT], hass.loop)
    smartvideohub.start()
    await smartvideohub.initialised.wait()

    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": smartvideohub,
    }

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(config_entry, [
            Platform.MEDIA_PLAYER,
            Platform.SELECT,
            Platform.TEXT,
            Platform.BUTTON,
            Platform.SWITCH
        ])
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [
            Platform.MEDIA_PLAYER,
            Platform.SELECT,
            Platform.TEXT,
            Platform.BUTTON,
            Platform.SWITCH
        ]
    )
    hass.data[DOMAIN][entry.entry_id]['client'].stop()
    return unload_ok