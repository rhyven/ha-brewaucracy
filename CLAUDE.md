# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (HACS-distributed) that polls a JSON feed produced by an external
service (a separate LLM-based email/newsletter processor, not part of this repo) and exposes it as
Home Assistant sensor entities. There is no build system, package manager, or test suite in this repo —
it's pure Python against the Home Assistant integration API, meant to be copied into
`/config/custom_components/brewaucracy/` or installed via HACS.

There is no local Home Assistant install to run or test against in this environment. Validate changes by
reading the code against the Home Assistant integration conventions (below), not by executing it.

## Architecture

Everything lives in `custom_components/brewaucracy/`. Data flows in one direction:

1. **`coordinator.py`** — `BrewaucracyCoordinator` (a `DataUpdateCoordinator`) polls a single fixed URL
   (`FEED_URL`) every 60 seconds using ETag/`If-None-Match` conditional requests. The feed's JSON has
   three top-level sections, each with an `items` list: `taps`, `food_trucks`, `news`. `_require_sections`
   validates this shape on every fetch and raises `UpdateFailed` if it's missing or malformed — sensors
   assume this shape is already guaranteed by the time they read `coordinator.data`.
2. **`sensor.py`** — all entity classes read from `coordinator.data[section]["items"]` directly (via
   `BrewaucracyEntity._section` / `_find_item`). There's no intermediate data model; sensors are thin
   views over the raw feed dict.
3. **`ticker.py`** — pure string-formatting logic (`build_ticker`) that squeezes a list of titles into
   Home Assistant's 255-character state limit, used by the news/events sensors. This is the one part
   with any nontrivial logic and is the natural target for unit tests if any get added.

### Entity model

- All entities attach to a single shared `Brewaucracy` device (`DeviceInfo` with a fixed identifier),
  defined once in `BrewaucracyEntity.__init__`.
- `BrewaucracyEntity` is the base class all sensors inherit from. Subclasses override `_section_name`
  (`"taps"` / `"food_trucks"` / `"news"`) and `_timestamp_key`/`_stale_after` to control per-section
  staleness/availability — see `available` in `sensor.py`. Availability is entirely feed-timestamp-driven:
  there's no explicit connection state beyond what the coordinator already provides via
  `super().available`.
- Tap sensors are created dynamically as new tap numbers appear in the feed (`_add_taps` listener in
  `async_setup_entry`), since the number of taps isn't fixed. Food truck, news/events, joke, and minutes
  sensors are static and created once at setup.
- Food truck sensors cover a rolling 7-day window keyed by weekday name, not by absolute date — see
  `BrewaucracyFoodTruckEntity._date` and how `BrewaucracyFoodTruckSensor` offsets from "yesterday" to find
  the matching weekday. Weekdays the taproom is closed (`CLOSED_WEEKDAYS` = Mon–Wed) are disabled by
  default via `_attr_entity_registry_enabled_default`.
- News/events share one feed section (`news`) but are split into two sensor classes by filtering on
  `item.get("category") == "event"` (`BrewaucracyHeadlinesEntity._lists_events`).

### Config flow

`config_flow.py` is a no-input flow (`async_step_user` immediately creates the entry) — the integration
is zero-configuration by design (`single_config_entry: true` in `manifest.json`), matching the README's
"zero-configuration" claim. Don't add config fields without checking whether that constraint still holds.

## Key constraints to preserve when editing

- Sensor states must stay within Home Assistant's 255-character limit. Anything long (news items, events,
  the joke, full tap details) belongs in `extra_state_attributes`, not `native_value`. This is why
  `ticker.py` exists — reuse it rather than writing new truncation logic.
- Feed section names (`taps`, `food_trucks`, `news`) and their required shape are enforced centrally in
  `coordinator._require_sections`; sensors should be able to assume `items` is always a list of dicts once
  `coordinator.data` is set.
- The `brand/` directory feeds Home Assistant's icon system (2026.3+ reads it directly; older versions use
  the brands CDN). Follow the size/naming conventions in `brand/README.md` if adding brand assets.
