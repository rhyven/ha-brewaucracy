from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo

from .coordinator import BrewaucracyCoordinator

DOMAIN = "brewaucracy"
PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SENSOR]

type BrewaucracyConfigEntry = ConfigEntry[BrewaucracyCoordinator]


def brewaucracy_device_info() -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, DOMAIN)},
        name="Brewaucracy",
        manufacturer="Brewaucracy",
        configuration_url="https://www.brewaucracy.co.nz",
    )


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
