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
  }catch(f){
    console.error(f);
    el.fehlertext.textContent = f.message || "Unbekannter Fehler.";
    zeige("fehler");
  }
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
  return `
    <li class="event ${ausblick?"ausblick":""}">
      <div class="kopfzeile">
        <span class="badge badge-kat">${escape(e.kategorie||"Sonstiges")}</span>
        ${entf}${geprueft}
      </div>
      <p class="datum">${escape(formatiereDatum(e.datumStart))}${uhrzeit}</p>
      <h3>${escape(e.titel)}</h3>
      <p class="ort">${escape(e.stadt||e.ort||"")}</p>
      ${e.beschreibungKurz?`<p class="besch">${escape(e.beschreibungKurz)}</p>`:""}
      <p class="meta">${escape((e.kategorie||""))}${alter}${kosten}</p>
      <div class="fuss">
        <span class="quelle-name">Quelle: ${escape(e.quelleName||"unbekannt")}</span>
        <a class="quelle-link" href="${escape(e.quelleUrl||"#")}" target="_blank" rel="noopener noreferrer">Zur Quelle &rarr;</a>
      </div>
    </li>`;
}

function verdrahte(){
  el.kategorie.addEventListener("change",ev=>{state.filter.kategorie=ev.target.value;rendern();});
  el.zeitraum.addEventListener("change",ev=>{state.filter.zeitraum=ev.target.value;rendern();});
  el.entfernung.addEventListener("input",ev=>{
    state.filter.maxEntfernung=Number(ev.target.value);
    el.entfernungWert.textContent=ev.target.value;
    rendern();
  });
}

document.addEventListener("DOMContentLoaded",()=>{ verdrahte(); ladeDaten(); });
