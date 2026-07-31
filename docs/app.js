/* ============================================================
   Weekend-Events — Frontend-Logik (Vanilla JS)
   Laedt docs/data/events.json und stellt die Events dar.
   ============================================================ */
"use strict";

const state = {
  alle: [],
  filter: { kategorie: "alle", maxEntfernung: 30, zeitraum: "alle" },
};

const el = {
  kategorie: document.getElementById("kategorie"),
  entfernung: document.getElementById("entfernung"),
  entfernungWert: document.getElementById("entfernung-wert"),
  zeitraum: document.getElementById("zeitraum"),
  zaehler: document.getElementById("zaehler"),
  laden: document.getElementById("ladezustand"),
  fehler: document.getElementById("fehlerzustand"),
  fehlertext: document.getElementById("fehlertext"),
  leer: document.getElementById("leerzustand"),
  absWe: document.getElementById("abschnitt-wochenende"),
  absAus: document.getElementById("abschnitt-ausblick"),
  listeWe: document.getElementById("liste-wochenende"),
  listeAus: document.getElementById("liste-ausblick"),
  absArchiv: document.getElementById("abschnitt-archiv"),
  listeArchiv: document.getElementById("liste-archiv"),
  archivZaehler: document.getElementById("archiv-zaehler"),
  datenstand: document.getElementById("datenstand"),
};

const MONATE = ["Januar","Februar","März","April","Mai","Juni","Juli","August",
                "September","Oktober","November","Dezember"];
const WOCHENTAGE = ["Sonntag","Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag"];

function escape(t){ const d=document.createElement("div"); d.textContent=t==null?"":String(t); return d.innerHTML; }

function formatiereDatum(iso){
  if(!iso) return "Termin folgt";
  const d=new Date(iso+"T00:00:00");
  if(isNaN(d)) return iso;
  return `${WOCHENTAGE[d.getDay()]}, ${d.getDate()}. ${MONATE[d.getMonth()]} ${d.getFullYear()}`;
}

/** Heute als ISO-Tag "YYYY-MM-DD" (lokale Zeit). */
function heuteIso(){
  const d=new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
}

/** True, wenn ein Event vorbei ist (Enddatum bzw. Startdatum vor heute).
    So bleibt die Liste taeglich aktuell, auch wenn der Scan nur montags laeuft.
    Events ohne Datum gelten nie als vergangen. */
function istVergangen(e){
  const ende = e.datumEnd || e.datumStart;
  if(!ende) return false;
  return ende.slice(0,10) < heuteIso();
}

/** Datumsanzeige fuer die Karte. Mehrtaegige Events werden als Zeitraum
    gezeigt; laeuft so ein Event bereits (Start vergangen, Ende zukuenftig),
    steht "noch bis …" statt eines vergangen wirkenden Startdatums. */
function formatiereZeitraum(e){
  const start = e.datumStart;
  const ende = e.datumEnd;
  if(!start) return "Termin folgt";
  // Eintaegig (oder Ende == Start): normales Datum.
  if(!ende || ende.slice(0,10)===start.slice(0,10)) return formatiereDatum(start);
  const heute = heuteIso();
  // Mehrtaegig und laeuft schon: "noch bis <Ende>".
  if(start.slice(0,10) < heute) return `noch bis ${formatiereDatum(ende)}`;
  // Mehrtaegig, noch nicht begonnen: "<Start> – <Ende>".
  return `${formatiereDatum(start)} – ${formatiereDatum(ende)}`;
}

async function ladeDaten(){
  zeige("laden");
  try{
    const resp = await fetch("data/events.json", { cache:"no-cache" });
    if(!resp.ok) throw new Error(`Server-Antwort ${resp.status}`);
    const daten = await resp.json();
    if(!Array.isArray(daten)) throw new Error("Unerwartetes Datenformat.");
    state.alle = daten;
    fuelleKategorien(daten);
    setzeDatenstand(daten);
    rendern();
    ladeArchiv();  // unabhaengig, blockiert die Hauptansicht nicht
  }catch(f){
    console.error(f);
    el.fehlertext.textContent = f.message || "Unbekannter Fehler.";
    zeige("fehler");
  }
}

/** Laedt das Archiv (vergangene Events) nach. Fehlt die Datei, bleibt der
    Abschnitt einfach ausgeblendet — kein Fehler fuer den Nutzer. */
async function ladeArchiv(){
  try{
    const resp = await fetch("data/archiv.json", { cache:"no-cache" });
    if(!resp.ok) return;                          // 404 = noch kein Archiv
    const daten = await resp.json();
    if(!Array.isArray(daten) || daten.length===0) return;
    rendereArchiv(daten);
  }catch(f){
    console.warn("Archiv nicht verfuegbar:", f);  // still & leise
  }
}

