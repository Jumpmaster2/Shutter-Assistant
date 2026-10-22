# Shutter Assistant

[Deutsche Version](README.md)

Custom integration for Home Assistant that controls roller shutters and blinds automatically (the height of the cover; slats of venetian blinds are not tilted): sun protection per direction, evening mode, ventilation position, weather protection (wind, rain, frost), manual override, morning opening and vacation simulation. Everything is set up in the user interface, nothing is hard coded. There is no AI and no learning; the rules are easy to follow and every movement is written to the logbook with its reason.

It typically replaces a bundle of YAML automations with many helpers (input_boolean, input_number, timer) for sun protection, auto up, evening run, closing after the window was closed, ventilation, override and vacation.

> Status: version 0.6.0.

## How it works

The integration is event driven: it only reacts to state changes of the configured entities and to calculated points in time (the sun enters or leaves a sector, evening start, hold times, end of an override, day change). Nothing is polled every few seconds.

### Groups and windows

* A **group** is a direction of the sun: azimuth from and to plus any number of sun sensors (PV power, brightness in lux, radiation e.g. from Open-Meteo). A group has no thresholds.
* A **window** is a cover with window contact(s) and a group. All thresholds, positions and times belong to the window.

### Sun protection

* **Summer day:** sun protection only happens on summer days. At the day change (default 01:00) the high of the daily forecast is checked. If the outdoor temperature rises above the threshold during the day, it becomes a summer day as well, but only when the forecast low of the coming night is at least 14 °C (adjustable). A warm afternoon in spring or autumn with a cool night therefore does not start sun protection. Without a low in the forecast the summer day counts as before.
* **Sun condition per window:** summer day AND outdoor temperature above the threshold of the window (with hold time) AND every sun sensor of the group above its threshold. All of it must be fulfilled for the sun hold time and ends immediately. After a restart it is evaluated right away; the hold time starts at the start.
* **Heat need (optional):** with a **room temperature** per window the cover is only lowered when the room is too warm: with a thermostat (climate) from setpoint + 2 K, with a temperature sensor from 24 °C. While the chosen **air conditioner** cools, the room counts as too warm and sun protection takes load off it. If it reports no action (e.g. Midea), the mode "cool" counts, and in the mode "auto" a room temperature above its target. While the global **heating wanted** entity is on (e.g. an input_boolean "heating season"), the warmth of the sun is welcome: the cover is only lowered when the room is too warm anyway; windows without a room temperature stay up. Opening again does not depend on this, it still only follows the sun.
* **Lowering:** when the sun is in the sector of the group and the sun condition applies, the cover moves once a day to the sun protection position. If it is already further closed it is only marked and left alone. An open window prevents the movement; a notification is sent once a day (can be switched off per window), only if a movement was really prevented. Lowering follows after the window was closed.
* **Auto up:** when the sun leaves the sector, the cover opens again, but only if it still stands at the sun protection position (up to the tolerance above it). Covers moved elsewhere by hand stay. No auto up in the evening mode, during an override or an opening block. Can be switched off per window.
* **Manual sun protection:** if someone lowers a cover by hand far enough while the sun shines (default at most 25 %), it counts as sun protection for today. Optionally every movement exactly onto the sun protection position counts as well.

### Evening

* **Evening mode:** starts when the sun drops below the set elevation (default -4 °), at the earliest at 17:00 and at the latest at 21:00. It ends at 03:30 or at sunrise. Global values or per window.
* **Evening run:** at the start of the evening mode every cover closes once if the window is closed and no override is active (per window: close despite override, e.g. bedrooms).
* **Evening position:** per window the target of the evening run, of closing after the window was closed and of the vacation evening. Default 0 % = closed; e.g. 20 % leaves a gap on warm nights.
* **Close after window closed:** if a window is closed in the evening, the cover closes (from 16:00, also during an override).
* **Ventilation position:** if a window is opened and the cover is (almost) closed, it moves to the ventilation position (default 30 %). In the evening after 3 s, during the day after 60 s if the window is still open.

### Window contacts, tilted and door

* **Open, tilted, closed:** window contacts report "on" = open. Window handles with the states `open`, `tilted` and `closed` work as well, and there are **tilt contacts** ("on" = tilted). Unknown or unavailable counts as open (tilted for tilt contacts).
* **Tilted:** a window that is only tilted no longer prevents closing, but the cover stops at the ventilation position. Tilting a window moves to the ventilation position like opening it. A fully open window prevents closing as before.
* **Lockout protection (door):** while the contact reports open, nothing closes below the ventilation position, also not with the window exception, closing after the window was closed or the weather protection.

