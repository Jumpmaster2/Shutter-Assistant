// Shutter Assistant dashboard card: the windows with status, position, next action
// and buttons, plus a small sun compass. For every user (the settings stay in the
// admin panel). Plain web component without build step; the structure comes from
// the WebSocket command shutter_assistant/card, the live values from the states.
//
//   type: custom:shutter-assistant-card
//   title: Rollos          # optional
//   windows: [Wohnzimmer]  # optional: names or ids, default all
//   compass: true          # optional: show the sun compass

import { NEXT_ACTION, STATUS } from "./labels.js";
import "./tiles.js";

const UI = {
  de: {
    title: "Rollos",
    position: "Position",
    window: "Fenster",
    open: "offen",
    tilted: "gekippt",
    closed: "zu",
    unavailable: "nicht verfügbar",
    loading: "Lädt …",
    notLoaded: "Shutter Assistant ist nicht eingerichtet oder nicht geladen.",
    noWindows: "Keine Fenster.",
    override: "Übersteuert",
    until: (t) => `bis ${t}`,
    untilSunrise: "bis Sonnenaufgang",
    up: "Öffnen",
    stop: "Stopp",
    down: "Schließen",
    resume: "Automatik fortsetzen",
    automaticOff: "Automatik aus",
    sun: (az, el) => `Sonne ${az}° · Höhe ${el}°`,
    protections: { wind: "Windschutz", rain: "Regenschutz", frost: "Frostschutz" },
  },
  en: {
    title: "Covers",
    position: "Position",
    window: "Window",
    open: "open",
    tilted: "tilted",
    closed: "closed",
    unavailable: "unavailable",
    loading: "Loading …",
    notLoaded: "Shutter Assistant is not set up or not loaded.",
    noWindows: "No windows.",
    override: "Override",
    until: (t) => `until ${t}`,
    untilSunrise: "until sunrise",
    up: "Open",
    stop: "Stop",
    down: "Close",
    resume: "Resume automatic",
    automaticOff: "Automatic off",
    sun: (az, el) => `Sun ${az}° · elevation ${el}°`,
    protections: { wind: "Wind protection", rain: "Rain protection", frost: "Frost protection" },
  },
};

