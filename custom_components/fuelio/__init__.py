"""The Fuelio integration."""

from __future__ import annotations

from collections.abc import Iterable

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTRY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS, SERVICE_RELOAD
from .coordinator import FuelioDataUpdateCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Fuelio integration."""
    hass.data.setdefault(DOMAIN, {})

    async def async_handle_reload(call) -> None:
        """Reload one or all Fuelio coordinators."""
        entry_id = call.data.get(CONF_ENTRY_ID)
        if entry_id:
            coordinators = [hass.data[DOMAIN][entry_id]]
        else:
            coordinators = list(_iter_coordinators(hass))

        for coordinator in coordinators:
            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD,
        async_handle_reload,
        schema=vol.Schema({vol.Optional(CONF_ENTRY_ID): cv.string}),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fuelio from a config entry."""
    coordinator = FuelioDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


def _iter_coordinators(hass: HomeAssistant) -> Iterable[FuelioDataUpdateCoordinator]:
    """Return all loaded Fuelio coordinators."""
    return hass.data.get(DOMAIN, {}).values()
