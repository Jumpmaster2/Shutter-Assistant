// Shutter Assistant sidebar panel: overview and all settings on one page.
// Plain web component without build step; uses only the hass object and the
// WebSocket commands of the integration. Type, range, unit and domains of every
// field come from the integration (the same selectors as in the dialogs).

import { CHOICES, ERRORS, LABELS, NEXT_ACTION, STATUS } from "./labels.js";

const UI = {
  de: {
    title: "Shutter Assistant",
    tabs: { overview: "Übersicht", windows: "Fenster", groups: "Gruppen", general: "Allgemein", evening: "Abend & Urlaub" },
    cards: {
      sensors: ["Sensoren & Meldungen", "Außentemperatur, Wettervorhersage, Sprache und wer bei offenem Fenster eine Meldung bekommt."],
      summer: ["Sommertag", "Sonnenschutz gibt es nur an Sommertagen."],
      override: ["Manuelle Übersteuerung", "Wann eine Bedienung von Hand (Taster, App, Sprachassistent) die Übersteuerung eines Fensters startet. Dauer und weitere Einstellungen stehen am Fenster."],
      startup: ["Neustart-Schutz", "Nach dem Start von Home Assistant eine Weile keine Fahrten."],
      advanced: ["Erweitert", "Selten benötigte Einstellungen."],
      evening: ["Abendmodus", "Schließt die Rollos einmal und sperrt Auto-Hoch. Fenster können eigene Zeiten haben."],
      vacation: ["Urlaubssimulation", "Solange Urlaub ist, öffnen die Fenster morgens und schließen abends zu zufälligen Zeiten."],
      w_basics: ["Fenster", "Rollo, Fensterkontakte und Himmelsrichtung."],
      w_sun: ["Sonnenschutz", "Schwellen, Haltezeiten, Position und Auto-Hoch."],
      w_manual: ["Manuellen Sonnenschutz erkennen", "Ein bei Sonne von Hand heruntergefahrenes Rollo gilt als Sonnenschutz für heute."],
      w_evening: ["Abend", "Abendlauf, Nachziehen und eigene Abendzeiten."],
      w_override: ["Übersteuerung", "Nach einer Fahrt von Hand pausiert die Automatik für dieses Fenster."],
      w_vent: ["Lüften & Urlaub", "Lüftungsposition beim Öffnen des Fensters und Teilnahme an der Urlaubssimulation."],
      w_morning: ["Morgenöffnung", "Nie bei Übersteuerung, Öffnungssperre oder einem seit dem Abend von Hand verstellten Rollo. Im Urlaub öffnet die Simulation."],
      w_conditions: ["Zusatzbedingungen", "Öffnungssperre (z. B. Fernseher an), Schließ-Auslöser und Fenster-Ausnahme."],
      w_protection: ["Wetterschutz & Tür", "Positionen bei Wind und Regen, Spalt bei Frost und der Aussperrschutz einer Tür. Die Sensoren stehen unter Allgemein > Wetterschutz."],
      protection: ["Wetterschutz", "Wind und Regen fahren die beteiligten Fenster auf ihre Schutzposition, auch bei Übersteuerung. Frost lässt beim Schließen einen Spalt. Die Positionen stehen am Fenster."],
      g_basics: ["Gruppe", "Eine Himmelsrichtung. Die Schwellen stehen am Fenster."],
      g_sensors: ["Sonnensensoren", "Jeder Sensor der Gruppe muss die Schwelle des Fensters erreichen."],
      compass: ["Sonnenkompass", "Aktueller Sonnenstand und die Bereiche der Gruppen."],
      windows: ["Fenster", "Alle Fenster mit Gruppe, Status und Position."],
      groups: ["Gruppen", "Himmelsrichtungen mit ihren Sonnensensoren."],
      hints: ["Hinweise", ""],
      house: ["Haus", "Für das Bild im Sonnenkompass. Sind alle drei Werte eingetragen, erscheint das Haus in der Mitte des Kompasses."],
    },
    labels: {
      house_azimuth: ["Vorderseite zeigt nach", "Himmelsrichtung, in die die Vorderseite schaut (90° = Ost, 180° = Süd, 270° = West), z. B. auf einer Karte abgelesen."],
      house_width: ["Länge der Vorderseite", "Gilt auch für die Rückseite."],
      house_depth: ["Tiefe", "Länge der beiden Seitenwände."],
      wall_position: ["Position an der Wand", "1 = ganz links, von innen durch die Wand nach draußen geschaut. Bestimmt die Reihenfolge im Kompass, Fenster ohne Zahl kommen danach."],
    },
    wallOthers: (list) => `An dieser Wand: ${list}`,
    wall: "Wand",
    wallHelpGroup: "Setzt den Azimut-Bereich auf die Ausrichtung der Wand ± 90° (danach frei änderbar). Die Wand wird im Kompass in der Farbe der Gruppe gezeigt.",
    wallHelpWindow: "Das Fenster erscheint an dieser Wand im Kompass. Ohne Angabe gilt die Wand der Gruppe.",
    noWall: "Keine Wand",
    likeGroup: (wall) => `Wie die Gruppe: ${wall}`,
    noHouse: "Erst unter „Allgemein“ das Haus eintragen, dann lassen sich Wände wählen.",
    houseIncomplete: "Sind alle drei Werte eingetragen, erscheint hier das Haus.",
    front: "Vorderseite",
    dirsLong: ["Nord", "Nordost", "Ost", "Südost", "Süd", "Südwest", "West", "Nordwest"],
    wallName: (dir, deg) => `${dir}wand (${deg}°)`,
    markers: { sun_protection: "Sonnenschutz", override: "Übersteuerung", evening: "Abend", open: "Fenster offen" },
    save: "Speichern",
    saved: "Gespeichert",
    cancel: "Abbrechen",
    delete: "Löschen",
    add: "Hinzufügen",
    edit: "Bearbeiten",
    duplicate: "Duplizieren",
    copyOf: (name) => `${name} (Kopie)`,
    duplicated: "Kopie angelegt: Rollo und Fensterkontakte neu wählen, dann speichern.",
    confirmDelete: "Wirklich löschen?",
    confirmDeleteGroup: (names) => `Diese Fenster verwenden die Gruppe und haben danach keinen Sonnenschutz: ${names}. Trotzdem löschen?`,
    discard: "Ungespeicherte Änderungen verwerfen?",
    notFound: "nicht gefunden",
    none: "–",
    addValue: "Wert eingeben und Enter",
    noGroup: "Keine Gruppe (kein Sonnenschutz)",
    loadError: "Konfiguration konnte nicht geladen werden",
    notLoaded: "Die Integration ist gerade nicht geladen. Einstellungen lassen sich ändern, Zustände fehlen.",
    loading: "wird geladen …",
    automaticOn: "Automatik an",
    automaticOff: "Automatik aus",
    turnOn: "Einschalten",
    turnOff: "Ausschalten",
    summary: (w, s, o) => `${w} Fenster · ${s} im Sonnenschutz · ${o} übersteuert`,
    summer: "Sommertag",
    yes: "ja",
    no: "nein",
    on: "an",
    off: "aus",
    forecast: (v, t, u) => `Vorhersage ${v} ${u}, ab ${t} ${u}`,
    noForecast: "keine Vorhersage",
    raised: "durch die Außentemperatur",
    evening: "Abendmodus",
    eveningActive: (t) => `aktiv bis ${t}`,
    eveningAt: (t) => `beginnt um ${t}`,
    vacation: "Urlaub",
    restart: "Neustart-Schutz",
    until: (t) => `bis ${t}`,
    untilSunrise: "bis Sonnenaufgang",
    noWindows: "Noch keine Fenster angelegt.",
    noGroups: "Noch keine Gruppen angelegt. Ohne Gruppe gibt es keinen Sonnenschutz.",
    position: "Position",
    open: "offen",
    closed: "zu",
    tilted: "gekippt",
    nextAction: "Nächste Aktion",
    protections: { wind: "Windschutz", rain: "Regenschutz", frost: "Frostschutz" },
    unavailable: "nicht verfügbar",
    window: "Fenster",
    group: "Gruppe",
    lastReason: "Letzter Grund",
    override: "Übersteuerung",
    endOverride: "Beenden",
    overrideEnded: "Übersteuerung beendet",
    sunCheck: "Sonnenbedingung",
    check: {
      summer: "Sommertag",
      night: "Nacht (später Sommertag)",
      nightText: (v, t, u) => `Tiefstwert ${v} ${u}, ab ${t} ${u}`,
      noNight: "kein Tiefstwert",
      raisedText: (v) => `durch die Außentemperatur${v ? `, ${v}` : ""}`,
      room: "Raum zu warm",
      roomText: (v, l, u) => `${v} ${u}, ab ${l} ${u}`,
      roomUnknown: "kein Wert, zählt als warm",
      cooling: "Klimaanlage",
      coolingOn: "kühlt, Raum zählt als warm",
      coolingOff: "kühlt nicht",
      heating: "Heizbedarf",
      heatingOn: "an, Sonnenwärme erwünscht",
      heatingOff: "aus",
      temperature: "Außentemperatur",
      hold: "Haltezeit Sonne",
      sector: "Sonne im Bereich (zum Absenken)",
      on: "Sonnenbedingung erfüllt",
      off: "Sonnenbedingung nicht erfüllt",
      today: "Sonnenschutz heute",
      pendingAt: (t) => `erfüllt ab ${t}`,
      holdText: (m) => `${m} min lang erfüllt`,
      from: "ab",
      noValue: "kein Wert",
      sectorText: (az, from, to) => `Sonne ${az}°, Bereich ${from}° bis ${to}°`,
    },
    kinds: { pv: "PV", lux: "Helligkeit", radiation: "Strahlung" },
    compass: {
      sun: "Sonne",
      azimuth: "Azimut",
      elevation: "Höhe",
      noSun: "Sonnenstand nicht verfügbar (Integration „Sun“ fehlt).",
      below: "unter dem Horizont",
      inSector: "Sonne im Bereich",
      windowsCount: (n) => (n === 1 ? "1 Fenster" : `${n} Fenster`),
    },
    dirs: ["N", "NO", "O", "SO", "S", "SW", "W", "NW"],
    hints: "Hinweise",
    noHints: "Keine Hinweise",
    missing: (where, id) => `${where}: ${id} gibt es nicht`,
    missingGroup: (w) => `${w}: die Gruppe wurde gelöscht, kein Sonnenschutz`,
    noWeather: "Keine Wetter-Entität: der Sommertag beginnt nur, wenn die Außentemperatur die Schwelle überschreitet.",
    noTemperature: "Weder Außentemperatur-Sensor noch Wetter-Entität: es gibt keinen Sommertag.",
    global: "Allgemein",
    columns: { name: "Name", group: "Gruppe", status: "Status", position: "Position" },
    usedBy: "Verwendet von",
    unused: "Von keinem Fenster verwendet",
    newWindow: "Neues Fenster",
    newGroup: "Neue Gruppe",
    fieldErrors: { required: "Pflichtfeld", invalid_value: "Ungültiger Wert" },
    checkFields: "Bitte die markierten Felder prüfen.",
    sunNoGroup: "Ohne Gruppe gibt es keinen Sonnenschutz. Unter „Fenster“ eine Gruppe wählen.",
    preview: "Vorschau",
  },
  en: {
    title: "Shutter Assistant",
    tabs: { overview: "Overview", windows: "Windows", groups: "Groups", general: "General", evening: "Evening & vacation" },
    cards: {
      sensors: ["Sensors & messages", "Outdoor temperature, weather forecast, language and who gets a message about an open window."],
      summer: ["Summer day", "Sun protection only runs on summer days."],
      override: ["Manual override", "When a movement by hand (switch, app, voice assistant) starts the override of a window. Duration and further settings are set per window."],
      startup: ["Restart protection", "No movement for a while after Home Assistant started."],
      advanced: ["Advanced", "Settings that are rarely needed."],
      evening: ["Evening mode", "Closes the covers once and blocks auto up. Windows can use own times."],
      vacation: ["Vacation simulation", "While vacation is active, the windows open in the morning and close in the evening at random times."],
      w_basics: ["Window", "Cover, window contacts and sun direction."],
      w_sun: ["Sun protection", "Thresholds, hold times, position and auto up."],
      w_manual: ["Detect manual sun protection", "A cover lowered by hand while the sun shines counts as sun protection for today."],
      w_evening: ["Evening", "Evening run, closing after the window is closed and own evening times."],
      w_override: ["Override", "After a manual movement the automatic pauses for this window."],
      w_vent: ["Ventilation & vacation", "Ventilation position when the window opens and taking part in the vacation simulation."],
      w_morning: ["Morning opening", "Never with an active override, an opening block or a cover moved by hand since the evening. During vacation the simulation opens instead."],
      w_conditions: ["Additional conditions", "Opening block (e.g. TV on), close trigger and window exception."],
      w_protection: ["Weather protection & door", "Positions with wind and rain, a gap with frost and the lockout protection of a door. The sensors are under General > Weather protection."],
      protection: ["Weather protection", "Wind and rain move the windows that take part to their protection position, also during an override. Frost keeps a gap when closing. The positions are set per window."],
      g_basics: ["Group", "A direction of the sun. Thresholds are set per window."],
      g_sensors: ["Sun sensors", "Every sensor of the group must reach the threshold of the window."],
      compass: ["Sun compass", "Current position of the sun and the sectors of the groups."],
      windows: ["Windows", "All windows with group, status and position."],
      groups: ["Groups", "Directions of the sun with their sensors."],
      hints: ["Notes", ""],
      house: ["House", "For the picture in the sun compass. When all three values are set, the house appears in the middle of the compass."],
    },
    labels: {
      house_azimuth: ["Front faces", "Direction the front looks to (90° = east, 180° = south, 270° = west), e.g. read from a map."],
      house_width: ["Length of the front", "Also the back."],
      house_depth: ["Depth", "Length of the two side walls."],
      wall_position: ["Position on the wall", "1 = far left, looking out through the wall from inside. Sets the order in the compass, windows without a number come after."],
    },
    wallOthers: (list) => `On this wall: ${list}`,
    wall: "Wall",
    wallHelpGroup: "Sets the azimuth sector to the direction of the wall ± 90° (can be changed afterwards). The wall is shown in the compass in the colour of the group.",
    wallHelpWindow: "The window appears at this wall in the compass. Without a wall the wall of the group is used.",
    noWall: "No wall",
    likeGroup: (wall) => `Like the group: ${wall}`,
    noHouse: "Enter the house under \"General\" first, then walls can be chosen.",
    houseIncomplete: "When all three values are set, the house appears here.",
    front: "front",
    dirsLong: ["North", "North-east", "East", "South-east", "South", "South-west", "West", "North-west"],
    wallName: (dir, deg) => `${dir} wall (${deg}°)`,
    markers: { sun_protection: "Sun protection", override: "Override", evening: "Evening", open: "Window open" },
    save: "Save",
    saved: "Saved",
    cancel: "Cancel",
    delete: "Delete",
    add: "Add",
    edit: "Edit",
    duplicate: "Duplicate",
    copyOf: (name) => `${name} (copy)`,
    duplicated: "Copy created: choose cover and window contacts, then save.",
    confirmDelete: "Really delete?",
    confirmDeleteGroup: (names) => `These windows use the group and lose their sun protection: ${names}. Delete anyway?`,
    discard: "Discard unsaved changes?",
    notFound: "not found",
    none: "–",
    addValue: "Type a value and press Enter",
    noGroup: "No group (no sun protection)",
    loadError: "Could not load the configuration",
    notLoaded: "The integration is not loaded right now. Settings can be changed, states are missing.",
    loading: "loading …",
    automaticOn: "Automatic on",
    automaticOff: "Automatic off",
    turnOn: "Turn on",
    turnOff: "Turn off",
    summary: (w, s, o) => `${w} windows · ${s} sun protected · ${o} overridden`,
    summer: "Summer day",
    yes: "yes",
    no: "no",
    on: "on",
    off: "off",
    forecast: (v, t, u) => `forecast ${v} ${u}, from ${t} ${u}`,
    noForecast: "no forecast",
    raised: "by the outdoor temperature",
    evening: "Evening mode",
    eveningActive: (t) => `active until ${t}`,
    eveningAt: (t) => `starts at ${t}`,
    vacation: "Vacation",
    restart: "Restart protection",
    until: (t) => `until ${t}`,
    untilSunrise: "until sunrise",
    noWindows: "No windows yet.",
    noGroups: "No groups yet. Without a group there is no sun protection.",
    position: "Position",
    open: "open",
    closed: "closed",
    tilted: "tilted",
    nextAction: "Next action",
    protections: { wind: "Wind protection", rain: "Rain protection", frost: "Frost protection" },
    unavailable: "unavailable",
    window: "Window",
    group: "Group",
    lastReason: "Last reason",
    override: "Override",
    endOverride: "End",
    overrideEnded: "Override ended",
    sunCheck: "Sun condition",
    check: {
      summer: "Summer day",
      night: "Night (late summer day)",
      nightText: (v, t, u) => `low ${v} ${u}, from ${t} ${u}`,
      noNight: "no forecast low",
      raisedText: (v) => `by the outdoor temperature${v ? `, ${v}` : ""}`,
      room: "Room too warm",
      roomText: (v, l, u) => `${v} ${u}, from ${l} ${u}`,
      roomUnknown: "no value, counts as warm",
      cooling: "Air conditioner",
      coolingOn: "cooling, room counts as warm",
      coolingOff: "not cooling",
      heating: "Heating wanted",
      heatingOn: "on, warmth of the sun welcome",
      heatingOff: "off",
      temperature: "Outdoor temperature",
      hold: "Sun hold time",
      sector: "Sun in the sector (for lowering)",
      on: "Sun condition met",
      off: "Sun condition not met",
      today: "Sun protection today",
      pendingAt: (t) => `met from ${t}`,
      holdText: (m) => `met for ${m} min`,
      from: "from",
      noValue: "no value",
      sectorText: (az, from, to) => `sun ${az}°, sector ${from}° to ${to}°`,
    },
    kinds: { pv: "PV", lux: "Brightness", radiation: "Radiation" },
    compass: {
      sun: "Sun",
      azimuth: "Azimuth",
      elevation: "Elevation",
      noSun: "Position of the sun not available (\"Sun\" integration missing).",
      below: "below the horizon",
      inSector: "Sun in the sector",
      windowsCount: (n) => (n === 1 ? "1 window" : `${n} windows`),
    },
    dirs: ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
    hints: "Notes",
    noHints: "No notes",
    missing: (where, id) => `${where}: ${id} does not exist`,
    missingGroup: (w) => `${w}: the group was deleted, no sun protection`,
    noWeather: "No weather entity: the summer day only starts when the outdoor temperature exceeds the threshold.",
    noTemperature: "Neither outdoor temperature sensor nor weather entity: there is no summer day.",
    global: "General",
    columns: { name: "Name", group: "Group", status: "Status", position: "Position" },
    usedBy: "Used by",
    unused: "Not used by any window",
    newWindow: "New window",
    newGroup: "New group",
    fieldErrors: { required: "Required", invalid_value: "Invalid value" },
    checkFields: "Please check the marked fields.",
    sunNoGroup: "Without a group there is no sun protection. Choose a group under \"Window\".",
    preview: "Preview",
  },
};