/** Rendert den Archiv-Abschnitt: neueste vergangene Events zuerst. */
function rendereArchiv(daten){
  const evs = daten
    .filter(e=>e.datumStart)
    .sort((a,b)=>(b.datumStart||"").localeCompare(a.datumStart||""));
  if(evs.length===0) return;
  el.listeArchiv.innerHTML = evs.map(archivKarte).join("");
  el.archivZaehler.textContent = evs.length===1 ? "1 Event" : `${evs.length} Events`;
  el.absArchiv.hidden = false;
}

function fuelleKategorien(daten){
  const kats=[...new Set(daten.map(e=>e.kategorie).filter(Boolean))].sort();
  el.kategorie.length=1;
  for(const k of kats){
    const o=document.createElement("option"); o.value=k; o.textContent=k; el.kategorie.appendChild(o);
  }
}

function setzeDatenstand(daten){
  const stempel=daten.map(e=>e.lastChecked).filter(Boolean).sort().pop();
  if(stempel){ const d=new Date(stempel);
    el.datenstand.textContent = isNaN(d) ? "–"
      : `${String(d.getDate()).padStart(2,"0")}.${String(d.getMonth()+1).padStart(2,"0")}.${d.getFullYear()}`;
  } else el.datenstand.textContent="–";
}

function zeige(welcher){
  el.laden.hidden = welcher!=="laden";
  el.fehler.hidden = welcher!=="fehler";
  el.leer.hidden = welcher!=="leer";
  const listen = welcher==="liste";
  el.absWe.hidden = !listen || state._we===0;
  el.absAus.hidden = !listen || state._aus===0;
}

function gefiltert(){
  const f=state.filter;
  return state.alle.filter(e=>{
    if(istVergangen(e)) return false;  // vorbei -> nicht mehr anzeigen
    if(f.kategorie!=="alle" && e.kategorie!==f.kategorie) return false;
    if(e.entfernungKm!=null && e.entfernungKm>f.maxEntfernung) return false;
    if(f.zeitraum!=="alle" && (e.zeitraum||"wochenende")!==f.zeitraum) return false;
    return true;
  });
}

function rendern(){
  const evs=gefiltert().sort((a,b)=>(a.datumStart||"9999").localeCompare(b.datumStart||"9999"));
  const we=evs.filter(e=>(e.zeitraum||"wochenende")==="wochenende");
  const aus=evs.filter(e=>e.zeitraum==="ausblick");
  state._we=we.length; state._aus=aus.length;

  if(evs.length===0){ zeige("leer"); el.zaehler.textContent=""; return; }

  el.zaehler.textContent = evs.length===1 ? "1 Event gefunden" : `${evs.length} Events gefunden`;
  el.listeWe.innerHTML = we.map(karte).join("");
  el.listeAus.innerHTML = aus.map(karte).join("");
  zeige("liste");
}

function karte(e){
  const ausblick = e.zeitraum==="ausblick";
  const entf = e.entfernungKm!=null ? `<span class="badge badge-entf">${e.entfernungKm} km</span>` : "";
  const geprueft = e.manuellGeprueft ? `<span class="geprueft-badge">geprüft</span>` : "";
  const uhrzeit = e.uhrzeit ? ` · ${escape(e.uhrzeit)} Uhr` : "";
  const alter = e.altersempfehlung ? ` · ${escape(e.altersempfehlung)}` : "";
  const kosten = e.kostenHinweis ? ` · ${escape(e.kostenHinweis)}` : "";
  const kalenderBtn = e.datumStart
    ? `<button type="button" class="kalender-btn" data-id="${escape(e.id)}">📅 Zum Kalender</button>`
    : "";
  // Indoor/Outdoor-Badge
  const ort2 = e.drinnenDraussen==="draussen"
    ? `<span class="badge badge-ort">🌳 Draußen</span>`
    : (e.drinnenDraussen==="drinnen" ? `<span class="badge badge-ort">🏠 Drinnen</span>` : "");
  // Wetter-Zeile (nur wenn Vorhersage vorhanden)
  const w = e.wetter;
  const wetter = w
    ? `<p class="wetter">${w.emoji} ${escape(w.text||"")} · ${Math.round(w.tempMax)}°C</p>`
    : "";
  return `
    <li class="event ${ausblick?"ausblick":""}">
      <div class="kopfzeile">
        <span class="badge badge-kat">${escape(e.kategorie||"Sonstiges")}</span>
        ${ort2}${entf}${geprueft}
      </div>
      <p class="datum">${escape(formatiereZeitraum(e))}${uhrzeit}</p>
      <h3>${escape(e.titel)}</h3>
      <p class="ort">${escape(e.stadt||e.ort||"")}</p>
      ${wetter}
      ${e.beschreibungKurz?`<p class="besch">${escape(e.beschreibungKurz)}</p>`:""}
      <p class="meta">${escape((e.kategorie||""))}${alter}${kosten}</p>
      <div class="fuss">
        <span class="quelle-name">Quelle: ${escape(e.quelleName||"unbekannt")}</span>
        <div class="aktionen">
          ${kalenderBtn}
          <a class="quelle-link" href="${escape(e.quelleUrl||"#")}" target="_blank" rel="noopener noreferrer">Zur Quelle &rarr;</a>
        </div>
      </div>
    </li>`;
}

