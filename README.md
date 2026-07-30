# Weekend-Events — Besondere Kinder-Events rund um Sinsheim

Statische Website, die **wöchentlich besondere Kinder- und Familienveranstaltungen**
(Feste, Ferienprogramme, Aktionstage, Sonderausstellungen, Märkte, Aufführungen)
in der Region Sinsheim (~30 km) anzeigt. **Standard-Dauerangebote werden bewusst
ausgeblendet** — es geht nur um das Besondere fürs Wochenende.

- **Live-Seite:** https://yolocb.github.io/Weekend_Events/
- **Repository:** https://github.com/Yolocb/Weekend_Events
- **Zielgruppe:** Familie mit Kind (~6–12 Jahre)
- **Betrieb:** Python-Scraper → `events.json` → GitHub Pages, wöchentlich (montags) per GitHub Actions
- **Frontend:** Vanilla HTML/CSS/JS, mobile-first, keine Frameworks

## Projektstruktur

```
Weekend-Events/
├── docs/                         ← GitHub-Pages-Ordner
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── data/
│       ├── events.json           ← sichere Treffer (für die Seite)
│       └── review.json           ← unsichere Treffer (zur Prüfung)
├── scripts/
│   ├── scan_events.py            ← Scraper (Feeds+HTML, Haversine, Scoring)
│   ├── sources.json              ← kuratierte Quellen-Liste
│   ├── orte.json                 ← Orte→Koordinaten (Entfernung)
│   └── requirements.txt
├── .github/workflows/weekly-scan.yml
├── PROJEKT-PROMPT.md
└── README.md
```

## Lokal testen

```bash
# Scraper (schreibt docs/data/events.json + review.json)
cd scripts
pip install -r requirements.txt
python scan_events.py --verbose

# Frontend ansehen
cd ../docs
python -m http.server 8000   # dann http://localhost:8000
```

## Deployment über GitHub Pages

1. Repo auf GitHub anlegen und pushen.
2. **Settings → Pages → Source:** Branch `main`, Ordner `/docs`.
3. **Settings → Actions → General → Workflow permissions:** „Read and write
   permissions" aktivieren (damit der Workflow committen darf).

## Wöchentlicher Betrieb (GitHub Actions)

Der Workflow `weekly-scan.yml` läuft **montags** automatisch (plus manuell über
„Run workflow"), führt den Scraper aus und committet geänderte `events.json` /
`review.json` zurück. GitHub Pages aktualisiert die Seite dann selbst.

## Quellen pflegen (`scripts/sources.json`)

Neue Quelle ergänzen:
```json
{ "name": "Stadt XY", "ort": "XY", "url": "https://…/veranstaltungen",
  "typ": "html", "aktiv": true, "prioritaet": 3 }
```
- **`typ`:** `ical` (bevorzugt, stabilster Weg) · `rss` · `html` (Fallback).
- **Vor dem Aktivieren prüfen:** Gibt es einen iCal/RSS-Feed? Ist die Seite
  JavaScript-gerendert? (Dann findet der HTML-Scraper nichts — der Scraper meldet
  das im Log als „vermutlich JS-gerendert".)
- Neue Orte mit Koordinaten in `orte.json` ergänzen (für die Entfernungsberechnung).

## Wie die Filterung funktioniert

- **Positiv-/Negativ-Keywords** + Kinder-/Familienbezug + Datum im Fenster + Umkreis
  ergeben einen **Relevanz-Score (0–1)**.
- **Score ≥ 0.6** → `events.json` (Seite); darunter → `review.json` (Prüfliste).
- **Zeitfenster:** ab Scan-Tag bis kommenden Sonntag („dieses Wochenende") + 7 Tage
  Ausblick. Vergangene Events fallen automatisch raus.
- **`manuellGeprueft: true`** an einem Event schützt es vor Überschreiben und hält
  es (solange im Fenster) auf der Seite — für von dir bestätigte Termine.

## Aktueller Reifegrad & nächste Schritte

Das Grundgerüst ist **lauffähig und feinjustiert**. Der letzte Testlauf band den
Heidelberg-iCal-Feed an (876 Rohtreffer) und lieferte nach Filterung echte
Kinder-Events wie „Minecraft Kreativtag", „Dash programmieren" (Kinder-Coding),
„Mario Kart Turnier" und „Onilo Boardstory" (Kinder-Vorlesen).

**Bereits umgesetzter Feinschliff:**
- **Datums-Parsing:** Einzeldaten, „Datum: …", **Zeitspannen** („30.07. bis
  28.08.", „28.–30. Juli") inkl. `datumEnd`.
- **Titel-Extraktion:** Überschrift/Link bevorzugt, Kalender-Präfixe/Metadaten
  („30 Jul", „Details einblenden", „Datum/Veranstalter …") werden entfernt.
- **Scoring:** Kinder-/Familienbezug ist **entscheidend** — ohne ihn bleibt der
  Score unter der Schwelle. Erweiterte Negativliste (Repair Café, Weinfest,
  Stadtführungen/Rundgänge u. a.) hält Erwachsenen-Formate fern.
- **Heidelberg-iCal** angebunden (Sammel-Feed, stabilste Quelle).

**Weiterhin sinnvoll (iterativ):**
- Einzelne Grenzfälle nachschärfen (z. B. „Überraschungstour Altstadt").
- Ortserkennung verfeinern (Heidelberg-Feed nennt teils „Neckarmünzplatz" statt
  Stadt → in `orte.json` ergänzen).
- Weitere Quellen aus der Ausbau-Reserve aktivieren.
- **`review.json` sichten** und echte Treffer per `manuellGeprueft: true` übernehmen.

## Recht & Qualität

- **Immer Quelle verlinken**; „Angaben ohne Gewähr, bitte beim Veranstalter prüfen".
- Termine **nie erfinden** — nur, was aus einer Quelle stammt.
- robots.txt & Nutzungsbedingungen der Quellen respektieren; höfliche Request-Rate.
