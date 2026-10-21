// Small tiles for the sections view, loaded together with card.js.
//
// Cover or window contact, 3 x 1: the cover comes down as slats from the top of
// the tile, an open or tilted window colors the tile.
//
//   type: custom:shutter-assistant-tile
//   entity: cover.wohnzimmer       # cover, binary_sensor (on = open) or sensor (open/tilted/closed)
//   name: Wohnzimmer               # optional
//
// Window with cover and contact, 6 x 1: the name at the top, below the window
// on the left and the cover on the right:
//
//   type: custom:shutter-assistant-window-tile
//   window: Wohnzimmer             # name or id of a window of Shutter Assistant, or:
//   cover: cover.wohnzimmer
//   contact: binary_sensor.wohnzimmerfenster
//   tilt: binary_sensor.wohnzimmerfenster_gekippt   # optional, on = tilted
//
// Both take the colors color_cover, color_closed, color_open and color_tilted:
// a name of the theme (purple, orange, ...) or any CSS color.

const UI = {
  de: { open: "Offen", tilted: "Gekippt", closed: "Zu", opening: "Öffnet", closing: "Schließt", unavailable: "n. v.", notFound: "Nicht gefunden" },
  en: { open: "Open", tilted: "Tilted", closed: "Closed", opening: "Opening", closing: "Closing", unavailable: "n/a", notFound: "Not found" },
};

const INVALID = ["unavailable", "unknown"];
const COLORS = {
  color_cover: "var(--state-cover-active-color, var(--purple-color, #926bc7))",
  color_closed: "var(--state-inactive-color, var(--disabled-text-color, #7a7a7a))",
  color_open: "var(--orange-color, #ff9800)",
  color_tilted: "var(--blue-color, #2196f3)",
};
const COLOR_SCHEMA = Object.keys(COLORS).map((name) => ({ name, selector: { ui_color: {} } }));

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// "purple" -> the color of the theme, "#123456" or "rgb(...)" as is
const cssColor = (value) => (/^[a-z][a-z-]*$/i.test(value) ? `var(--${value}-color, ${value})` : value);
// "state" and "none" of the color picker mean the default
const DEFAULT_COLOR = ["", "state", "none"];

const FORM_LABELS = {
  de: { entity: "Entität", window: "Fenster von Shutter Assistant (Name)", cover: "Rollo", contact: "Fensterkontakt", tilt: "Kippkontakt", name: "Name", icon: "Symbol", color_cover: "Farbe Rollo", color_closed: "Farbe geschlossen", color_open: "Farbe Fenster offen", color_tilted: "Farbe Fenster gekippt" },
  en: { entity: "Entity", window: "Window of Shutter Assistant (name)", cover: "Cover", contact: "Window contact", tilt: "Tilt contact", name: "Name", icon: "Icon", color_cover: "Cover color", color_closed: "Closed color", color_open: "Window open color", color_tilted: "Window tilted color" },
};
const computeLabel = (schema) => {
  const lang = String(document.querySelector("home-assistant")?.hass?.language || "en").toLowerCase().startsWith("de") ? "de" : "en";
  return FORM_LABELS[lang][schema.name] || schema.name;
};

