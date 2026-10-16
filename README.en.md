# Shutter Assistant

[Deutsche Version](README.md)

Custom integration for Home Assistant that controls roller shutters and blinds automatically: sun protection per direction, evening mode, ventilation position, manual override, morning opening and vacation simulation. Everything is set up in the user interface, nothing is hard coded. There is no AI and no learning; the rules are easy to follow and every movement is written to the logbook with its reason.

It typically replaces a bundle of YAML automations with many helpers (input_boolean, input_number, timer) for sun protection, auto up, evening run, closing after the window was closed, ventilation, override and vacation.

> Status: version 0.2.2.

## How it works

The integration is event driven: it only reacts to state changes of the configured entities and to calculated points in time (the sun enters or leaves a sector, evening start, hold times, end of an override, day change). Nothing is polled every few seconds.

### Groups and windows

* A **group** is a direction of the sun: azimuth from and to plus any number of sun sensors (PV power, brightness in lux, radiation e.g. from Open-Meteo). A group has no thresholds.
* A **window** is a cover with window contact(s) and a group. All thresholds, positions and times belong to the window.

### Sun protection

* **Summer day:** sun protection only happens on summer days. At the day change (default 01:00) the high of the daily forecast is checked. If the outdoor temperature rises above the threshold during the day, it becomes a summer day as well.
* **Sun condition per window:** summer day AND outdoor temperature above the threshold of the window (with hold time) AND every sun sensor of the group above its threshold. All of it must be fulfilled for the sun hold time and ends immediately. After a restart it is evaluated right away; the hold time starts at the start.
* **Lowering:** when the sun is in the sector of the group and the sun condition applies, the cover moves once a day to the sun protection position. If it is already further closed it is only marked and left alone. An open window prevents the movement; a notification is sent once a day (can be switched off per window), only if a movement was really prevented. Lowering follows after the window was closed.
* **Auto up:** when the sun leaves the sector, the cover opens again, but only if it still stands at the sun protection position (up to the tolerance above it). Covers moved elsewhere by hand stay. No auto up in the evening mode, during an override or an opening block. Can be switched off per window.
* **Manual sun protection:** if someone lowers a cover by hand far enough while the sun shines (default at most 25 %), it counts as sun protection for today. Optionally every movement exactly onto the sun protection position counts as well.

### Evening

* **Evening mode:** starts when the sun drops below the set elevation (default -4 °), at the earliest at 17:00 and at the latest at 21:00. It ends at 03:30 or at sunrise. Global values or per window.
* **Evening run:** at the start of the evening mode every cover closes once if the window is closed and no override is active (per window: close despite override, e.g. bedrooms).
* **Close after window closed:** if a window is closed in the evening, the cover closes (from 16:00, also during an override).
* **Ventilation position:** if a window is opened and the cover is (almost) closed, it moves to the ventilation position (default 30 %). In the evening after 3 s, during the day after 60 s if the window is still open.

### Override

Every manual movement (button, app; not by Shutter Assistant and not by other automations or scripts) starts an override for the window, default 60 min. Every further movement restarts it. Optionally it also ends at sunrise; duration 0 means only at sunrise. The integration remembers its own movements, so late position reports are not taken for manual movements.

### Additional conditions instead of special rules

* **Opening block:** while an entity is not in one of the free states, nothing opens automatically (auto up, ventilation, vacation morning, morning opening). Example: TV on.
* **Close trigger:** when one of the entities becomes active (on delay), the cover closes once per active cycle if it is open more than the minimum position and the window is closed. With an open window it closes as soon as the window is closed. The cycle ends when all entities are inactive (off delay). Example: switching on the TV closes the living room cover.
* **Window exception:** while an entity is available, an open window does not prevent closing movements and no notification is sent. Example: an air conditioner with its hose through the balcony door.

### Morning opening (per window, default off)

Modes: fixed time (workday and weekend or holiday via an optional workday sensor), sunrise or sun elevation with offset, brightness of the group above a threshold with hold time, trigger entity (a timestamp like the next alarm of a phone, or an entity that turns on). Plus a period from earliest to latest, a target position (open or partial) and optionally directly the sun protection position if the sun condition applies. Not with an override, an opening block or a cover moved by hand since the evening.

### Vacation simulation

While one of the vacation entities is on (e.g. the same helper as for the heating), the normal evening run rests. Instead the participating windows open in the morning at a random time (default 07:00 to 08:00) to a random position (60 to 100 %) and close in the evening at random (19:00 to 20:30). Sun protection and ventilation keep running.

### Restart protection

After Home Assistant started there are no movements for some minutes (default 5). Afterwards everything is evaluated and the evening run is caught up for windows not yet closed (only from 12:00). Overrides, daily markers and the automatic switch survive restarts.

## Installation via HACS

1. Open HACS, choose **Custom repositories** in the menu at the top right.
2. Add the repository `https://github.com/Jumpmaster2/Shutter-Assistant`, type **Integration**.
3. Download **Shutter Assistant** and restart Home Assistant.
4. **Settings > Devices & services > Add integration > Shutter Assistant**.
5. Add groups and windows in the **Shutter Assistant** dashboard (sidebar).

Requires Home Assistant 2026.10 or newer.

## Configuration

### Dashboard

After the setup there is a **Shutter Assistant** page in the sidebar (administrators only). **Configure** at the integration (Devices & services) opens this page directly.

