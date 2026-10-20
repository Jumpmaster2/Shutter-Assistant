# Audit Shutter Assistant 0.3.2

Stand: 2026-10-20. Geprüft wurden alle getrackten Dateien. Ruff und pytest waren lokal nicht verfügbar (die HA-Tests brauchen Linux/macOS), die Bewertung beruht auf dem Lesen des Codes. Unsichere Punkte sind mit „zu prüfen“ markiert.


## 1. Zusammenfassung & Gesamtbewertung
Shutter Assistant steuert Rollos ereignisgesteuert: Sonnenschutz pro Himmelsrichtung (Gruppe), Abendlauf, Nachziehen, Lüften, manuelle Übersteuerung, Morgenöffnung, Urlaubssimulation und Neustart-Schutz. Es gibt keine Cloud und keine Zugangsdaten (`iot_class: calculated`). Die Integration nutzt nur HA-Entitäten, `weather.get_forecasts`, `notify.*` und `cover.*`. Die Konfiguration läuft über Config Entry, Options Flow, Subentries (Gruppe, Fenster) und zusätzlich über ein Admin-Panel mit WebSocket-API.

**Architektur:** `__init__` → `ShutterEngine` (DataUpdateCoordinator ohne Polling, `engine.py`). Die reine Logik in `logic/` ist ohne HA testbar. Plattformen: binary_sensor, sensor, switch. Dazu `config_flow.py` (auch Quelle der Selektoren für das Panel), `websocket.py`, `panel.py` + `frontend/`, `logbook.py`, `diagnostics.py` und Persistenz über `Store`.

**Gesamtbewertung: gut (≈ 7,5/10).** Die Architektur ist sauber, die Logik liegt getrennt, es gibt viele Szenario-Tests, alles wird beim Entladen aufgeräumt (Listener, Timer, Store), unique_ids sind stabil, `has_entity_name` ist gesetzt, die Übersetzungen de/en sind vollständig, das Panel escapt durchgehend (`esc`) und die WebSocket-Befehle sind `require_admin`. Es gibt keine kritischen Sicherheitsfunde. Die wichtigsten Schwächen:
- Es wird überall **°C angenommen**. Für Nutzer mit imperialem Einheitensystem ist die Integration damit fachlich falsch.
- Zwei Fehler im Flow: **optionale Entitäten lassen sich im Dialog nicht mehr leeren**.
- Die Vorhersage nutzt **nur `type: daily`**.
- **Große Attribute landen ungefiltert im Recorder**.

**Nicht anwendbar, geprüft:** Reauth, ConfigEntryAuthFailed/NotReady, SSL, HTTP-Sessions, Secrets. Die Integration hat keine externen Verbindungen. Hartcodierte Zugangsdaten gibt es nicht, `scripts/check_privacy.py` ist vorhanden.