const GROUP_COLORS = ["#f9a825", "#1e88e5", "#e53935", "#43a047", "#8e24aa", "#00897b", "#ef6c00", "#6d4c41"];
const INVALID = ["unavailable", "unknown"];
const STATUS_STYLE = {
  protection: ["mdi:weather-windy", "danger"],
  off: ["mdi:pause-circle-outline", "muted"],
  startup: ["mdi:restart", "muted"],
  override: ["mdi:hand-back-right-outline", "purple"],
  evening: ["mdi:weather-night", "indigo"],
  sun_protection: ["mdi:white-balance-sunny", "warn"],
  vacation: ["mdi:airplane", "teal"],
  ready: ["mdi:check-circle-outline", "ok"],
};
const PROTECTIONS = [
  ["wind", "mdi:weather-windy"],
  ["rain", "mdi:weather-pouring"],
  ["frost", "mdi:snowflake"],
];

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class ShutterAssistantCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._data = null;
    this._error = false;
    this._sig = "";
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
  }

  setConfig(config) {
    this._config = { compass: true, ...(config || {}) };
    this._sig = "";
    this._render();
  }

  static getStubConfig() {
    return {};
  }

  getCardSize() {
    return 2 + (this._windows().length || 1);
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._data && !this._loading) this._load();
    const sig = this._signature();
    if (sig !== this._sig) {
      this._sig = sig;
      this._render();
    }
  }

  get lang() {
    const lang = this._data?.language || this._hass?.language || "en";
    return String(lang).toLowerCase().startsWith("de") ? "de" : "en";
  }

  get ui() {
    return UI[this.lang];
  }

  async _load() {
    if (!this._hass) return;
    this._loading = true;
    try {
      this._data = await this._hass.connection.sendMessagePromise({ type: "shutter_assistant/card" });
      this._error = false;
    } catch (_err) {
      this._error = true;
    }
    this._loading = false;
    this._sig = "";
    this._render();
    // entities of new windows exist only after the integration reloaded
    if (this._data && this._data.windows.some((w) => !w.entities?.status)) {
      setTimeout(() => {
        this._data = null;
        if (this._hass) this.hass = this._hass;
      }, 5000);
    }
  }

  _state(id) {
    return id ? this._hass?.states?.[id] : undefined;
  }

  _windows() {
    const all = this._data?.windows || [];
    const wanted = this._config?.windows;
    if (!Array.isArray(wanted) || !wanted.length) return all;
    return wanted.map((key) => all.find((w) => w.id === key || w.name === key)).filter(Boolean);
  }

  _ids() {
    const ids = ["sun.sun", ...Object.values(this._data?.entities || {})];
    for (const win of this._windows()) ids.push(win.cover, ...Object.values(win.entities || {}));
    return ids.filter(Boolean);
  }

  _signature() {
    if (!this._hass || !this._data) return `${!!this._hass}|${this._error}`;
    return this._ids()
      .map((id) => {
        const st = this._state(id);
        if (!st) return "-";
        if (id === "sun.sun") return `${Math.round(st.attributes.azimuth || 0)}|${Math.round(st.attributes.elevation || 0)}`;
        return `${st.state}|${st.last_updated}`;
      })
      .join(";");
  }

  _time(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const today = new Date();
    const opts = { hour: "2-digit", minute: "2-digit" };
    if (date.toDateString() !== today.toDateString()) opts.weekday = "short";
    return date.toLocaleTimeString(this._hass?.locale?.language || this.lang, opts);
  }

  _position(win) {
    const st = this._state(win.cover);
    if (!st || INVALID.includes(st.state)) return null;
    const pos = st.attributes.current_position;
    if (pos !== undefined && pos !== null) return Number(pos);
    if (st.state === "open") return 100;
    if (st.state === "closed") return 0;
    return null;
  }

  _groupColor(id) {
    const index = (this._data?.groups || []).findIndex((g) => g.id === id);
    return GROUP_COLORS[(index < 0 ? 0 : index) % GROUP_COLORS.length];
  }

  // ------------------------------------------------------------------ actions

  _onClick(ev) {
    const button = ev.target.closest("button[data-action]");
    if (!button || !this._hass) return;
    const win = this._windows().find((w) => w.id === button.dataset.id);
    if (!win) return;
    const action = button.dataset.action;
    if (action === "resume") {
      this._hass.callService("shutter_assistant", "resume", { entity_id: [win.cover] });
      return;
    }
    // by hand: starts an override like a button on the wall
    const service = { up: "open_cover", stop: "stop_cover", down: "close_cover" }[action];
    if (service) this._hass.callService("cover", service, { entity_id: win.cover });
  }

  // ------------------------------------------------------------------ render

  _render() {
    if (!this._config) return;
    const ui = this.ui;
    const title = this._config.title ?? ui.title;
    let body;
    if (this._error || (this._data && !this._data.loaded)) body = `<div class="muted">${esc(ui.notLoaded)}</div>`;
    else if (!this._data || !this._hass) body = `<div class="muted">${esc(ui.loading)}</div>`;
    else {
      const windows = this._windows();
      body = `${this._top()}
        <div class="rows">${windows.length ? windows.map((w) => this._row(w)).join("") : `<div class="muted">${esc(ui.noWindows)}</div>`}</div>`;
    }
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <ha-card>
        ${title ? `<h1 class="card-header">${esc(title)}</h1>` : ""}
        <div class="content">${body}</div>
      </ha-card>`;
  }

  _top() {
    const ui = this.ui;
    const ent = this._data.entities || {};
    const chips = [];
    const auto = this._state(ent.automatic);
    if (auto && auto.state === "off") chips.push(`<span class="chip muted"><ha-icon icon="mdi:pause-circle-outline"></ha-icon>${esc(ui.automaticOff)}</span>`);
    for (const [kind, icon] of PROTECTIONS) {
      if (this._state(ent[`${kind}_protection`])?.state === "on") {
        chips.push(`<span class="chip danger"><ha-icon icon="${icon}"></ha-icon>${esc(ui.protections[kind])}</span>`);
      }
    }
    const compass = this._config.compass === false ? "" : this._compass();
    if (!compass && !chips.length) return "";
    return `<div class="top">${compass}<div class="top-side">${chips.join("")}${compass ? this._sunText() : ""}</div></div>`;
  }

  _sunText() {
    const sun = this._state("sun.sun")?.attributes;
    if (!sun || sun.azimuth === undefined) return "";
    return `<div class="muted small">${esc(this.ui.sun(Math.round(sun.azimuth), Math.round(sun.elevation)))}</div>`;
  }

  _compass() {
    const groups = this._data.groups || [];
    const size = 120;
    const c = size / 2;
    // room for the direction letters at the edge
    const outer = 46;
    const point = (az, r) => [c + r * Math.sin((az * Math.PI) / 180), c - r * Math.cos((az * Math.PI) / 180)];
    const arc = (from, to, r1, r2) => {
      let span = (((to - from) % 360) + 360) % 360;
      if (span === 0 || span >= 360) span = 359.99;
      const large = span > 180 ? 1 : 0;
      const [x1, y1] = point(from, r2);
      const [x2, y2] = point(from + span, r2);
      const [x3, y3] = point(from + span, r1);
      const [x4, y4] = point(from, r1);
      return `M${x1.toFixed(2)} ${y1.toFixed(2)} A${r2} ${r2} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} L${x3.toFixed(2)} ${y3.toFixed(2)} A${r1} ${r1} 0 ${large} 0 ${x4.toFixed(2)} ${y4.toFixed(2)} Z`;
    };
    const band = Math.max(4, Math.min(10, 30 / Math.max(1, groups.length)));
    const rings = groups
      .map((g, i) => {
        const from = Number(g.azimuth_from);
        const to = Number(g.azimuth_to);
        if (Number.isNaN(from) || Number.isNaN(to) || from === to) return "";
        const r2 = outer - 1 - i * (band + 1);
        const color = this._groupColor(g.id);
        return `<path d="${arc(from, to, r2 - band, r2)}" fill="${color}" fill-opacity="0.7" stroke="${color}"><title>${esc(g.name)}</title></path>`;
      })
      .join("");
    const dirs = this.lang === "de" ? ["N", "O", "S", "W"] : ["N", "E", "S", "W"];
    const labels = [0, 90, 180, 270]
      .map((az, i) => {
        const [x, y] = point(az, outer + 7);
        return `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" class="dir">${dirs[i]}</text>`;
      })
      .join("");
    let sunMark = "";
    const sun = this._state("sun.sun")?.attributes;
    if (sun && sun.azimuth !== undefined) {
      const el = Number(sun.elevation);
      const below = el < 0;
      const r = below ? outer + 2 : Math.max(0, outer * (1 - Math.min(90, el) / 90));
      const [x, y] = point(Number(sun.azimuth), r);
      sunMark = `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${below ? 3.5 : 5.5}" class="sun ${below ? "below" : ""}"></circle>`;
    }
    return `<svg viewBox="0 0 ${size} ${size}" class="compass" role="img">
      <circle cx="${c}" cy="${c}" r="${outer}" class="ring"></circle>${rings}${labels}${sunMark}
    </svg>`;
  }

  _row(win) {
    const ui = this.ui;
    const statusState = this._state(win.entities?.status);
    const status = statusState && !INVALID.includes(statusState.state) ? statusState.state : null;
    const attrs = statusState?.attributes || {};
    const [icon, cls] = STATUS_STYLE[status] || ["mdi:window-shutter", "muted"];
    const statusText = status ? (STATUS[this.lang] || STATUS.en)[status] || status : ui.unavailable;
    const position = this._position(win);
    const contact = attrs.window_open ? ui.open : attrs.window_tilted ? ui.tilted : ui.closed;
    const details = [position === null ? ui.unavailable : `${ui.position} ${position} %`];
    // only windows with contacts
    if ((attrs.window_sensors || []).length || attrs.window_tilted) details.push(`${ui.window} ${contact}`);
    const next = this._state(win.entities?.next_action);
    if (next && !INVALID.includes(next.state)) {
      const action = (NEXT_ACTION[this.lang] || NEXT_ACTION.en)[next.attributes.action];
      if (action) details.push(`${action} ${this._time(next.state)}`);
    }
    const override = this._state(win.entities?.override);
    const overrideOn = override?.state === "on";
    const overrideText = overrideOn ? `${ui.override} ${override.attributes.until ? ui.until(this._time(override.attributes.until)) : ui.untilSunrise}` : "";
    const closed = position === null ? 0 : 100 - position;
    const id = esc(win.id);
    return `<div class="row">
      <span class="shutter ${position === null ? "na" : ""}"><span class="slats" style="height:${closed}%"></span></span>
      <div class="info">
        <div class="name"><span>${esc(win.name)}</span><span class="pill ${cls}"><ha-icon icon="${icon}"></ha-icon>${esc(statusText)}</span></div>
        <div class="muted small">${esc(details.join(" · "))}</div>
        ${overrideOn ? `<div class="small override">${esc(overrideText)} <button class="link" data-action="resume" data-id="${id}">${esc(ui.resume)}</button></div>` : ""}
      </div>
      <div class="buttons">
        <button class="icon" data-action="up" data-id="${id}" title="${esc(ui.up)}" aria-label="${esc(ui.up)}"><ha-icon icon="mdi:arrow-up"></ha-icon></button>
        <button class="icon" data-action="stop" data-id="${id}" title="${esc(ui.stop)}" aria-label="${esc(ui.stop)}"><ha-icon icon="mdi:stop"></ha-icon></button>
        <button class="icon" data-action="down" data-id="${id}" title="${esc(ui.down)}" aria-label="${esc(ui.down)}"><ha-icon icon="mdi:arrow-down"></ha-icon></button>
      </div>
    </div>`;
  }
}

