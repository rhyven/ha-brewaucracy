from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import BrewaucracyConfigEntry, brewaucracy_device_info

DOMAIN = "brewaucracy"
VESSEL_SIZES_ML = (280, 400, 500, 568)
DEFAULT_VESSEL_SIZE_ML = 400


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrewaucracyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([BrewaucracyPreferredVesselSizeSelect()])


class BrewaucracyPreferredVesselSizeSelect(SelectEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:glass-mug-variant"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_unique_id = f"{DOMAIN}_preferred_vessel_size"
    _attr_name = "Preferred vessel size (mL)"
    _attr_options = [str(size) for size in VESSEL_SIZES_ML]
    _attr_current_option = str(DEFAULT_VESSEL_SIZE_ML)
    entity_id = f"select.{DOMAIN}_preferred_vessel_size"

    def __init__(self) -> None:
        super().__init__()
        self._attr_device_info = brewaucracy_device_info()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self.options:
            self._attr_current_option = last_state.state

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
