# Shutter Assistant

[English version](README.en.md)

Custom Integration für Home Assistant, die Rollos und Raffstores automatisch steuert: Sonnenschutz nach Himmelsrichtung, Abendmodus, Lüftungsposition, manuelle Übersteuerung, Morgenöffnung und Urlaubssimulation. Alles wird in der Oberfläche eingestellt, nichts ist fest im Code. Es gibt keine KI und kein Lernen, die Regeln sind nachvollziehbar und jede Fahrt steht mit Grund im Logbuch.

Die Integration ersetzt typischerweise ein Bündel von YAML-Automationen mit vielen Helfern (input_boolean, input_number, timer) für Sonnenschutz, Auto-Hoch, Abendlauf, Nachziehen, Lüften, Übersteuerung und Urlaub.

> Status: Version 0.1.0.

## Funktionsweise

Die Integration arbeitet ereignisgesteuert: Sie reagiert nur auf Zustandswechsel der eingestellten Entitäten und auf berechnete Zeitpunkte (Sonne betritt oder verlässt einen Bereich, Abendbeginn, Haltezeiten, Ende einer Übersteuerung, Tageswechsel). Es gibt kein Abfragen im Sekundentakt.

### Gruppen und Fenster

* Eine **Gruppe** ist eine Himmelsrichtung: Azimut von und bis sowie beliebig viele Sonnensensoren (PV-Leistung, Helligkeit in Lux, Strahlung z. B. von Open-Meteo). Eine Gruppe hat keine Schwellen.
* Ein **Fenster** ist ein Rollo mit Fensterkontakt(en) und einer Gruppe. Alle Schwellen, Positionen und Zeiten stehen am Fenster.

### Sonnenschutz

* **Sommertag:** Sonnenschutz gibt es nur an Sommertagen. Beim Tageswechsel (Standard 01:00) wird die Höchsttemperatur der Tagesvorhersage geprüft. Steigt die Außentemperatur tagsüber über die Schwelle, wird es ebenfalls ein Sommertag.
* **Sonnenbedingung je Fenster:** Sommertag UND Außentemperatur über der Schwelle des Fensters (mit Haltezeit) UND jeder Sonnensensor der Gruppe über seiner Schwelle. Das Ganze muss die Sonnen-Haltezeit lang erfüllt sein und endet sofort. Nach einem Neustart wird sofort ausgewertet, die Haltezeit läuft ab dem Start.
* **Absenken:** Steht die Sonne im Bereich der Gruppe und gilt die Sonnenbedingung, fährt das Rollo einmal am Tag auf die Sonnenschutz-Position. Ist es schon weiter zu, wird es nur vorgemerkt und bleibt in Ruhe. Ein offenes Fenster verhindert die Fahrt; dann gibt es einmal am Tag eine Benachrichtigung (pro Fenster abschaltbar), aber nur wenn wirklich eine Fahrt verhindert wurde. Nach dem Schließen des Fensters wird nachgeholt.
* **Auto-Hoch:** Verlässt die Sonne den Bereich, öffnet das Rollo wieder, aber nur wenn es noch auf der Sonnenschutz-Position steht (bis zur Toleranz darüber). Von Hand anders gestellte Rollos bleiben, wie sie sind. Kein Auto-Hoch im Abendmodus, bei Übersteuerung oder Öffnungssperre. Pro Fenster abschaltbar.
* **Manuellen Sonnenschutz erkennen:** Fährt jemand bei Sonne ein Rollo von Hand weit genug herunter (Standard höchstens 25 %), gilt das als Sonnenschutz für heute. Optional zählt auch jede Fahrt genau auf die Sonnenschutz-Position.

### Abend

* **Abendmodus:** beginnt, wenn die Sonne unter die eingestellte Höhe sinkt (Standard -4 °), frühestens um 17:00 und spätestens um 21:00. Er endet um 03:30 oder bei Sonnenaufgang. Werte global oder pro Fenster.
* **Abendlauf:** zu Beginn des Abendmodus schließt jedes Rollo einmal, wenn das Fenster zu ist und keine Übersteuerung aktiv ist (pro Fenster einstellbar: trotz Übersteuerung schließen, z. B. Schlafräume).
* **Nachziehen:** wird am Abend ein Fenster geschlossen, fährt das Rollo zu (ab 16:00, auch bei Übersteuerung).
* **Lüftungsposition:** wird ein Fenster geöffnet und das Rollo ist (fast) zu, fährt es auf die Lüftungsposition (Standard 30 %). Abends nach 3 s, tagsüber nach 60 s, wenn das Fenster dann noch offen ist.

