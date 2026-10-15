# Umstieg von YAML-Automationen / Moving from YAML automations

[Deutsch](#deutsch) | [English](#english)

## Deutsch

Shutter Assistant ersetzt typische Rollo-Automationen samt ihrer Helfer. Vorgehen:

1. Integration installieren und einrichten (globale Werte wie bisher).
2. Für jede Himmelsrichtung eine **Gruppe** anlegen (Azimut und Sonnensensoren).
3. Für jedes Rollo ein **Fenster** anlegen und die bisherigen Werte eintragen.
4. Die alten Automationen **ausschalten** (nicht löschen) und ein paar Tage beobachten (Logbuch, Sensor "Letzter Grund").
5. Danach alte Automationen und Helfer löschen und Dashboards auf die neuen Entitäten umstellen.

### Typische Zuordnung

| Bisher (YAML) | Shutter Assistant |
|---|---|
| Schalter "Rollo-Automatik" (input_boolean) | Schalter **Automatik** |
| Tagesprüfung der Höchsttemperatur (weather.get_forecasts), Helfer "Sommertag" | Optionen **Sommertag**, Binärsensor **Sommertag** |
| Schwelle Höchsttemperatur (input_number) | Sommertag ab |
| Ist-Temperatur-Schwelle mit `for:` | Fenster: Außentemperatur mindestens, Haltezeit Temperatur |
| Azimut von/bis je Himmelsrichtung (input_number) | Gruppe: Azimut von, bis |
| Strahlungs-, PV- und Lux-Schwellen, Minuten-Helfer | Fenster: Schwellen und Haltezeit Sonne |
| Sonnenschutz-Position je Raum (input_number) | Fenster: Sonnenschutz-Position |
| Marker "Sonnenschutz heute" (input_boolean), Reset in der Nacht | intern, Binärsensor **Sonnenschutz heute**, Tageswechsel |
| Auto-Hoch je Raum (Position = Sonnenschutz-Position bis +5 %) | Fenster: Auto-Hoch, Toleranz |
| Push "Fenster offen, Rollo nicht gefahren" mit Merker | Benachrichtigungsdienste und Fenster-Option |
| Manuell gefahrenes Rollo als "heute" markieren | Fenster: Manueller Sonnenschutz bis, Erkennungszeitraum, Nachlauf |
| Abendmodus über Sonnenhöhe mit Zeit-Fallback | Optionen **Abendmodus** (oder eigene Werte am Fenster) |
| Abendlauf mit "heute geschlossen"-Markern | Fenster: Abendlauf, Binärsensor **Abends geschlossen** |
| Nachziehen bei Fenster zu | Fenster: Nachziehen, Option Nachziehen ab |
| Lüften auf 30 % beim Öffnen | Fenster: Lüftungsposition, Verzögerungen |
| Übersteuerung über Timer oder input_boolean mit Reset | Fenster: Übersteuerung Dauer, Sonnenaufgang |
| Schlafräume schließen abends trotz Übersteuerung | Fenster: Abend- und Urlaubsfahrten trotz Übersteuerung |
| TV an: Rollo zu (einmal pro Einschaltzyklus) | Fenster: Schließ-Auslöser |
| TV an: kein Auto-Hoch / kein Lüften | Fenster: Öffnungssperre |
| Klimaanlage: Balkontür offen zählt als zu | Fenster: Fenster-Ausnahme |
| Startphase-Helfer nach Neustart | Optionen **Neustart-Schutz** |
| Nachtlauf zum Aufräumen der Marker | Option Ende der Nacht |
| Urlaubs-Morgen- und Abendfahrt mit Zufall | Optionen **Urlaub**, Fenster: Urlaubssimulation |

### Was sich bewusst unterscheidet

* Kein Abfragen im Sekundentakt: Sonnenbereiche werden über berechnete Zeitpunkte erkannt.
* Eigene Fahrten werden erkannt, späte Positionsmeldungen lösen keine Übersteuerung aus.
* Übersteuerungen, Marker und der Automatik-Schalter bleiben über Neustarts erhalten.
* Der Abendmodus wird aus Uhrzeit und Sonne berechnet, auch direkt nach einem Neustart.

## English

Shutter Assistant replaces typical cover automations together with their helpers. Steps:

1. Install and set up the integration (global values as before).
2. Add a **group** for every direction of the sun (azimuth and sun sensors).
3. Add a **window** for every cover and enter the previous values.
4. **Disable** (do not delete) the old automations and watch a few days (logbook, sensor "Last reason").
5. Afterwards delete old automations and helpers and switch dashboards to the new entities.

### Typical mapping

| Before (YAML) | Shutter Assistant |
|---|---|
| Switch "cover automatic" (input_boolean) | switch **Automatic** |
| Daily check of the forecast high (weather.get_forecasts), helper "summer day" | options **Summer day**, binary sensor **Summer day** |
| Threshold forecast high (input_number) | Summer day from |
| Current temperature threshold with `for:` | window: outdoor temperature at least, temperature hold time |
| Azimuth from/to per direction (input_number) | group: azimuth from, to |
| Radiation, PV and lux thresholds, minute helpers | window: thresholds and sun hold time |
| Sun protection position per room (input_number) | window: sun protection position |
| Marker "sun protection today" (input_boolean), reset at night | internal, binary sensor **Sun protection today**, day change |
| Auto up per room (position = sun position up to +5 %) | window: auto up, tolerance |
| Push "window open, cover not moved" with marker | notification services and window option |
| Mark a manually lowered cover as "today" | window: manual sun protection up to, detection period, follow-up |
| Evening mode by sun elevation with time fallback | options **Evening mode** (or own values at the window) |
| Evening run with "closed today" markers | window: evening run, binary sensor **Closed this evening** |
| Close when the window is closed in the evening | window: close after window closed, option from |
| Ventilate to 30 % when opening | window: ventilation position, delays |
| Override via timer or input_boolean with reset | window: override duration, sunrise |
| Bedrooms close in the evening despite override | window: evening and vacation runs despite override |
| TV on: close the cover (once per cycle) | window: close trigger |
| TV on: no auto up / no ventilation | window: opening block |
| Air conditioner: open balcony door counts as closed | window: window exception |
| Start phase helper after a restart | options **Restart protection** |
| Night run cleaning up markers | option end of the night |
| Vacation morning and evening runs with randomness | options **Vacation**, window: vacation simulation |

### Intended differences

* No polling every few seconds: sun sectors are detected via calculated points in time.
* Own movements are recognised, late position reports do not start an override.
* Overrides, markers and the automatic switch survive restarts.
* The evening mode is calculated from time and sun, also directly after a restart.
