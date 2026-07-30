#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_events.py — Weekend-Events Scraper

Sammelt besondere Kinder-Events in der Region Sinsheim (~30 km) und schreibt:
  docs/data/events.json   -> sichere Treffer (Score >= SCHWELLE), fuer die Seite
  docs/data/review.json   -> unsichere Treffer zur manuellen Pruefung

Design (bewusst GitHub-Actions-tauglich, kein Headless-Browser):
  1. Quellen aus sources.json (nur aktiv=true).
  2. Pro Quelle: iCal/RSS bevorzugt, sonst HTML-Fallback. JS-gerenderte Seiten
     werden erkannt und protokolliert (statt still 0 Treffer).
  3. Deutsche Datumsangaben -> ISO; Filter aufs Zeitfenster (Do..So + Ausblick).
  4. Keyword-Scoring (Positiv-/Negativliste, Kinder-/Familienbezug).
  5. Entfernung via Haversine gegen orte.json.
  6. Dedup (stadt|datum|titel); manuellGeprueft:true bleibt erhalten.
"""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("FEHLER: Bitte 'pip install -r requirements.txt' ausfuehren.")
    sys.exit(1)

# icalendar ist optional — nur fuer iCal-Quellen noetig.
try:
    from icalendar import Calendar
    HAT_ICAL = True
except ImportError:
    HAT_ICAL = False

# ----------------------------------------------------------------------
# Konfiguration
# ----------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
SOURCES_FILE = SCRIPT_DIR / "sources.json"
ORTE_FILE = SCRIPT_DIR / "orte.json"
DOCS_DATA = PROJECT_DIR / "docs" / "data"
EVENTS_FILE = DOCS_DATA / "events.json"
REVIEW_FILE = DOCS_DATA / "review.json"

USER_AGENT = ("WeekendEventsBot/1.0 (privates Familienprojekt; woechentlicher "
              "Scan; Kontakt: bitte-nicht-blockieren@example.org)")
REQUEST_TIMEOUT = 12
POLITE_DELAY = 1.0
MAX_RETRIES = 1

SCHWELLE = 0.5            # ab hier "sicher" -> events.json (bewusst inklusiv:
                          # auch allgemeine Familien-Events kommen durch)
ANZAHL_WOCHENENDEN = 2   # wie viele kommende Wochenenden abdecken (inkl. dem naechsten)

# Positiv-/Negativ-Keywords (kleingeschrieben, umlautnormalisiert)
POSITIV = [
    "fest", "kinderfest", "familienfest", "ferienprogramm", "ferien",
    "mitmach", "aktionstag", "sonderausstellung", "markt", "umzug",
    "auffuehrung", "auffuehrung", "theater", "workshop", "bastel",
    "kinder", "familie", "familien", "puppentheater", "zirkus",
    "flohmarkt", "kindertheater", "erlebnis", "entdeck", "mitmachen",
]
NEGATIV = [
    "oeffnungszeit", "taeglich geoeffnet", "jeden montag", "jeden dienstag",
    "ab 18", "ue18", "gottesdienst", "sitzung", "mitgliederversammlung",
    "vortrag fuer erwachsene", "senioren", "stammtisch", "vernissage",
    "repair cafe", "repair-cafe", "jugendparty", "party", "disco", "clubbing",
    "weinprobe", "weinfest", "oktoberfest", "generalversammlung", "sprechstunde",
    "blutspende", "flohmarkt fuer erwachsene", "kleidermarkt", "sommer-lounge",
    "liegestuehle", "shopping", "after work",
    # Generische Tourismus-/Erwachsenen-Formate (kein Kinder-Event):
    "altstadtrundgang", "stadtrundfahrt", "stadtfuehrung", "schlossfuehrung",
    "fuehrung", "rundgang", "rundfahrt", "aufstellung", "meditation",
    "juedisches leben", "universitaet", "spaziergang", "wanderung fuer",
    # Erwachsenen-Formate (aus Testlauf ergaenzt):
    "wein", "weinnacht", "tango", "consciustouch", "conscioustouch",
    "bewusster beruehrung", "bewusste beruehrung", "mantra", "yoga",
    "arzneien", "traditionellen chinesischen", "einsteiger", "kultursommer",
    "big band", "weinnacht im schlosshof",
]
KINDER_BEZUG = ["kind", "kinder", "familie", "familien", "kids", "schueler",
                "grundschul", "bastel", "puppen", "maerchen"]

# Kategorie-Erkennung
KATEGORIEN = [
    ("Ferienprogramm", ["ferienprogramm", "ferien"]),
    ("Fest", ["fest", "kinderfest", "familienfest", "umzug"]),
    ("Markt", ["markt", "flohmarkt", "basar"]),
    ("Aufführung", ["theater", "auffuehrung", "auffuehrung", "konzert", "zirkus", "puppen"]),
    ("Workshop", ["workshop", "bastel", "mitmach", "kurs"]),
    ("Ausstellung", ["ausstellung", "sonderausstellung", "museum"]),
]

MONATE = {
    "januar": 1, "jan": 1, "februar": 2, "feb": 2, "maerz": 3, "märz": 3,
    "mrz": 3, "april": 4, "apr": 4, "mai": 5, "juni": 6, "jun": 6,
    "juli": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sep": 9,
    "sept": 9, "oktober": 10, "okt": 10, "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}


def norm(text):
    """Kleinbuchstaben + Umlaute/Akzente vereinheitlichen."""
    t = (text or "").lower()
    t = (t.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
          .replace("ß", "ss"))
    # Akzente entfernen (café -> cafe), damit Keywords zuverlaessig matchen.
    t = (t.replace("é", "e").replace("è", "e").replace("ê", "e")
          .replace("á", "a").replace("à", "a").replace("â", "a"))
    return t


# ----------------------------------------------------------------------
# Zeitfenster
# ----------------------------------------------------------------------
def zeitfenster(heute=None):
    """(start, wochenende_ende, ausblick_ende) berechnen.
    start = heute; wochenende_ende = kommender Sonntag;
    ausblick_ende = Sonntag des ANZAHL_WOCHENENDEN-ten Wochenendes."""
    heute = heute or date.today()
    # Tage bis Sonntag (Mo=0 .. So=6)
    bis_so = 6 - heute.weekday()
    if bis_so < 0:
        bis_so += 7
    wochenende_ende = heute + timedelta(days=bis_so)
    # Ende = Sonntag des N-ten Wochenendes (jedes weitere Wochenende +7 Tage).
    ausblick_ende = wochenende_ende + timedelta(days=7 * (ANZAHL_WOCHENENDEN - 1))
    return heute, wochenende_ende, ausblick_ende


# ----------------------------------------------------------------------
# Entfernung (Haversine) + Orts-Tabelle
# ----------------------------------------------------------------------
def lade_orte():
    daten = json.loads(ORTE_FILE.read_text(encoding="utf-8"))
    mp = daten["_meta"]["mittelpunkt"]
    tabelle = {}
    for o in daten["orte"]:
        tabelle[norm(o["ort"])] = o
    return mp, tabelle


def haversine(lat1, lon1, lat2, lon2):
    import math
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(R * 2 * math.asin(math.sqrt(a)), 1)


def entfernung_fuer_ort(ortstext, mp, orte_tab):
    """Sucht bekannten Ort in der Tabelle -> vorberechnete Entfernung.
    Rueckgabe: (stadt, entfernungKm|None)."""
    n = norm(ortstext)
    for schluessel, o in orte_tab.items():
        if schluessel and schluessel in n:
            return o["ort"], o["entfernungKm"]
    return ortstext.strip() or "", None


# ----------------------------------------------------------------------
# Datum-Parsing (deutsch -> ISO)
# ----------------------------------------------------------------------
RE_NUM = re.compile(r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{2,4})?\b")
RE_TXT = re.compile(r"\b(\d{1,2})\.?\s+([A-Za-zäöüÄÖÜ]+)\s+(\d{4})\b")
# Bevorzugt: explizit als "Datum ..." ausgewiesen (z. B. "Datum 30.07.2026").
RE_LABEL = re.compile(r"Datum\s*:?\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", re.I)


def parse_datum(text, jahr_fallback=None):
    """Erstes plausibles Datum -> ISO (YYYY-MM-DD) oder None.
    Ein explizit mit 'Datum ...' ausgewiesenes Datum hat Vorrang."""
    jahr_fallback = jahr_fallback or date.today().year
    m = RE_LABEL.search(text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            pass
    m = RE_TXT.search(text)
    if m:
        tag = int(m.group(1)); monat = MONATE.get(norm(m.group(2))); jahr = int(m.group(3))
        if monat:
            try:
                return date(jahr, monat, tag).isoformat()
            except ValueError:
                pass
    m = RE_NUM.search(text)
    if m:
        tag = int(m.group(1)); monat = int(m.group(2))
        jahr = int(m.group(3)) if m.group(3) else jahr_fallback
        if jahr < 100:
            jahr += 2000
        try:
            return date(jahr, monat, tag).isoformat()
        except ValueError:
            pass
    return None


# Zeitspannen erkennen (Start + Ende).
#  "30.07.2026 bis 28.08.2026" / "30.07. - 28.08.2026"
RE_SPAN_NUM = re.compile(
    r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?\s*(?:bis|-|–|—|\bbis\b)\s*"
    r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
#  "28. - 30. Juli 2026" / "28.–30. Juli 2026" (gemeinsamer Monat/Jahr)
RE_SPAN_TXT = re.compile(
    r"(\d{1,2})\.?\s*(?:bis|-|–|—)\s*(\d{1,2})\.?\s+([A-Za-zäöüÄÖÜ]+)\s+(\d{4})")


def parse_zeitraum(text, jahr_fallback=None):
    """Liefert (startISO, endeISO). Ende == Start, wenn keine Spanne erkennbar.
    Erkennt numerische Spannen und Textmonat-Spannen; sonst Einzeldatum."""
    jahr_fallback = jahr_fallback or date.today().year

    # Label-Datum ("Datum: 30.07.2026 bis 28.08.2026") zuerst — auch mit Spanne.
    label = RE_LABEL.search(text)
    if label:
        rest = text[label.start():label.start() + 60]
        m2 = re.search(r"(?:bis|-|–|—)\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", rest)
        try:
            start = date(int(label.group(3)), int(label.group(2)), int(label.group(1))).isoformat()
        except ValueError:
            start = None
        if start and m2:
            try:
                ende = date(int(m2.group(3)), int(m2.group(2)), int(m2.group(1))).isoformat()
                return start, ende
            except ValueError:
                return start, start
        if start:
            return start, start

    m = RE_SPAN_NUM.search(text)
    if m:
        j2 = int(m.group(6))
        j1 = int(m.group(3)) if m.group(3) else j2
        try:
            start = date(j1, int(m.group(2)), int(m.group(1))).isoformat()
            ende = date(j2, int(m.group(5)), int(m.group(4))).isoformat()
            return start, ende
        except ValueError:
            pass

    m = RE_SPAN_TXT.search(text)
    if m:
        monat = MONATE.get(norm(m.group(3))); jahr = int(m.group(4))
        if monat:
            try:
                start = date(jahr, monat, int(m.group(1))).isoformat()
                ende = date(jahr, monat, int(m.group(2))).isoformat()
                return start, ende
            except ValueError:
                pass

    einzel = parse_datum(text, jahr_fallback)
    return einzel, einzel


# ----------------------------------------------------------------------
# Scoring & Klassifikation
# ----------------------------------------------------------------------
def klassifiziere(text):
    n = norm(text)
    for kat, keys in KATEGORIEN:
        if any(k in n for k in keys):
            return kat
    return "Sonstiges"


def score(text, iso_datum, entfernung, mp_umkreis):
    """Relevanz-Score 0..1.

    Ausgewogen: Klarer Kinder-/Familienbezug gibt einen starken Bonus, ist aber
    NICHT zwingend — auch allgemeine Familien-Events (Feste, Maerkte, Auffuehrungen)
    koennen die Schwelle erreichen, wenn genug Positiv-Signale vorliegen. Die
    Negativliste haelt eindeutig Erwachsenes (Weinfest, Stadtfuehrung ...) fern.
    """
    n = norm(text)
    pos = sum(1 for k in POSITIV if k in n)
    neg = sum(1 for k in NEGATIV if k in n)
    hat_kinderbezug = any(k in n for k in KINDER_BEZUG)

    s = 0.20                           # Grundwert: Event hat POSITIV-Keyword getroffen
    s += min(pos, 3) * 0.15            # bis 0.45 aus Positiv-Keywords
    if hat_kinderbezug:
        s += 0.25                      # Kinder-/Familienbezug: Bonus (nicht mehr zwingend)
    if iso_datum:
        s += 0.10                      # Datum erkannt
    if entfernung is not None and entfernung <= mp_umkreis:
        s += 0.08                      # im Umkreis
    s -= neg * 0.40                    # Negativ-Keywords ziehen stark ab (Erwachsenes raus)

    return round(max(0.0, min(1.0, s)), 3)


# ----------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------
def hole(session, url):
    for versuch in range(MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                if not r.encoding or r.encoding.lower() == "iso-8859-1":
                    r.encoding = r.apparent_encoding
                return r.text, r.status_code, None
            return None, r.status_code, f"HTTP {r.status_code}"
        except requests.exceptions.RequestException as exc:
            letzter = f"{type(exc).__name__}"
            if versuch < MAX_RETRIES:
                time.sleep(POLITE_DELAY)
    return None, None, letzter


def ist_js_seite(html):
    """Heuristik: sehr wenig sichtbarer Text + App-Root -> vermutlich JS-gerendert."""
    if not html:
        return False
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    sichtbar = soup.get_text(" ", strip=True)
    hat_approot = bool(re.search(r'id="(app|root|__next)"', html))
    return len(sichtbar) < 400 or hat_approot


# ----------------------------------------------------------------------
# Indoor/Outdoor-Erkennung + Wetter (Open-Meteo, kein API-Key)
# ----------------------------------------------------------------------
DRAUSSEN_KEYS = ["park", "freibad", "see", "wiese", "platz", "markt", "strasse",
                 "innenstadt", "garten", "hof", "wald", "open air", "openair",
                 "spielplatz", "gelaende", "festplatz", "fussgaengerzone", "flohmarkt"]
DRINNEN_KEYS = ["museum", "halle", "theater", "kino", "bibliothek", "buecherei",
                "saal", "zentrum", "haus", "schule", "kirche", "arena", "indoor",
                "werkstatt", "atelier"]


def drinnen_draussen(text):
    """Grobe Einschaetzung: 'drinnen' | 'draussen' | '' (unbekannt)."""
    n = norm(text)
    d_aus = sum(1 for k in DRAUSSEN_KEYS if k in n)
    d_in = sum(1 for k in DRINNEN_KEYS if k in n)
    if d_aus > d_in:
        return "draussen"
    if d_in > d_aus:
        return "drinnen"
    return ""


# WMO-Wettercode -> (Kurztext, Emoji)
WMO = {
    0: ("klar", "☀️"), 1: ("überwiegend klar", "🌤️"), 2: ("wechselnd bewölkt", "⛅"),
    3: ("bewölkt", "☁️"), 45: ("Nebel", "🌫️"), 48: ("Nebel", "🌫️"),
    51: ("Niesel", "🌦️"), 53: ("Niesel", "🌦️"), 55: ("Niesel", "🌦️"),
    61: ("Regen", "🌧️"), 63: ("Regen", "🌧️"), 65: ("starker Regen", "🌧️"),
    71: ("Schnee", "🌨️"), 73: ("Schnee", "🌨️"), 75: ("starker Schnee", "🌨️"),
    80: ("Schauer", "🌦️"), 81: ("Schauer", "🌦️"), 82: ("starke Schauer", "⛈️"),
    95: ("Gewitter", "⛈️"), 96: ("Gewitter", "⛈️"), 99: ("Gewitter", "⛈️"),
}

# Niederschlags-Codes (Niesel/Regen/Schauer/Gewitter) — an Regenwahrscheinlichkeit pruefen.
NIEDERSCHLAG_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}


def plausibilisiere_wetter(code, txt, emoji, temp, regen):
    """Macht Wetterlage und Regenwahrscheinlichkeit widerspruchsfrei.

    - Niederschlags-Code (z. B. 'Schauer') bei niedriger Regenwahrscheinlichkeit
      (< 30 %) -> zu 'wechselnd bewoelkt' abschwaechen (kein 'Schauer bei 10 %').
    - Nebel-Code bei warmer Temperatur (>= 20 °C) -> 'heiter/bewoelkt'
      (Morgennebel loest sich auf; passt nicht zu 31 °C Tagesmax).
    """
    if code in NIEDERSCHLAG_CODES and (regen is None or regen < 30):
        return "wechselnd bewölkt", "⛅"
    if code in (45, 48) and temp is not None and temp >= 20:
        return "heiter bis wolkig", "🌤️"
    return txt, emoji


def hole_wetter(session, mp, start, ende, log):
    """Holt die Tagesvorhersage (Open-Meteo) fuer den Zeitraum. Dict datum->wetter."""
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={mp['lat']}"
           f"&longitude={mp['lon']}&daily=weathercode,temperature_2m_max,"
           f"precipitation_probability_max&timezone=Europe%2FBerlin&forecast_days=16")
    text, status, err = hole(session, url)
    if err or not text:
        log.append(f"[Wetter] Open-Meteo nicht erreichbar: {err}")
        return {}
    try:
        d = json.loads(text).get("daily", {})
        tab = {}
        for i, tag in enumerate(d.get("time", [])):
            code = d["weathercode"][i]
            temp = d["temperature_2m_max"][i]
            regen = d["precipitation_probability_max"][i]
            txt, emoji = WMO.get(code, ("", "🌡️"))
            txt, emoji = plausibilisiere_wetter(code, txt, emoji, temp, regen)
            tab[tag] = {
                "code": code, "text": txt, "emoji": emoji,
                "tempMax": temp,
                "regenProzent": regen,
                # Regen nur anzeigen, wenn er wirklich relevant ist (>= 20 %).
                "regenZeigen": regen is not None and regen >= 20,
            }
        return tab
    except Exception as exc:
        log.append(f"[Wetter] Parsefehler: {exc}")
        return {}


# ----------------------------------------------------------------------
# Quellen verarbeiten
# ----------------------------------------------------------------------
def make_event(titel, beschreibung, iso_datum, ort, quelle, mp, orte_tab, umkreis, iso_ende=None):
    stadt, entf = entfernung_fuer_ort(ort or quelle.get("ort", ""), mp, orte_tab)
    volltext = f"{titel} {beschreibung}"
    sc = score(volltext, iso_datum, entf, umkreis)
    kat = klassifiziere(volltext)
    eid = hashlib.sha1(norm(f"{stadt}|{iso_datum}|{titel}").encode()).hexdigest()[:12]
    return {
        "id": eid,
        "titel": titel.strip()[:160],
        "beschreibungKurz": re.sub(r"\s+", " ", beschreibung).strip()[:240],
        "datumStart": iso_datum or "",
        "datumEnd": iso_ende or iso_datum or "",
        "uhrzeit": "",
        "ort": (ort or "").strip(),
        "adresse": "",
        "stadt": stadt,
        "entfernungKm": entf,
        "kategorie": kat,
        "drinnenDraussen": drinnen_draussen(volltext),
        "wetter": None,
        "altersempfehlung": "",
        "kostenHinweis": "",
        "quelleName": quelle.get("name", ""),
        "quelleUrl": quelle.get("url", ""),
        "relevanzScore": sc,
        "manuellGeprueft": False,
        "lastChecked": datetime.now().isoformat(timespec="seconds"),
    }


def verarbeite_ical(session, quelle, mp, orte_tab, umkreis, log):
    if not HAT_ICAL:
        log.append(f"[{quelle['name']}] icalendar nicht installiert - uebersprungen")
        return []
    text, status, err = hole(session, quelle["url"])
    if err or not text:
        log.append(f"[{quelle['name']}] iCal-Fehler: {err}")
        return []
    events = []
    try:
        cal = Calendar.from_ical(text)
        for comp in cal.walk("VEVENT"):
            titel = str(comp.get("summary", ""))
            besch = str(comp.get("description", ""))
            ort = str(comp.get("location", ""))
            dt = comp.get("dtstart")
            iso = dt.dt.isoformat()[:10] if dt else None
            dte = comp.get("dtend")
            iso_ende = dte.dt.isoformat()[:10] if dte else iso
            events.append(make_event(titel, besch, iso, ort, quelle, mp, orte_tab,
                                     umkreis, iso_ende=iso_ende))
    except Exception as exc:
        log.append(f"[{quelle['name']}] iCal-Parsefehler: {exc}")
    return events


def extrahiere_titel(el, blocktext):
    """Bestmoeglichen Titel aus einem HTML-Block ziehen.
    Bevorzugt Ueberschrift/Link; entfernt typische Kalender-Praefixe/Rauschen."""
    kandidat = ""
    titel_el = el.find(["h1", "h2", "h3", "h4"])
    if titel_el:
        kandidat = titel_el.get_text(" ", strip=True)
    if not kandidat:
        a = el.find("a")
        if a and len(a.get_text(strip=True)) >= 6:
            kandidat = a.get_text(" ", strip=True)
    if not kandidat:
        kandidat = blocktext

    # Fuehrende Datums-/Rausch-Praefixe entfernen: "30 Jul ", "Details einblenden ".
    kandidat = re.sub(r"^\s*\d{1,2}\s*[A-Za-zäöü]{3,}\s+", "", kandidat)
    kandidat = re.sub(r"^\s*Details einblenden\s*", "", kandidat, flags=re.I)
    kandidat = re.sub(r"^\s*Termin\s*", "", kandidat, flags=re.I)
    # Abschneiden vor Metadaten-Woertern, falls Titel = ganzer Block.
    kandidat = re.split(r"\s+(?:Datum|Uhrzeit|Veranstalter|icon\.)\b", kandidat)[0]
    kandidat = re.sub(r"\s+", " ", kandidat).strip(" -–—·|")
    return kandidat[:120] if kandidat else "(ohne Titel)"


def verarbeite_html(session, quelle, mp, orte_tab, umkreis, log):
    text, status, err = hole(session, quelle["url"])
    if err or not text:
        log.append(f"[{quelle['name']}] HTML-Fehler: {err}")
        return []
    if ist_js_seite(text):
        log.append(f"[{quelle['name']}] Vermutlich JS-gerendert - Feed suchen! "
                    f"(kein Headless-Browser)")
        return []
    soup = BeautifulSoup(text, "html.parser")
    events = []
    # Heuristik: Blöcke mit Datum + Keyword einsammeln.
    for el in soup.find_all(["article", "li", "div", "tr"]):
        blocktext = el.get_text(" ", strip=True)
        if not blocktext or len(blocktext) < 15:
            continue
        n = norm(blocktext)
        if not any(k in n for k in POSITIV):
            continue
        iso, iso_ende = parse_zeitraum(blocktext)
        if not iso:
            continue
        titel = extrahiere_titel(el, blocktext)
        events.append(make_event(titel, blocktext, iso, "", quelle, mp, orte_tab,
                                  umkreis, iso_ende=iso_ende))
    return events


# ----------------------------------------------------------------------
# Merge / Filter / Schreiben
# ----------------------------------------------------------------------
def im_fenster(iso, start, ausblick_ende):
    if not iso:
        return False
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return False
    return start <= d <= ausblick_ende


def dedup(events):
    seen, out = set(), []
    for e in sorted(events, key=lambda x: x.get("relevanzScore", 0), reverse=True):
        key = norm(f"{e['stadt']}|{e['datumStart']}|{e['titel']}")
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def lade_bestehende_geprueft(pfad):
    """Manuell geprüfte Events aus bestehender events.json bewahren."""
    if not pfad.exists():
        return []
    try:
        return [e for e in json.loads(pfad.read_text(encoding="utf-8"))
                if e.get("manuellGeprueft")]
    except (json.JSONDecodeError, OSError):
        return []


def main():
    ap = argparse.ArgumentParser(description="Weekend-Events Scraper")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    umkreis = sources["_meta"].get("umkreisKm", 30)
    aktive = [q for q in sources["quellen"] if q.get("aktiv")]
    mp, orte_tab = lade_orte()

    start, we_ende, ausblick_ende = zeitfenster()
    print(f"Zeitfenster: {start} .. {we_ende} (Wochenende) .. {ausblick_ende} (Ausblick)")
    print(f"Aktive Quellen: {len(aktive)}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"})

    alle, log = [], []
    for q in aktive:
        typ = q.get("typ", "html")
        print(f"-> {q['name']} ({typ})")
        if typ == "ical":
            ev = verarbeite_ical(session, q, mp, orte_tab, umkreis, log)
        elif typ == "rss":
            ev = verarbeite_html(session, q, mp, orte_tab, umkreis, log)  # RSS ~ XML, gleiche Heuristik
        else:
            ev = verarbeite_html(session, q, mp, orte_tab, umkreis, log)
        print(f"   {len(ev)} Rohtreffer")
        alle.extend(ev)
        time.sleep(POLITE_DELAY)

    # Zeitfenster-Filter + Umkreis (Orte ausserhalb 30km raus, wenn Entfernung bekannt).
    gefiltert = []
    for e in alle:
        if not im_fenster(e["datumStart"], start, ausblick_ende):
            continue
        if e["entfernungKm"] is not None and e["entfernungKm"] > umkreis:
            continue
        # Ausblick-Kennzeichnung
        d = date.fromisoformat(e["datumStart"])
        e["zeitraum"] = "wochenende" if d <= we_ende else "ausblick"
        gefiltert.append(e)

    gefiltert = dedup(gefiltert)

    sicher = [e for e in gefiltert if e["relevanzScore"] >= SCHWELLE]
    review = [e for e in gefiltert if e["relevanzScore"] < SCHWELLE]

    # Manuell geprüfte Bestandsevents bewahren (nur wenn noch im Fenster).
    geprueft = [e for e in lade_bestehende_geprueft(EVENTS_FILE)
                if im_fenster(e.get("datumStart"), start, ausblick_ende)]
    geprueft_ids = {e["id"] for e in geprueft}
    sicher = geprueft + [e for e in sicher if e["id"] not in geprueft_ids]
    sicher.sort(key=lambda e: e.get("datumStart") or "9999")

    # Wetter fuer die sichtbaren Events anreichern (ein API-Call, Open-Meteo).
    wetter_tab = hole_wetter(session, mp, start, ausblick_ende, log)
    if wetter_tab:
        for e in sicher:
            e["wetter"] = wetter_tab.get(e.get("datumStart"))

    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    EVENTS_FILE.write_text(json.dumps(sicher, ensure_ascii=False, indent=2), encoding="utf-8")
    REVIEW_FILE.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 50)
    print(f"FERTIG: {len(sicher)} Events (Seite), {len(review)} zur Pruefung")
    if log:
        print("\nHinweise/Fehler:")
        for z in log:
            print(" -", z)


if __name__ == "__main__":
    main()
