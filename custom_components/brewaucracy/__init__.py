from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import BrewaucracyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type BrewaucracyConfigEntry = ConfigEntry[BrewaucracyCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BrewaucracyConfigEntry) -> bool:
    coordinator = BrewaucracyCoordinator(hass, async_get_clientsession(hass))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BrewaucracyConfigEntry
) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
