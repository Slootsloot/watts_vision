"""Watts Vision Component."""

from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval

from .const import API_CLIENT, DOMAIN, SCAN_INTERVAL
from .watts_api import WattsApi

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Watts Vision from a config entry."""
    _LOGGER.debug("Set up Watts Vision")
    hass.data.setdefault(DOMAIN, {})

    client = WattsApi(hass, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    try:
        await hass.async_add_executor_job(client.getLoginToken)
        await hass.async_add_executor_job(client.loadData)
    except Exception as exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unable to set up Watts Vision")
        raise ConfigEntryNotReady from exception

    hass.data[DOMAIN][entry.entry_id] = {API_CLIENT: client}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def refresh_devices(event_time: datetime) -> None:
        await hass.async_add_executor_job(client.reloadDevices)

    unsub_refresh = async_track_time_interval(hass, refresh_devices, SCAN_INTERVAL)
    hass.data[DOMAIN][entry.entry_id]["unsub_refresh"] = unsub_refresh

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Watts Vision")
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        unsub_refresh = entry_data.get("unsub_refresh")
        if unsub_refresh is not None:
            unsub_refresh()
    return unload_ok