### Weather protection

* **Wind and rain:** globally a wind sensor with a threshold (in the unit of the sensor) and a rain sensor (on/off or an amount above a threshold). Per window a **position with wind** and **with rain**, empty = not affected (e.g. external venetian blinds to 100 % with wind, a roof window to 0 % with rain). An **own wind threshold** on a window replaces the global threshold for that window (e.g. a balcony shutter already from 50 km/h, the others only from 75 km/h); it has its own release time, and the wind protection binary sensor is on while any window is protected (attribute `windows`). The protection starts at once and moves the affected covers to their position, **also during an override and with the automatic off** (not during the restart protection; caught up afterwards). Wind comes before rain. An open window only prevents closing; it is caught up as soon as the window is closed.
* **While the protection runs,** all other rules of the window rest (status "Weather protection"). It ends only after the value stayed on the safe side for the **release time** (default 15 min). An unavailable sensor never ends a protection. Afterwards the automatic decides again (sun protection, evening run); the old position is not restored.
* **Frost:** windows with a **lowest position with frost** (e.g. 5 %) close only down to it while the outdoor temperature is at or below the frost threshold (default 1 °C), so the cover cannot freeze on. This applies to all automatic movements and services, not to the wind and rain protection.
* Start and end are written to the logbook, plus the event `shutter_assistant_protection` with `kind` (wind, rain, frost) and `active`.

### Reliability

* **Spacing between cover commands** (advanced, default 0 = all at once): several covers move one after the other, e.g. every 2 s, against radio collisions.
* **Check the position** (advanced, default after 90 s): if a cover has not reached its target by then (± 5 %), the command is repeated once. If that fails too, there is a notification, a logbook entry and the event `shutter_assistant_cover_failed`. A cover still moving at the check is looked at once more later. A movement by hand ends the check.

### Override

Every manual movement (button, app; not by Shutter Assistant and not by other automations or scripts) starts an override for the window, default 60 min. Every further movement restarts it. Optionally it also ends at sunrise; duration 0 means only at sunrise. The integration remembers its own movements, so late position reports are not taken for manual movements.

In the global settings (dashboard **General**, card **Manual override**) you choose when it starts: **only when the cover really moves** (default; the position changes by more than 2 %, covers without a position stand differently afterwards) or **with every command by hand, also without movement**. With the default, e.g. "Alexa, open all covers" starts no override for covers that are already open.

### Additional conditions instead of special rules

* **Opening block:** while an entity is not in one of the free states, nothing opens automatically (auto up, ventilation, vacation morning, morning opening). Example: TV on.
* **Close trigger:** when one of the entities becomes active (on delay), the cover closes once per active cycle if it is open more than the minimum position and the window is closed. With an open window it closes as soon as the window is closed. The cycle ends when all entities are inactive (off delay). Example: switching on the TV closes the living room cover.
* **Window exception:** while an entity is available, an open window does not prevent closing movements and no notification is sent. Example: an air conditioner with its hose through the balcony door.

### Morning opening (per window, default off)

Modes: fixed time (workday and weekend or holiday via an optional workday sensor), sunrise or sun elevation with offset, brightness of the group above a threshold with hold time, trigger entity (a timestamp like the next alarm of a phone, or an entity that turns on). Plus a period from earliest to latest, a target position (open or partial) and optionally directly the sun protection position if the sun condition applies. Not with an override, an opening block or a cover moved by hand since the evening.

### Vacation simulation

While one of the vacation entities is on (e.g. an input_boolean "vacation"), the normal evening run rests. Instead the participating windows open in the morning at a random time (default 07:00 to 08:00) to a random position (60 to 100 %) and close in the evening at random (19:00 to 20:30). Sun protection and ventilation keep running.

### Restart protection

After Home Assistant started there are no movements for some minutes (default 5). Afterwards everything is evaluated and the evening run is caught up for windows not yet closed (only from 12:00). Overrides, daily markers, a running weather protection and the automatic switches survive restarts.

## Installation via HACS

1. Open HACS, choose **Custom repositories** in the menu at the top right.
2. Add the repository `https://github.com/Jumpmaster2/Shutter-Assistant`, type **Integration**.
3. Download **Shutter Assistant** and restart Home Assistant.
4. **Settings > Devices & services > Add integration > Shutter Assistant**.
5. Add groups and windows in the **Shutter Assistant** dashboard (sidebar).

