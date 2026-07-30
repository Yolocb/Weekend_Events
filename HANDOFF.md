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
- Quellen (`scripts/sources.json`): **12 aktiv, 10 liefern Events**. iCal: Heidelberg,
  Wiesloch. dvv-HTML (parse_vevents, 3 Layout-Varianten): Rhein-Neckar-Kreis,
  Neckargemünd, Waibstadt (5,7 km!), Mosbach, Schwetzingen. HTML-Heuristik: Sinsheim,
  Regionsportal, Eppingen, Angelbachtal (6,7 km), Östringen. Reserve: Heilbronn, Bruchsal.
- GitHub-Actions-Workflow `weekly-scan.yml`: **montags** 05:17 UTC (`17 5 * * 1`)
  + workflow_dispatch; committet events.json + review.json automatisch.
- GitHub Pages aktiv (Branch main, /docs). Workflow-Schreibrechte aktiv.
- events.json enthält aktuell **12 echte Events** (keine Beispieldaten).
- **Wetter pro Event** (Open-Meteo, kein Key) + **Indoor/Outdoor-Badge** + plausibilisierte
  Wetteranzeige. **Kalender-Button (.ics)** pro Event.
- Letzter Commit: `3f5b287` (4 weitere Quellen + robusterer dvv-Parser).

## Wichtige Stellschrauben (in scan_events.py)
- `ANZAHL_WOCHENENDEN = 2` — wie viele Wochenenden abdecken.
- `SCHWELLE = 0.5` — ab hier auf die Seite (niedriger = mehr, höher = strenger).
- `POSITIV` / `NEGATIV` / `KINDER_BEZUG` — Keyword-Listen fürs Scoring.
- `DRAUSSEN_KEYS` / `DRINNEN_KEYS` — Indoor/Outdoor-Erkennung.
- `WMO` + `plausibilisiere_wetter()` — Wettercode→Text/Emoji, Widerspruchs-Bereinigung.
- `parse_vevents()` — dvv-Plattform, **3 Layout-Varianten** (vevent/summary,
  zmitem/titelzmtitel, zmitem__time/a.titel). Browser-User-Agent noetig (sonst
  liefern dvv-Seiten Bots abgespeckte Version ohne Events).
- Scoring bewusst inklusiv: Kinderbezug ist Bonus (nicht Pflicht).

## ERLEDIGT (bisherige Sessions)
- Idee 1: Mehr Quellen — von 3 auf **12 aktive Quellen** (10 mit Events) ausgebaut.
- Idee 4: Kalender-Button (.ics) pro Event.
- Wetter-Hinweis + Indoor/Outdoor, danach plausibilisiert; Regen%-Anzeige entfernt.
- Qualitaets-Report (report.md) pro Lauf.
- Rhein-Neckar-Kreis-Fix (Browser-UA + hCalendar/vevent-Parser) -> skalierte auf
  Neckargemünd, Waibstadt, Mosbach, Schwetzingen (alle dvv-Plattform).
- Alle 13 Umkreis-Gemeinden systematisch geprueft.

## NÄCHSTE SCHRITTE — offene Ideen (morgen)
- **Favoriten/„Wir gehen hin"** (Merken-Funktion, Frontend/localStorage).
- **Karten-Ansicht** (Leaflet/OpenStreetMap, Koordinaten aus orte.json).
- **Ortserkennung verbessern**: „Neckarmünzplatz"→Heidelberg, PLZ aus Text,
  entfernungKm:null vermeiden.
- **Auswahl-Qualitaet/Duplikate**: review.json (~103) sichten; doppelte Events
  mit gleichem Titel aber unterschiedlichem Datum (z.B. „Schatzsuche") ggf. bundeln.
- Nicht erschlossen (kein einfacher Zugang, kein dvv): Leimen, Walldorf, Nussloch,
  Meckesheim, Bad Rappenau, Zuzenhausen, Neckarbischofsheim, Mühlhausen, Bammental,
  Hockenheim (dvv, aber 0 Events auf Kalenderseite).

## Betrieb / Konventionen
- Alles Deutsch (UI, Code, Commits). Vanilla JS + statisch, keine Frameworks.
- Neue Events immer erst prüfen, bevor manuellGeprueft:true.
- Voll-Scans über GitHub-Workflow (lokales Netz zeitweise unzuverlässig).
- Lokales Ansehen: `cd docs && python -m http.server 8000`.
- Vor Git-Push mit User abstimmen.
- Workflow-Status per API:
  https://api.github.com/repos/Yolocb/Weekend_Events/actions/workflows/weekly-scan.yml/runs?per_page=1