## 2. Tabelle aller Funde
| ID | Kategorie | Schwere | Datei:Zeile | Problem | Auswirkung | Lösungsvorschlag |
|---|---|---|---|---|---|---|
| F01 | Logik/Allgemeingültigkeit | **Hoch** | sensor.py:37, const.py:69-70/206/210, config_flow.py:238-239/547/551, panel.js:82/108/112/1000/1004 | Temperaturen sind fest als °C angenommen: Einheit des Sensors „Vorhersage Höchsttemperatur“, Standardschwellen 23/14/19/24, Einheiten der Selektoren, Panel-Texte. HA liefert Vorhersage und Sensoren im Einheitensystem der Instanz (bei imperial in °F, zu prüfen pro Wetter-Integration). | Bei °F ist praktisch jeder Tag ein Sommertag (23 °F). Der Sensor zeigt einen falschen Wert, weil er °F-Zahlen als °C meldet und HA sie dann umrechnet. | Einheit aus `hass.config.units.temperature_unit` verwenden. Standardwerte beim Einrichten umrechnen (`TemperatureConverter`). Selektor-Einheit dynamisch setzen. Das Panel nimmt die Einheit aus dem Payload. |
| F02 | Bug (Options Flow) | Mittel | config_flow.py:395-397 | Im Schritt „Sommertag“ wird `_save(user_input)` ohne `remove` aufgerufen. Eine geleerte **Heizbedarf**-Entität fehlt im `user_input` und der alte Wert bleibt. | Der Heizbedarf lässt sich im Dialog nicht mehr entfernen, nur noch im Panel. | `remove=(CONF_HEATING_ENTITY,)`, analog zu `general`. Test ergänzen. |
| F03 | Bug (Subentry-Flow) | Mittel | config_flow.py:751-756 | Im Schritt „Sonnenschutz“ werden geleerte `room_entity`/`cooling_entity` nicht entfernt. `_values.update()` behält die alten Werte. | Raumtemperatur bzw. Klimaanlage lassen sich beim Ändern des Fensters nicht entfernen. | Vor dem `update` `CONF_ROOM_ENTITY` und `CONF_COOLING_ENTITY` poppen (wie in `behavior`). Test ergänzen. |
| F04 | Allgemeingültigkeit | Mittel | engine.py:1413-1423 | Abgefragt wird nur `get_forecasts` mit `type: daily`. Wetter-Entitäten, die nur `hourly`/`twice_daily` liefern, bekommen nie eine Vorhersage (es gibt alle 30 min einen Retry und einen INFO-Log). | Der Sommertag kommt dann nur noch über die Außentemperatur zustande, ohne dass der Nutzer erfährt warum. | `supported_features` prüfen und auf `twice_daily`/`hourly` ausweichen (Maximum und Nacht-Minimum aggregieren). Fehlende Unterstützung als Repair-Issue oder Panel-Hinweis melden. |
| F05 | Performance/Recorder | Mittel | binary_sensor.py:105-107, sensor.py:60-62 | `SunCondition` hat ca. 30 Attribute, `Status` hat 9, Werte wie Raumtemperatur und Fälligkeiten ändern sich ständig. Es ist kein `_unrecorded_attributes` gesetzt. | Die Recorder-Datenbank wächst pro Fenster spürbar. | `_unrecorded_attributes = frozenset({...})` für die Kontrollattribute setzen. |
| F06 | Performance | Niedrig | engine.py:961/1066/1246 | `async_update_listeners()` schreibt bei **jeder** Cover-Positionsmeldung und bei jeder Attributänderung von Klima und Raum die Zustände **aller** Entitäten aller Fenster (6·N+4). | Viele unnötige Zustandsschreibungen und Recorder-Last bei vielen Fenstern. | Nur bei echter Änderung aktualisieren (Signatur vergleichen) oder Entitäten pro Fenster per Dispatcher-Signal anstoßen. |
| F07 | HA-Konformität | Niedrig | engine.py:959/995/1401/1431 | `hass.async_create_task` ist nicht an den Config Entry gebunden. | Laufende Service-Aufrufe und Vorhersage-Abrufe werden beim Entladen nicht abgebrochen. | `self.config_entry.async_create_background_task(...)` bzw. `entry.async_create_task` verwenden. |
| F08 | Robustheit | Niedrig, zu prüfen | engine.py:1428-1442 | Endet ein Vorhersage-Task nach `async_shutdown`, plant er über `_schedule` einen neuen Timer auf der toten Engine. | Möglicher Timer-Leak und Auswertung nach dem Entladen. | Ein `_shutdown`-Flag in `_schedule`/`async_update_forecast` prüfen (zusammen mit F07). |
| F09 | Fehlerbehandlung | Niedrig | engine.py:1413-1419 | `get_forecasts` wird mit `blocking=True` und ohne Timeout aufgerufen. | Eine hängende Wetter-Integration blockiert den Task dauerhaft. | `asyncio.timeout(30)` setzen und bei Ablauf den Retry-Pfad nutzen. |
| F10 | Sicherheit | Niedrig | config_flow.py:222-229, engine.py:1008-1012 | Bei den Benachrichtigungsdiensten ist `custom_value=True` erlaubt. `domain.service` ist frei wählbar, z. B. `script.x` oder `homeassistant.restart`, und wird mit `title`/`message` aufgerufen. Nur Admins können das setzen. | Es lassen sich beliebige Dienste auslösen, ein zu weit reichender Service-Aufruf. | Nur die Domain `notify` zulassen und in Flow und WebSocket prüfen (Fehler `invalid_notify_service`). Optional `notify.send_message` mit notify-Entitäten unterstützen. |
| F11 | Datenschutz | Niedrig, zu prüfen | diagnostics.py:16 | `entry.as_dict()` geht ungeschwärzt in die Diagnose. Benachrichtigungsdienste wie `notify.mobile_app_<name>` enthalten oft Personen- oder Gerätenamen. | Persönliche Namen landen in Diagnose-Dateien, die Nutzer in Issues posten. | `async_redact_data` auf `notify_services` und Titel anwenden. |
| F12 | HA-Konformität | Niedrig | engine.py:484-498 | Das Repair-Issue `missing_group_<id>` wird nur für bestehende Fenster gelöscht, nicht für gelöschte Fenster und nicht in `async_remove_entry`. | Verwaiste Reparaturhinweise bleiben stehen. | Alle Issues der Domain abgleichen. In `async_remove_entry` alle löschen. |
| F13 | UX/HA-Konformität | Niedrig | entity.py, sensor.py, binary_sensor.py | Kein `entity_category`, kein `entity_registry_enabled_default`. | Überladene Geräteseiten. „Letzter Grund“ und „Sonnenbedingung“ sind Diagnose-Werte. | „Letzter Grund“, „Sonnenbedingung“ und „Vorhersage Höchsttemperatur“ als `EntityCategory.DIAGNOSTIC` markieren. „Abends geschlossen“ und „Sonnenschutz heute“ standardmäßig deaktivieren (zu entscheiden, Panel nutzt sie per Registry-Lookup, das funktioniert auch deaktiviert, zu prüfen). |
| F14 | HA-Konformität | Niedrig | sensor.py:33-44 | `ForecastMax` hat keine `state_class` und nur eine Nachkommastelle, `suggested_display_precision` fehlt. | Keine Langzeitstatistik. | `SensorStateClass.MEASUREMENT` und `suggested_display_precision=1` setzen. |
| F15 | Logik | Niedrig, zu prüfen | engine.py:392-395 | Der Neustart-Schutz zählt ab dem Setup des Entries, nicht ab „HA gestartet“. | Bei langsamem Start (über 5 min) endet der Schutz, bevor alle Geräte da sind. | Den Schutz in `_async_started` ab dem Startzeitpunkt (neu) setzen. |
| F16 | Logik/Validierung | Niedrig | config_flow.py:520-534, websocket.py:356 | Es wird nicht geprüft, ob ein Rollo schon in einem anderen Fenster verwendet wird. | Zwei Fenster steuern dasselbe Rollo gegenläufig, Übersteuerungen werden doppelt erkannt. | Fehler `cover_in_use` mit Namen des anderen Fensters. |
| F17 | Validierung/UX | Niedrig | config_flow.py:219/448 | Entity-Selektoren haben keinen `device_class`-Filter (Außentemperatur, Lux, Strahlung, PV). | Leicht falsche Sensoren wählbar, z. B. Luftfeuchte statt Temperatur. | `device_class` `temperature`, `illuminance`, `irradiance`, `power` vorschlagen. Optional prüfen, ob der Zustand numerisch ist (Fehler `not_numeric`). |
| F18 | Logik (Randfall) | Niedrig, zu prüfen | engine.py:1179-1186, logic/override.py:149-155 | Polartag/-nacht: kein Sonnenaufgang → Dauer 0 → `override_until=None` und `override_sunrise=True`. `async_track_sunrise` feuert nicht. | Die Übersteuerung endet nie. | Fallback-Höchstdauer, z. B. 24 h. |
| F19 | Robustheit | Niedrig | __init__.py:18-30 | Schlägt `async_forward_entry_setups` fehl, nachdem `engine.async_setup()` gelaufen ist, bleiben Listener und Timer registriert. | Leak bei fehlerhaftem Setup. | Mit try/except `await engine.async_shutdown()` aufrufen und weiterwerfen. |
| F20 | Codequalität | Niedrig | logic/window.py:137/259/270/285 | `assert` in Produktionslogik. | Fällt mit `python -O` weg (praktisch harmlos). | Durch explizite `if … is None: return []` ersetzen. |
| F21 | Codequalität | Niedrig | logic/sun.py:20-22, logic/override.py:37-38, config_flow.py:732-733 | Toter oder überflüssiger Code: `sun.elevation()` ist ungenutzt, `CommandTracker.pending()` wird nur in Tests genutzt, eine Schleife läuft über ein einelementiges Tupel. | Unnötiger Wartungsaufwand. | Entfernen bzw. vereinfachen. |
| F22 | Codequalität | Niedrig | engine.py:170 | Magische Zahl `SET_POSITION = 4`. | Bricht still, falls sich das Enum ändert (unwahrscheinlich). | `CoverEntityFeature.SET_POSITION` importieren (aus `homeassistant.components.cover`, ohne Plattformabhängigkeit). |
| F23 | Funktionsumfang | Niedrig | README.md:5 | Die README nennt „Raffstores“, es gibt aber keine Lamellen-Steuerung (`set_cover_tilt_position`). | Erwartung wird nicht erfüllt. | README präzisieren oder eine Tilt-Position pro Fenster als Option (Phase 3). |
| F24 | Übersetzungen | Niedrig | translations/*.json (window: behavior/morning*) | 18 Felder haben keine `data_description`: override_sunrise_reset, open_block_free_states, close_trigger_active_states/on_delay/off_delay/min_position/max_lock, ventilation_position, ventilation_delay_evening, morning_enabled/mode/earliest, morning_time_workday/weekend, morning_sun_event/offset, morning_lux_hold. | Fachbegriffe bleiben unerklärt. | Beschreibungen mit Beispiel ergänzen (de/en/strings), danach `gen_labels.py` ausführen. |
| F25 | UX | Niedrig | translations: error.* | Fehlermeldungen sagen nicht immer, wie man den Fehler behebt, z. B. `no_lux_sensor`, `night_end_after_evening`. | Nutzer ratlos. | Abhilfe ergänzen, z. B. „…: Helligkeitssensor in der Gruppe ergänzen oder einen anderen Modus wählen.“ |
| F26 | Allgemeingültigkeit | Niedrig | de/en.json (heating_entity, room_entity, radiation_sensors), README.md:24 | Die Beispiele sind auf das System des Autors zugeschnitten: „AI Heating Assistant“, „Open-Meteo“, „Balkonkraftwerk“, „derselbe Helfer wie für die Heizung“. | Wirkt für Fremdnutzer unverständlich. | Neutrale Beispiele, z. B. „ein input_boolean ‚Heizperiode‘ oder ein Schalter eines Heizungs-Blueprints“. |
| F27 | HACS/Quality Scale | Niedrig, zu prüfen | hacs.json:3, manifest.json | Die Mindestversion `2026.10.0` ist sehr neu (benötigte APIs prüfen). `quality_scale` ist nicht deklariert, es gibt kein `quality_scale.yaml`. | Unnötig kleine Nutzerbasis, Qualitätsstand unklar. | Die tatsächlich benötigte Mindestversion ermitteln. `quality_scale.yaml` anlegen (Bronze/Silber-Regeln abhaken). |
| F28 | Doku | Mittel | README.md / README.en.md | Es fehlen: manuelle Installation, Debug-Logging, Fehlerbehebung/FAQ, Deinstallation, Hinweis auf Einheiten, Voraussetzungen (`sun.sun`, Wetter-Entität), Erklärung der Entitäten-Attribute für eigene Karten mit Beispiel-YAML. | Höhere Einstiegshürde, mehr Support-Fragen. | Siehe Abschnitt 5. |
| F29 | Tests | Mittel | tests/ha/* | Kritische Fälle sind ungetestet, siehe Abschnitt 6. | Regressionen wie F02/F03 bleiben unentdeckt. | Tests ergänzen. |

## 3. Systemspezifische Werte → vorgeschlagene Einstellung
| Wert (heute) | Fundstelle | Vorschlag | Ort | Standard / Validierung |
|---|---|---|---|---|
| Temperaturen in °C (23/14/19/24 °C, 2 K) | const.py, config_flow.py | Einheit aus dem HA-Einheitensystem, Standards umgerechnet | automatisch (keine Option) | °F: 73/57/66/75 °F, Abstand 4 °F |
| Vorhersage-Typ `daily` | engine.py:1416 | „Vorhersage-Art“: automatisch / täglich / zweimal täglich / stündlich | Options Flow „Sommertag“ | automatisch nach `supported_features` |
| Außentemperatur-Sensor Pflicht | config_flow.py:219 | optional. Ohne Sensor wird `temperature` der Wetter-Entität verwendet | Config Flow | Mindestens eins von beiden (Fehler `need_temperature_source`) |
| Werktage Mo–Fr (Fallback) | logic/morning.py:35 | Auswahl „Wochenendtage“ (Mehrfachauswahl Mo–So) | Options Flow „Allgemein“ | Sa, So |
| Entprellung Fensterkontakt 5 s | const.py:22 | „Fenster gilt als geschlossen nach“ | Options Flow „Allgemein“ (erweitert) | 5 s, 0–120 |
| Vorhersage-Retry 30 min | engine.py:167 | eher Konstante lassen, optional „Erneuter Versuch nach“ | Options Flow (erweitert) | 30 min, 5–240 |
| Ventilsperre-/Aktiv-Zustände (`off`, `standby`, `playing` …) | const.py:198-199 | bleibt Vorschlag, ist bereits einstellbar | — | ok |
| Panel-Pfad `shutter-assistant`, Seitenleisten-Titel | panel.py:11, :42 | Option „Panel in der Seitenleiste anzeigen“ (an/aus) | Options Flow „Allgemein“ | an |
| Panel nur für Admins | panel.py:44 | bleibt (Sicherheit) | — | — |
| Sprache nur de/en | messages.py | ok, „auto“ fällt auf en zurück; weitere Sprachen über Übersetzungen | — | — |
| `sun.sun` vorausgesetzt (Panel) | panel.js:751/1027 | Hinweis im Panel ist vorhanden. Zusätzlich in README nennen | Doku | — |
| Beispiele „AI Heating Assistant“, „Open-Meteo“ | Übersetzungen | neutral formulieren (F26) | Übersetzungen | — |
| Lamellen (Raffstore) | — | „Lamellenwinkel bei Sonnenschutz“ (optional, nur wenn Rollo `SET_TILT_POSITION` kann) | Fenster → Sonnenschutz | leer = aus, 0–100 % |

Bereits gut: Alle Zeiten, Positionen, Schwellen, Haltezeiten und Sonnenwinkel sind einstellbar. Es gibt keine hartcodierten IPs, Hosts, Ports, Entity-IDs oder Benutzer. Zeitzone und Standort kommen aus `hass.config`. Abfrageintervalle gibt es nicht, alles ist ereignisgesteuert. Auto-Discovery ist hier nicht sinnvoll, weil die Integration berechnet und kein Gerät hat. Eine Vorbelegung ist möglich: einzige `weather.*`-Entität bzw. einzige Außentemperatur vorschlagen, Workday-Sensor automatisch vorschlagen.

## 4. UI-Verbesserungen (Vorher → Nachher)
1. **Einrichtung**, Schritt 1: Vorher ist nur „Außentemperatur-Sensor“ Pflicht und alle Sensoren sind wählbar. Nachher: Selektor mit `device_class: temperature`, Wetter-Entität vorausgewählt (wenn es genau eine gibt), Hinweis „mindestens eins von beiden“.
2. **Einheiten**: Vorher steht fest „°C“ in Dialog und Panel. Nachher wird die Einheit aus dem Einheitensystem genommen, das Panel liest sie aus `config_payload`.
3. **Benachrichtigungsdienste**: Vorher Freitext mit beliebigen Diensten. Nachher nur `notify.*`. Fehlertext: „Nur Benachrichtigungsdienste (notify.…) sind erlaubt. Wähle einen Dienst aus der Liste.“
4. **Sonnensensoren der Gruppe**: Vorher drei ungefilterte Sensorlisten. Nachher filtern nach `irradiance`, `power`, `illuminance`. Die Beschreibung nennt die erwartete Einheit.
5. **Fenster-Dialog, Schritt „Sonnenschutz“**: Vorher zeigt er Raumgrenze und Sollwert-Abstand gleichzeitig. Nachher (wie im Panel) nur das passende Feld zum gewählten Raum-Entitätstyp. Im Dialog geht das nur über einen Zwischenschritt oder Abschnitte. Alternativ in den Beschreibungen klar „nur bei Thermostat“/„nur bei Sensor“.
6. **Schritt „Verhalten“**: Vorher fehlen 9 Beschreibungen (F24). Nachher hat jedes Feld eine Erklärung mit Beispiel, z. B. „Aktiv-Zustände: Zustände, in denen ein Schließ-Auslöser als aktiv gilt, z. B. `playing` beim Fernseher“.
7. **Fehlermeldungen** (F25): Vorher „Die Gruppe dieses Fensters hat keinen Helligkeitssensor.“ Nachher dazu: „Füge der Gruppe einen Helligkeitssensor hinzu oder wähle einen anderen Modus.“
8. **Doppeltes Rollo** (F16): Neuer Fehler „Dieses Rollo wird schon vom Fenster ‚{name}‘ gesteuert.“
9. **Entitäten** (F13): Diagnose-Kategorie für „Letzter Grund“, „Sonnenbedingung“ und „Vorhersage Höchsttemperatur“. Die Icons sind bereits sinnvoll.
10. **Options-Menü**: Vorher 6 gleichrangige Punkte. Nachher bleibt das, ergänzt um einen Punkt „Erweitert“ (Entprellung, Panel anzeigen), damit die Grundeinstellungen schlank bleiben.

## 5. Dokumentation – was fehlt
- Manuelle Installation (Ordner `custom_components/shutter_assistant` kopieren, Neustart).
- Debug-Logging:
  ```yaml
  logger:
    logs:
      custom_components.shutter_assistant: debug
  ```
  Das Logging selbst ist dünn, siehe F06/F09. Debug-Logs an Entscheidungen ergänzen.
- Fehlerbehebung/FAQ: kein Sonnenschutz (Checkliste Sonnenbedingung), Übersteuerung startet ungewollt, Vorhersage fehlt, Rollo ohne Positionsunterstützung, Diagnose herunterladen.
- Einheiten (°C/°F), Voraussetzungen (Integration Sun, optional Wetter/Workday).
- Deinstallation: was gelöscht wird (Store, Panel).
- Beispiel-YAML für eigene Dashboard-Karten mit den Attributen.
- Changelog bzw. GitHub-Releases für HACS-Versionen.

## 6. Tests – kritische Lücken
- **Options Flow**: Schritte `general`, `summer`, `evening` (Fehlerfälle), `startup`. **Leeren optionaler Felder** (Wetter, Werktag, Heizbedarf), deckt F02 auf.
- **Fenster-Reconfigure**: Raum- und Klima-Entität leeren (F03). Schritte `behavior` und Morgen-Modi `sun`/`brightness`/`trigger` über den Dialog.
- **Lebenszyklus**: Unload/Reload ohne verbleibende Listener und Timer (`engine._timers`, `_unsubs` leer). `async_remove_entry` löscht Store und Panel. Fehlerhaftes Setup (F19).
- **Diagnostics**-Ausgabe (inkl. Schwärzung nach F11).
- **Repair-Issue** `missing_group` erscheint und verschwindet (F12).
- **Rollos**: unavailable, ohne `SET_POSITION` (Warnung, keine Fahrt), Fehler beim Service-Aufruf.
- **Einheiten**: imperiales System (F01).
- **Vorhersage**: nur stündlich/zweimal täglich (F04), Timeout (F09).
- **WebSocket**: Nicht-Admin wird abgewiesen. Unbekannte Option → `invalid`. Notify-Domain-Prüfung (F10).
- **Randfälle**: Zeitumstellung (Abend/Morgen am Umstellungstag), Polarregion (F18).
- Hinweis: Lokal sind weder Ruff noch pytest installiert, die HA-Tests brauchen Linux/macOS (CI oder WSL).

## 7. Priorisierte Reihenfolge der Behebung
1. **F02, F03**: Leeren optionaler Felder, mit Tests (klein, klarer Bug).
2. **F01**: Temperatur-Einheiten (Sensor, Standards, Selektoren, Panel), mit Test für imperial.
3. **F10, F11**: Notify-Domain einschränken, Diagnose schwärzen.
4. **F07, F08, F09, F19**: Task-Bindung an den Entry, Shutdown-Flag, Timeout, Setup-Fehler.
5. **F04**: Vorhersage-Art (inkl. Option).
6. **F05, F06, F13, F14**: Recorder-Attribute, Listener-Updates, Entitätskategorien, state_class.
7. **F12, F15, F16, F17, F18**: Repair-Aufräumen, Neustart-Schutz, doppeltes Rollo, Filter, Polar-Fallback.
8. **F24, F25, F26**: Übersetzungen (de/en/strings) + `gen_labels.py`.
9. **F20, F21, F22**: Codequalität.
10. **F27, F28, F29**: quality_scale, README (de/en), restliche Tests. F23 (Lamellen) als optionales Feature zum Schluss bzw. eigenes Ticket.


## 8. Stand der Behebung (Version 0.4.0, Branch `audit-fixes`)

| ID | Stand | Umsetzung |
|---|---|---|
| F01 | behoben | `units.py`: Einheit aus dem Einheitensystem; Standardwerte, Selektoren, Sensor „Vorhersage Höchsttemperatur“ und Panel nutzen sie (Test mit °F) |
| F02, F03 | behoben | geleerte Felder werden entfernt (Tests für Options- und Fenster-Dialog) |
| F04 | behoben | Option „Vorhersage-Art“ (automatisch/täglich/zweimal täglich/stündlich), `logic/forecast.py`, Repair-Issue ohne Vorhersage |
| F05 | behoben | `_unrecorded_attributes` für „Sonnenbedingung“ und „Status“ |
| F06 | teilweise | Cover-Meldungen aktualisieren die Entitäten nur noch einmal pro Ereignis; HA verwirft unveränderte Zustände ohnehin |
| F07, F08, F09 | behoben | Tasks am Config Entry, Shutdown-Sperre für Timer und Tasks, 30-s-Timeout für die Vorhersage |
| F10 | behoben | nur `notify.*` (Prüfung in Dialog und Panel, Engine überspringt andere Dienste) |
| F11 | behoben | Diagnose schwärzt die Benachrichtigungsdienste |
| F12 | behoben | verwaiste Repair-Issues werden gelöscht, beim Entfernen alle |
| F13 | behoben | „Letzter Grund“, „Sonnenbedingung“, „Vorhersage Höchsttemperatur“ als Diagnose; standardmäßig deaktiviert wird nichts, weil Panel und Automationen die Zustände brauchen |
| F14 | behoben | `state_class` und Anzeigegenauigkeit |
| F15 | behoben | Neustart-Schutz läuft ab „Home Assistant gestartet“ |
| F16 | behoben | Fehler `cover_in_use` in Dialog und Panel |
| F17 | behoben (Prüfung statt Filter) | Fehler `not_numeric` für Außentemperatur und Sonnensensoren; ein strenger `device_class`-Filter hätte Sensoren ohne Geräteklasse ausgeschlossen |
| F18 | behoben | ohne Sonnenaufgang endet die Übersteuerung nach 24 h |
| F19 | behoben | Setup-Fehler räumt die Engine auf |
| F20, F21, F22 | behoben | keine `assert`, toter Code entfernt, `CoverEntityFeature` |
| F23 | dokumentiert | README nennt die Einschränkung (Behanghöhe, keine Lamellen); Lamellensteuerung als eigenes Feature offen |
| F24, F25, F26 | behoben | alle Felder mit Beschreibung, Fehlermeldungen mit Abhilfe, neutrale Beispiele |
| F27 | offen, zu prüfen | Mindestversion 2026.10 bleibt, weil nur damit getestet; `quality_scale.yaml` ist für Custom Integrations nicht vorgesehen |
| F28 | behoben | README de/en: manuelle Installation, Einheiten, Fehlerbehebung, Debug-Log, Entfernen, Karten-Beispiel |
| F29 | behoben | neue Tests: Options-Flow, Leeren, Einheiten, Vorhersage-Arten, Timeout, Unload, Entfernen, Diagnose, Repairs, Rollos, Notify, Admin-Rechte, Panel ohne Seitenleiste |

Neue Optionen: Wochenendtage, Vorhersage-Art, Außentemperatur aus der Wetter-Entität, „Erweitert“ (Fenster gilt als geschlossen nach, Dashboard in der Seitenleiste).