Requires Home Assistant 2026.10 or newer and the **Sun** integration (set up by default). A weather entity with a forecast and a workday sensor are optional.

## Manual installation

1. Download the latest release and copy the folder `custom_components/shutter_assistant` into the folder `config/custom_components/` of Home Assistant.
2. Restart Home Assistant and add the integration as described above.

## Temperature units

All temperatures (thresholds, forecast, room) are in the unit of the Home Assistant unit system. With °F the defaults are converted (summer day from 73 °F, night from 57 °F, outdoor temperature from 66 °F, room from 75 °F, setpoint plus 4 °F). If the unit system is changed later, adjust the thresholds by hand.

## Configuration

### Dashboard

After the setup there is a **Shutter Assistant** page in the sidebar (administrators only). **Configure** at the integration (Devices & services) opens this page directly.

* **Overview:** automatic on/off, summer day (forecast and threshold), start of the evening mode, vacation, weather protection and restart protection. Next to it the **sun compass** with the current position of the sun and the sectors of the groups, notes (e.g. configured entities that do not exist, or a deleted group) and all windows with status, position, window contact (open, tilted, closed), next action and last reason. A running override can be **ended** right there. The **sun condition check** shows every part of the condition per window with the current value and threshold: summer day (with the night low when the outdoor temperature started it), outdoor temperature, every sun sensor, room, air conditioner, heating wanted, hold time (with the time it will be met) and whether the sun is in the sector.
* **Windows:** all windows as a table, click to edit. The editor shows the settings by topic in cards (window, sun protection, detect manual sun protection, evening, override, ventilation & vacation, morning opening, additional conditions, weather protection & door). Only the fields that apply are shown: thresholds only for the sensor types of the group, own evening times only when switched on, for the morning opening only the fields of the chosen mode. **Duplicate** creates a new window with the same settings; only cover and window contacts are chosen again.
* **Groups:** directions of the sun with the current values of their sensors and the windows using them. While editing, the compass shows the sector of the group right away.
* **House in the compass** (under **General**): length of the front, depth and the direction the front faces. When all three values are set, the house appears to scale and turned in the middle of the compass. A group can then get a **wall**: the azimuth sector is set to the direction of the wall ± 90° (can be changed afterwards) and the wall is shown in the colour of the group. **Windows** appear as marks at their wall (own wall or the one of the group), coloured live by sun protection, override and evening, hollow when the window is open; a click opens the window. **Position on the wall** (1, 2, 3 …) sets the order of the windows on a wall: 1 is far left, looking out through the wall from inside; windows without a number come after.
* **General** and **Evening & vacation:** the global settings in cards, each card is saved on its own.

Values are checked exactly like in the dialogs (same ranges, units and rules). The dialogs (options, add or change group and window) are still available.

### Setup and options (global)

| Option | Default | Meaning |
|---|---|---|
| Outdoor temperature sensor | | without a sensor the current temperature of the weather entity is used (at least one of both) |
| Weather entity | the only one, if there is exactly one | forecast for the summer day |
| Language of messages | like Home Assistant | German or English for logbook, last reason and push |
| Notification services | | only `notify.*`, e.g. `notify.mobile_app_phone` |
| Workday sensor | | optional, for the morning opening (e.g. Workday integration, knows public holidays) |
| Weekend days | Saturday, Sunday | only without a workday sensor |
| Summer day from | 23 °C | high of the forecast |
| Late summer day only with a night from | 14 °C | low of the coming night, when only the outdoor temperature starts the summer day |
| Heating wanted | | optional, e.g. an `input_boolean` "heating season"; on = warmth of the sun welcome |
| Day change | 01:00 | check the forecast, reset daily markers |
| Kind of forecast | automatic | daily, twice daily or hourly; automatic takes the first the weather entity supports |
| Evening earliest, sun elevation, latest | 17:00, -4 °, 21:00 | |
| End of the night | 03:30 | |
| Close after window closed, from | 16:00 | |
| Vacation entities | | "on" = vacation |
| Vacation morning from, random period | 07:00, 60 min | |
| Opening position from, to | 60 %, 100 % | |
| Vacation evening from, random period | 19:00, 90 min | |
| Override starts | only with a real movement | or with every command by hand, also without movement |
| Wind sensor, wind protection from | , 50 | unit of the sensor (e.g. km/h) |
| Rain sensor, rain protection above | , 0 | on/off or an amount (e.g. mm/h) |
| Frost at or below | 1 °C | outdoor temperature, only for windows with a frost position |
| Release after | 15 min | the weather protection ends only after this time on the safe side |
| Restart protection | 5 min | |
| Catch up the evening run from | 12:00 | |
| Window counts as closed after (advanced) | 5 s | debounce of the window contacts |
| Spacing between cover commands (advanced) | 0 s | 0 = all at once |
| Check the position after (advanced) | 90 s | repeat once, then report; 0 = off |
| Dashboard in the sidebar (advanced) | on | off: only reachable with "Configure" at the integration |

