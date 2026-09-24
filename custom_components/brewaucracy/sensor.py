from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import BrewaucracyConfigEntry
from .coordinator import BrewaucracyCoordinator
from .ticker import build_ticker

DOMAIN = "brewaucracy"
VENUE_TZ = ZoneInfo("Pacific/Auckland")
WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
CLOSED_WEEKDAYS = (0, 1, 2)


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrewaucracyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    async_add_entities(
        [
            *(
                BrewaucracyFoodTruckSensor(coordinator, weekday)
                for weekday in range(len(WEEKDAYS))
            ),
            BrewaucracyTodayFoodTruckSensor(coordinator),
            BrewaucracyUpcomingEventsSensor(coordinator),
            BrewaucracyNewsSensor(coordinator),
            BrewaucracyJokeSensor(coordinator),
            BrewaucracyCommitteeMinutesSensor(coordinator),
        ]
    )

    known_taps: set[int] = set()

    @callback
    def _add_taps() -> None:
        new: list[BrewaucracyTapSensor] = []
        for item in coordinator.data["taps"]["items"]:
            number = item.get("tap")
            if isinstance(number, int) and number not in known_taps:
                known_taps.add(number)
                new.append(BrewaucracyTapSensor(coordinator, number))
        if new:
            async_add_entities(new)

    _add_taps()
    entry.async_on_unload(coordinator.async_add_listener(_add_taps))


class BrewaucracyEntity(CoordinatorEntity[BrewaucracyCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _section_name = "news"
    _timestamp_key = "source_received_at"
    _stale_after = timedelta(days=8)

    def __init__(self, coordinator: BrewaucracyCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name="Brewaucracy",
            manufacturer="Brewaucracy",
            configuration_url="https://www.brewaucracy.co.nz",
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        try:
            recorded = datetime.fromisoformat(self._section.get(self._timestamp_key))
        except (TypeError, ValueError):
            return False
        return (
            recorded.tzinfo is not None
            and dt_util.utcnow() - recorded <= self._stale_after
        )

    @property
    def _section(self) -> dict[str, Any]:
        return self.coordinator.data[self._section_name]

    def _find_item(self, key: str, value: Any) -> dict[str, Any] | None:
        return next(
            (item for item in self._section["items"] if item.get(key) == value),
            None,
        )


class BrewaucracyTapSensor(BrewaucracyEntity):
    _attr_icon = "mdi:beer"
    _section_name = "taps"
    _timestamp_key = "source_fetched_at"
    _stale_after = timedelta(hours=12)

    def __init__(self, coordinator: BrewaucracyCoordinator, tap: int) -> None:
        super().__init__(coordinator)
        self._tap = tap
        self._attr_unique_id = f"{DOMAIN}_tap_{tap:02d}"
        self._attr_name = f"Tap {tap:02d}"

    @property
    def native_value(self) -> str | None:
        item = self._find_item("tap", self._tap)
        if item is None:
            return None
        if item.get("class") == "nis":
            return "Not in Service"
        name = item.get("name")
        if not name:
            return "Empty"
        brewery = (item.get("brewery") or "").strip()
        if brewery and brewery != "Brewaucracy":
            return f"{brewery} - {name}"
        return name

    @property
    def entity_picture(self) -> str | None:
        item = self._find_item("tap", self._tap)
        if item is None:
            return None
        return item.get("badge_url") or None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        item = self._find_item("tap", self._tap)
        if item is None:
            return None
        return {
            "tap": item.get("tap"),
            "class": item.get("class"),
            "brewery": item.get("brewery"),
            "style": item.get("style"),
            "abv": item.get("abv"),
            "prices": item.get("prices"),
            "takeaway_per_litre": item.get("takeaway_per_litre"),
            "currency": self._section.get("currency"),
            "source_fetched_at": self._section.get("source_fetched_at"),
        }


class BrewaucracyFoodTruckEntity(BrewaucracyEntity):
    _attr_icon = "mdi:truck"
    _section_name = "food_trucks"

    @property
    def _date(self) -> date:
        return datetime.now(VENUE_TZ).date()

    @property
    def native_value(self) -> str | None:
        item = self._find_item("date", self._date.isoformat())
        if item is None:
            return None
        vendor = item.get("vendor") or ""
        if vendor.strip().lower() == "none":
            return "No truck - BYO"
        return vendor or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        item = self._find_item("date", self._date.isoformat()) or {}
        return {
            "date": self._date.isoformat(),
            "from_time": item.get("from_time"),
        }


class BrewaucracyTodayFoodTruckSensor(BrewaucracyFoodTruckEntity):
    _attr_unique_id = f"{DOMAIN}_food_truck_today"
    _attr_name = "Today's Food Truck"
    entity_id = f"sensor.{DOMAIN}_food_truck_today"


class BrewaucracyFoodTruckSensor(BrewaucracyFoodTruckEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BrewaucracyCoordinator, weekday: int) -> None:
        super().__init__(coordinator)
        self._weekday = weekday
        self._attr_entity_registry_enabled_default = weekday not in CLOSED_WEEKDAYS
        name = WEEKDAYS[weekday]
        self._attr_unique_id = f"{DOMAIN}_food_truck_{name}"
        self._attr_name = f"Food Truck {weekday + 1} - {name.capitalize()}"

    @property
    def _date(self) -> date:
        start = super()._date - timedelta(days=1)
        return start + timedelta(days=(self._weekday - start.weekday()) % 7)


class BrewaucracyHeadlinesEntity(BrewaucracyEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _lists_events: bool
    _empty_state: str

    @property
    def _items(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self._section["items"]
            if (item.get("category") == "event") == self._lists_events
        ]

    @property
    def native_value(self) -> str:
        return build_ticker(
            [item.get("title") for item in self._items], self._empty_state
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"count": len(self._items), "items": self._items}


class BrewaucracyUpcomingEventsSensor(BrewaucracyHeadlinesEntity):
    _attr_icon = "mdi:calendar-star"
    _attr_unique_id = f"{DOMAIN}_upcoming_events"
    _attr_name = "Upcoming events"
    _lists_events = True
    _empty_state = "No events this week"


class BrewaucracyNewsSensor(BrewaucracyHeadlinesEntity):
    _attr_icon = "mdi:newspaper"
    _attr_unique_id = f"{DOMAIN}_brewery_news"
    _attr_name = "Brewery news"
    _lists_events = False
    _empty_state = "No news this week"


class BrewaucracyJokeSensor(BrewaucracyEntity):
    _attr_icon = "mdi:emoticon-happy-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_unique_id = f"{DOMAIN}_weekly_joke"
    _attr_name = "Weekly joke"

    @property
    def native_value(self) -> str:
        if not self._section.get("joke"):
            return "No joke this week"
        week_of = _parse_date(self._section.get("week_of"))
        when = f"{week_of.day} {week_of:%B}" if week_of else "this week"
        return f"See Attributes for {when}'s knee-slapper"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"joke": self._section.get("joke")}


class BrewaucracyCommitteeMinutesSensor(BrewaucracyEntity):
    _attr_icon = "mdi:file-document-outline"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_unique_id = f"{DOMAIN}_committee_minutes"
    _attr_name = "Minutes from Committee Meeting"
    entity_id = f"sensor.{DOMAIN}_committee_minutes"

    @property
    def native_value(self) -> date | None:
        return _parse_date(self._section.get("week_of"))
