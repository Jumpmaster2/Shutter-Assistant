# Shutter Assistant

[English version](README.en.md)

Custom Integration für Home Assistant, die Rollos und Raffstores automatisch steuert (die Behanghöhe; Lamellen werden nicht gewendet): Sonnenschutz nach Himmelsrichtung, Abendmodus, Lüftungsposition, manuelle Übersteuerung, Morgenöffnung und Urlaubssimulation. Alles wird in der Oberfläche eingestellt, nichts ist fest im Code. Es gibt keine KI und kein Lernen, die Regeln sind nachvollziehbar und jede Fahrt steht mit Grund im Logbuch.

Die Integration ersetzt typischerweise ein Bündel von YAML-Automationen mit vielen Helfern (input_boolean, input_number, timer) für Sonnenschutz, Auto-Hoch, Abendlauf, Nachziehen, Lüften, Übersteuerung und Urlaub.

> Status: Version 0.4.0.

## Funktionsweise

Die Integration arbeitet ereignisgesteuert: Sie reagiert nur auf Zustandswechsel der eingestellten Entitäten und auf berechnete Zeitpunkte (Sonne betritt oder verlässt einen Bereich, Abendbeginn, Haltezeiten, Ende einer Übersteuerung, Tageswechsel). Es gibt kein Abfragen im Sekundentakt.

### Gruppen und Fenster

* Eine **Gruppe** ist eine Himmelsrichtung: Azimut von und bis sowie beliebig viele Sonnensensoren (PV-Leistung, Helligkeit in Lux, Strahlung z. B. von Open-Meteo). Eine Gruppe hat keine Schwellen.
* Ein **Fenster** ist ein Rollo mit Fensterkontakt(en) und einer Gruppe. Alle Schwellen, Positionen und Zeiten stehen am Fenster.

### Sonnenschutz

* **Sommertag:** Sonnenschutz gibt es nur an Sommertagen. Beim Tageswechsel (Standard 01:00) wird die Höchsttemperatur der Tagesvorhersage geprüft. Steigt die Außentemperatur tagsüber über die Schwelle, wird es ebenfalls ein Sommertag, aber nur, wenn der Vorhersage-Tiefstwert der kommenden Nacht mindestens 14 °C beträgt (einstellbar). Ein warmer Nachmittag im Frühling oder Herbst mit kühler Nacht löst also keinen Sonnenschutz aus. Ohne Tiefstwert in der Vorhersage gilt der Sommertag wie bisher.
* **Sonnenbedingung je Fenster:** Sommertag UND Außentemperatur über der Schwelle des Fensters (mit Haltezeit) UND jeder Sonnensensor der Gruppe über seiner Schwelle. Das Ganze muss die Sonnen-Haltezeit lang erfüllt sein und endet sofort. Nach einem Neustart wird sofort ausgewertet, die Haltezeit läuft ab dem Start.
* **Wärmebedarf (optional):** Mit einer **Raumtemperatur** je Fenster wird nur abgesenkt, wenn der Raum zu warm ist: bei einem Thermostat (climate) ab Sollwert + 2 K, bei einem Temperatursensor ab 24 °C. Kühlt die gewählte **Klimaanlage**, gilt der Raum als zu warm, der Sonnenschutz entlastet sie. Meldet sie keine Aktion (z. B. Midea), zählt der Modus „Kühlen“ und im Modus „Auto“ eine Raumtemperatur über ihrem Sollwert. Ist die globale **Heizbedarf**-Entität an (z. B. ein input_boolean „Heizperiode“), ist Sonnenwärme erwünscht: Abgesenkt wird dann nur, wenn der Raum trotzdem zu warm ist. Fenster ohne Raumtemperatur bleiben dann oben. Das Wiederöffnen ist davon unabhängig, es hängt weiter nur am Sonnenstand.
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

In den Grundeinstellungen (Dashboard **Allgemein**, Karte **Manuelle Übersteuerung**) lässt sich wählen, wann sie beginnt: **nur wenn das Rollo wirklich fährt** (Standard; die Position ändert sich um mehr als 2 %, bei Rollos ohne Position steht es danach anders) oder **bei jedem Befehl von Hand, auch ohne Fahrt**. Mit dem Standard startet z. B. „Alexa, alle Rollos auf“ keine Übersteuerung bei Rollos, die schon offen sind.