### Groups

**Add group**: name, azimuth from and to (90 ° = east, 180 ° = south, 270 ° = west; the bounds themselves do not count), radiation, PV and brightness sensors.

### Windows

**Add window** in four steps:

1. **Window:** name, cover, window contacts (also window handles), tilt contacts, group (no group = no sun protection).
2. **Sun protection:** thresholds for the sensor types of the group, outdoor temperature at least (19 °C), hold times temperature (10 min) and sun (5 min), room temperature (thermostat: too warm from setpoint + 2 K, sensor: from 24 °C), air conditioner, sun protection position (10 %), tolerance for auto up (5 %), auto up, notification about an open window, manual sun protection up to (25 %), detection period (5 min), follow-up (5 min), moving onto the sun protection position counts.
3. **Behaviour:** override (60 min, sunrise, evening and vacation runs despite override), additional conditions, evening (evening run, evening position 0 %, close after window closed, own evening times), ventilation (30 %, counts as closed up to 5 %, 3 s in the evening, 60 s during the day), vacation simulation, weather protection & door (position with wind, own wind threshold, position with rain, lowest position with frost, lockout protection).
4. **Morning opening:** on or off, mode and period, then the settings of the mode.

Positions: 100 % = open, 0 % = closed.

**Changing:** in the dashboard or with the gear icon of the window, then choose the category (window, sun protection, behaviour, morning opening). Each category is saved on its own, the others stay unchanged.

## Entities

Global (device "Shutter Assistant"):

* Switch **Automatic** (off = no automatic movement; survives restarts)
* Binary sensors **Summer day** and **Evening mode**
* Binary sensors **Wind protection**, **Rain protection** and **Frost protection** (only when set up, with the end of the release time)
* Sensor **Forecast high**

Per window (own device):

* Sensor **Status** (weather protection, automatic off, restart protection, manual override, closed for the evening, sun protection, vacation simulation, ready)
* Sensor **Last reason** (text, code, position, time)
* Sensor **Next action** (point in time, attribute `action`: evening run, morning opening, end of the override, sun enters or leaves the sector, weather protection may end)
* Switches **Automatic** (only this window; the weather protection keeps working) and **Sun protection** (off = not lowered for the sun; covers already lowered open again as usual), both survive restarts
* Binary sensors **Manual override** (with end), **Sun condition** (with partial conditions), **Sun protection today**, **Closed this evening**

For control cards on a dashboard, **Sun condition** (thresholds, sensors, azimuth sector, hold times and when they end) and **Status** (cover, window contacts, evening start, override end) provide all values as attributes. **Evening mode** has the start and end of the current or next evening, **Automatic** the end of a running restart protection.

Every movement and every override is written to the **logbook** with its reason.

## Services and events

All services act on the covers of configured windows (`entity_id`, also an entity of the window); without `entity_id` on all windows. They start no override.

| Service | Effect |
|---|---|
| `shutter_assistant.move` | `action`: `open`, `close`, `evening` (evening position, marked as closed for the evening), `sun_protection` (sun protection position, marked as sun protection, opens later by auto up), `ventilation` or `position` with `position`. Frost and the lockout protection still apply. |
| `shutter_assistant.start_override` | override like a movement by hand; `duration` in minutes (empty = duration of the window, 0 = until sunrise) |
| `shutter_assistant.end_override` | end a running override |
| `shutter_assistant.resume` | end the override and let the automatic decide right away (sun protection, evening run) |

```yaml
# Example: thunderstorm warning, all covers on the ground floor to the evening position
action: shutter_assistant.move
data:
  entity_id: [cover.living_room, cover.kitchen]
  action: evening
```

Events for own automations:

* `shutter_assistant_cover_moved`: every cover command with `window`, `window_id`, `entity_id`, `position` and `reason` (e.g. `sun_lower`, `evening_close`, `protection_wind`, `service`)
* `shutter_assistant_cover_failed`: target not reached after the repetition, with `position` and `current_position`
* `shutter_assistant_protection`: weather protection starts or ends, with `kind` and `active`