### Übersteuerung

Jede manuelle Bewegung (am Taster, in der App, nicht durch Shutter Assistant und nicht durch andere Automationen oder Skripte) startet eine Übersteuerung für das Fenster, Standard 60 min. Jede weitere Bewegung startet sie neu. Optional endet sie zusätzlich bei Sonnenaufgang, mit Dauer 0 nur bei Sonnenaufgang. Die Integration merkt sich ihre eigenen Fahrten, späte Positionsmeldungen werden deshalb nicht fälschlich als manuell gewertet.

### Zusatzbedingungen statt Sonderregeln

* **Öffnungssperre:** solange eine Entität nicht in einem der Freigabe-Zustände ist, wird nicht automatisch geöffnet (Auto-Hoch, Lüften, Urlaub morgens, Morgenöffnung). Beispiel: Fernseher an.
* **Schließ-Auslöser:** wird eine der Entitäten aktiv (Ein-Verzögerung), schließt das Rollo einmal pro Aktiv-Zyklus, wenn es weiter offen ist als die Mindestposition und das Fenster zu ist. Ist das Fenster offen, wird geschlossen, sobald es zu ist. Der Zyklus endet, wenn alle Entitäten inaktiv sind (Aus-Verzögerung). Beispiel: Fernseher einschalten schließt das Wohnzimmer-Rollo.
* **Fenster-Ausnahme:** solange eine Entität verfügbar ist, verhindert ein offenes Fenster keine Schließfahrt und es gibt keine Benachrichtigung. Beispiel: Klimaanlage mit Schlauch durch die Balkontür.

### Morgenöffnung (pro Fenster, Standard aus)

Modi: feste Uhrzeit (Werktag sowie Wochenende und Feiertag über einen optionalen Werktag-Sensor), Sonnenaufgang oder Sonnenhöhe mit Versatz, Helligkeit der Gruppe über einer Schwelle mit Haltezeit, Auslöser-Entität (Zeitstempel wie der nächste Wecker des Handys, oder eine Entität, die angeht). Dazu ein Zeitfenster frühestens und spätestens, eine Zielposition (offen oder Teilöffnung) und optional direkt die Sonnenschutz-Position, wenn die Sonnenbedingung gilt. Nicht bei Übersteuerung, Öffnungssperre oder einem seit dem Abend von Hand verstellten Rollo.

### Urlaubssimulation

Solange eine der Urlaubs-Entitäten an ist (z. B. derselbe Helfer wie für die Heizung), ruht der normale Abendlauf. Stattdessen öffnen die teilnehmenden Fenster morgens zu einer zufälligen Zeit (Standard 07:00 bis 08:00) auf eine zufällige Position (60 bis 100 %) und schließen abends zufällig (19:00 bis 20:30). Sonnenschutz und Lüften laufen weiter.

### Neustart-Schutz

Nach dem Start von Home Assistant gibt es einige Minuten (Standard 5) keine Fahrten. Danach wird ausgewertet und der Abendlauf für noch nicht geschlossene Fenster nachgeholt (nur ab 12:00). Übersteuerungen, Tagesmarker und der Automatik-Schalter bleiben über Neustarts erhalten.

## Installation über HACS

1. HACS öffnen, oben rechts im Menü **Benutzerdefinierte Repositories** wählen.
2. Repository `https://github.com/Jumpmaster2/Shutter-Assistant`, Typ **Integration**, hinzufügen.
3. **Shutter Assistant** herunterladen und Home Assistant neu starten.
4. **Einstellungen > Geräte & Dienste > Integration hinzufügen > Shutter Assistant**.

Voraussetzung: Home Assistant 2026.10 oder neuer.

## Konfiguration