const TABS = [
  ["overview", "mdi:view-dashboard-outline"],
  ["windows", "mdi:window-shutter"],
  ["groups", "mdi:compass-outline"],
  ["general", "mdi:tune-variant"],
  ["evening", "mdi:weather-night"],
];

// Global settings: cards per tab
const SETTINGS = {
  general: [
    { id: "sensors", icon: "mdi:thermometer", fields: ["outdoor_temperature", "weather", "language", "notify_services", "workday_entity", "weekend_days"] },
    { id: "override", icon: "mdi:hand-back-right-outline", fields: ["override_trigger"] },
    { id: "summer", icon: "mdi:white-balance-sunny", fields: ["summer_threshold", "night_threshold", "heating_entity", "day_change_time", "forecast_type"] },
    { id: "startup", icon: "mdi:restart", fields: ["startup_delay", "catch_up_after"] },
    { id: "protection", icon: "mdi:weather-windy", fields: ["wind_entity", "wind_threshold", "rain_entity", "rain_threshold", "frost_threshold", "protection_release"] },
    { id: "advanced", icon: "mdi:cog-outline", fields: ["window_closed_delay", "command_interval", "verify_after", "show_panel"] },
    { id: "house", icon: "mdi:home-outline", fields: ["house_azimuth", "house_width", "house_depth"], preview: true },
  ],
  evening: [
    { id: "evening", icon: "mdi:weather-sunset-down", fields: ["evening_earliest", "evening_elevation", "evening_latest", "night_end", "follow_up_earliest"] },
    {
      id: "vacation",
      icon: "mdi:airplane",
      fields: ["vacation_entities", "vacation_morning_start", "vacation_morning_window", "vacation_position_min", "vacation_position_max", "vacation_evening_start", "vacation_evening_window"],
    },
  ],
};

const KINDS = [
  ["radiation", "radiation_sensors", "radiation_threshold", "mdi:weather-sunny-alert"],
  ["pv", "pv_sensors", "pv_threshold", "mdi:solar-power-variant"],
  ["lux", "lux_sensors", "lux_threshold", "mdi:brightness-6"],
];
const MORNING_MODE_FIELDS = {
  time: ["morning_time_workday", "morning_time_weekend"],
  sun: ["morning_sun_event", "morning_sun_elevation", "morning_sun_offset"],
  brightness: ["morning_lux_threshold", "morning_lux_hold"],
  trigger: ["morning_trigger_entity", "morning_trigger_offset"],
};

// Window editor: cards with the fields that apply for the current values
const WINDOW_CARDS = [
  { id: "w_basics", icon: "mdi:window-shutter-cog", fields: () => ["name", "cover", "window_sensors", "tilt_sensors", "group", "wall", "wall_position"] },
  {
    id: "w_sun",
    icon: "mdi:sun-angle-outline",
    needsGroup: true,
    fields: (d, group) => [
      ...KINDS.filter(([, sensors]) => (group?.data?.[sensors] || []).length).map(([, , threshold]) => threshold),
      "temperature_threshold",
      "temperature_hold",
      "room_entity",
      ...(String(d.room_entity || "").startsWith("climate.") ? ["room_margin"] : d.room_entity ? ["room_threshold"] : []),
      "cooling_entity",
      "sun_hold",
      "sun_position",
      "position_tolerance",
      "auto_up",
      "notify_open_window",
    ],
  },
  {
    id: "w_manual",
    icon: "mdi:hand-pointing-down",
    needsGroup: true,
    fields: () => ["manual_max_position", "manual_detection_window", "manual_follow_up", "manual_at_sun_position"],
  },
  {
    id: "w_evening",
    icon: "mdi:weather-night",
    fields: (d) => ["evening_close", "evening_position", "follow_up_close", "evening_custom", ...(d.evening_custom ? ["evening_earliest", "evening_elevation", "evening_latest"] : [])],
  },
  { id: "w_override", icon: "mdi:hand-back-right-outline", fields: () => ["override_duration", "override_sunrise_reset", "override_ignore_evening"] },
  {
    id: "w_vent",
    icon: "mdi:window-open-variant",
    fields: () => ["ventilation", "ventilation_position", "closed_position", "ventilation_delay_evening", "ventilation_delay_day", "vacation"],
  },
  {
    id: "w_morning",
    icon: "mdi:weather-sunset-up",
    fields: (d) =>
      d.morning_enabled
        ? ["morning_enabled", "morning_mode", ...(MORNING_MODE_FIELDS[d.morning_mode] || []), "morning_earliest", "morning_latest", "morning_position", "morning_sun_position"]
        : ["morning_enabled"],
  },
  {
    id: "w_conditions",
    icon: "mdi:link-variant",
    fields: () => [
      "open_block_entity",
      "open_block_free_states",
      "close_trigger_entities",
      "close_trigger_active_states",
      "close_trigger_on_delay",
      "close_trigger_off_delay",
      "close_trigger_min_position",
      "close_trigger_max_lock",
      "window_exception_entity",
    ],
  },
];
WINDOW_CARDS.push({ id: "w_protection", icon: "mdi:weather-windy", fields: () => ["wind_position", "window_wind_threshold", "rain_position", "frost_position", "lockout_protection"] });
const GROUP_CARDS = [
  { id: "g_basics", icon: "mdi:compass-outline", fields: () => ["name", "wall", "azimuth_from", "azimuth_to"] },
  { id: "g_sensors", icon: "mdi:weather-sunny", fields: () => ["radiation_sensors", "pv_sensors", "lux_sensors"] },
];
// changing one of these shows or hides other fields
const REDRAW_KEYS = new Set(["group", "wall", "evening_custom", "morning_enabled", "morning_mode"]);
// walls of the house by their angle to the front (right and left seen from inside)
const WALLS = [
  ["front", 0],
  ["right", 90],
  ["back", 180],
  ["left", 270],
];
const MARKER_COLORS = { protection: "#e53935", sun_protection: "#ffa600", override: "#8e24aa", evening: "#5c6bc0", vacation: "#00897b" };