## Dashboard card

For every user (also without admin rights) there is the card **Shutter Assistant** in the card dialog: all windows with status, position, window contact, next action and a running override (with "Resume automatic"), buttons to open, stop and close (they act like a button on the wall, so they start an override), active weather protection and a small sun compass. Nothing can be set up from the card.

```yaml
type: custom:shutter-assistant-card
title: Covers            # optional
windows: [Living room]   # optional: names or ids, default all
compass: true            # optional: show the sun compass
```

### Small tiles for the sections dashboard

**Shutter Assistant tile** (3 × 1): one cover or one window contact. The name at the top, below it the icon and the state (position or open, tilted, closed). The cover comes down as slats from the top of the tile. An open or tilted window colors the tile. A tap opens the more info dialog.

```yaml
type: custom:shutter-assistant-tile
entity: cover.living_room  # cover, binary_sensor (on = open) or window handle (open/tilted/closed)
name: Living room          # optional
icon: mdi:blinds           # optional
```

**Shutter Assistant window tile** (6 × 1): window and cover together: the name at the top, below it the window (open, tilted, closed) on the left and the cover with its position on the right. Without a window contact only the cover.

```yaml
type: custom:shutter-assistant-window-tile
window: Living room        # window of Shutter Assistant (name or id), or yourself:
cover: cover.living_room
contact: binary_sensor.living_room_window
tilt: binary_sensor.living_room_window_tilted   # optional, on = tilted
```

Colors (both tiles, optional): `color_cover`, `color_closed`, `color_open` and `color_tilted`, each a color name of the theme (`purple`, `orange`, `teal`, ...) or a CSS color (`"#00897b"`). Everything can also be set in the card editor.

## Own dashboard cards

The attributes of the entities can be used in own cards, for example:

```yaml
type: entities
title: Living room
entities:
  - entity: sensor.living_room_status
  - entity: binary_sensor.living_room_sun_condition
    secondary_info: last-changed
  - type: attribute
    entity: sensor.living_room_status
    attribute: evening_start
    name: Evening from
  - type: attribute
    entity: binary_sensor.living_room_sun_condition
    attribute: condition_on_at
    name: Sun condition met from
```

"Sun condition", "Last reason" and "Forecast high" are diagnostic entities. The attributes of "Sun condition" and "Status" are not stored in the history (they change often).

## Troubleshooting

* **No sun protection:** open the **sun condition check** of the window in the dashboard. Every part shows its value and threshold. Frequent reasons: no summer day (forecast below the threshold), no group, a sun sensor below the threshold, the hold time is still running, an open window, an active override.
* **Override starts unexpectedly:** choose "only when the cover really moves" (dashboard **General**, card **Manual override**). Movements of other automations and scripts never count.
* **No forecast:** the dashboard and the repairs page show a note when the weather entity supports no forecast. Choose the kind of forecast or another weather entity.
* **Cover does not move to a position:** covers without position support can only be opened and closed (a warning is logged).
* **Notification "cover did not reach … %":** the cover does not report its position or not exactly. Increase "Check the position after" (advanced) or set it to 0.
* **Cover stays up or at the ventilation position:** weather protection active (status "Weather protection"), window tilted, lockout protection of an open door or frost. The last reason and the overview show what applies.
* **Diagnostics:** Settings > Devices & services > Shutter Assistant > ⋮ > Download diagnostics (notification services are redacted).

### Debug log

```yaml
logger:
  default: warning
  logs:
    custom_components.shutter_assistant: debug
```

Or at the integration: ⋮ > **Enable debug logging**.

## Removal

Settings > Devices & services > Shutter Assistant > ⋮ > **Delete**. The stored state (overrides, markers), the dashboard and the repair notes are removed. Remove the folder or the HACS download afterwards.

## Moving from YAML automations

See [docs/migration.md](docs/migration.md).

## Development

```bash
pip install -r requirements_test.txt
pytest
```

The labels of the dashboard (`frontend/labels.js`) are generated from the translations: after changing `translations/*.json` run `python scripts/gen_labels.py` once (a test checks this).

The rules in `custom_components/shutter_assistant/logic/` do not depend on Home Assistant and can be tested on their own. The tests with Home Assistant need Linux or macOS (they also run in GitHub Actions). Lint with `ruff check custom_components tests scripts`.

## License

MIT, see [LICENSE](LICENSE).