### Einrichtung und Optionen (global)

| Option | Standard | Bedeutung |
|---|---|---|
| Außentemperatur-Sensor | | Pflicht |
| Wetter-Entität | | Tagesvorhersage für den Sommertag |
| Sprache der Meldungen | wie Home Assistant | Deutsch oder Englisch für Logbuch, letzten Grund und Push |
| Benachrichtigungsdienste | | z. B. `notify.mobile_app_phone` |
| Werktag-Sensor | | optional, für die Morgenöffnung (z. B. Workday-Integration) |
| Sommertag ab | 23 °C | Höchsttemperatur der Vorhersage |
| Tageswechsel | 01:00 | Vorhersage prüfen, Tagesmarker zurücksetzen |
| Abendmodus frühestens, Sonnenhöhe, spätestens | 17:00, -4 °, 21:00 | |
| Ende der Nacht | 03:30 | |
| Nachziehen ab | 16:00 | |
| Urlaubs-Entitäten | | "an" = Urlaub |
| Urlaub morgens ab, Zufallszeitraum | 07:00, 60 min | |
| Öffnungsposition von, bis | 60 %, 100 % | |
| Urlaub abends ab, Zufallszeitraum | 19:00, 90 min | |
| Neustart-Schutz | 5 min | |
| Abendlauf nachholen ab | 12:00 | |

### Gruppen

**Gruppe hinzufügen**: Name, Azimut von und bis (90 ° = Ost, 180 ° = Süd, 270 ° = West; die Grenzen selbst zählen nicht), Strahlungs-, PV- und Helligkeitssensoren.

### Fenster

**Fenster hinzufügen** in vier Schritten:

1. **Fenster:** Name, Rollo, Fensterkontakte, Gruppe (ohne Gruppe kein Sonnenschutz).
2. **Sonnenschutz:** Schwellen für die Sensortypen der Gruppe, Außentemperatur mindestens (19 °C), Haltezeiten Temperatur (10 min) und Sonne (5 min), Sonnenschutz-Position (10 %), Toleranz für Auto-Hoch (5 %), Auto-Hoch, Benachrichtigung bei offenem Fenster, manueller Sonnenschutz bis (25 %), Erkennungszeitraum (5 min), Nachlauf (5 min), Fahrt auf Sonnenschutz-Position zählt.
3. **Verhalten:** Übersteuerung (60 min, Sonnenaufgang, Abend- und Urlaubsfahrten trotz Übersteuerung), Zusatzbedingungen, Abend (Abendlauf, Nachziehen, eigene Abendzeiten), Lüften (30 %, gilt als geschlossen bis 5 %, 3 s abends, 60 s tagsüber), Urlaubssimulation.
4. **Morgenöffnung:** an oder aus, Modus und Zeitfenster, danach die Einstellungen des Modus.

Positionen: 100 % = offen, 0 % = zu.

## Entitäten

Global (Gerät "Shutter Assistant"):

* Schalter **Automatik** (aus = keine automatische Fahrt; bleibt über Neustarts erhalten)
* Binärsensoren **Sommertag** und **Abendmodus**
* Sensor **Vorhersage Höchsttemperatur**

Je Fenster (eigenes Gerät):

* Sensor **Status** (Automatik aus, Neustart-Schutz, Manuelle Übersteuerung, Abends geschlossen, Sonnenschutz, Urlaubssimulation, Bereit)
* Sensor **Letzter Grund** (Text, Code, Position, Zeit)
* Binärsensoren **Manuelle Übersteuerung** (mit Ende), **Sonnenbedingung** (mit Teilbedingungen), **Sonnenschutz heute**, **Abends geschlossen**

Jede Fahrt und jede Übersteuerung steht mit Grund im **Logbuch**.

## Umstieg von YAML-Automationen

Siehe [docs/migration.md](docs/migration.md).

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

Die Regeln in `custom_components/shutter_assistant/logic/` haben keine Abhängigkeit zu Home Assistant und sind einzeln testbar. Die Tests mit Home Assistant brauchen Linux oder macOS (sie laufen auch in GitHub Actions).

## Lizenz

MIT, siehe [LICENSE](LICENSE).