const STATUS_STYLE = {
  protection: ["mdi:weather-windy", "danger"],
  off: ["mdi:pause-circle-outline", "muted"],
  startup: ["mdi:restart", "muted"],
  override: ["mdi:hand-back-right-outline", "purple"],
  evening: ["mdi:weather-night", "indigo"],
  sun_protection: ["mdi:white-balance-sunny", "warn"],
  vacation: ["mdi:airplane", "teal"],
  ready: ["mdi:check-circle-outline", "ok"],
};
const GROUP_COLORS = ["#f9a825", "#1e88e5", "#e53935", "#43a047", "#8e24aa", "#00897b", "#ef6c00", "#6d4c41"];
const INVALID = ["unavailable", "unknown"];

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const clone = (value) => JSON.parse(JSON.stringify(value ?? null));
const prettyService = (svc) =>
  String(svc)
    .replace(/^notify\./, "")
    .replace(/^mobile_app_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

// same rule as the integration: bounds are exclusive, start > end wraps around north
const inSector = (az, from, to) => (from <= to ? from < az && az < to : az > from || az < to);

class ShutterAssistantPanel extends HTMLElement {
  constructor() {
    super();
    this._tab = "overview";
    this._drafts = {};
    this._errors = {};
    this._edit = null;
    this._cfg = null;
    this._error = null;
    this._sig = "";
    this._expanded = new Set();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("input", (ev) => this._onInput(ev));
    this.shadowRoot.addEventListener("change", (ev) => this._onInput(ev, true));
    this.shadowRoot.addEventListener("keydown", (ev) => this._onKey(ev));
    this.shadowRoot.addEventListener("pointerdown", () => (this._lastPointer = Date.now()));
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._load();
    else this._live();
  }

  get hass() {
    return this._hass;
  }

  set narrow(value) {
    this._narrow = value;
    const btn = this.shadowRoot.querySelector(".menu");
    if (btn) btn.style.display = value ? "" : "none";
  }

  set panel(value) {
    this._panel = value;
  }

  // ------------------------------------------------------------------ texts

  get lang() {
    const language = this._hass?.locale?.language || this._hass?.language || "en";
    return language.startsWith("de") ? "de" : "en";
  }

  get locale() {
    return this._hass?.locale?.language || this._hass?.language || "en";
  }

  get ui() {
    return UI[this.lang];
  }

  label(key) {
    return (LABELS[this.lang] || LABELS.en)[key] || this.ui.labels[key] || [key, ""];
  }

  _time(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const zone = this._hass?.locale?.time_zone === "server" ? this._hass?.config?.time_zone : undefined;
    const day = (d) => d.toLocaleDateString(this.locale, { timeZone: zone });
    const time = date.toLocaleTimeString(this.locale, { hour: "2-digit", minute: "2-digit", timeZone: zone });
    if (day(new Date()) === day(date)) return time;
    return `${date.toLocaleDateString(this.locale, { weekday: "short", timeZone: zone })} ${time}`;
  }

  _num(value, digits = 1) {
    const number = Number(value);
    if (value === null || value === undefined || value === "" || Number.isNaN(number)) return "";
    return number.toLocaleString(this.locale, { maximumFractionDigits: digits });
  }

  get _unit() {
    return this._cfg?.temperature_unit || "°C";
  }

  _dir(az) {
    return this.ui.dirs[Math.round((((Number(az) % 360) + 360) % 360) / 45) % 8];
  }

  // ------------------------------------------------------------------ house

  // house from the options (or the values being edited), null until all three are set
  _house(values = this._cfg?.options || {}) {
    const az = Number(values.house_azimuth);
    const width = Number(values.house_width);
    const depth = Number(values.house_depth);
    const set = (v) => v !== null && v !== undefined && v !== "";
    if (![values.house_azimuth, values.house_width, values.house_depth].every(set)) return null;
    if ([az, width, depth].some((v) => Number.isNaN(v)) || width <= 0 || depth <= 0) return null;
    return { az, width, depth };
  }

  _wallFacing(house, wall) {
    const offset = (WALLS.find(([id]) => id === wall) || [])[1];
    return offset === undefined ? null : (((house.az + offset) % 360) + 360) % 360;
  }

  _wallName(house, wall) {
    const facing = this._wallFacing(house, wall);
    if (facing === null) return wall;
    const dir = this.ui.dirsLong[Math.round(facing / 45) % 8];
    const name = this.ui.wallName(dir, this._num(facing, 0));
    return wall === "front" ? `${name} – ${this.ui.front}` : name;
  }

  _windowWall(win) {
    return win.data.wall || this._group(win.data.group)?.data?.wall || null;
  }

  // windows on a wall in their order: numbered first (1 = left seen from inside), then the rest
  _sortedOnWall(windows) {
    const pos = (w) => {
      const n = Number(w.data.wall_position);
      return w.data.wall_position && !Number.isNaN(n) ? n : Infinity;
    };
    return windows
      .map((w, i) => [w, i])
      .sort((a, b) => pos(a[0]) - pos(b[0]) || a[1] - b[1])
      .map(([w]) => w);
  }

  _wallLabel(win) {
    const pos = Number(win.data.wall_position);
    return win.data.wall_position && !Number.isNaN(pos) ? `${Math.round(pos)}. ${win.title}` : win.title;
  }

  // window markers and highlighted walls of the groups for the compass
  _houseLayers(house, { excludeGroup = null, extraWall = null, clickable = false } = {}) {
    if (!house) return {};
    const walls = {};
    for (const g of this._groups) {
      if (g.id !== excludeGroup && g.data.wall && !walls[g.data.wall]) walls[g.data.wall] = this._groupColor(g.id);
    }
    if (extraWall?.wall) walls[extraWall.wall] = extraWall.color;
    // the walls run from left to right as seen from inside, so the sorted order is the drawn order
    const markers = this._sortedOnWall(this._windows.filter((w) => this._windowWall(w)))
      .map((w) => {
        const status = this._status(w);
        const open = this._windowOpen(w);
        const statusText = status ? (STATUS[this.lang] || STATUS.en)[status] || status : "";
        return {
          id: w.id,
          wall: this._windowWall(w),
          color: MARKER_COLORS[status] || "var(--secondary-text-color)",
          open,
          title: [this._wallLabel(w), statusText, open ? this.ui.markers.open : ""].filter(Boolean).join(" · "),
        };
      });
    return { house, walls, markers, clickable };
  }

  _markerLegend(layers) {
    if (!layers.markers?.length) return "";
    const m = this.ui.markers;
    const item = (color, text, open = false) =>
      `<span class="legend-item"><span class="legend-mark ${open ? "open" : ""}" style="--mark:${color}"></span>${esc(text)}</span>`;
    return `<div class="legend">${item(MARKER_COLORS.sun_protection, m.sun_protection)}${item(MARKER_COLORS.override, m.override)}${item(MARKER_COLORS.evening, m.evening)}${item("var(--secondary-text-color)", m.open, true)}</div>`;
  }

  // ------------------------------------------------------------------ data

  async _load(silent = false) {
    this._lastLoad = Date.now();
    try {
      this._cfg = await this._hass.callWS({ type: "shutter_assistant/config" });
      this._error = null;
    } catch (err) {
      this._error = err.message || String(err);
    }
    if (!silent) {
      this._render();
      return;
    }
    const lists = this.shadowRoot.querySelector(".datalists");
    if (lists) lists.innerHTML = this._datalists();
    if (!this._edit && !this._typing()) this._rerenderContent();
  }

  _refreshLater() {
    // a change reloads the integration; new entities exist only afterwards
    clearTimeout(this._refreshTimer);
    this._refreshTimer = setTimeout(() => this._load(true), 2500);
  }

  _typing() {
    const active = this.shadowRoot.activeElement;
    return !!active && ["INPUT", "SELECT", "TEXTAREA"].includes(active.tagName);
  }

  _ws(msg) {
    return this._hass.callWS(msg);
  }

  _state(entityId) {
    return entityId ? this._hass.states[entityId] : undefined;
  }

  _name(entityId) {
    return this._state(entityId)?.attributes?.friendly_name || entityId;
  }

  get _groups() {
    return this._cfg?.groups || [];
  }

  get _windows() {
    return this._cfg?.windows || [];
  }

  _group(id) {
    return this._groups.find((g) => g.id === id);
  }

  _groupColor(id) {
    const index = this._groups.findIndex((g) => g.id === id);
    return GROUP_COLORS[(index < 0 ? 0 : index) % GROUP_COLORS.length];
  }

  _windowData(win) {
    return { ...(this._cfg.defaults?.window || {}), ...win.data };
  }

  // ------------------------------------------------------------------ rendering

  _render() {
    const ui = this.ui;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="toolbar">
        <button class="menu icon-btn" data-action="menu" style="${this._narrow ? "" : "display:none"}"><ha-icon icon="mdi:menu"></ha-icon></button>
        <div class="title"><ha-icon icon="mdi:window-shutter-auto"></ha-icon>${esc(ui.title)}</div>
      </div>
      <div class="tabs">
        ${TABS.map(
          ([id, icon]) =>
            `<button class="tab ${this._tab === id ? "active" : ""}" data-tab="${id}"><ha-icon icon="${icon}"></ha-icon><span>${esc(ui.tabs[id])}</span></button>`,
        ).join("")}
      </div>
      <div class="content">${this._content()}</div>
      <div class="datalists">${this._datalists()}</div>
      <div class="toast" hidden></div>`;
    this._sig = this._signature();
  }

  _content() {
    const ui = this.ui;
    if (this._error) return `<div class="card error">${esc(ui.loadError)}: ${esc(this._error)}</div>`;
    if (!this._cfg) return `<div class="card muted">${esc(ui.loading)}</div>`;
    const banner = this._cfg.loaded ? "" : `<div class="card banner"><ha-icon icon="mdi:alert-outline"></ha-icon><span>${esc(ui.notLoaded)}</span></div>`;
    if (this._edit) return banner + this._editor();
    switch (this._tab) {
      case "overview":
        return banner + this._overview();
      case "windows":
        return banner + this._windowsTab();
      case "groups":
        return banner + this._groupsTab();
      default:
        return banner + `<div class="grid">${(SETTINGS[this._tab] || []).map((card) => this._settingsCard(card)).join("")}</div>`;
    }
  }

  _rerenderContent(focusSelector) {
    const content = this.shadowRoot.querySelector(".content");
    if (!content) return;
    content.innerHTML = this._content();
    if (focusSelector) content.querySelector(focusSelector)?.focus();
    this._sig = this._signature();
  }

  _datalists() {
    if (!this._hass || !this._cfg) return "";
    const all = Object.keys(this._hass.states).sort();
    const option = (id) => `<option value="${esc(id)}">${esc(this._name(id))}</option>`;
    const lists = new Map([["dl-all", all]]);
    for (const info of Object.values(this._cfg.fields || {})) {
      const domains = info.entity?.domain;
      if (domains?.length) lists.set(this._listId(domains), all.filter((id) => domains.includes(id.split(".")[0])));
    }
    let html = [...lists].map(([id, ids]) => `<datalist id="${id}">${ids.map(option).join("")}</datalist>`).join("");
    html += `<datalist id="dl-services">${(this._cfg.notify_services || []).map((s) => `<option value="${esc(s)}"></option>`).join("")}</datalist>`;
    for (const [key, info] of Object.entries(this._cfg.fields || {})) {
      const options = info.select?.custom_value ? info.select.options || [] : [];
      if (options.length && key !== "notify_services") {
        html += `<datalist id="dl-opt-${esc(key)}">${options.map((o) => `<option value="${esc(o.value ?? o)}"></option>`).join("")}</datalist>`;
      }
    }
    return html;
  }

  _listId(domains) {
    return domains?.length ? `dl-${domains.join("-")}` : "dl-all";
  }

  // ------------------------------------------------------------------ live updates

  _liveIds() {
    const cfg = this._cfg;
    const ids = [...Object.values(cfg.entities || {}), "sun.sun", cfg.options.outdoor_temperature, ...(cfg.options.vacation_entities || [])];
    for (const win of this._windows) {
      ids.push(...Object.values(win.entities || {}), win.data.cover, ...(win.data.window_sensors || []), ...(win.data.tilt_sensors || []));
    }
    for (const group of this._groups) {
      for (const [, sensors] of KINDS) ids.push(...(group.data[sensors] || []));
    }
    return ids.filter(Boolean);
  }

  _signature() {
    if (!this._hass || !this._cfg) return "";
    return this._liveIds()
      .map((id) => {
        const st = this._state(id);
        if (!st) return `${id}=-`;
        if (id === "sun.sun") return `${id}=${Math.round(st.attributes.azimuth || 0)}|${Math.round(st.attributes.elevation || 0)}`;
        return `${id}=${st.state}|${st.last_updated}`;
      })
      .join(";");
  }

  _live() {
    if (!this._cfg) return;
    // entities of a new window exist only after the integration reloaded
    if (this._windows.some((w) => !w.entities?.status) && Date.now() - (this._lastLoad || 0) > 4000) {
      this._load(true);
      return;
    }
    const sig = this._signature();
    if (sig === this._sig) return;
    // fast changing sensors: redraw at most every few seconds and not during a click
    const wait = Math.max((this._lastLive || 0) + 3000, (this._lastPointer || 0) + 1500) - Date.now();
    if (wait > 0) {
      if (!this._liveTimer) {
        this._liveTimer = setTimeout(() => {
          this._liveTimer = null;
          this._live();
        }, wait);
      }
      return;
    }
    this._sig = sig;
    this._lastLive = Date.now();
    if (this._edit) {
      // only the read-only blocks of an editor follow the states
      for (const el of this.shadowRoot.querySelectorAll("[data-live-block]")) {
        el.innerHTML = this._liveBlock(el.dataset.liveBlock);
      }
      return;
    }
    if (["overview", "windows", "groups"].includes(this._tab) && !this._typing()) {
      const content = this.shadowRoot.querySelector(".content");
      if (content) content.innerHTML = this._content();
    }
  }

  _liveBlock(name) {
    if (name === "check" && this._edit?.id) {
      const win = this._windows.find((w) => w.id === this._edit.id);
      return win ? this._sunCheck(win) : "";
    }
    if (name === "compass" && this._edit?.type === "group") return this._groupPreview();
    return "";
  }

  // ------------------------------------------------------------------ window state helpers

  _status(win) {
    const st = this._state(win.entities?.status);
    return st && !INVALID.includes(st.state) ? st.state : null;
  }

  _statusPill(win) {
    const status = this._status(win);
    if (!status) return `<span class="pill muted">${esc(win.entities?.status ? this.ui.unavailable : this.ui.loading)}</span>`;
    const [, cls] = STATUS_STYLE[status] || ["", ""];
    return `<span class="pill ${cls}">${esc((STATUS[this.lang] || STATUS.en)[status] || status)}</span>`;
  }

  _position(win) {
    const st = this._state(win.data.cover);
    if (!st || INVALID.includes(st.state)) return null;
    const pos = st.attributes.current_position;
    if (pos !== undefined && pos !== null) return Number(pos);
    if (st.state === "open") return 100;
    if (st.state === "closed") return 0;
    return null;
  }

  _shutter(position) {
    const closed = position === null ? 0 : 100 - position;
    return `<span class="shutter ${position === null ? "na" : ""}"><span class="slats" style="height:${closed}%"></span></span>`;
  }

  _windowOpen(win) {
    const attrs = this._state(win.entities?.status)?.attributes;
    if (attrs && "window_open" in attrs) return !!attrs.window_open;
    return (win.data.window_sensors || []).some((id) => this._state(id)?.state !== "off");
  }

  _windowTilted(win) {
    return !!this._state(win.entities?.status)?.attributes?.window_tilted;
  }

  // ------------------------------------------------------------------ overview

  _overview() {
    return `<div class="grid">${this._statusCard()}${this._compassCard()}${this._hintsCard()}</div>
      <div class="section-title"><ha-icon icon="mdi:window-shutter"></ha-icon>${esc(this.ui.cards.windows[0])}</div>
      ${this._windows.length ? `<div class="grid tiles-grid">${this._windows.map((w) => this._windowTile(w)).join("")}</div>` : this._emptyWindows()}`;
  }

  _emptyWindows() {
    return `<div class="card"><div class="muted">${esc(this.ui.noWindows)}</div>
      <div class="actions"><button class="btn primary" data-new="window"><ha-icon icon="mdi:plus"></ha-icon>${esc(this.ui.add)}</button></div></div>`;
  }

  _statusCard() {
    const ui = this.ui;
    const cfg = this._cfg;
    const ent = cfg.entities || {};
    const auto = this._state(ent.automatic);
    const on = auto?.state === "on";
    const statuses = this._windows.map((w) => this._status(w));
    const count = (s) => statuses.filter((x) => x === s).length;

    const summer = this._state(ent.summer_day);
    const sa = summer?.attributes || {};
    const threshold = this._num(cfg.options.summer_threshold);
    let summerText = summer ? (summer.state === "on" ? ui.yes : ui.no) : ui.unavailable;
    if (summer) {
      if (sa.raised_by_outdoor_temperature && summer.state === "on") summerText += ` (${ui.raised})`;
      else summerText += ` (${sa.forecast_max !== null && sa.forecast_max !== undefined ? ui.forecast(this._num(sa.forecast_max), threshold, this._unit) : ui.noForecast})`;
    }
    const evening = this._state(ent.evening_mode);
    const ea = evening?.attributes || {};
    const eveningText = !evening ? ui.unavailable : evening.state === "on" ? ui.eveningActive(this._time(ea.end)) : ea.start ? ui.eveningAt(this._time(ea.start)) : ui.off;
    const facts = [
      ["mdi:white-balance-sunny", ui.summer, summerText, summer?.state === "on" ? "warn" : ""],
      ["mdi:weather-night", ui.evening, eveningText, evening?.state === "on" ? "indigo" : ""],
    ];
    const vacationIds = cfg.options.vacation_entities || [];
    if (vacationIds.length) {
      const vac = vacationIds.some((id) => this._state(id)?.state === "on");
      facts.push(["mdi:airplane", ui.vacation, vac ? ui.on : ui.off, vac ? "teal" : ""]);
    }
    for (const [kind, icon] of [["wind", "mdi:weather-windy"], ["rain", "mdi:weather-pouring"], ["frost", "mdi:snowflake"]]) {
      const guard = this._state(ent[`${kind}_protection`]);
      if (!guard) continue;
      const active = guard.state === "on";
      const release = guard.attributes?.release_at;
      facts.push([icon, ui.protections[kind], active ? (release ? ui.until(this._time(release)) : ui.on) : ui.off, active ? "danger" : ""]);
    }
    const restart = auto?.attributes?.restart_protection_until;
    if (restart) facts.push(["mdi:restart", ui.restart, ui.until(this._time(restart)), "muted"]);

    return `<div class="card status">
      <div class="status-main">
        <ha-icon icon="${on ? "mdi:window-shutter-auto" : "mdi:window-shutter-alert"}" class="${on ? "on" : "offc"}"></ha-icon>
        <div class="grow">
          <div class="status-text">${esc(auto ? (on ? ui.automaticOn : ui.automaticOff) : ui.unavailable)}</div>
          <div class="muted">${esc(ui.summary(this._windows.length, count("sun_protection"), count("override")))}</div>
        </div>
        ${auto ? `<button class="btn ${on ? "" : "primary"}" data-action="toggle-automatic"><ha-icon icon="mdi:power"></ha-icon>${esc(on ? ui.turnOff : ui.turnOn)}</button>` : ""}
      </div>
      <div class="facts">${facts
        .map(([icon, name, value, cls]) => `<div class="fact ${cls}"><ha-icon icon="${icon}"></ha-icon><span class="fact-name">${esc(name)}</span><span class="fact-value">${esc(value)}</span></div>`)
        .join("")}</div>
    </div>`;
  }

  _hintsCard() {
    const ui = this.ui;
    const cfg = this._cfg;
    const hints = [];
    const exists = (id) => !!this._state(id);
    const check = (where, ids) => {
      for (const id of ids.filter(Boolean)) if (!exists(id)) hints.push(["mdi:alert-outline", ui.missing(where, id)]);
    };
    const o = cfg.options;
    check(ui.global, [o.outdoor_temperature, o.weather, o.workday_entity, o.heating_entity, o.wind_entity, o.rain_entity, ...(o.vacation_entities || [])]);
    for (const svc of o.notify_services || []) {
      if (!(cfg.notify_services || []).includes(svc)) hints.push(["mdi:alert-outline", ui.missing(ui.global, svc)]);
    }
    for (const group of this._groups) check(group.title, KINDS.flatMap(([, sensors]) => group.data[sensors] || []));
    for (const win of this._windows) {
      const d = win.data;
      check(win.title, [d.cover, ...(d.window_sensors || []), ...(d.tilt_sensors || []), d.room_entity, d.cooling_entity, d.open_block_entity, d.window_exception_entity, ...(d.close_trigger_entities || []), d.morning_enabled && d.morning_mode === "trigger" ? d.morning_trigger_entity : null]);
      if (d.group && !this._group(d.group)) hints.push(["mdi:alert-outline", ui.missingGroup(win.title)]);
    }
    if (!o.weather && !o.outdoor_temperature) hints.push(["mdi:alert-outline", ui.noTemperature]);
    else if (!o.weather) hints.push(["mdi:information-outline", ui.noWeather]);
    return `<div class="card">
      <h2><ha-icon icon="mdi:information-outline"></ha-icon>${esc(ui.hints)}</h2>
      ${hints.length
        ? `<div class="rows">${hints.map(([icon, text]) => `<div class="row ${icon.includes("alert") ? "warn-row" : "info-row"}"><ha-icon icon="${icon}"></ha-icon><span>${esc(text)}</span></div>`).join("")}</div>`
        : `<div class="muted">${esc(ui.noHints)}</div>`}
    </div>`;
  }

  _windowTile(win) {
    const ui = this.ui;
    const d = this._windowData(win);
    const status = this._status(win);
    const [icon] = STATUS_STYLE[status] || ["mdi:window-shutter"];
    const position = this._position(win);
    const group = this._group(d.group);
    const open = this._windowOpen(win);
    const tilted = this._windowTilted(win);
    const next = this._state(win.entities?.next_action);
    const nextText = next && !INVALID.includes(next.state) ? (NEXT_ACTION[this.lang] || NEXT_ACTION.en)[next.attributes.action] || "" : "";
    const override = this._state(win.entities?.override);
    const reason = this._state(win.entities?.last_reason);
    const reasonText = reason && !INVALID.includes(reason.state) ? reason.state : "";
    const reasonTime = reason?.attributes?.time ? this._time(reason.attributes.time) : "";
    const expanded = this._expanded.has(win.id);
    const overrideRow =
      override?.state === "on"
        ? `<div class="row override-row"><ha-icon icon="mdi:hand-back-right-outline"></ha-icon>
            <span class="grow">${esc(ui.override)} ${esc(override.attributes.until ? ui.until(this._time(override.attributes.until)) : ui.untilSunrise)}</span>
            <button class="btn small" data-action="end-override" data-id="${esc(win.id)}">${esc(ui.endOverride)}</button></div>`
        : "";
    return `<div class="card tile-card">
      <div class="tile-head">
        ${this._shutter(position)}
        <div class="tile-name">
          <div class="tile-title"><ha-icon icon="${icon}"></ha-icon>${esc(win.title)}</div>
          <div class="muted small">${esc(position === null ? ui.unavailable : `${ui.position} ${position} %`)} · ${esc(ui.window)} ${esc(open ? ui.open : tilted ? ui.tilted : ui.closed)}</div>
        </div>
        ${this._statusPill(win)}
      </div>
      <div class="rows">
        <div class="row"><ha-icon icon="mdi:compass-outline" style="color:${group ? this._groupColor(group.id) : "var(--disabled-text-color)"}"></ha-icon>
          <span class="grow">${esc(ui.group)}</span><span class="muted">${esc(group ? group.title : ui.none)}</span></div>
        ${reasonText ? `<div class="row"><ha-icon icon="mdi:history"></ha-icon><span class="grow reason">${esc(reasonText)}</span><span class="muted">${esc(reasonTime)}</span></div>` : ""}
        ${nextText ? `<div class="row"><ha-icon icon="mdi:clock-outline"></ha-icon><span class="grow">${esc(ui.nextAction)}: ${esc(nextText)}</span><span class="muted">${esc(this._time(next.state))}</span></div>` : ""}
        ${overrideRow}
      </div>
      ${expanded && group ? `<div class="check-wrap">${this._sunCheck(win)}</div>` : ""}
      <div class="actions">
        ${group ? `<button class="btn" data-action="expand" data-id="${esc(win.id)}"><ha-icon icon="mdi:${expanded ? "chevron-up" : "white-balance-sunny"}"></ha-icon>${esc(ui.sunCheck)}</button>` : ""}
        <button class="btn" data-edit="window" data-id="${esc(win.id)}"><ha-icon icon="mdi:pencil-outline"></ha-icon>${esc(ui.edit)}</button>
      </div>
    </div>`;
  }

  // Sun condition, part by part, from the attributes of the sun condition sensor
  _sunCheck(win) {
    const ui = this.ui;
    const c = ui.check;
    const sensor = this._state(win.entities?.sun_condition);
    if (!sensor || INVALID.includes(sensor.state)) return `<div class="muted small">${esc(win.entities?.sun_condition ? ui.unavailable : ui.loading)}</div>`;
    const a = sensor.attributes;
    const rows = [];
    const row = (state, label, detail) => rows.push([state, label, detail]);
    const has = (v) => v !== null && v !== undefined;
    const unit = a.temperature_unit || this._unit;
    const forecastText = has(a.forecast_max) ? ui.forecast(this._num(a.forecast_max), this._num(a.summer_threshold), unit) : ui.noForecast;
    const byForecast = has(a.forecast_max) && Number(a.forecast_max) >= Number(a.summer_threshold);
    row(a.summer_day ? "ok" : "fail", c.summer, a.raised_by_outdoor_temperature && !byForecast ? c.raisedText(forecastText) : forecastText);
    if (a.raised_by_outdoor_temperature && !byForecast && has(a.night_threshold)) {
      const nightOk = !has(a.night_low) || Number(a.night_low) >= Number(a.night_threshold);
      row(nightOk ? "ok" : "fail", c.night, has(a.night_low) ? c.nightText(this._num(a.night_low), this._num(a.night_threshold), unit) : c.noNight);
    }
    const temp = has(a.outdoor_temperature) ? `${this._num(a.outdoor_temperature)} ${unit}` : c.noValue;
    row(
      a.temperature_ok ? "ok" : a.temperature_ok_at ? "wait" : "fail",
      c.temperature,
      `${temp}, ${c.from} ${this._num(a.temperature_threshold)} ${unit}${a.temperature_ok_at ? ` · ${c.pendingAt(this._time(a.temperature_ok_at))}` : ""}`,
    );
    for (const [kind] of KINDS) {
      const info = a.sensors?.[kind];
      if (!info) continue;
      for (const id of info.entities || []) {
        const st = this._state(id);
        const value = st && !INVALID.includes(st.state) ? Number(st.state) : null;
        const unit = st?.attributes?.unit_of_measurement || "";
        const ok = value !== null && !Number.isNaN(value) && value >= Number(info.threshold);
        row(ok ? "ok" : "fail", `${ui.kinds[kind]}: ${this._name(id)}`, `${value === null || Number.isNaN(value) ? c.noValue : `${this._num(value, 0)} ${unit}`}, ${c.from} ${this._num(info.threshold, 0)} ${unit}`);
      }
    }
    if (a.room_entity) {
      row(
        a.room_warm === false ? "fail" : "ok",
        `${c.room}: ${this._name(a.room_entity)}`,
        has(a.room_temperature) ? c.roomText(this._num(a.room_temperature), this._num(a.room_limit), unit) : c.roomUnknown,
      );
    }
    if (a.cooling_entity) row(a.cooling ? "ok" : "muted", `${c.cooling}: ${this._name(a.cooling_entity)}`, a.cooling ? c.coolingOn : c.coolingOff);
    if (a.heating_entity) row(a.heating_day ? (a.heat_need ? "ok" : "fail") : "ok", `${c.heating}: ${this._name(a.heating_entity)}`, a.heating_day ? c.heatingOn : c.heatingOff);
    row(sensor.state === "on" ? "ok" : a.condition_on_at ? "wait" : "fail", c.hold, a.condition_on_at ? c.pendingAt(this._time(a.condition_on_at)) : c.holdText(this._num(a.sun_hold, 0)));
    const sunAz = this._state("sun.sun")?.attributes?.azimuth;
    row(a.in_sector ? "ok" : "fail", c.sector, sunAz !== undefined ? c.sectorText(this._num(sunAz, 0), this._num(a.azimuth_from, 0), this._num(a.azimuth_to, 0)) : `${this._num(a.azimuth_from, 0)}° – ${this._num(a.azimuth_to, 0)}°`);
    const today = this._state(win.entities?.sun_protection_today)?.state === "on";
    const icons = { ok: "mdi:check-circle", fail: "mdi:close-circle-outline", wait: "mdi:timer-sand", muted: "mdi:minus-circle-outline" };
    return `<div class="check">
      <div class="check-result ${sensor.state === "on" ? "ok" : ""}"><ha-icon icon="mdi:white-balance-sunny"></ha-icon>
        <span class="grow">${esc(sensor.state === "on" ? c.on : c.off)}</span>
        <span class="pill ${today ? "warn" : "muted"}">${esc(c.today)}: ${esc(today ? ui.yes : ui.no)}</span></div>
      ${rows
        .map(([state, label, detail]) => `<div class="check-row ${state}"><ha-icon icon="${icons[state]}"></ha-icon><span class="check-label">${esc(label)}</span><span class="check-detail">${esc(detail)}</span></div>`)
        .join("")}
    </div>`;
  }

  // ------------------------------------------------------------------ sun compass

  _compassCard() {
    const ui = this.ui;
    const [title, desc] = ui.cards.compass;
    const sun = this._state("sun.sun")?.attributes;
    const legend = this._groups
      .map((g) => {
        const from = Number(g.data.azimuth_from);
        const to = Number(g.data.azimuth_to);
        const count = this._windows.filter((w) => w.data.group === g.id).length;
        const active = sun && inSector(Number(sun.azimuth), from, to);
        return `<button class="row link" data-edit="group" data-id="${esc(g.id)}"><span class="dot" style="background:${this._groupColor(g.id)}"></span>
          <span class="grow"><span class="two-line">${esc(g.title)}</span><span class="muted small">${esc(`${this._num(from, 0)}°–${this._num(to, 0)}° · ${ui.compass.windowsCount(count)}`)}</span></span>
          ${active ? `<span class="pill warn">${esc(ui.compass.inSector)}</span>` : ""}</button>`;
      })
      .join("");
    const layers = this._houseLayers(this._house(), { clickable: true });
    return `<div class="card">
      <h2><ha-icon icon="mdi:compass-rose"></ha-icon>${esc(title)}</h2><p class="desc">${esc(desc)}</p>
      <div class="compass-wrap">${this._compassSvg(this._groups.map((g) => ({ id: g.id, from: g.data.azimuth_from, to: g.data.azimuth_to, color: this._groupColor(g.id) })), layers)}</div>
      ${this._sunText()}${this._markerLegend(layers)}
      <div class="rows">${legend || `<div class="muted">${esc(ui.noGroups)}</div>`}</div>
    </div>`;
  }

  _sunText() {
    const ui = this.ui;
    const sun = this._state("sun.sun")?.attributes;
    if (!sun || sun.azimuth === undefined) return `<div class="muted small center">${esc(ui.compass.noSun)}</div>`;
    const below = Number(sun.elevation) < 0;
    return `<div class="sun-text"><ha-icon icon="${below ? "mdi:weather-night" : "mdi:white-balance-sunny"}"></ha-icon>
      ${esc(`${ui.compass.azimuth} ${this._num(sun.azimuth, 0)}° (${this._dir(sun.azimuth)}) · ${ui.compass.elevation} ${this._num(sun.elevation, 0)}°`)}${below ? ` · ${esc(ui.compass.below)}` : ""}</div>`;
  }

  // sectors: [{from, to, color, highlight, faint}]
  // layers: {house, walls: {wall: color}, markers: [{id, wall, color, open, title}], labels}
  _compassSvg(sectors, layers = {}) {
    const size = 240;
    const c = size / 2;
    const outer = 92;
    const house = layers.house;
    const point = (az, r) => [c + r * Math.sin((az * Math.PI) / 180), c - r * Math.cos((az * Math.PI) / 180)];
    const arc = (from, to, r1, r2) => {
      let span = (((to - from) % 360) + 360) % 360;
      if (span === 0) span = 360;
      if (span >= 360) span = 359.99;
      const end = from + span;
      const large = span > 180 ? 1 : 0;
      const [x1, y1] = point(from, r2);
      const [x2, y2] = point(end, r2);
      const [x3, y3] = point(end, r1);
      const [x4, y4] = point(from, r1);
      return `M${x1.toFixed(2)} ${y1.toFixed(2)} A${r2} ${r2} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} L${x3.toFixed(2)} ${y3.toFixed(2)} A${r1} ${r1} 0 ${large} 0 ${x4.toFixed(2)} ${y4.toFixed(2)} Z`;
    };
    const count = Math.max(1, sectors.length);
    // with a house the rings get narrower so the house has room in the middle
    const band = house ? Math.max(3, Math.min(14, (30 - 2 * count) / count)) : Math.max(8, Math.min(18, 54 / count));
    const rings = sectors
      .map((s, i) => {
        const r2 = outer - 2 - i * (band + 2);
        const r1 = r2 - band;
        const from = Number(s.from);
        const to = Number(s.to);
        if (Number.isNaN(from) || Number.isNaN(to) || from === to) return "";
        const opacity = s.faint ? 0.25 : s.highlight ? 0.95 : 0.7;
        return `<path d="${arc(from, to, r1, r2)}" fill="${s.color}" fill-opacity="${opacity}" stroke="${s.color}" stroke-width="${s.highlight ? 2 : 1}"></path>`;
      })
      .join("");
    let ticks = "";
    for (let az = 0; az < 360; az += 15) {
      if (az % 90 === 0) continue;
      const long = az % 45 === 0;
      const [x1, y1] = point(az, outer + 2);
      const [x2, y2] = point(az, outer + (long ? 9 : 5));
      ticks += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" class="tick ${long ? "long" : ""}"></line>`;
    }
    const dirs = this.ui.dirs;
    const labels = [0, 90, 180, 270]
      .map((az, i) => {
        const [x, y] = point(az, outer + 15);
        return `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" class="dir">${dirs[i * 2]}</text>`;
      })
      .join("");
    const inner = outer - 2 - (sectors.length ? sectors.length * (band + 2) : 0) - 6;
    // the sun is drawn over the house, the window markers and labels over the sun
    const houseSvg = house ? this._houseSvg(house, layers, c, inner) : { base: "", top: "" };
    const sun = this._state("sun.sun")?.attributes;
    let sunRay = "";
    let sunMark = "";
    if (sun && sun.azimuth !== undefined) {
      const az = Number(sun.azimuth);
      const el = Number(sun.elevation);
      const below = el < 0;
      const r = below ? outer + 6 : Math.max(0, outer * (1 - Math.min(90, el) / 90));
      const [x, y] = point(az, r);
      const [rx, ry] = point(az, outer + 6);
      sunRay = `<line x1="${c}" y1="${c}" x2="${rx.toFixed(1)}" y2="${ry.toFixed(1)}" class="sun-ray ${below ? "below" : ""}"></line>`;
      sunMark = `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${below ? 6 : 9}" class="sun ${below ? "below" : ""}"></circle>`;
    }
    return `<svg viewBox="0 0 ${size} ${size}" class="compass" role="img">
      <circle cx="${c}" cy="${c}" r="${outer}" class="ring"></circle>
      <circle cx="${c}" cy="${c}" r="${(outer * 2) / 3}" class="ring inner"></circle>
      <circle cx="${c}" cy="${c}" r="${outer / 3}" class="ring inner"></circle>
      ${ticks}${rings}${labels}${sunRay}${houseSvg.base}${sunMark}${houseSvg.top}
      ${house ? "" : `<circle cx="${c}" cy="${c}" r="2.5" class="center"></circle>`}
    </svg>`;
  }

  // the house as a turned rectangle in the middle of the compass, scaled to the free room
  _houseSvg(house, layers, c, inner) {
    const u = (az) => [Math.sin((az * Math.PI) / 180), -Math.cos((az * Math.PI) / 180)];
    const [fx, fy] = u(house.az);
    const [rx, ry] = u(house.az + 90);
    const room = Math.max(12, inner) * (layers.labels ? 0.68 : 0.9);
    const scale = room / (0.5 * Math.hypot(house.width, house.depth));
    const hw = (house.width / 2) * scale;
    const hd = (house.depth / 2) * scale;
    // f: towards the front, r: towards the right (seen from inside)
    const pt = (f, r) => [c + fx * f + rx * r, c + fy * f + ry * r];
    const n = (v) => v.toFixed(1);
    const line = ([x1, y1], [x2, y2]) => `x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}"`;
    const points = (list) => list.map(([x, y]) => `${n(x)},${n(y)}`).join(" ");
    const FL = pt(hd, -hw);
    const FR = pt(hd, hw);
    const BR = pt(-hd, hw);
    const BL = pt(-hd, -hw);
    const walls = { front: [FL, FR], right: [FR, BR], back: [BR, BL], left: [BL, FL] };
    const ridge = house.width >= house.depth ? line(pt(0, -hw * 0.8), pt(0, hw * 0.8)) : line(pt(-hd * 0.8, 0), pt(hd * 0.8, 0));
    let svg = `<polygon points="${points([FL, FR, BR, BL])}" class="house"></polygon><line ${ridge} class="ridge"></line>`;
    for (const [wall, color] of Object.entries(layers.walls || {})) {
      if (walls[wall]) svg += `<line ${line(...walls[wall])} class="wall-mark" style="stroke:${color}"><title>${esc(this._wallName(house, wall))}</title></line>`;
    }
    svg += `<polygon points="${points([pt(hd + 7, 0), pt(hd + 2, -4), pt(hd + 2, 4)])}" class="front-mark"><title>${esc(this.ui.front)}</title></polygon>`;
    let top = "";
    const byWall = {};
    for (const m of layers.markers || []) (byWall[m.wall] ||= []).push(m);
    for (const [wall, list] of Object.entries(byWall)) {
      if (!walls[wall]) continue;
      const [[x1, y1], [x2, y2]] = walls[wall];
      const length = Math.hypot(x2 - x1, y2 - y1) || 1;
      const half = Math.min(5, (length / (list.length + 1)) * 0.4);
      const [dx, dy] = [(x2 - x1) / length, (y2 - y1) / length];
      list.forEach((m, i) => {
        const t = (i + 1) / (list.length + 1);
        const [mx, my] = [x1 + (x2 - x1) * t, y1 + (y2 - y1) * t];
        const ends = [[mx - dx * half, my - dy * half], [mx + dx * half, my + dy * half]];
        const edit = layers.clickable ? ` data-edit="window" data-id="${esc(m.id)}"` : "";
        top += `<g class="marker ${layers.clickable ? "link" : ""}"${edit}><title>${esc(m.title)}</title>
          <line ${line(...ends)} class="marker-edge"></line><line ${line(...ends)} class="marker-line" style="stroke:${m.color}"></line>${m.open ? `<line ${line(...ends)} class="marker-open"></line>` : ""}</g>`;
      });
    }
    if (layers.labels) {
      for (const [wall, offset] of WALLS) {
        const [[x1, y1], [x2, y2]] = walls[wall];
        const [nx, ny] = u(house.az + offset);
        const facing = this._wallFacing(house, wall);
        top += `<text x="${n((x1 + x2) / 2 + nx * 10)}" y="${n((y1 + y2) / 2 + ny * 10)}" class="wall-label">${esc(this._dir(facing))}</text>`;
      }
    }
    return { base: `<g class="house-layer">${svg}</g>`, top: `<g class="house-layer">${top}</g>` };
  }

  // compass of the house card (values being edited)
  _housePreview() {
    const values = {};
    for (const key of ["house_azimuth", "house_width", "house_depth"]) values[key] = this._value("house", key);
    const house = this._house(values);
    const layers = house ? { ...this._houseLayers(house), labels: true } : {};
    const walls = house
      ? `<div class="wall-list">${WALLS.map(([wall]) => `<span class="chip">${esc(this._wallName(house, wall))}</span>`).join("")}</div>`
      : `<div class="muted small center">${esc(this.ui.houseIncomplete)}</div>`;
    return `${this._compassSvg([], layers)}${walls}`;
  }

  // ------------------------------------------------------------------ windows tab

  _windowsTab() {
    const ui = this.ui;
    const [title, desc] = ui.cards.windows;
    const rows = this._windows
      .map((win) => {
        const group = this._group(win.data.group);
        const position = this._position(win);
        const status = this._status(win);
        const [icon] = STATUS_STYLE[status] || ["mdi:window-shutter"];
        return `<tr data-edit="window" data-id="${esc(win.id)}">
          <td class="c-icon"><ha-icon icon="${icon}"></ha-icon></td>
          <td class="c-name"><div>${esc(win.title)}</div><div class="muted small entity-id">${esc(win.data.cover)}</div></td>
          <td class="hide-narrow">${group ? `<span class="dot" style="background:${this._groupColor(group.id)}"></span> ${esc(group.title)}` : `<span class="muted">${esc(ui.none)}</span>`}</td>
          <td class="c-state">${this._statusPill(win)}</td>
          <td class="c-pos hide-narrow">${this._shutter(position)} ${esc(position === null ? "" : `${position} %`)}</td>
          <td class="c-edit hide-narrow"><ha-icon icon="mdi:pencil-outline" class="muted"></ha-icon></td>
        </tr>`;
      })
      .join("");
    return `<div class="card">
      <h2><ha-icon icon="mdi:window-shutter"></ha-icon>${esc(title)}</h2><p class="desc">${esc(desc)}</p>
      ${this._windows.length
        ? `<div class="table-wrap"><table><thead><tr><th class="c-icon"></th><th class="c-name">${esc(ui.columns.name)}</th><th class="hide-narrow c-group">${esc(ui.columns.group)}</th><th class="c-state">${esc(ui.columns.status)}</th><th class="hide-narrow c-pos">${esc(ui.columns.position)}</th><th class="c-edit hide-narrow"></th></tr></thead><tbody>${rows}</tbody></table></div>`
        : `<div class="muted">${esc(ui.noWindows)}</div>`}
      <div class="actions"><button class="btn primary" data-new="window"><ha-icon icon="mdi:plus"></ha-icon>${esc(ui.add)}</button></div>
    </div>`;
  }

  // ------------------------------------------------------------------ groups tab

  _sensorValue(id) {
    const st = this._state(id);
    if (!st || INVALID.includes(st.state)) return this.ui.unavailable;
    return `${this._num(st.state, 0)} ${st.attributes.unit_of_measurement || ""}`.trim();
  }

  _groupsTab() {
    const ui = this.ui;
    const sun = this._state("sun.sun")?.attributes;
    const cards = this._groups
      .map((g) => {
        const from = Number(g.data.azimuth_from);
        const to = Number(g.data.azimuth_to);
        const windows = this._windows.filter((w) => w.data.group === g.id);
        const active = sun && inSector(Number(sun.azimuth), from, to);
        const sensors = KINDS.flatMap(([kind, key, , icon]) =>
          (g.data[key] || []).map(
            (id) => `<div class="row"><ha-icon icon="${icon}"></ha-icon><span class="grow">${esc(this._name(id))}</span><span class="muted">${esc(this._sensorValue(id))}</span></div>`,
          ),
        ).join("");
        return `<div class="card">
          <h2><span class="dot big" style="background:${this._groupColor(g.id)}"></span>${esc(g.title)}${active ? ` <span class="pill warn">${esc(ui.compass.inSector)}</span>` : ""}</h2>
          <p class="desc">${esc(`${this._num(from, 0)}° (${this._dir(from)}) – ${this._num(to, 0)}° (${this._dir(to)})`)}</p>
          <div class="rows">${sensors || `<div class="muted">${esc(ui.none)}</div>`}</div>
          <div class="muted small used">${esc(windows.length ? `${ui.usedBy}: ${windows.map((w) => w.title).join(", ")}` : ui.unused)}</div>
          <div class="actions"><button class="btn" data-edit="group" data-id="${esc(g.id)}"><ha-icon icon="mdi:pencil-outline"></ha-icon>${esc(ui.edit)}</button></div>
        </div>`;
      })
      .join("");
    return `<div class="grid">${this._compassCard()}${cards}</div>
      <div class="actions"><button class="btn primary" data-new="group"><ha-icon icon="mdi:plus"></ha-icon>${esc(ui.add)}</button></div>`;
  }

  // ------------------------------------------------------------------ settings cards (global)

  _value(cardId, key) {
    const draft = this._drafts[cardId];
    if (draft && key in draft) return draft[key];
    return this._cfg.options[key];
  }

  _settingsCard(card) {
    const ui = this.ui;
    const [title, desc] = ui.cards[card.id] || [card.id, ""];
    const dirty = !!this._drafts[card.id];
    const errors = this._errors[card.id] || {};
    const fields = card.fields.map((key) => this._field(card.id, key, this._value(card.id, key), errors[key])).join("");
    const preview = card.preview ? `<div class="compass-wrap small" data-house-preview>${this._housePreview()}</div>` : "";
    return `<div class="card" data-card="${card.id}">
      <h2><ha-icon icon="${card.icon}"></ha-icon>${esc(title)}</h2>${desc ? `<p class="desc">${esc(desc)}</p>` : ""}
      ${preview}<div class="fields">${fields}</div>
      <div class="actions"><span class="msg ${Object.keys(errors).length ? "bad" : ""}">${Object.keys(errors).length ? esc(this._errorSummary(errors, card.fields)) : ""}</span>
        ${dirty ? `<button class="btn" data-cancel="${card.id}">${esc(ui.cancel)}</button>` : ""}
        <button class="btn primary" data-save="${card.id}" ${dirty ? "" : "disabled"}>${esc(ui.save)}</button></div></div>`;
  }

  _errorText(code) {
    return (ERRORS[this.lang] || ERRORS.en)[code] || this.ui.fieldErrors[code] || code;
  }

  _errorSummary(errors, shown) {
    const hidden = Object.keys(errors).filter((key) => !shown.includes(key));
    if (!hidden.length) return this.ui.checkFields;
    return `${this.ui.checkFields} ${hidden.map((key) => `${this.label(key)[0]}: ${this._errorText(errors[key])}`).join(", ")}`;
  }

  // ------------------------------------------------------------------ fields

  _field(scope, key, value, error) {
    const ui = this.ui;
    const [name, help] = this.label(key);
    const attrs = `data-scope="${scope}" data-k="${key}"`;
    let extra = "";
    if (key === "wall_position") {
      const wall = this._edit?.data?.wall || this._group(this._edit?.data?.group)?.data?.wall;
      if (!this._house() || !wall) return "";
      const others = this._sortedOnWall(this._windows.filter((w) => w.id !== this._edit.id && this._windowWall(w) === wall));
      if (others.length) extra = `<small>${esc(ui.wallOthers(others.map((w) => this._wallLabel(w)).join(" · ")))}</small>`;
    }
    const helpHtml = (help ? `<small>${esc(help)}</small>` : "") + extra;
    const errHtml = error ? `<span class="field-error">${esc(this._errorText(error))}</span>` : "";
    const cls = `field ${error ? "invalid" : ""}`;
    if (key === "group") {
      return `<label class="${cls}"><span class="lbl">${esc(name)}</span><select ${attrs} data-kind="group">
        <option value="">${esc(ui.noGroup)}</option>
        ${this._groups.map((g) => `<option value="${esc(g.id)}" ${g.id === value ? "selected" : ""}>${esc(g.title)}</option>`).join("")}
        ${value && !this._group(value) ? `<option value="${esc(value)}" selected>${esc(value)} (${esc(ui.notFound)})</option>` : ""}
        </select>${errHtml}${helpHtml}</label>`;
    }
    if (key === "wall") {
      const house = this._house();
      const isWindow = this._edit?.type === "window";
      if (!house) return `<div class="field"><span class="lbl">${esc(ui.wall)}</span><small>${esc(ui.noHouse)}</small></div>`;
      const groupWall = isWindow ? this._group(this._edit.data.group)?.data?.wall : null;
      const empty = groupWall ? ui.likeGroup(this._wallName(house, groupWall)) : ui.noWall;
      return `<label class="${cls}"><span class="lbl">${esc(ui.wall)}</span><select ${attrs} data-kind="wall">
        <option value="">${esc(empty)}</option>
        ${WALLS.map(([wall]) => `<option value="${wall}" ${wall === value ? "selected" : ""}>${esc(this._wallName(house, wall))}</option>`).join("")}
        </select>${errHtml}<small>${esc(isWindow ? ui.wallHelpWindow : ui.wallHelpGroup)}</small></label>`;
    }
    const info = this._cfg.fields?.[key];
    if (!info) return "";
    const type = Object.keys(info)[0];
    const conf = info[type] || {};
    switch (type) {
      case "boolean":
        return `<label class="${cls} toggle-row"><span><span class="lbl">${esc(name)}</span>${helpHtml}</span>
          <input type="checkbox" class="switch-input" ${attrs} data-kind="boolean" ${value ? "checked" : ""}><span class="switch ${value ? "on" : ""}"></span></label>`;
      case "number": {
        const display = value === null || value === undefined ? "" : Number(value);
        return `<label class="${cls}"><span class="lbl">${esc(name)}</span><span class="with-unit">
          <input type="number" ${attrs} data-kind="number" value="${esc(display)}" min="${conf.min ?? ""}" max="${conf.max ?? ""}" step="${conf.step ?? "any"}">
          ${conf.unit_of_measurement ? `<span class="unit">${esc(conf.unit_of_measurement)}</span>` : ""}</span>${errHtml}${helpHtml}</label>`;
      }
      case "time":
        return `<label class="${cls}"><span class="lbl">${esc(name)}</span><input type="time" step="60" ${attrs} data-kind="time" value="${esc(String(value ?? "").slice(0, 5))}">${errHtml}${helpHtml}</label>`;
      case "text":
        return `<label class="${cls}"><span class="lbl">${esc(name)}</span><input type="text" ${attrs} data-kind="text" value="${esc(value ?? "")}">${errHtml}${helpHtml}</label>`;
      case "entity": {
        const listId = this._listId(conf.domain);
        if (conf.multiple) return this._chips(cls, name, attrs, "entities", Array.isArray(value) ? value : [], listId, errHtml + helpHtml);
        const st = value ? this._state(value) : null;
        const hint = value ? (st ? this._name(value) : `⚠ ${ui.notFound}`) : "";
        return `<label class="${cls}"><span class="lbl">${esc(name)}</span>
          <input type="text" list="${listId}" ${attrs} data-kind="entity" value="${esc(value ?? "")}" placeholder="${esc((conf.domain || ["entity"])[0])}.…" autocomplete="off">
          <span class="entity-hint ${value && !st ? "bad" : ""}">${esc(hint)}</span>${errHtml}${helpHtml}</label>`;
      }
      case "select": {
        const choices = this._choices(conf);
        if (conf.multiple && !conf.custom_value) {
          const chosen = Array.isArray(value) ? value : [];
          return `<div class="${cls}"><span class="lbl">${esc(name)}</span><div class="seg">
            ${choices.map(([k, v]) => `<button class="seg-btn ${chosen.includes(k) ? "on" : ""}" data-toggle="${esc(k)}" ${attrs}>${esc(v)}</button>`).join("")}
            </div>${errHtml}${helpHtml}</div>`;
        }
        if (conf.multiple) {
          const listId = key === "notify_services" ? "dl-services" : `dl-opt-${key}`;
          return this._chips(cls, name, attrs, key === "notify_services" ? "services" : "values", Array.isArray(value) ? value : [], listId, errHtml + helpHtml);
        }
        if (conf.mode === "list" && choices.length <= 4) {
          return `<div class="${cls}"><span class="lbl">${esc(name)}</span><div class="seg">
            ${choices.map(([k, v]) => `<button class="seg-btn ${k === value ? "on" : ""}" data-seg="${esc(k)}" ${attrs}>${esc(v)}</button>`).join("")}
            </div>${errHtml}${helpHtml}</div>`;
        }
        return `<label class="${cls}"><span class="lbl">${esc(name)}</span><select ${attrs} data-kind="select">
          ${choices.map(([k, v]) => `<option value="${esc(k)}" ${k === value ? "selected" : ""}>${esc(v)}</option>`).join("")}
          </select>${errHtml}${helpHtml}</label>`;
      }
      default:
        return "";
    }
  }

  _choices(conf) {
    const translated = conf.translation_key ? (CHOICES[this.lang] || CHOICES.en)[conf.translation_key] || {} : {};
    return (conf.options || []).map((o) => {
      const value = typeof o === "object" ? o.value : o;
      const labelText = typeof o === "object" ? o.label : translated[o] || o;
      return [value, labelText];
    });
  }

  _chips(cls, name, attrs, kind, list, listId, extra) {
    const ui = this.ui;
    const chips = list
      .map((item, i) => {
        let text = item;
        let bad = false;
        if (kind === "entities") {
          const st = this._state(item);
          text = st ? this._name(item) : item;
          bad = !st;
          if (st?.attributes?.unit_of_measurement && !INVALID.includes(st.state) && this._num(st.state) !== "") {
            text += ` · ${this._num(st.state, 0)} ${st.attributes.unit_of_measurement}`;
          }
        } else if (kind === "services") {
          text = prettyService(item);
          bad = !(this._cfg.notify_services || []).includes(item);
        }
        return `<span class="chip ${bad ? "bad" : ""}" title="${esc(item)}">${esc(text)}<button class="chip-btn" data-remove="${i}" ${attrs}>✕</button></span>`;
      })
      .join("");
    return `<div class="${cls}"><span class="lbl">${esc(name)}</span>
      <div class="chips">${chips}</div>
      <input type="text" list="${listId}" data-add="1" ${attrs} placeholder="${esc(ui.addValue)}" autocomplete="off">${extra}</div>`;
  }

  // ------------------------------------------------------------------ editors (window, group)

  _editor() {
    const ui = this.ui;
    const e = this._edit;
    const d = e.data;
    const isWindow = e.type === "window";
    const group = isWindow ? this._group(d.group) : null;
    const errors = e.errors || {};
    const shown = [];
    const cards = (isWindow ? WINDOW_CARDS : GROUP_CARDS)
      .map((card) => {
        const [title, desc] = ui.cards[card.id];
        let body;
        if (card.needsGroup && !group) {
          if (card.id !== "w_sun") return "";
          body = `<div class="muted">${esc(ui.sunNoGroup)}</div>`;
        } else {
          const keys = card.fields(d, group);
          shown.push(...keys);
          body = `<div class="fields">${keys.map((key) => this._field("edit", key, d[key], errors[key])).join("")}</div>`;
          if (card.id === "w_sun" && e.id) body = `<div class="check-wrap" data-live-block="check">${this._liveBlock("check")}</div>${body}`;
          if (card.id === "g_basics") body = `<div class="compass-wrap small" data-live-block="compass">${this._groupPreview()}</div>${body}`;
        }
        const extra = card.id === "w_sun" && group ? ` <span class="muted small">(${esc(group.title)})</span>` : "";
        return `<div class="card"><h2><ha-icon icon="${card.icon}"></ha-icon>${esc(title)}${extra}</h2>${desc ? `<p class="desc">${esc(desc)}</p>` : ""}${body}</div>`;
      })
      .join("");
    const win = isWindow && e.id ? this._windows.find((w) => w.id === e.id) : null;
    const title = d.name || (isWindow ? ui.newWindow : ui.newGroup);
    const hasErrors = Object.keys(errors).length > 0;
    return `<div class="card editor-head">
        <button class="icon-btn" data-action="close-edit" title="${esc(ui.cancel)}"><ha-icon icon="mdi:arrow-left"></ha-icon></button>
        <ha-icon icon="${isWindow ? "mdi:window-shutter" : "mdi:compass-outline"}"></ha-icon>
        <h2 class="head-title">${esc(title)}</h2>
        <div class="head-actions">
          ${win ? this._statusPill(win) : ""}
          ${e.id && isWindow ? `<button class="btn" data-action="duplicate"><ha-icon icon="mdi:content-copy"></ha-icon><span class="hide-narrow">${esc(ui.duplicate)}</span></button>` : ""}
          ${e.id ? `<button class="btn danger" data-action="delete-sub"><ha-icon icon="mdi:delete-outline"></ha-icon><span class="hide-narrow">${esc(ui.delete)}</span></button>` : ""}
        </div>
      </div>
      ${e.notice ? `<div class="card banner info"><ha-icon icon="mdi:information-outline"></ha-icon><span>${esc(e.notice)}</span></div>` : ""}
      <div class="grid editor-grid">${cards}</div>
      <div class="editor-actions">
        <span class="msg ${hasErrors ? "bad" : ""}">${hasErrors ? esc(this._errorSummary(errors, shown)) : ""}</span>
        <button class="btn" data-action="close-edit">${esc(ui.cancel)}</button>
        <button class="btn primary" data-action="save-sub" ${e.dirty || !e.id ? "" : "disabled"}><ha-icon icon="mdi:content-save-outline"></ha-icon>${esc(ui.save)}</button>
      </div>`;
  }

  _groupPreview() {
    const e = this._edit;
    if (!e || e.type !== "group") return "";
    const sectors = this._groups
      .filter((g) => g.id !== e.id)
      .map((g) => ({ from: g.data.azimuth_from, to: g.data.azimuth_to, color: this._groupColor(g.id), faint: true }));
    const color = e.id ? this._groupColor(e.id) : GROUP_COLORS[this._groups.length % GROUP_COLORS.length];
    sectors.unshift({ from: e.data.azimuth_from, to: e.data.azimuth_to, color, highlight: true });
    const layers = this._houseLayers(this._house(), { excludeGroup: e.id, extraWall: { wall: e.data.wall, color } });
    return `${this._compassSvg(sectors, layers)}${this._sunText()}`;
  }

  _openEditor(type, item, notice) {
    const defaults = clone(this._cfg.defaults?.[type] || {});
    const data = { ...defaults, ...clone(item?.data || {}) };
    if (item) data.name = data.name || item.title;
    if (type === "window") {
      // own evening times start from the global ones (like in the dialog)
      for (const key of ["evening_earliest", "evening_elevation", "evening_latest"]) {
        if (data[key] === undefined || data[key] === null) data[key] = this._cfg.options[key];
      }
    }
    this._edit = { type, id: item?.id || null, data, errors: {}, dirty: false, notice };
    this._rerenderContent();
    this._scrollTop();
  }

  _scrollTop() {
    this.shadowRoot.querySelector(".toolbar")?.scrollIntoView?.({ block: "start" });
  }

  _closeEditor(force = false) {
    if (!force && this._edit?.dirty && !confirm(this.ui.discard)) return;
    this._edit = null;
    this._rerenderContent();
  }

  // ------------------------------------------------------------------ events

  _setValue(scope, key, value, redraw = false) {
    if (scope === "edit") {
      this._edit.data[key] = value;
      if (key === "wall" && value && this._edit.type === "group") {
        const facing = this._wallFacing(this._house() || { az: 0 }, value);
        // the sun shines on a wall while it is less than 90° beside its direction
        this._edit.data.azimuth_from = Math.round((facing + 270) % 360);
        this._edit.data.azimuth_to = Math.round((facing + 90) % 360);
      }
      this._edit.dirty = true;
      if (this._edit.errors?.[key]) delete this._edit.errors[key];
      const save = this.shadowRoot.querySelector('[data-action="save-sub"]');
      if (save) save.disabled = false;
      if (redraw || REDRAW_KEYS.has(key)) {
        this._rerenderContent();
      } else if (this._edit.type === "group" && (key === "azimuth_from" || key === "azimuth_to")) {
        const preview = this.shadowRoot.querySelector('[data-live-block="compass"]');
        if (preview) preview.innerHTML = this._groupPreview();
      }
      return;
    }
    this._drafts[scope] = this._drafts[scope] || {};
    this._drafts[scope][key] = value;
    const save = this.shadowRoot.querySelector(`[data-save="${scope}"]`);
    if (save) save.disabled = false;
    const preview = scope === "house" && this.shadowRoot.querySelector("[data-house-preview]");
    if (preview) preview.innerHTML = this._housePreview();
    if (redraw) this._rerenderContent();
  }

  _currentList(scope, key) {
    const value = scope === "edit" ? this._edit.data[key] : this._value(scope, key);
    return Array.isArray(value) ? [...value] : [];
  }

  _onInput(ev, isChange = false) {
    const el = ev.target;
    if (el.dataset.add) {
      if (isChange) this._addListValue(el);
      return;
    }
    const { scope, k: key, kind } = el.dataset;
    if (!scope || !key || !kind) return;
    let value;
    if (kind === "boolean") {
      if (!isChange) return;
      value = el.checked;
      const sw = el.nextElementSibling;
      if (sw?.classList.contains("switch")) sw.classList.toggle("on", value);
    } else if (kind === "number") {
      value = el.value === "" ? null : Number(el.value);
    } else if (kind === "group" || kind === "wall") {
      if (!isChange) return;
      value = el.value || null;
    } else if (kind === "select") {
      if (!isChange) return;
      value = el.value;
    } else {
      value = el.value;
    }
    if (kind === "entity") {
      const hint = el.parentElement.querySelector(".entity-hint");
      if (hint) {
        const st = value ? this._state(value) : null;
        hint.textContent = value ? (st ? this._name(value) : `⚠ ${this.ui.notFound}`) : "";
        hint.classList.toggle("bad", !!value && !st);
      }
    }
    // the name is only shown in the title after leaving the field
    this._setValue(scope, key, value, false);
  }

  _onKey(ev) {
    const el = ev.target;
    if (ev.key === "Enter" && el.dataset.add) {
      ev.preventDefault();
      this._addListValue(el);
    }
  }

  _addListValue(el) {
    const value = el.value.trim();
    if (!value) return;
    const { scope, k: key } = el.dataset;
    const list = this._currentList(scope, key);
    if (!list.includes(value)) list.push(value);
    this._setValue(scope, key, list);
    this._rerenderContent(`[data-add][data-k="${key}"][data-scope="${scope}"]`);
  }

  async _onClick(ev) {
    const el = ev.target.closest("button, [data-edit], [data-tab]");
    if (!el || el.disabled) return;
    const d = el.dataset;
    if (d.tab) {
      if (this._edit?.dirty && !confirm(this.ui.discard)) return;
      this._tab = d.tab;
      this._edit = null;
      this._render();
      return;
    }
    if (d.remove !== undefined) {
      ev.preventDefault();
      const list = this._currentList(d.scope, d.k);
      list.splice(Number(d.remove), 1);
      this._setValue(d.scope, d.k, list, true);
      return;
    }
    if (d.toggle !== undefined) {
      ev.preventDefault();
      const list = this._currentList(d.scope, d.k);
      const index = list.indexOf(d.toggle);
      if (index >= 0) list.splice(index, 1);
      else list.push(d.toggle);
      this._setValue(d.scope, d.k, list, true);
      return;
    }
    if (d.seg !== undefined) {
      ev.preventDefault();
      this._setValue(d.scope, d.k, d.seg, true);
      return;
    }
    if (d.save) return this._saveCard(d.save, el);
    if (d.cancel) {
      delete this._drafts[d.cancel];
      delete this._errors[d.cancel];
      this._rerenderContent();
      return;
    }
    if (d.new) {
      this._openEditor(d.new, null);
      return;
    }
    if (d.edit) {
      if (this._edit?.dirty && !confirm(this.ui.discard)) return;
      const item = (d.edit === "window" ? this._windows : this._groups).find((x) => x.id === d.id);
      if (item) this._openEditor(d.edit, item);
      return;
    }
    switch (d.action) {
      case "menu":
        this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
        break;
      case "toggle-automatic": {
        const id = this._cfg.entities.automatic;
        await this._hass.callService("switch", this._state(id)?.state === "on" ? "turn_off" : "turn_on", { entity_id: id });
        break;
      }
      case "expand":
        if (this._expanded.has(d.id)) this._expanded.delete(d.id);
        else this._expanded.add(d.id);
        this._rerenderContent();
        break;
      case "end-override":
        el.disabled = true;
        try {
          await this._ws({ type: "shutter_assistant/end_override", window_id: d.id });
          this._toast(this.ui.overrideEnded);
        } catch (err) {
          el.disabled = false;
          this._toast(err.message || String(err), true);
        }
        break;
      case "close-edit":
        this._closeEditor();
        break;
      case "save-sub":
        await this._saveSub(el);
        break;
      case "duplicate": {
        const e = this._edit;
        const data = clone(e.data);
        data.name = this.ui.copyOf(data.name || "");
        data.cover = "";
        data.window_sensors = [];
        this._edit = { type: "window", id: null, data, errors: {}, dirty: true, notice: this.ui.duplicated };
        this._rerenderContent();
        this._scrollTop();
        break;
      }
      case "delete-sub":
        await this._deleteSub(el);
        break;
      default:
        break;
    }
  }

  async _saveCard(cardId, button) {
    const draft = this._drafts[cardId];
    if (!draft) return;
    button.disabled = true;
    try {
      const result = await this._ws({ type: "shutter_assistant/save_options", options: draft });
      if (result.errors) {
        this._errors[cardId] = result.errors;
        this._rerenderContent();
        return;
      }
      this._cfg = result.config;
      delete this._drafts[cardId];
      delete this._errors[cardId];
      this._rerenderContent();
      this._toast(this.ui.saved);
      this._refreshLater();
    } catch (err) {
      button.disabled = false;
      this._cardMessage(button, err.message || String(err), true);
    }
  }

  async _saveSub(button) {
    const e = this._edit;
    const msg = { type: "shutter_assistant/save_subentry", subentry_type: e.type, data: e.data };
    if (e.id) msg.subentry_id = e.id;
    button.disabled = true;
    try {
      const result = await this._ws(msg);
      if (result.errors) {
        e.errors = result.errors;
        this._rerenderContent();
        return;
      }
      this._cfg = result.config;
      this._edit = null;
      this._rerenderContent();
      this._toast(this.ui.saved);
      this._refreshLater();
    } catch (err) {
      button.disabled = false;
      this._cardMessage(button, err.message || String(err), true);
    }
  }

  async _deleteSub(button) {
    const e = this._edit;
    let question = this.ui.confirmDelete;
    if (e.type === "group") {
      const users = this._windows.filter((w) => w.data.group === e.id).map((w) => w.title);
      if (users.length) question = this.ui.confirmDeleteGroup(users.join(", "));
    }
    if (!confirm(question)) return;
    try {
      const result = await this._ws({ type: "shutter_assistant/delete_subentry", subentry_id: e.id });
      this._cfg = result.config;
      this._edit = null;
      this._rerenderContent();
      this._toast(this.ui.saved);
      this._refreshLater();
    } catch (err) {
      this._cardMessage(button, err.message || String(err), true);
    }
  }

  _cardMessage(el, text, bad = false) {
    const msg = (el.closest(".card") || el.closest(".editor-actions"))?.querySelector(".msg") || this.shadowRoot.querySelector(".editor-actions .msg");
    if (msg) {
      msg.textContent = text;
      msg.classList.toggle("bad", bad);
    } else {
      this._toast(text, bad);
    }
  }

  _toast(text, bad = false) {
    const toast = this.shadowRoot.querySelector(".toast");
    if (!toast) return;
    toast.textContent = text;
    toast.classList.toggle("bad", bad);
    toast.hidden = false;
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => (toast.hidden = true), 2500);
  }
}