* **Overview:** automatic on/off, summer day (forecast and threshold), start of the evening mode, vacation and restart protection. Next to it the **sun compass** with the current position of the sun and the sectors of the groups, notes (e.g. configured entities that do not exist, or a deleted group) and all windows with status, position, window contact and last reason. A running override can be **ended** right there. The **sun condition check** shows every part of the condition per window with the current value and threshold: summer day, outdoor temperature, every sun sensor, hold time (with the time it will be met) and whether the sun is in the sector.
* **Windows:** all windows as a table, click to edit. The editor shows the settings by topic in cards (window, sun protection, detect manual sun protection, evening, override, ventilation & vacation, morning opening, additional conditions). Only the fields that apply are shown: thresholds only for the sensor types of the group, own evening times only when switched on, for the morning opening only the fields of the chosen mode. **Duplicate** creates a new window with the same settings; only cover and window contacts are chosen again.
* **Groups:** directions of the sun with the current values of their sensors and the windows using them. While editing, the compass shows the sector of the group right away.
* **House in the compass** (under **General**): length of the front, depth and the direction the front faces. When all three values are set, the house appears to scale and turned in the middle of the compass. A group can then get a **wall**: the azimuth sector is set to the direction of the wall ± 90° (can be changed afterwards) and the wall is shown in the colour of the group. **Windows** appear as marks at their wall (own wall or the one of the group), coloured live by sun protection, override and evening, hollow when the window is open; a click opens the window. **Position on the wall** (1, 2, 3 …) sets the order of the windows on a wall: 1 is far left, looking out through the wall from inside; windows without a number come after.
* **General** and **Evening & vacation:** the global settings in cards, each card is saved on its own.

Values are checked exactly like in the dialogs (same ranges, units and rules). The dialogs (options, add or change group and window) are still available.

### Setup and options (global)

| Option | Default | Meaning |
|---|---|---|
| Outdoor temperature sensor | | required |
| Weather entity | | daily forecast for the summer day |
| Language of messages | like Home Assistant | German or English for logbook, last reason and push |
| Notification services | | e.g. `notify.mobile_app_phone` |
| Workday sensor | | optional, for the morning opening (e.g. Workday integration) |
| Summer day from | 23 °C | high of the forecast |
| Day change | 01:00 | check the forecast, reset daily markers |
| Evening earliest, sun elevation, latest | 17:00, -4 °, 21:00 | |
| End of the night | 03:30 | |
| Close after window closed, from | 16:00 | |
| Vacation entities | | "on" = vacation |
| Vacation morning from, random period | 07:00, 60 min | |
| Opening position from, to | 60 %, 100 % | |
| Vacation evening from, random period | 19:00, 90 min | |
| Restart protection | 5 min | |
| Catch up the evening run from | 12:00 | |

### Groups

**Add group**: name, azimuth from and to (90 ° = east, 180 ° = south, 270 ° = west; the bounds themselves do not count), radiation, PV and brightness sensors.

### Windows

**Add window** in four steps:

1. **Window:** name, cover, window contacts, group (no group = no sun protection).
2. **Sun protection:** thresholds for the sensor types of the group, outdoor temperature at least (19 °C), hold times temperature (10 min) and sun (5 min), sun protection position (10 %), tolerance for auto up (5 %), auto up, notification about an open window, manual sun protection up to (25 %), detection period (5 min), follow-up (5 min), moving onto the sun protection position counts.
3. **Behaviour:** override (60 min, sunrise, evening and vacation runs despite override), additional conditions, evening (evening run, close after window closed, own evening times), ventilation (30 %, counts as closed up to 5 %, 3 s in the evening, 60 s during the day), vacation simulation.
4. **Morning opening:** on or off, mode and period, then the settings of the mode.

Positions: 100 % = open, 0 % = closed.

**Changing:** in the dashboard or with the gear icon of the window, then choose the category (window, sun protection, behaviour, morning opening). Each category is saved on its own, the others stay unchanged.

## Entities

Global (device "Shutter Assistant"):

* Switch **Automatic** (off = no automatic movement; survives restarts)
* Binary sensors **Summer day** and **Evening mode**
* Sensor **Forecast high**

Per window (own device):

* Sensor **Status** (automatic off, restart protection, manual override, closed for the evening, sun protection, vacation simulation, ready)
* Sensor **Last reason** (text, code, position, time)
* Binary sensors **Manual override** (with end), **Sun condition** (with partial conditions), **Sun protection today**, **Closed this evening**

For control cards on a dashboard, **Sun condition** (thresholds, sensors, azimuth sector, hold times and when they end) and **Status** (cover, window contacts, evening start, override end) provide all values as attributes. **Evening mode** has the start and end of the current or next evening, **Automatic** the end of a running restart protection.

Every movement and every override is written to the **logbook** with its reason.

## Moving from YAML automations

See [docs/migration.md](docs/migration.md).

## Development

```bash
pip install -r requirements_test.txt
pytest
```

The labels of the dashboard (`frontend/labels.js`) are generated from the translations: after changing `translations/*.json` run `python scripts/gen_labels.py` once (a test checks this).

The rules in `custom_components/shutter_assistant/logic/` do not depend on Home Assistant and can be tested on their own. The tests with Home Assistant need Linux or macOS (they also run in GitHub Actions).

## License

MIT, see [LICENSE](LICENSE).