### Zusatzbedingungen statt Sonderregeln

* **Öffnungssperre:** solange eine Entität nicht in einem der Freigabe-Zustände ist, wird nicht automatisch geöffnet (Auto-Hoch, Lüften, Urlaub morgens, Morgenöffnung). Beispiel: Fernseher an.
* **Schließ-Auslöser:** wird eine der Entitäten aktiv (Ein-Verzögerung), schließt das Rollo einmal pro Aktiv-Zyklus, wenn es weiter offen ist als die Mindestposition und das Fenster zu ist. Ist das Fenster offen, wird geschlossen, sobald es zu ist. Der Zyklus endet, wenn alle Entitäten inaktiv sind (Aus-Verzögerung). Beispiel: Fernseher einschalten schließt das Wohnzimmer-Rollo.
* **Fenster-Ausnahme:** solange eine Entität verfügbar ist, verhindert ein offenes Fenster keine Schließfahrt und es gibt keine Benachrichtigung. Beispiel: Klimaanlage mit Schlauch durch die Balkontür.

### Morgenöffnung (pro Fenster, Standard aus)

Modi: feste Uhrzeit (Werktag sowie Wochenende und Feiertag über einen optionalen Werktag-Sensor), Sonnenaufgang oder Sonnenhöhe mit Versatz, Helligkeit der Gruppe über einer Schwelle mit Haltezeit, Auslöser-Entität (Zeitstempel wie der nächste Wecker des Handys, oder eine Entität, die angeht). Dazu ein Zeitfenster frühestens und spätestens, eine Zielposition (offen oder Teilöffnung) und optional direkt die Sonnenschutz-Position, wenn die Sonnenbedingung gilt. Nicht bei Übersteuerung, Öffnungssperre oder einem seit dem Abend von Hand verstellten Rollo.

### Urlaubssimulation

Solange eine der Urlaubs-Entitäten an ist (z. B. ein input_boolean „Urlaub“), ruht der normale Abendlauf. Stattdessen öffnen die teilnehmenden Fenster morgens zu einer zufälligen Zeit (Standard 07:00 bis 08:00) auf eine zufällige Position (60 bis 100 %) und schließen abends zufällig (19:00 bis 20:30). Sonnenschutz und Lüften laufen weiter.

### Neustart-Schutz

Nach dem Start von Home Assistant gibt es einige Minuten (Standard 5) keine Fahrten. Danach wird ausgewertet und der Abendlauf für noch nicht geschlossene Fenster nachgeholt (nur ab 12:00). Übersteuerungen, Tagesmarker und der Automatik-Schalter bleiben über Neustarts erhalten.

## Installation über HACS

1. HACS öffnen, oben rechts im Menü **Benutzerdefinierte Repositories** wählen.
2. Repository `https://github.com/Jumpmaster2/Shutter-Assistant`, Typ **Integration**, hinzufügen.
3. **Shutter Assistant** herunterladen und Home Assistant neu starten.
4. **Einstellungen > Geräte & Dienste > Integration hinzufügen > Shutter Assistant**.
5. Gruppen und Fenster im Dashboard **Shutter Assistant** (Seitenleiste) anlegen.

Voraussetzung: Home Assistant 2026.10 oder neuer und die Integration **Sonne** (Sun, standardmäßig eingerichtet). Eine Wetter-Entität mit Vorhersage und ein Werktag-Sensor sind optional.

## Manuelle Installation

1. Die neueste Version herunterladen und den Ordner `custom_components/shutter_assistant` in den Ordner `config/custom_components/` von Home Assistant kopieren.
2. Home Assistant neu starten und die Integration wie oben beschrieben hinzufügen.

## Temperatur-Einheiten

Alle Temperaturen (Schwellen, Vorhersage, Raum) gelten in der Einheit des Einheitensystems von Home Assistant. Bei °F werden die Standardwerte umgerechnet (Sommertag ab 73 °F, Nacht ab 57 °F, Außentemperatur ab 66 °F, Raum ab 75 °F, Sollwert plus 4 °F). Wird das Einheitensystem später umgestellt, die Schwellen bitte von Hand anpassen.