/** Kompakte Karte fuers Archiv — ohne Wetter/Kalender, mit Link zur Quelle. */
function archivKarte(e){
  const entf = e.entfernungKm!=null ? `<span class="badge badge-entf">${e.entfernungKm} km</span>` : "";
  const quelle = e.quelleUrl
    ? `<a class="archiv-link" href="${escape(e.quelleUrl)}" target="_blank" rel="noopener noreferrer">Quelle &rarr;</a>`
    : "";
  return `
    <li class="event archiv-event">
      <div class="kopfzeile">
        <span class="badge badge-kat">${escape(e.kategorie||"Sonstiges")}</span>
        ${entf}
      </div>
      <p class="datum">${escape(formatiereDatum(e.datumStart))}</p>
      <h3>${escape(e.titel)}</h3>
      <p class="ort">${escape(e.stadt||e.ort||"")}</p>
      ${quelle}
    </li>`;
}

/** ISO "2026-08-01" -> "20260801" fuer ICS-Ganztagstermine. */
function icsDatum(iso){ return iso.replace(/-/g,""); }

/** Escaped Sonderzeichen fuer ICS-Textfelder (RFC 5545). */
function icsEscape(text){
  return String(text==null?"":text)
    .replace(/\\/g,"\\\\").replace(/;/g,"\\;").replace(/,/g,"\\,")
    .replace(/\r?\n/g,"\\n");
}

/** Baut einen ganztaegigen VEVENT-Kalendereintrag als .ics-Text. */
function baueICS(e){
  const start = icsDatum(e.datumStart);
  // DTEND ist bei Ganztagsterminen exklusiv -> Tag nach datumEnd.
  const endeBasis = e.datumEnd || e.datumStart;
  const ed = new Date(endeBasis+"T00:00:00");
  ed.setDate(ed.getDate()+1);
  const ende = `${ed.getFullYear()}${String(ed.getMonth()+1).padStart(2,"0")}${String(ed.getDate()).padStart(2,"0")}`;
  const ort = [e.veranstaltungsort, e.adresse, e.stadt, e.ort].filter(Boolean).join(", ");
  const zeit = e.uhrzeit ? `Beginn: ${e.uhrzeit} Uhr` : "";
  const besch = [e.beschreibungKurz, zeit, e.quelleUrl].filter(Boolean).join("\n\n");
  return [
    "BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Weekend-Events//DE","CALSCALE:GREGORIAN",
    "BEGIN:VEVENT",
    `UID:${e.id}@weekend-events`,
    `DTSTART;VALUE=DATE:${start}`,
    `DTEND;VALUE=DATE:${ende}`,
    `SUMMARY:${icsEscape(e.titel)}`,
    `LOCATION:${icsEscape(ort)}`,
    `DESCRIPTION:${icsEscape(besch)}`,
    "END:VEVENT","END:VCALENDAR",
  ].join("\r\n");
}

/** Bietet die .ics-Datei eines Events als Download an. */
function ladeKalenderHerunter(id){
  const e = state.alle.find(x=>x.id===id);
  if(!e || !e.datumStart) return;
  const blob = new Blob([baueICS(e)], {type:"text/calendar;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `event-${e.datumStart}.ics`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function verdrahte(){
  el.kategorie.addEventListener("change",ev=>{state.filter.kategorie=ev.target.value;rendern();});
  el.zeitraum.addEventListener("change",ev=>{state.filter.zeitraum=ev.target.value;rendern();});
  el.entfernung.addEventListener("input",ev=>{
    state.filter.maxEntfernung=Number(ev.target.value);
    el.entfernungWert.textContent=ev.target.value;
    rendern();
  });
  // Kalender-Buttons (per Delegation, da Karten dynamisch erzeugt werden).
  document.addEventListener("click",ev=>{
    const btn = ev.target.closest(".kalender-btn");
    if(btn) ladeKalenderHerunter(btn.dataset.id);
  });
}

document.addEventListener("DOMContentLoaded",()=>{ verdrahte(); ladeDaten(); });
