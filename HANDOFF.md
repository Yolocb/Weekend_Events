# Handoff: Weekend-Events — Stand & nächste Ideen

**Datum:** 2026-07-30. Erste Version fertig, live & produktiv.

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
- Quellen (`scripts/sources.json`): aktiv = Heidelberg (iCal-Sammelfeed!), Sinsheim
  (HTML), Regionsportal „Im Süden ganz oben". Inaktiv/Reserve: Rhein-Neckar-Kreis,
  Heilbronn, Bruchsal, Wiesloch.
- GitHub-Actions-Workflow `weekly-scan.yml`: **montags** 05:17 UTC (`17 5 * * 1`)
  + workflow_dispatch; committet events.json + review.json automatisch.
- GitHub Pages aktiv (Branch main, /docs). Workflow-Schreibrechte aktiv.
- events.json enthält aktuell **12 echte Events** (Beispieldaten entfernt).
- Erster Workflow-Lauf lief erfolgreich, Auto-Commit bestätigt.

## Wichtige Stellschrauben (in scan_events.py)
- `ANZAHL_WOCHENENDEN = 2` — wie viele Wochenenden abdecken.
- `SCHWELLE = 0.5` — ab hier auf die Seite (niedriger = mehr, höher = strenger).
- `POSITIV` / `NEGATIV` / `KINDER_BEZUG` — Keyword-Listen fürs Scoring.
- Scoring bewusst inklusiv: Kinderbezug ist Bonus (nicht Pflicht); allgemeine
  Familien-Events kommen durch, klar Erwachsenes (Wein/Tango/Führungen) fliegt raus.

## NÄCHSTE SCHRITTE — 5 Vorschläge (User will später wählen)
1. **Mehr Quellen aktivieren** (größter Daten-Hebel): weitere iCal/RSS in der
   Region suchen (Klima-Arena Sinsheim, Museen, Stadtfeste), Reserve-Quellen
   scharfschalten.
2. **Ortserkennung/Entfernung verlässlicher**: PLZ aus Text ziehen, Stadtteile →
   Stadt (Bsp „Neckarmünzplatz"→Heidelberg); entfernungKm:null vermeiden.
3. **E-Mail-Benachrichtigung montags** (größter Alltagsnutzen): Workflow schickt
   kurze Wochenübersicht per Mail.
4. **Kalender-Export (.ics) pro Event** (schnellster Gewinn): „Zum Kalender"-Button;
   Logik aus dem iphone-crm-workflow-Projekt übertragbar.
5. **Auswahl-Qualität schärfen**: Grenzfälle (Überraschungstour, Genuss-/Kulturmarkt),
   bessere Alters-/Kontexterkennung, review.json einmal durchgehen.

Empfehlung: #3 (Alltagsnutzen) oder #1 (Daten-Hebel) zuerst; #4 als schneller Gewinn.

## Betrieb / Konventionen
- Alles Deutsch (UI, Code, Commits). Vanilla JS + statisch, keine Frameworks.
- Neue Events immer erst prüfen, bevor manuellGeprueft:true.
- Voll-Scans über GitHub-Workflow (lokales Netz zeitweise unzuverlässig).
- Lokales Ansehen: `cd docs && python -m http.server 8000`.
- Vor Git-Push mit User abstimmen.
- Workflow-Status per API:
  https://api.github.com/repos/Yolocb/Weekend_Events/actions/workflows/weekly-scan.yml/runs?per_page=1