## Konfiguration

### Dashboard

Nach der Einrichtung gibt es in der Seitenleiste die Seite **Shutter Assistant** (nur für Administratoren). **Einstellungen** bei der Integration (Geräte & Dienste) öffnet direkt diese Seite.

* **Übersicht:** Automatik an/aus, Sommertag (Vorhersage und Schwelle), Beginn des Abendmodus, Urlaub und Neustart-Schutz. Dazu der **Sonnenkompass** mit dem aktuellen Sonnenstand und den Bereichen der Gruppen, Hinweise (z. B. eingestellte Entitäten, die es nicht gibt, oder eine gelöschte Gruppe) und alle Fenster mit Status, Position, Fensterkontakt und letztem Grund. Eine laufende Übersteuerung lässt sich direkt **beenden**. Der **Sonnenbedingung-Check** zeigt je Fenster jede Teilbedingung mit aktuellem Wert und Schwelle: Sommertag (mit Nacht-Tiefstwert, wenn die Außentemperatur ihn ausgelöst hat), Außentemperatur, jeder Sonnensensor, Raum, Klimaanlage, Heizbedarf, Haltezeit (mit Uhrzeit, ab wann sie erfüllt ist) und ob die Sonne im Bereich steht.
* **Fenster:** alle Fenster als Tabelle, anklicken zum Bearbeiten. Der Editor zeigt die Einstellungen nach Themen in Karten (Fenster, Sonnenschutz, Manuellen Sonnenschutz erkennen, Abend, Übersteuerung, Lüften & Urlaub, Morgenöffnung, Zusatzbedingungen). Es erscheinen nur die Felder, die gerade gelten: Schwellen nur für die Sensortypen der Gruppe, eigene Abendzeiten nur wenn eingeschaltet, bei der Morgenöffnung nur die Felder des gewählten Modus. **Duplizieren** legt ein neues Fenster mit denselben Einstellungen an, nur Rollo und Fensterkontakte werden neu gewählt.
* **Gruppen:** Himmelsrichtungen mit den aktuellen Werten ihrer Sensoren und den Fenstern, die sie verwenden. Beim Bearbeiten zeigt der Kompass den Bereich der Gruppe sofort an.
* **Haus im Kompass** (unter **Allgemein**): Länge der Vorderseite, Tiefe und die Richtung, in die die Vorderseite zeigt. Sind alle drei Werte eingetragen, erscheint das Haus maßstabsgetreu gedreht in der Mitte des Kompasses. Einer Gruppe lässt sich dann eine **Wand** zuordnen: der Azimut-Bereich wird auf die Ausrichtung der Wand ± 90° gesetzt (danach frei änderbar) und die Wand erscheint in der Farbe der Gruppe. **Fenster** erscheinen als Markierung an ihrer Wand (eigene Wand oder die der Gruppe), live eingefärbt nach Sonnenschutz, Übersteuerung und Abend, hohl bei offenem Fenster; ein Klick öffnet das Fenster. Mit **Position an der Wand** (1, 2, 3 …) lässt sich die Reihenfolge der Fenster einer Wand festlegen: 1 ist ganz links, von innen durch die Wand nach draußen geschaut; Fenster ohne Zahl kommen danach.
* **Allgemein** und **Abend & Urlaub:** die globalen Einstellungen in Karten, jede Karte wird für sich gespeichert.

Die Werte werden genauso geprüft wie in den Dialogen (gleiche Bereiche, Einheiten und Regeln). Die Dialoge (Optionen, Gruppe und Fenster hinzufügen oder ändern) gibt es weiterhin.

### Einrichtung und Optionen (global)

