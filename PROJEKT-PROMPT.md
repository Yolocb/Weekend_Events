# Projekt-Prompt: „Weekend-Events" — Kinder-Events rund um Sinsheim

> Diesen Prompt in Visual Studio (mit Opus als LLM / Vibe Programming) als
> Startauftrag verwenden. Kopiere den Abschnitt „PROMPT" komplett.
> (Optimierte Fassung — Datums-, Umkreis- und Datenquellen-Logik geschärft.)

---

## PROMPT

Du bist ein erfahrener Senior Web Developer und Data Engineer. Baue mir ein
vollständiges, lauffähiges Projekt namens **„Weekend-Events"**. Arbeite iterativ,
triff bei Unklarheiten sinnvolle Standard-Annahmen und weise mich darauf hin.

### Ziel
Eine **statische Website**, die **wöchentlich besondere Kinder-Events in der
Region Sinsheim** anzeigt. Zielgruppe: Familie mit einer 10-jährigen Tochter.
Es geht **ausschließlich um Besonderes** — Feste, Sonderveranstaltungen,
Ferienprogramme, Aktionstage, temporäre Ausstellungen, Märkte, Mitmach-Aktionen,
Aufführungen. **Standard-Dauerangebote** (reguläre Öffnungszeiten von Schwimmbad,
Museum, Spielplatz; laufende Vereins-/Kursangebote) sollen **NICHT** erscheinen.

### Region & Entfernungsberechnung
- Mittelpunkt: **74889 Sinsheim** (Koordinaten ca. 49.252 N, 8.878 E).
- Umkreis: **max. ca. 30 km Luftlinie** (u. a. Heidelberg, Heilbronn, Bad Rappenau,
  Eppingen, Wiesloch, Bruchsal, Hockenheim, Neckargemünd).
- **Entfernung konkret berechnen:** Pro Event-Ort eine Koordinate bestimmen und die
  **Luftlinie zu Sinsheim per Haversine-Formel** rechnen (kein bezahltes API nötig).
  Nutze eine **kleine, gepflegte Orts→Koordinaten-Tabelle** (`orte.json`) für die
  bekannten Städte/Gemeinden der Region; unbekannte Orte optional per **Nominatim/
  OpenStreetMap** (mit Cache + Rate-Limit) geocoden. Events ohne bestimmbare
  Koordinate: nicht hart verwerfen, sondern mit `entfernungKm: null` markieren.

### Zielgruppe / Alter
- Fokus **Kinder ca. 6–12 Jahre** (meine Tochter ist 10).
- Reine Kleinkind- (0–3) oder reine Erwachsenen-Events niedriger scoren.

### Zeitfenster (wichtig — eindeutig)
- Der Scan läuft **donnerstags**. „Relevantes Fenster" = **ab dem Scan-Tag bis
  einschließlich dem kommenden Sonntag** (also Do–So), plus optional die **darauf
  folgenden 7 Tage** als Ausblick (getrennt kennzeichnen: „dieses Wochenende" vs.
  „Ausblick nächste Woche").
- Mehrtägige Events (z. B. Ferienprogramm über 2 Wochen) einschließen, wenn sie in
  dieses Fenster **hineinragen**.
- Deutsche Datumsangaben (`14.03.`, `14. März`, `Sa 14.3.`, Zeitspannen) erkennen,
  nach **ISO (YYYY-MM-DD)** normalisieren. Vergangene Events aussortieren.

### Architektur (an GitHub Pages angepasst)
- **Statische Site**, veröffentlicht über **GitHub Pages** aus Ordner `/docs`;
  `index.html` liegt in `/docs`.
- **Kein Live-Scraping im Browser.** Ein **Python-Scraper** sammelt die Daten und
  schreibt `docs/data/events.json`; das Frontend lädt sie per `fetch()` mit
  **relativem Pfad** (kein führendes `/`, damit es im GitHub-Pages-Unterpfad läuft).
- **Frontend:** Vanilla HTML/CSS/JS, **keine Frameworks**, **mobile-first**
  (ich nutze es am Wochenende meist am Handy).
- **Sprache:** komplett Deutsch (UI, Code-Kommentare, Commit-Messages).

### Datenquellen — iCal/RSS bevorzugen (stabiler als HTML)
- **Bevorzugt maschinenlesbare Feeds nutzen:** Viele Städte/Portale bieten
  Veranstaltungen als **iCal (.ics)** oder **RSS** an — das ist deutlich robuster
  als HTML-Scraping. Prüfe pro Quelle zuerst, ob es einen Feed gibt.
- **HTML nur als Fallback.** Achtung: **Viele moderne Kalender sind
  JavaScript-gerendert** — reines `requests`+`BeautifulSoup` findet dort nichts.
  Erkenne solche Fälle, protokolliere sie und markiere die Quelle als „JS-Seite,
  Feed suchen" statt still 0 Treffer zu liefern. (Kein Headless-Browser — bleibt
  GitHub-Actions-tauglich.)
- **Kuratierte Quellen-Liste** (`sources.json`): pro Eintrag `name, ort, url,
  typ (ical|rss|html), aktiv, hinweis`. Klein & verlässlich starten (2–4 Quellen),
  iterativ erweitern.
- Nur **öffentlich zugängliche** Seiten; **robots.txt & Nutzungsbedingungen
  respektieren**; höfliche Request-Rate (Delay), sprechender User-Agent.

### Filter-Logik „nur Besonderes"
- **Positivliste** (Fest, Kinderfest, Ferienprogramm, Ferien, Mitmach, Aktionstag,
  Sonderausstellung, Markt, Umzug, Aufführung, Theater für Kinder, Workshop …).