const STYLE = `
:host { display:block; min-height:100vh; overflow-x:hidden; background:var(--primary-background-color); color:var(--primary-text-color); font-family:var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
* { box-sizing:border-box; }
.toolbar { display:flex; align-items:center; height:56px; padding:0 12px; background:var(--app-header-background-color, var(--primary-color)); color:var(--app-header-text-color, #fff); gap:8px; }
.title { display:flex; align-items:center; gap:10px; font-size:20px; font-weight:400; }
.tabs { display:flex; overflow-x:auto; background:var(--app-header-background-color, var(--primary-color)); padding:0 8px; scrollbar-width:none; }
.tab { display:flex; align-items:center; gap:6px; background:none; border:none; color:var(--app-header-text-color, #fff); opacity:.75; padding:10px 14px; cursor:pointer; border-bottom:2px solid transparent; font-size:14px; white-space:nowrap; }
.tab.active { opacity:1; border-bottom-color:var(--app-header-text-color, #fff); }
.tab ha-icon { --mdc-icon-size:20px; }
.content { padding:16px; max-width:1240px; margin:0 auto; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:16px; align-items:start; }
.tiles-grid { grid-template-columns:repeat(auto-fill, minmax(300px, 1fr)); }
.editor-grid { grid-template-columns:repeat(auto-fit, minmax(380px, 1fr)); }
.content > .card { margin-bottom:16px; }
.content > .actions { margin-top:16px; }
.section-title { display:flex; align-items:center; gap:8px; font-size:16px; font-weight:500; margin:24px 4px 12px; color:var(--secondary-text-color); }
.card { min-width:0; overflow-wrap:anywhere; background:var(--ha-card-background, var(--card-background-color, #fff)); border-radius:var(--ha-card-border-radius, 12px); border:1px solid var(--divider-color, #e0e0e0); padding:16px; box-shadow:var(--ha-card-box-shadow, none); }
.card.error { color:var(--error-color); }
.banner { display:flex; align-items:center; gap:10px; border-color:var(--warning-color, #ffa600); }
.banner ha-icon { color:var(--warning-color, #ffa600); }
.banner.info { border-color:var(--primary-color); }
.banner.info ha-icon { color:var(--primary-color); }
h2 { display:flex; align-items:center; gap:10px; margin:0 0 4px; font-size:18px; font-weight:500; }
h2 ha-icon { color:var(--state-icon-color, var(--primary-color)); }
.desc { margin:0 0 12px; color:var(--secondary-text-color); font-size:14px; }
.fields { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); gap:12px 20px; margin-top:8px; }
.field { display:flex; flex-direction:column; gap:4px; font-size:14px; min-width:0; }
.field.invalid input, .field.invalid select { border-color:var(--error-color, #db4437); }
.field-error { color:var(--error-color, #db4437); font-size:12px; }
.lbl { font-weight:500; }
small { color:var(--secondary-text-color); font-size:12px; line-height:1.3; }
input[type=text], input[type=number], input[type=time], select, textarea {
  font:inherit; color:var(--primary-text-color); background:var(--input-fill-color, var(--secondary-background-color, #f5f5f5));
  border:1px solid var(--divider-color, #ccc); border-radius:8px; padding:8px 10px; width:100%; min-width:0; }
input:focus, select:focus, textarea:focus { outline:2px solid var(--primary-color); outline-offset:-1px; }
.with-unit { display:flex; align-items:center; gap:6px; }
.unit { color:var(--secondary-text-color); min-width:28px; }
.entity-hint { font-size:12px; color:var(--secondary-text-color); min-height:14px; }
.entity-hint.bad, .chip.bad, .msg.bad { color:var(--error-color, #db4437); }
.toggle-row { flex-direction:row; align-items:center; justify-content:space-between; gap:12px; cursor:pointer; }
.toggle-row > span:first-child { display:flex; flex-direction:column; gap:2px; }
.switch-input { display:none; }
.switch { position:relative; flex:none; width:36px; height:20px; border-radius:10px; background:var(--switch-unchecked-track-color, #9e9e9e); transition:background .2s; }
.switch::after { content:""; position:absolute; top:2px; left:2px; width:16px; height:16px; border-radius:50%; background:#fff; transition:left .2s; }
.switch.on { background:var(--switch-checked-track-color, var(--primary-color)); }
.switch.on::after { left:18px; }
.chips { display:flex; flex-wrap:wrap; gap:6px; }
.chip { max-width:100%; overflow-wrap:anywhere; display:inline-flex; align-items:center; gap:4px; background:var(--secondary-background-color, #eee); border-radius:16px; padding:3px 4px 3px 10px; font-size:13px; }
.chip-btn { border:none; background:none; cursor:pointer; color:var(--secondary-text-color); padding:0 4px; font-size:12px; }
.seg { display:flex; flex-wrap:wrap; gap:6px; }
.seg-btn { border:1px solid var(--divider-color); background:none; color:var(--primary-text-color); border-radius:16px; padding:6px 12px; cursor:pointer; font:inherit; font-size:13px; text-align:left; }
.seg-btn.on { background:var(--primary-color); color:var(--text-primary-color, #fff); border-color:var(--primary-color); }
.actions { display:flex; align-items:center; justify-content:flex-end; gap:8px; margin-top:16px; flex-wrap:wrap; }
.msg { margin-right:auto; font-size:13px; color:var(--secondary-text-color); }
.grow { flex:1; min-width:0; }
.btn { display:inline-flex; align-items:center; gap:6px; font:inherit; font-weight:500; border-radius:18px; padding:8px 16px; cursor:pointer; border:1px solid var(--divider-color); background:none; color:var(--primary-color); white-space:nowrap; }
.btn.small { padding:4px 12px; font-size:13px; }
.btn ha-icon { --mdc-icon-size:18px; }
.btn.primary { background:var(--primary-color); color:var(--text-primary-color, #fff); border-color:var(--primary-color); }
.btn.danger { color:var(--error-color, #db4437); border-color:var(--error-color, #db4437); }
.btn:disabled { opacity:.45; cursor:default; }
.icon-btn { background:none; border:none; color:inherit; cursor:pointer; padding:4px; display:inline-flex; }
.status { display:flex; flex-direction:column; gap:14px; }
.status-main { display:flex; align-items:center; gap:12px 16px; flex-wrap:wrap; }
.status-main > .grow { flex:1 1 180px; }
.status-main > ha-icon { --mdc-icon-size:52px; }
.status-main > ha-icon.on { color:var(--success-color, #43a047); }
.status-main > ha-icon.offc { color:var(--disabled-text-color, #9e9e9e); }
.status-text { font-size:22px; font-weight:500; }
.facts { display:flex; flex-direction:column; gap:6px; }
.fact { display:flex; align-items:center; gap:10px; font-size:14px; padding:6px 10px; border-radius:10px; background:var(--secondary-background-color, #f5f5f5); }
.fact ha-icon { --mdc-icon-size:20px; color:var(--secondary-text-color); }
.fact.warn ha-icon { color:var(--warning-color, #ffa600); }
.fact.indigo ha-icon { color:#5c6bc0; }
.fact.teal ha-icon { color:#00897b; }
.fact-name { flex:0 0 auto; min-width:7.5em; font-weight:500; }
.fact-value { flex:1; text-align:right; color:var(--secondary-text-color); overflow-wrap:anywhere; }
.rows { display:flex; flex-direction:column; }
.row { display:flex; align-items:center; gap:10px; padding:8px 4px; border-bottom:1px solid var(--divider-color); font:inherit; font-size:14px; color:var(--primary-text-color); background:none; border-left:none; border-right:none; border-top:none; text-align:left; width:100%; }
.row:last-child { border-bottom:none; }
.row > span { min-width:0; overflow-wrap:anywhere; }
.row > span.grow { flex:1 1 40%; }
.row > span.muted { flex:0 1 auto; text-align:right; }
.row.link { cursor:pointer; }
.row.link:hover, tbody tr:hover { background:var(--secondary-background-color, #f5f5f5); }
.reason { font-size:13px; }
.two-line { display:block; }
.warn-row ha-icon, .override-row ha-icon { color:var(--warning-color, #ffa600); }
.info-row ha-icon { color:var(--primary-color); }
.muted { color:var(--secondary-text-color); }
.small { font-size:12px; }
.center { text-align:center; }
.used { margin-top:8px; }
.pill { display:inline-block; border-radius:12px; padding:2px 10px; font-size:12px; background:var(--secondary-background-color, #eee); white-space:nowrap; }
.pill.danger { background:rgba(229,57,53,.15); color:var(--error-color, #c62828); }
.fact.danger ha-icon { color:var(--error-color, #c62828); }
.pill.ok { background:rgba(67,160,71,.15); color:var(--success-color, #2e7d32); }
.pill.warn { background:rgba(255,166,0,.18); color:var(--warning-color, #b26a00); }
.pill.purple { background:rgba(142,36,170,.15); color:#8e24aa; }
.pill.indigo { background:rgba(92,107,192,.18); color:#5c6bc0; }
.pill.teal { background:rgba(0,137,123,.15); color:#00897b; }
.pill.muted { color:var(--secondary-text-color); }
.dot { display:inline-block; width:10px; height:10px; border-radius:50%; flex:none; }
.dot.big { width:14px; height:14px; }
.tile-card { display:flex; flex-direction:column; gap:8px; }
.tile-card .actions { margin-top:auto; padding-top:4px; }
.tile-head { display:flex; align-items:center; gap:8px 12px; flex-wrap:wrap; }
.tile-name { flex:1 1 9em; min-width:0; }
.tile-title, .head-title { overflow-wrap:break-word; }
.tile-title { display:flex; align-items:center; gap:8px; font-size:16px; font-weight:500; }
.tile-title ha-icon { --mdc-icon-size:20px; color:var(--state-icon-color, var(--primary-color)); }
.shutter { position:relative; display:inline-block; flex:none; width:26px; height:34px; border:2px solid var(--secondary-text-color); border-radius:3px; overflow:hidden; vertical-align:middle; background:linear-gradient(var(--secondary-background-color, #e3f2fd), var(--secondary-background-color, #e3f2fd)); }
.shutter .slats { position:absolute; left:0; right:0; top:0; background:repeating-linear-gradient(to bottom, var(--secondary-text-color) 0 3px, transparent 3px 5px); opacity:.8; }
.shutter.na { opacity:.35; border-style:dashed; }
td .shutter { width:16px; height:22px; border-width:1.5px; margin-right:6px; }
.check-wrap { margin:4px 0; }
.check { border:1px solid var(--divider-color); border-radius:10px; padding:8px 10px; display:flex; flex-direction:column; gap:4px; font-size:13px; }
.check-result { display:flex; align-items:center; gap:8px; font-weight:500; padding-bottom:6px; border-bottom:1px solid var(--divider-color); }
.check-result ha-icon { --mdc-icon-size:20px; color:var(--disabled-text-color, #9e9e9e); }
.check-result.ok ha-icon { color:var(--warning-color, #ffa600); }
.check-row { display:grid; grid-template-columns:20px minmax(8.5em, 1fr) minmax(0, 1.3fr); gap:8px; align-items:center; }
.check-label { overflow-wrap:normal; }
.check-row ha-icon { --mdc-icon-size:18px; }
.check-row.ok ha-icon { color:var(--success-color, #43a047); }
.check-row.fail ha-icon { color:var(--disabled-text-color, #9e9e9e); }
.check-row.wait ha-icon { color:var(--warning-color, #ffa600); }
.check-row.muted ha-icon { color:var(--disabled-text-color, #9e9e9e); }
.check-detail { color:var(--secondary-text-color); text-align:right; }
.compass-wrap { display:flex; justify-content:center; margin:4px 0; }
.compass-wrap.small { flex-direction:column; align-items:center; }
.compass { width:100%; max-width:240px; height:auto; }
.compass-wrap.small .compass { max-width:200px; }
.compass .ring { fill:none; stroke:var(--divider-color, #ccc); stroke-width:1.5; }
.compass .ring.inner { stroke-dasharray:2 4; stroke-width:1; }
.compass .tick { stroke:var(--secondary-text-color); stroke-width:1; opacity:.6; }
.compass .tick.long { stroke-width:2; opacity:1; }
.compass .dir { fill:var(--secondary-text-color); font-size:12px; font-weight:500; text-anchor:middle; dominant-baseline:central; }
.compass .sun { fill:#fdd835; stroke:#f9a825; stroke-width:2; filter:drop-shadow(0 0 4px rgba(253,216,53,.8)); }
.compass .sun.below { fill:var(--disabled-text-color, #9e9e9e); stroke:none; filter:none; }
.compass .sun-ray { stroke:#f9a825; stroke-width:1.5; stroke-dasharray:3 3; }
.compass .sun-ray.below { stroke:var(--disabled-text-color, #9e9e9e); }
.compass .center { fill:var(--secondary-text-color); }
.compass .house { fill:var(--card-background-color, #fff); stroke:var(--primary-text-color, #212121); stroke-width:1.5; stroke-linejoin:round; }
.compass .ridge { stroke:var(--secondary-text-color); stroke-width:1; stroke-dasharray:3 2; }
.compass .wall-mark { stroke-width:4; stroke-linecap:round; }
.compass .front-mark { fill:var(--primary-text-color, #212121); }
.compass .marker.link { cursor:pointer; }
.compass .marker-edge { stroke:var(--card-background-color, #fff); stroke-width:8; }
.compass .marker-line { stroke-width:5; }
.compass .marker-open { stroke:var(--card-background-color, #fff); stroke-width:2; }
.compass .wall-label { fill:var(--secondary-text-color); font-size:10px; font-weight:500; text-anchor:middle; dominant-baseline:central; }
.legend { display:flex; flex-wrap:wrap; justify-content:center; gap:4px 12px; font-size:12px; color:var(--secondary-text-color); margin:-2px 0 8px; }
.legend-item { display:inline-flex; align-items:center; gap:5px; }
.legend-mark { display:inline-block; width:12px; height:5px; background:var(--mark); }
.legend-mark.open { background:none; border:1.5px solid var(--mark); height:7px; }
.wall-list { display:flex; flex-wrap:wrap; gap:6px; justify-content:center; margin-top:2px; }
.sun-text { display:flex; align-items:center; justify-content:center; gap:6px; font-size:13px; color:var(--secondary-text-color); margin:2px 0 8px; text-align:center; }
.sun-text ha-icon { --mdc-icon-size:18px; color:#f9a825; }
.table-wrap { width:100%; overflow-x:auto; }
table { width:100%; border-collapse:collapse; font-size:14px; table-layout:fixed; }
th.c-icon { width:40px; } th.c-group { width:24%; } th.c-state { width:150px; } th.c-pos { width:90px; } th.c-edit { width:32px; }
td.c-name div { overflow-wrap:anywhere; }
th { text-align:left; font-weight:500; color:var(--secondary-text-color); padding:6px 8px; border-bottom:1px solid var(--divider-color); }
td { padding:8px; border-bottom:1px solid var(--divider-color); vertical-align:middle; }
tbody tr { cursor:pointer; }
.editor-head { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.editor-head h2 { margin:0; }
.editor-head .head-title { flex:1 1 8em; min-width:0; }
.head-actions { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-left:auto; }
.editor-head > ha-icon { color:var(--state-icon-color, var(--primary-color)); }
.editor-actions { position:sticky; bottom:0; z-index:2; display:flex; align-items:center; justify-content:flex-end; gap:8px; flex-wrap:wrap; margin-top:16px; padding:12px 16px; border:1px solid var(--divider-color); border-radius:12px; background:var(--ha-card-background, var(--card-background-color, #fff)); box-shadow:0 -2px 8px rgba(0,0,0,.08); }
.toast { position:fixed; bottom:24px; left:50%; transform:translateX(-50%); background:var(--primary-text-color); color:var(--primary-background-color); padding:10px 18px; border-radius:8px; z-index:10; }
.toast.bad { background:var(--error-color, #db4437); color:#fff; }
@media (max-width: 700px) {
  .hide-narrow { display:none; } .content { padding:8px; } .grid, .tiles-grid, .editor-grid { grid-template-columns:1fr; }
  .tab span { display:none; } .tab.active span { display:inline; } .tab { padding:10px 12px; }
  .fields { grid-template-columns:1fr; }
  th.c-icon { width:32px; } th.c-state { width:120px; }
  td { padding:8px 4px; } .entity-id { font-size:11px; }
  .card { padding:12px; }
  .fact-name { min-width:6em; }
  .status-main > ha-icon { --mdc-icon-size:40px; }
  .status-text { font-size:20px; }
}
`;

if (!customElements.get("shutter-assistant-panel")) {
  customElements.define("shutter-assistant-panel", ShutterAssistantPanel);
}
