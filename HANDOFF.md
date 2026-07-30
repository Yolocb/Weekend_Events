# Handoff: Weekend-Events — Stand & nächste Ideen

**Datum:** 2026-07-30 (aktualisiert). Live & produktiv; Quellen erweitert,
Kalender-Button + Wetter/Indoor-Outdoor ergänzt.

## Projekt-Kontext
Statische Website mit besonderen Kinder-/Familien-Events (Feste, Ferienprogramme,
Aktionstage …) in der Region Sinsheim (~30 km). Nur Besonderes, keine Dauerangebote.
Zielgruppe: Familie mit 10-jähriger Tochter, Sinsheim-Hoffenheim.

- **Live:** https://yolocb.github.io/Weekend_Events/
- **Repo:** https://github.com/Yolocb/Weekend_Events (Branch main)
- **Lokal:** `C:\Users\D043877\Claude Projects\Weekend-Events`
- **Letzter Commit:** `142d9dc`

## Aktueller Stand (fertig & live)
- Statische Site (docs/), Vanilla JS, mobile-first, seriöses Design, gut lesbar.
- Python-Scraper `scripts/scan_events.py`: iCal + HTML-Fallback, Haversine-
  Entfernung (orte.json), Keyword-Scoring, Zeitfenster = **2 Wochenenden**, Dedup,
  `manuellGeprueft`-Schutz, review.json für unsichere Treffer.
- Quellen (`scripts/sources.json`): **5 aktiv** = Heidelberg (iCal), Sinsheim (HTML),
  Regionsportal „Im Süden ganz oben" (HTML), **Wiesloch (iCal, neu)**,
  **Rhein-Neckar-Kreis (HTML, neu)**. Reserve/inaktiv: Heilbronn, Bruchsal.
- GitHub-Actions-Workflow `weekly-scan.yml`: **montags** 05:17 UTC (`17 5 * * 1`)
  + workflow_dispatch; committet events.json + review.json automatisch.
- GitHub Pages aktiv (Branch main, /docs). Workflow-Schreibrechte aktiv.
- events.json enthält aktuell **12 echte Events** (keine Beispieldaten).
- **Wetter pro Event** (Open-Meteo, kein Key) + **Indoor/Outdoor-Badge** + plausibilisierte
  Wetteranzeige. **Kalender-Button (.ics)** pro Event.
- Letzter Commit: `3373441` (Wetteranzeige plausibilisieren).

## Wichtige Stellschrauben (in scan_events.py)
- `ANZAHL_WOCHENENDEN = 2` — wie viele Wochenenden abdecken.
- `SCHWELLE = 0.5` — ab hier auf die Seite (niedriger = mehr, höher = strenger).
- `POSITIV` / `NEGATIV` / `KINDER_BEZUG` — Keyword-Listen fürs Scoring.
- `DRAUSSEN_KEYS` / `DRINNEN_KEYS` — Indoor/Outdoor-Erkennung.
- `WMO` + `plausibilisiere_wetter()` — Wettercode→Text/Emoji, Widerspruchs-Bereinigung.
- Scoring bewusst inklusiv: Kinderbezug ist Bonus (nicht Pflicht); allgemeine
  Familien-Events kommen durch, klar Erwachsenes (Wein/Tango/Führungen) fliegt raus.

## ERLEDIGT (bisherige Sessions)
- Idee 1: Mehr Quellen — Wiesloch (iCal) + Rhein-Neckar-Kreis aktiviert (Commit 17256c4).
- Idee 4: Kalender-Button (.ics) pro Event (Commit 1f3eaa2).
- Wetter-Hinweis + Indoor/Outdoor pro Event (Commit 7f961ce), danach plausibilisiert (3373441).
- Design mehrfach überarbeitet: seriös/professionell, lesbare Quellenangaben
  (Klassen-Konflikt fuss/seiten-fuss behoben).

## NÄCHSTE SCHRITTE — offene Ideen
Aus erster Liste offen:
- **Ortserkennung/Entfernung verlässlicher**: PLZ aus Text, Stadtteile→Stadt
  (Bsp „Neckarmünzplatz"→Heidelberg); entfernungKm:null vermeiden.
- **E-Mail-Wochenübersicht montags** (Workflow schickt Zusammenfassung per Mail).
- **Auswahl-Qualität schärfen**: Grenzfälle, bessere Alters-/Kontexterkennung, review.json sichten.

Aus zweiter Vorschlagsrunde offen:
- **Favoriten/„Wir gehen hin"** (Merken-Funktion, rein Frontend/localStorage).
- **Karten-Ansicht** (Leaflet/OpenStreetMap, Koordinaten aus orte.json).
- **Archiv vergangener Events**.
- **Qualitäts-Report pro Lauf** (Zusammenfassung im Workflow).

## Betrieb / Konventionen
- Alles Deutsch (UI, Code, Commits). Vanilla JS + statisch, keine Frameworks.
- Neue Events immer erst prüfen, bevor manuellGeprueft:true.
- Voll-Scans über GitHub-Workflow (lokales Netz zeitweise unzuverlässig).
- Lokales Ansehen: `cd docs && python -m http.server 8000`.
- Vor Git-Push mit User abstimmen.
- Workflow-Status per API:
  https://api.github.com/repos/Yolocb/Weekend_Events/actions/workflows/weekly-scan.yml/runs?per_page=1