- **Negativliste** (reguläre Öffnungszeiten, „täglich geöffnet", „jeden Montag",
  Ü18/Ab-18, Gottesdienst, Sitzung, Mitgliederversammlung …).
- **Relevanz-Score 0–1** aus: Positiv-Keywords, Kinder-/Familienbezug, Datum im
  Fenster, Ort im Umkreis. **Schwellwert** (z. B. ≥ 0.6) → auf die Seite; darunter →
  `review.json` (Prüfliste), **nicht** direkt sichtbar.
- **Kuratierte Einträge schützen:** Ein `manuellGeprueft: true`-Flag bewahrt von mir
  bestätigte Events vor Überschreiben/Filterung beim nächsten Lauf.
- **Deduplizieren** über `stadt + datumStart + normalisierter Titel`.

### Automatisierung (GitHub Actions, wöchentlich)
- Workflow `.github/workflows/weekly-scan.yml`: **Cron donnerstags früh**
  (z. B. `0 5 * * 4`) **plus** `workflow_dispatch` (manueller Start).
- `permissions: contents: write`; committet geänderte `docs/data/events.json`
  (und `review.json`) automatisch zurück.
- **Aktuelle Action-Versionen** verwenden (`actions/checkout@v4`+,
  `actions/setup-python@v5`+) — Node-Deprecation vermeiden.
- Scraper **GitHub-tauglich**: kurze Timeouts, ≤1 Retry, nicht erreichbare/tote
  Quellen sauber überspringen und protokollieren, Gesamtlaufzeit klar < 6 h.

### Datenmodell (ein Event in events.json)
`id, titel, beschreibungKurz, datumStart, datumEnd, uhrzeit, ort, adresse, stadt,
entfernungKm (Zahl|null), kategorie (Fest|Ferienprogramm|Workshop|Ausstellung|
Markt|Aufführung|Sonstiges), altersempfehlung, kostenHinweis, quelleName,
quelleUrl, relevanzScore, manuellGeprueft (bool), lastChecked (ISO-Zeitstempel)`.

### Frontend-Funktionen
- **Karten-Ansicht**, nach Datum sortiert; Abschnitte „**Dieses Wochenende**" und
  „**Ausblick**".
- Filter: **Kategorie**, **max. Entfernung** (Schieberegler/Auswahl), **Zeitraum**.
- Pro Event: Titel, Datum + Uhrzeit, Ort **+ Entfernung in km**, Kurzbeschreibung,
  Alters-Hinweis, Kostenhinweis, **Link zur Originalquelle** („Zur Quelle").
- Kopf: „Diese Woche besonders" + **Datenstand** (Datum des letzten Laufs).
- **Leerzustand definieren:** Wenn diese Woche nichts Besonderes gefunden wurde,
  eine freundliche Meldung zeigen („Diese Woche keine besonderen Events gefunden —
  schau nächste Woche wieder vorbei") statt leerer Seite.
- Mobile-first, hoher Kontrast, große Schrift.

### Qualität, Recht & Betrieb
- **Immer Quelle verlinken**; Footer-Hinweis „Angaben ohne Gewähr, bitte beim
  Veranstalter prüfen".
- Termine **nie erfinden** — nur, was aus einer Quelle stammt.
- Vergangene Events automatisch entfernen/archivieren.
- README mit Setup, Deployment (/docs), wöchentlichem Betrieb, **Quellenpflege**
  (wie füge ich eine Quelle in `sources.json` hinzu) und Erklärung der Filter.

### Liefere in dieser Reihenfolge
1. Kurze **Architektur-Übersicht** + Begründung der Datenquellen-Strategie (iCal/RSS zuerst).
2. **Projektstruktur** (Ordner/Dateien).
3. **`sources.json`** mit recherchierten Startquellen für die Region Sinsheim
   (jeweils mit Feed-Typ) + **`orte.json`** (Orte→Koordinaten).
4. **Python-Scraper** (`scripts/`) inkl. `requirements.txt` (Feeds + HTML-Fallback,
   Haversine-Entfernung, Scoring, Dedup, Zeitfenster-Filter).
5. **Frontend** (`docs/index.html`, `style.css`, `app.js`) + Beispiel-`events.json`,
   damit die Seite sofort etwas anzeigt.
6. **GitHub-Actions-Workflow** (`weekly-scan.yml`).
7. **README**.

Wenn Quellen JS-gerendert sind oder keine Feeds bieten, sag es offen und schlage
Alternativen vor, statt stumme Leertreffer zu liefern.

---

## Hinweise für mich (nicht Teil des Prompts)

- **Kritischer Erfolgsfaktor = Datenquellen.** Ob genug „besondere" Kinder-Events
  automatisch auffindbar sind, steht und fällt mit iCal/RSS-Feeds der Region.
  Klein starten, dann erweitern.
- **JS-gerenderte Kalender** waren im Lions-Projekt der größte Zeitfresser — der
  Prompt adressiert das jetzt explizit (Feeds bevorzugen, JS-Seiten erkennen).
- **`manuellGeprueft`-Flag + `review.json`**: bewährtes Muster aus dem Lions-Projekt,
  um kuratierte Treffer zu schützen und Fast-Treffer sichtbar zu machen.
- **Entfernung per Haversine + `orte.json`** ist bewusst simpel gehalten (kein
  bezahltes Geo-API), reicht für „Umkreis 30 km" locker.
- **Recht:** robots.txt/Nutzungsbedingungen je Quelle prüfen; nur öffentliche Daten;
  Quelle immer verlinken.