| Option | Standard | Bedeutung |
|---|---|---|
| Außentemperatur-Sensor | | ohne Sensor gilt die aktuelle Temperatur der Wetter-Entität (mindestens eins von beiden) |
| Wetter-Entität | die einzige, falls es genau eine gibt | Vorhersage für den Sommertag |
| Sprache der Meldungen | wie Home Assistant | Deutsch oder Englisch für Logbuch, letzten Grund und Push |
| Benachrichtigungsdienste | | nur `notify.*`, z. B. `notify.mobile_app_phone` |
| Werktag-Sensor | | optional, für die Morgenöffnung (z. B. Workday-Integration, kennt Feiertage) |
| Wochenendtage | Samstag, Sonntag | nur ohne Werktag-Sensor |
| Sommertag ab | 23 °C | Höchsttemperatur der Vorhersage |
| Später Sommertag nur bei Nacht ab | 14 °C | Tiefstwert der kommenden Nacht, wenn erst die Außentemperatur den Sommertag auslöst |
| Heizbedarf | | optional, z. B. ein `input_boolean` „Heizperiode“; an = Sonnenwärme erwünscht |
| Tageswechsel | 01:00 | Vorhersage prüfen, Tagesmarker zurücksetzen |
| Vorhersage-Art | automatisch | täglich, zweimal täglich oder stündlich; automatisch nimmt die erste, die die Wetter-Entität kann |
| Abendmodus frühestens, Sonnenhöhe, spätestens | 17:00, -4 °, 21:00 | |
| Ende der Nacht | 03:30 | |
| Nachziehen ab | 16:00 | |
| Urlaubs-Entitäten | | "an" = Urlaub |
| Urlaub morgens ab, Zufallszeitraum | 07:00, 60 min | |
| Öffnungsposition von, bis | 60 %, 100 % | |
| Urlaub abends ab, Zufallszeitraum | 19:00, 90 min | |
| Übersteuerung beginnt | nur bei echter Fahrt | oder bei jedem Befehl von Hand, auch ohne Fahrt |
| Neustart-Schutz | 5 min | |
| Abendlauf nachholen ab | 12:00 | |
| Fenster gilt als geschlossen nach (Erweitert) | 5 s | Entprellung der Fensterkontakte |
| Dashboard in der Seitenleiste (Erweitert) | an | aus: nur noch über „Einstellungen“ bei der Integration erreichbar |

### Gruppen

**Gruppe hinzufügen**: Name, Azimut von und bis (90 ° = Ost, 180 ° = Süd, 270 ° = West; die Grenzen selbst zählen nicht), Strahlungs-, PV- und Helligkeitssensoren.

### Fenster

**Fenster hinzufügen** in vier Schritten:

1. **Fenster:** Name, Rollo, Fensterkontakte, Gruppe (ohne Gruppe kein Sonnenschutz).
2. **Sonnenschutz:** Schwellen für die Sensortypen der Gruppe, Außentemperatur mindestens (19 °C), Haltezeiten Temperatur (10 min) und Sonne (5 min), Raumtemperatur (Thermostat: zu warm ab Sollwert + 2 K, Sensor: ab 24 °C), Klimaanlage, Sonnenschutz-Position (10 %), Toleranz für Auto-Hoch (5 %), Auto-Hoch, Benachrichtigung bei offenem Fenster, manueller Sonnenschutz bis (25 %), Erkennungszeitraum (5 min), Nachlauf (5 min), Fahrt auf Sonnenschutz-Position zählt.
3. **Verhalten:** Übersteuerung (60 min, Sonnenaufgang, Abend- und Urlaubsfahrten trotz Übersteuerung), Zusatzbedingungen, Abend (Abendlauf, Nachziehen, eigene Abendzeiten), Lüften (30 %, gilt als geschlossen bis 5 %, 3 s abends, 60 s tagsüber), Urlaubssimulation.
4. **Morgenöffnung:** an oder aus, Modus und Zeitfenster, danach die Einstellungen des Modus.

Positionen: 100 % = offen, 0 % = zu.

**Ändern:** im Dashboard oder über das Zahnrad beim Fenster, dann die Kategorie wählen (Fenster, Sonnenschutz, Verhalten, Morgenöffnung). Jede Kategorie wird für sich gespeichert, die anderen bleiben unverändert.

## Entitäten

Global (Gerät "Shutter Assistant"):

* Schalter **Automatik** (aus = keine automatische Fahrt; bleibt über Neustarts erhalten)
* Binärsensoren **Sommertag** und **Abendmodus**
* Sensor **Vorhersage Höchsttemperatur**

Je Fenster (eigenes Gerät):

