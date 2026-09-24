# Brewaucracy for Home Assistant

A zero-configuration custom integration that turns [Brewaucracy's](https://www.brewaucracy.co.nz) taproom feed and weekly email newsletter into Home Assistant entities - including the tap list, the food truck schedule, events, news and the weekly joke.

News and events are extracted from the email and put through an LLM to summarise into something suitable for a dashboard or announcement.

All the entities are grouped under a single `Brewaucracy` device. The tap list and food trucks are all visible as sensors, while the full brewery news, events, and Greig's joke live in attributes under their sensors (as they far surpass the 255 character limit).

Remember that food trucks are on a best-effort basis, and they sometimes need to cancel at the last minute. If an update comes via email, it will be processed and the food truck sensor will be updated - but sometimes these changes are only published on social media which I'm not scraping.

## Install

### via HACS

1. HACS -> three-dot menu -> Custom repositories.
2. Add `https://github.com/rhyven/ha-brewaucracy`, type Integration.
3. Find Brewaucracy in the HACS list, download it, then restart Home Assistant.
4. Then under Settings -> Devices & Services -> Add Integration, find & install Brewaucracy.
5. Make sure to expose the appropriate sensors if you want to ask "Hey Google, what's the food truck at Brewaucracy today?"

### Manually

Copy `custom_components/brewaucracy/` to `/config/custom_components/`, restart Home Assistant, then add the integration as per step 4 above.


## Entities

| Entity | State | Attributes |
| --- | --- | --- |
| `sensor.brewaucracy_tap_NN` | Beer name, `Empty`, `Not in Service`, or unknown | `tap`, `class`, `brewery`, `style`, `abv`, `prices`, `takeaway_per_litre`, `currency`, `source_fetched_at` |
| `sensor.brewaucracy_food_truck_today` | Vendor, `No truck - BYO`, or unknown | `date`, `from_time` |
| `sensor.brewaucracy_food_truck_N_<weekday>` | Vendor, `No truck - BYO`, or unknown | `date`, `from_time` |
| `sensor.brewaucracy_upcoming_events` | Event titles, as a ticker, or `No events this week` | `count`, `items` |
| `sensor.brewaucracy_brewery_news` | News titles, as a ticker, or `No news this week` | `count`, `items` |
| `sensor.brewaucracy_weekly_joke` | Pointer to the attribute, or `No joke this week` | `joke` |
| `sensor.brewaucracy_committee_minutes` | Issue date | n/a |

The week's food trucks, events, news, joke and newsletter date sensors are in the Diagnostic section of the device page so they stay off auto-generated dashboard views. The tap sensors and Today's Food Truck are not.

### Taps

Taps are fed from the same source as the taproom menu, with thanks to Greig and Phil, so it's as authoritative as possible. Although the sensors update every 60 seconds, my server refreshes from the data source more slowly, to avoid any impact on Brewaucracy infrastructure. The data is updated every 10 minutes during opening hours, and every 2 hours outside normal opening hours.

As a keg is emptied and rotated, the tap's status & attributes are updated.

Guest beers carry the brewery as a prefix (e.g., `Peckham's - Classic Apple`), while Brewaucracy house beers show the beer name alone. Tap badges render as `entity_picture`.

### The Other Sensors

While the tap list comes from a nice tidy machine-readable source, the Food Truck schedule and other bits are all best-effort from processing the weekly newsletter though an LLM. 

**Food Trucks**

The seven weekday Food Truck sensors cover a rolling seven-day window beginning yesterday - so by Tuesday morning, all food truck sensors will read `unknown` until the new newsletter is published on Thursday. `Today's Food Truck` duplicates whichever weekday sensor matches today.

Although the taproom is closed Monday to Wednesday, those three sensors are created just in case there's a future change, but they're disabled by default.

| State | Meaning |
| --- | --- |
| A food truck name | The newsletter anticipates this vendor on the day |
| `No truck - BYO` | The newsletter actively says no food truck is scheduled |
| `unknown` | The newsletter says nothing at all about the day |

**Events, News, and the Dad Joke**

To populate the `News` and `Events` sensors, the LLM attempts to differentiate between an event happening in the brewery (such as Quiz Night, Oktoberfest), and news regarding the brewery (such as an imminent new release, the last keg of a favourite, or roadworks). 

The State of each is a ticker of the item titles, trimmed to fit Home Assistant's 255-character state limit. Up to three titles are shown; with more than three, it just shows the first two followed by `and more!`. The full items (dates, times and body text) live within the attributes inside these sensors; you'll need to use templates or dashboards etc to get these details.

Because I don't modify the dad joke at all, it's generally going to be over the 255-char limit, so the State of the entity simply mentions that a joke exists and to check the attributes for it.


## Availability

Entities become unavailable when the feed cannot be read or is somehow munted, and otherwise per source block:

| Entities | Timestamp | Window |
| --- | --- | --- |
| Taps | `taps.source_fetched_at` | no new data for 12 hours |
| Food trucks | `food_trucks.source_received_at` | no new data for 8 days |
| Events, news, joke, minutes | `news.source_received_at` | no new data for 8 days |


## Requires

Home Assistant 2024.6 or later. The integration icon requires 2026.3 or later, but everything works on the older versions except the icon falls back to a placeholder.