const STYLE = `
:host { display:block; }
.content { padding:0 16px 16px; }
.card-header { margin:0; padding:16px 16px 8px; font-size:var(--ha-card-header-font-size, 24px); font-weight:normal; color:var(--ha-card-header-color, var(--primary-text-color)); }
.muted { color:var(--secondary-text-color); }
.small { font-size:12px; }
.top { display:flex; align-items:center; gap:16px; margin-bottom:8px; }
.top-side { display:flex; flex-direction:column; gap:6px; min-width:0; }
.compass { width:120px; height:120px; flex:none; }
.compass .ring { fill:none; stroke:var(--divider-color, #ddd); }
.compass .dir { font-size:9px; fill:var(--secondary-text-color); text-anchor:middle; dominant-baseline:central; }
.compass .sun { fill:#ffb300; stroke:#fff; stroke-width:1.5; }
.compass .sun.below { fill:var(--disabled-text-color, #999); }
.chip { display:inline-flex; align-items:center; gap:4px; font-size:12px; padding:2px 8px; border-radius:12px; width:max-content; }
.chip ha-icon, .pill ha-icon { --mdc-icon-size:14px; }
.chip.danger { background:rgba(229,57,53,.15); color:var(--error-color, #c62828); }
.chip.muted { background:var(--secondary-background-color); }
.rows { display:flex; flex-direction:column; gap:10px; }
.row { display:flex; align-items:center; gap:10px; }
.info { flex:1; min-width:0; }
.name { display:flex; align-items:center; gap:8px; flex-wrap:wrap; font-weight:500; }
.name > span:first-child { overflow:hidden; text-overflow:ellipsis; }
.pill { display:inline-flex; align-items:center; gap:3px; white-space:nowrap; font-size:11px; font-weight:normal; padding:1px 7px; border-radius:10px; background:var(--secondary-background-color); }
.pill.ok { background:rgba(67,160,71,.15); color:var(--success-color, #2e7d32); }
.pill.warn { background:rgba(255,166,0,.18); color:var(--warning-color, #b26a00); }
.pill.purple { background:rgba(142,36,170,.15); color:#8e24aa; }
.pill.indigo { background:rgba(92,107,192,.18); color:#5c6bc0; }
.pill.teal { background:rgba(0,137,123,.15); color:#00897b; }
.pill.danger { background:rgba(229,57,53,.15); color:var(--error-color, #c62828); }
.pill.muted { color:var(--secondary-text-color); }
.override { color:#8e24aa; }
.shutter { flex:none; width:22px; height:30px; border:2px solid var(--secondary-text-color); border-radius:3px; position:relative; overflow:hidden; background:var(--card-background-color, #fff); }
.shutter .slats { position:absolute; left:0; right:0; top:0; background:repeating-linear-gradient(var(--secondary-text-color) 0 2px, transparent 2px 4px); }
.shutter.na { opacity:.4; }
.buttons { display:flex; gap:2px; flex:none; }
button.icon { border:none; background:none; color:var(--primary-text-color); width:36px; height:36px; border-radius:50%; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; }
button.icon:hover { background:var(--secondary-background-color); }
button.link { border:none; background:none; padding:0; color:var(--primary-color); cursor:pointer; font:inherit; text-decoration:underline; }
@media (max-width: 380px) { .compass { width:96px; height:96px; } button.icon { width:32px; height:32px; } }
`;

if (!customElements.get("shutter-assistant-card")) {
  customElements.define("shutter-assistant-card", ShutterAssistantCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "shutter-assistant-card",
    name: "Shutter Assistant",
    description: "Windows with status, position, next action and buttons, plus the sun compass.",
    preview: true,
  });
}