* Sensor **Status** (Automatik aus, Neustart-Schutz, Manuelle Übersteuerung, Abends geschlossen, Sonnenschutz, Urlaubssimulation, Bereit)
* Sensor **Letzter Grund** (Text, Code, Position, Zeit)
* Binärsensoren **Manuelle Übersteuerung** (mit Ende), **Sonnenbedingung** (mit Teilbedingungen), **Sonnenschutz heute**, **Abends geschlossen**

Für Kontroll-Karten im Dashboard liefern **Sonnenbedingung** (Schwellen, Sensoren, Azimut-Bereich, Haltezeiten und wann sie ablaufen) und **Status** (Rollo, Fensterkontakte, Abendbeginn, Übersteuerung bis) alle Werte als Attribute. **Abendmodus** hat Beginn und Ende des aktuellen oder nächsten Abends, **Automatik** das Ende eines laufenden Neustart-Schutzes.

Jede Fahrt und jede Übersteuerung steht mit Grund im **Logbuch**.

## Eigene Dashboard-Karten

Die Attribute der Entitäten lassen sich in eigenen Karten verwenden, zum Beispiel:

```yaml
type: entities
title: Wohnzimmer
entities:
  - entity: sensor.wohnzimmer_status
  - entity: binary_sensor.wohnzimmer_sonnenbedingung
    secondary_info: last-changed
  - type: attribute
    entity: sensor.wohnzimmer_status
    attribute: evening_start
    name: Abend ab
  - type: attribute
    entity: binary_sensor.wohnzimmer_sonnenbedingung
    attribute: condition_on_at
    name: Sonnenbedingung erfüllt ab
```

„Sonnenbedingung“, „Letzter Grund“ und „Vorhersage Höchsttemperatur“ sind Diagnose-Entitäten. Die Attribute von „Sonnenbedingung“ und „Status“ werden nicht im Verlauf gespeichert (sie ändern sich oft).

## Fehlerbehebung

* **Kein Sonnenschutz:** im Dashboard den **Sonnenbedingung-Check** des Fensters öffnen. Jede Teilbedingung zeigt Wert und Schwelle. Häufige Gründe: kein Sommertag (Vorhersage unter der Schwelle), keine Gruppe, ein Sonnensensor unter der Schwelle, die Haltezeit läuft noch, offenes Fenster, aktive Übersteuerung.
* **Übersteuerung startet ungewollt:** „Nur wenn das Rollo wirklich fährt“ wählen (Dashboard **Allgemein**, Karte **Manuelle Übersteuerung**). Fahrten anderer Automationen und Skripte zählen nie.
* **Keine Vorhersage:** Dashboard und Reparaturen zeigen einen Hinweis, wenn die Wetter-Entität keine Vorhersage liefert. Vorhersage-Art oder eine andere Wetter-Entität wählen.
* **Rollo fährt nicht auf eine Position:** Rollos ohne Positionsunterstützung können nur auf und zu (im Log steht eine Warnung).
* **Diagnose:** Einstellungen > Geräte & Dienste > Shutter Assistant > ⋮ > Diagnose herunterladen (Benachrichtigungsdienste sind geschwärzt).

### Debug-Log

```yaml
logger:
  default: warning
  logs:
    custom_components.shutter_assistant: debug
```

Oder bei der Integration: ⋮ > **Debug-Protokollierung aktivieren**.

## Entfernen

Einstellungen > Geräte & Dienste > Shutter Assistant > ⋮ > **Löschen**. Gespeicherter Zustand (Übersteuerungen, Marker), Dashboard und Reparaturhinweise werden entfernt. Danach den Ordner bzw. den HACS-Download entfernen.

## Umstieg von YAML-Automationen

Siehe [docs/migration.md](docs/migration.md).

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

Die Beschriftungen des Dashboards (`frontend/labels.js`) werden aus den Übersetzungen erzeugt: nach einer Änderung an `translations/*.json` einmal `python scripts/gen_labels.py` ausführen (ein Test prüft das).

Die Regeln in `custom_components/shutter_assistant/logic/` haben keine Abhängigkeit zu Home Assistant und sind einzeln testbar. Die Tests mit Home Assistant brauchen Linux oder macOS (sie laufen auch in GitHub Actions). Linter: `ruff check custom_components tests scripts`.

## Lizenz

MIT, siehe [LICENSE](LICENSE).