class TileBase extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._sig = "";
    this.shadowRoot.addEventListener("click", () => this._moreInfo());
  }

  setConfig(config) {
    this._check(config || {});
    this._config = config;
    this._sig = "";
    this._render();
  }

  getCardSize() {
    return 1;
  }

  set hass(hass) {
    this._hass = hass;
    this._update?.();
    const sig = this._signature();
    if (sig !== this._sig) {
      this._sig = sig;
      this._render();
    }
  }

  get ui() {
    return String(this._hass?.language || "en").toLowerCase().startsWith("de") ? UI.de : UI.en;
  }

  _state(id) {
    return id ? this._hass?.states?.[id] : undefined;
  }

  _signature() {
    return this._ids()
      .map((id) => {
        const st = this._state(id);
        return st ? `${st.state}|${st.last_updated}` : "-";
      })
      .join(";");
  }

  _colors() {
    return Object.entries(COLORS)
      .map(([key, fallback]) => {
        const value = this._config[key];
        return `--${key.replace("_", "-")}:${DEFAULT_COLOR.includes(value ?? "") ? fallback : cssColor(value)};`;
      })
      .join("");
  }

  _moreInfo() {
    const entityId = this._moreInfoId();
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
  }

  // what the cover shows: icon class, text and how far it is closed
  _cover(id) {
    const st = this._state(id);
    const ui = this.ui;
    if (!st || INVALID.includes(st.state)) return { cls: "na", text: ui.unavailable, closed: 0 };
    let pos = st.attributes.current_position;
    pos = pos === undefined || pos === null ? null : Number(pos);
    if (pos === null) {
      const text = { open: ui.open, closed: ui.closed, opening: ui.opening, closing: ui.closing }[st.state] || st.state;
      return { cls: st.state === "closed" ? "closed" : "cover", text, closed: st.state === "closed" ? 100 : 0 };
    }
    return { cls: pos <= 0 ? "closed" : "cover", text: pos <= 0 ? ui.closed : `${pos} %`, closed: 100 - pos };
  }

  // open, tilted or closed from a contact (on = open) or a window handle, null if unknown
  _contact(contact, tilt) {
    const st = this._state(contact);
    if (!st || INVALID.includes(st.state)) return null;
    if (st.state === "on" || st.state === "open") return "open";
    if (st.state === "tilted" || this._state(tilt)?.state === "on") return "tilted";
    return "closed";
  }

  // window handles (sensor) and tilted windows have no fitting icon of their own
  _contactIcon(id, state) {
    if (id && !id.startsWith("sensor.") && state !== "tilted") return this._icon(id);
    return `<ha-icon icon="${state === "open" || state === "tilted" ? "mdi:window-open-variant" : "mdi:window-closed-variant"}"></ha-icon>`;
  }

  _windowText(state) {
    return state ? this.ui[state] : this.ui.unavailable;
  }

  // the icon of the entity like everywhere else in Home Assistant
  _icon(entityId, override) {
    if (override) return `<ha-icon icon="${esc(override)}"></ha-icon>`;
    return entityId && this._state(entityId) ? `<ha-state-icon data-entity="${esc(entityId)}"></ha-state-icon>` : `<ha-icon icon="mdi:help-circle-outline"></ha-icon>`;
  }

  _paint(html) {
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card style="${this._colors()}">${html}</ha-card>`;
    for (const el of this.shadowRoot.querySelectorAll("ha-state-icon")) {
      el.hass = this._hass;
      el.stateObj = this._state(el.dataset.entity);
    }
  }
}

class ShutterAssistantTile extends TileBase {
  _check(config) {
    if (!config.entity) throw new Error("entity is required");
  }

  static getStubConfig(hass) {
    const cover = Object.keys(hass?.states || {}).find((id) => id.startsWith("cover."));
    return { entity: cover || "" };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entity", required: true, selector: { entity: { domain: ["cover", "binary_sensor", "sensor"] } } },
        { name: "name", selector: { text: {} } },
        { name: "icon", selector: { icon: {} } },
        ...COLOR_SCHEMA,
      ],
      computeLabel,
    };
  }

  getGridOptions() {
    return { columns: 3, rows: 1, min_columns: 3, min_rows: 1 };
  }

  _ids() {
    return [this._config?.entity];
  }

  _moreInfoId() {
    return this._config?.entity;
  }

  _render() {
    if (!this._config || !this._hass) return;
    const id = this._config.entity;
    const st = this._state(id);
    const name = this._config.name || st?.attributes.friendly_name || id;
    let fill = "";
    let cls;
    let text;
    if (id.startsWith("cover.")) {
      const cover = this._cover(id);
      ({ cls, text } = cover);
      fill = `<div class="slats" style="height:${cover.closed}%"></div>`;
    } else {
      const state = this._contact(id);
      cls = state || "na";
      text = this._windowText(state);
      if (state === "open" || state === "tilted") fill = `<div class="tint"></div>`;
    }
    this._paint(`<div class="tile ${cls}">${fill}
      <div class="in">
        <div class="top"><span class="icon">${this._config.icon || id.startsWith("cover.") ? this._icon(id, this._config.icon) : this._contactIcon(id, cls)}</span><span class="value">${esc(text)}</span></div>
        <div class="name">${esc(name)}</div>
      </div></div>`);
  }
}

class ShutterAssistantWindowTile extends TileBase {
  _check(config) {
    if (!config.window && !config.cover) throw new Error("window or cover is required");
  }

  static getStubConfig(hass) {
    const cover = ShutterAssistantTile.getStubConfig(hass).entity;
    return cover ? { cover } : { window: "" };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "window", selector: { text: {} } },
        { name: "cover", selector: { entity: { domain: "cover" } } },
        { name: "contact", selector: { entity: { domain: ["binary_sensor", "sensor"] } } },
        { name: "tilt", selector: { entity: { domain: "binary_sensor" } } },
        { name: "name", selector: { text: {} } },
        ...COLOR_SCHEMA,
      ],
      computeLabel,
    };
  }

  getGridOptions() {
    return { columns: 6, rows: 1, min_columns: 6, min_rows: 1 };
  }

  setConfig(config) {
    this._win = undefined;
    super.setConfig(config);
  }

  // a window of Shutter Assistant: its cover and the window state of its status
  _update() {
    if (!this._config?.window || this._win !== undefined || this._loading || !this._hass) return;
    this._loading = true;
    this._hass.connection
      .sendMessagePromise({ type: "shutter_assistant/card" })
      .then((data) => {
        const key = this._config.window;
        this._win = (data.windows || []).find((w) => w.id === key || w.name === key) || null;
      })
      .catch(() => {
        this._win = null;
      })
      .finally(() => {
        this._loading = false;
        this._sig = "";
        if (this._hass) this.hass = this._hass;
      });
  }

  _coverId() {
    return this._config?.cover || this._win?.cover;
  }

  _ids() {
    return [this._coverId(), this._win?.entities?.status, this._config?.contact, this._config?.tilt];
  }

  _moreInfoId() {
    return this._coverId();
  }

  _windowState() {
    if (this._config.contact) return this._contact(this._config.contact, this._config.tilt);
    // only a cover: no window part
    if (!this._win) return undefined;
    const st = this._state(this._win?.entities?.status);
    if (!st || INVALID.includes(st.state)) return null;
    // windows without contacts have no window state
    if (!(st.attributes.window_sensors || []).length && !st.attributes.window_tilted) return undefined;
    return st.attributes.window_open ? "open" : st.attributes.window_tilted ? "tilted" : "closed";
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (this._config.window && !this._config.cover && this._win === null) {
      this._paint(`<div class="tile na"><div class="in center">${esc(this.ui.notFound)}: ${esc(this._config.window)}</div></div>`);
      return;
    }
    const coverId = this._coverId();
    if (!coverId) return;
    const cover = this._cover(coverId);
    const name =
      this._config.name ||
      this._win?.name ||
      this._state(this._config.contact)?.attributes.friendly_name ||
      this._state(coverId)?.attributes.friendly_name ||
      coverId;
    const state = this._windowState();
    const contactIcon = this._contactIcon(this._config.contact, state);
    const win =
      state === undefined
        ? ""
        : `<span class="part win ${state || "na"}"><span class="icon">${contactIcon}</span><span>${esc(this._windowText(state))}</span></span>`;
    this._paint(`<div class="tile ${cover.cls}"><div class="slats" style="height:${cover.closed}%"></div>
      <div class="in">
        <div class="name">${esc(name)}</div>
        <div class="bottom">${win}<span class="part cover"><span class="icon">${this._icon(coverId, this._config.icon)}</span><span>${esc(cover.text)}</span></span></div>
      </div></div>`);
  }
}

const STYLE = `
:host { display:block; height:100%; }
ha-card { height:100%; min-height:56px; overflow:hidden; cursor:pointer; position:relative; }
.tile { position:absolute; inset:0; --c:var(--color-cover); }
.tile.closed, .tile.na { --c:var(--color-closed); }
.tile.open { --c:var(--color-open); }
.tile.tilted { --c:var(--color-tilted); }
.tile.na .in { opacity:.5; }
.slats { position:absolute; left:0; right:0; top:0; transition:height .6s ease;
  background:repeating-linear-gradient(180deg, color-mix(in srgb, var(--color-cover) 30%, transparent) 0 5px, color-mix(in srgb, var(--color-cover) 16%, transparent) 5px 7px); }
.tint { position:absolute; inset:0; background:color-mix(in srgb, var(--c) 22%, transparent); }
.in { position:relative; height:100%; box-sizing:border-box; padding:6px 9px; display:flex; flex-direction:column; justify-content:space-between; min-width:0; }
.in.center { justify-content:center; font-size:12px; color:var(--secondary-text-color); }
.top, .bottom { display:flex; align-items:center; gap:4px; min-width:0; }
.icon { display:flex; flex:none; color:var(--c); --mdc-icon-size:20px; }
.value { margin-left:auto; font-weight:600; font-size:13px; white-space:nowrap; }
.tile.open .value, .tile.tilted .value { color:var(--c); font-size:11.5px; }
.name { font-size:12px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; color:var(--primary-text-color); }
.bottom { justify-content:space-between; }
.part { display:inline-flex; align-items:center; gap:4px; font-size:12px; font-weight:500; padding:1px 8px 1px 4px; border-radius:10px; white-space:nowrap; color:var(--primary-text-color); background:var(--secondary-background-color, rgba(127,127,127,.15)); }
.part .icon { --mdc-icon-size:16px; }
.part.cover { margin-left:auto; }
.win { color:var(--secondary-text-color); --c:var(--color-closed); }
.win.open { --c:var(--color-open); color:var(--c); background:color-mix(in srgb, var(--c) 20%, transparent); }
.win.tilted { --c:var(--color-tilted); color:var(--c); background:color-mix(in srgb, var(--c) 20%, transparent); }
`;

const TILES = [
  ["shutter-assistant-tile", ShutterAssistantTile, "Shutter Assistant tile", "Cover or window contact, 3 x 1: position as slats, open window colored."],
  ["shutter-assistant-window-tile", ShutterAssistantWindowTile, "Shutter Assistant window tile", "Window with cover and contact, 6 x 1."],
];

for (const [type, cls, name, description] of TILES) {
  if (customElements.get(type)) continue;
  customElements.define(type, cls);
  window.customCards = window.customCards || [];
  window.customCards.push({ type, name, description, preview: true });
}
