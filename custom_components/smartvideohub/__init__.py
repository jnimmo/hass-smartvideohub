import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from .pyvideohub import SmartVideoHub
from .const import *

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    smartvideohub = SmartVideoHub(config_entry.data[CONF_HOST], config_entry.data[CONF_PORT], hass.loop)
    smartvideohub.start()
    try:
        async with asyncio.timeout(30):
            await smartvideohub.initialised.wait()
    except TimeoutError as err:
        smartvideohub.stop()
        raise ConfigEntryNotReady(
            f"No response from Videohub at {config_entry.data[CONF_HOST]}"
        ) from err
    if not smartvideohub.connected:
        smartvideohub.stop()
        raise ConfigEntryNotReady(
            f"Cannot connect to Videohub at {config_entry.data[CONF_HOST]}"
        )

    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": smartvideohub,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, [
        Platform.MEDIA_PLAYER,
        Platform.SELECT,
        Platform.TEXT,
        Platform.BUTTON,
        Platform.SWITCH
    ])

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