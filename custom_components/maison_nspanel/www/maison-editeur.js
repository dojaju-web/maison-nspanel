/* Maison NSPanel – panneau de réglages (barre latérale) : éclairage, rappels, météo,
   climatisation, aspirateur, apparence. Tout est enregistré d'un coup. */
const TABS = [
  ["eclairage", "Éclairage", "mdi:lightbulb-group"],
  ["rappels", "Rappels", "mdi:bell-ring-outline"],
  ["meteo", "Météo", "mdi:weather-partly-cloudy"],
  ["clim", "Climatisation", "mdi:air-conditioner"],
  ["aspi", "Aspirateur", "mdi:robot-vacuum"],
  ["style", "Apparence", "mdi:palette-outline"],
];
const DAYS = [["mon", "Lun"], ["tue", "Mar"], ["wed", "Mer"], ["thu", "Jeu"], ["fri", "Ven"], ["sat", "Sam"], ["sun", "Dim"]];
const MIN_LABELS = { jamais: "Jamais", jaune: "À partir de jaune", orange: "À partir d'orange", rouge: "Rouge seulement", toujours: "Toujours (même vert)" };
const STYLE_LABELS = { verre: ["Verre sombre", "Cartes en verre teinté, titres en capitales (par défaut)."], ardoise: ["Ardoise", "Cartes sobres, titres en minuscules, météo en fond."] };
const VAC_FIELDS = [
  ["vac_battery", "Batterie", "sensor", "Capteur de batterie (%)"],
  ["vac_fan", "Puissance d'aspiration", "select", "Liste de choix (select) ou laissez vide pour utiliser l'aspirateur"],
  ["vac_area", "Surface nettoyée", "sensor", "Capteur de surface (m²)"],
  ["vac_time", "Durée de nettoyage", "sensor", "Capteur de durée (s ou min)"],
  ["vac_alert", "Alerte / erreur", "any", "Capteur d'erreur (facultatif)"],
];

class MaisonNspanelEditeur extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._cfg = null;
    this._info = {};
    this._saved = "";
    this._tab = "eclairage";
    this._search = "";
    this._open = null;
    this._pick = "";
    this._drag = null;
    this._msg = "";
    this._saving = false;
    this._loading = false;
  }

  set hass(h) {
    const first = !this._hass;
    this._hass = h;
    if (first) this._load();
  }
  set narrow(v) { this._narrow = v; }
  set panel(v) { this._panel = v; }

  async _load() {
    if (this._loading) return;
    this._loading = true;
    try {
      const r = await this._hass.callWS({ type: "maison_nspanel/get_settings" });
      this._cfg = r.settings;
      this._info = r.detected || {};
      this._saved = JSON.stringify(this._cfg);
    } catch (e) {
      this._msg = "Impossible de charger : " + (e && e.message ? e.message : e);
      this._cfg = { sections: [], rappels: [] };
    }
    this._loading = false;
    this._render();
  }

  get _dirty() { return JSON.stringify(this._cfg) !== this._saved; }
  get _sections() { return this._cfg.sections; }

  // ---------- utilitaires ----------
  _esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  _name(id) {
    const st = this._hass && this._hass.states[id];
    return (st && st.attributes && st.attributes.friendly_name) || id;
  }
  _ids(domains) {
    const d = Array.isArray(domains) ? domains : [domains];
    return Object.keys(this._hass.states).filter((id) => d.includes("any") || d.includes(id.split(".")[0])).sort();
  }
  _used() {
    const s = new Set();
    this._sections.forEach((x) => x.lumieres.forEach((l) => s.add(l.entity)));
    return s;
  }
  _available() {
    const used = this._used();
    const q = this._search.trim().toLowerCase();
    return Object.keys(this._hass.states)
      .filter((id) => (id.startsWith("light.") || id.startsWith("switch.")) && !used.has(id))
      .map((id) => ({ id, name: this._name(id) }))
      .filter((e) => !q || e.id.toLowerCase().includes(q) || e.name.toLowerCase().includes(q))
      .sort((a, b) => (a.id.startsWith("light.") === b.id.startsWith("light.") ? a.name.localeCompare(b.name) : a.id.startsWith("light.") ? -1 : 1));
  }
  _hex(c) { return "#" + (c || [250, 204, 21]).map((v) => Math.max(0, Math.min(255, v | 0)).toString(16).padStart(2, "0")).join(""); }
  _rgb(h) { return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) || 0); }

  // ---------- actions éclairage ----------
  _addSection() {
    this._sections.push({ nom: "NOUVELLE SECTION", lumieres: [] });
    this._open = this._sections.length - 1;
    this._pick = "";
    this._render();
    const inputs = this.shadowRoot.querySelectorAll(".sec-name");
    const last = inputs[inputs.length - 1];
    if (last) { last.focus(); last.select(); }
  }
  _delSection(i) {
    const s = this._sections[i];
    if (s.lumieres.length && !confirm(`Supprimer la section « ${s.nom} » et ses ${s.lumieres.length} lumière(s) ?`)) return;
    this._sections.splice(i, 1);
    this._open = null;
    this._render();
  }
  _moveSection(i, d) {
    const j = i + d;
    if (j < 0 || j >= this._sections.length) return;
    [this._sections[i], this._sections[j]] = [this._sections[j], this._sections[i]];
    this._render();
  }
  _addLight(i, id) {
    if (this._used().has(id)) return;
    this._sections[i].lumieres.push({ entity: id });
    this._render();
  }
  _delLight(i, k) { this._sections[i].lumieres.splice(k, 1); this._render(); }
  _moveLight(i, k, d) {
    const a = this._sections[i].lumieres, j = k + d;
    if (j < 0 || j >= a.length) return;
    [a[k], a[j]] = [a[j], a[k]];
    this._render();
  }
  _dropOn(i, before) {
    const d = this._drag;
    this._drag = null;
    if (!d) return;
    if (d.type === "section") {
      const [s] = this._sections.splice(d.i, 1);
      this._sections.splice(i, 0, s);
    } else {
      let light;
      if (d.from === "pool") light = { entity: d.id };
      else {
        light = this._sections[d.from].lumieres.splice(d.k, 1)[0];
        if (d.from === i && before != null && d.k < before) before -= 1;
      }
      if (!light) return;
      const arr = this._sections[i].lumieres;
      arr.splice(before == null ? arr.length : before, 0, light);
    }
    this._render();
  }
  _dropOnPool() {
    const d = this._drag;
    this._drag = null;
    if (d && d.type === "light" && d.from !== "pool") {
      this._sections[d.from].lumieres.splice(d.k, 1);
      this._render();
    }
  }

  // ---------- actions rappels ----------
  _addRappel() {
    this._cfg.rappels.push({ texte: "Nouveau rappel", icone: "mdi:bell-outline", jours: ["mon"], heure_debut: "00:00:00", heure_fin: "23:59:00", couleur: [250, 204, 21], actif: true });
    this._render();
  }

  // ---------- enregistrement ----------
  async _save() {
    this._saving = true; this._msg = ""; this._render();
    try {
      const c = this._cfg;
      const payload = { ...c };
      payload.sections = c.sections.map((s) => ({
        nom: s.nom.trim() || "SECTION",
        lumieres: s.lumieres.map((l) => {
          const o = { entity: l.entity };
          if (l.nom) o.nom = l.nom;
          if (l.icone) o.icone = l.icone;
          if (l.couleur) o.couleur = l.couleur;
          return o;
        }),
      }));
      const r = await this._hass.callWS({ type: "maison_nspanel/set_settings", settings: payload });
      this._cfg = r.settings;
      this._info = r.detected || this._info;
      this._saved = JSON.stringify(this._cfg);
      this._msg = "ok";
    } catch (e) {
      this._msg = "Erreur : " + (e && e.message ? e.message : e);
    }
    this._saving = false;
    this._render();
  }

  // ---------- rendu des onglets ----------
  _entityField(key, label, domains, help, detected) {
    const id = "dl-" + key;
    const val = this._cfg[key] || "";
    const opts = this._ids(domains).map((e) => `<option value="${this._esc(e)}">${this._esc(this._name(e))}</option>`).join("");
    const ph = detected ? "Auto : " + detected : "Choisir une entité…";
    const known = val && this._hass.states[val];
    return `<label class="field"><span>${this._esc(label)}</span>
      <div class="entity"><input class="ent" data-key="${key}" list="${id}" value="${this._esc(val)}" placeholder="${this._esc(ph)}" autocomplete="off" spellcheck="false" />
        ${val ? `<button class="ic" data-act="clear" data-key="${key}" title="Effacer">✕</button>` : ""}</div>
      <datalist id="${id}">${opts}</datalist>
      <small>${val ? (known ? this._esc(this._name(val)) : "⚠ entité introuvable") : this._esc(help || "")}</small></label>`;
  }

  _lightRow(i, k, l) {
    const st = this._hass.states[l.entity];
    const on = st && st.state === "on";
    const missing = !st;
    const kind = l.entity.startsWith("switch.") ? "interrupteur" : "lumière";
    return `<div class="light ${missing ? "missing" : ""}" draggable="true" data-sec="${i}" data-k="${k}">
      <span class="grip" title="Glisser pour déplacer">⋮⋮</span>
      <span class="dot ${on ? "on" : ""}"></span>
      <div class="lname">
        <input class="l-name" data-sec="${i}" data-k="${k}" value="${this._esc(l.nom || "")}" placeholder="${this._esc(this._name(l.entity))}" />
        <small>${this._esc(l.entity)} · ${kind}${missing ? " · introuvable" : ""}</small>
      </div>
      <button class="ic" data-act="lup" data-sec="${i}" data-k="${k}" title="Monter">▲</button>
      <button class="ic" data-act="ldown" data-sec="${i}" data-k="${k}" title="Descendre">▼</button>
      <button class="ic danger" data-act="ldel" data-sec="${i}" data-k="${k}" title="Retirer">✕</button>
    </div>`;
  }

  _picker(i) {
    const q = this._pick.toLowerCase();
    const items = this._available().filter((e) => !q || e.id.toLowerCase().includes(q) || e.name.toLowerCase().includes(q)).slice(0, 40);
    return `<div class="picker">
      <input class="pick-search" data-sec="${i}" placeholder="Rechercher une lumière…" value="${this._esc(this._pick)}" />
      <div class="pick-list">${items.length ? items.map((e) => `<button class="pick-item" data-act="padd" data-sec="${i}" data-id="${this._esc(e.id)}"><b>${this._esc(e.name)}</b><small>${this._esc(e.id)}</small></button>`).join("") : `<div class="empty">Aucune entité disponible</div>`}</div>
    </div>`;
  }

  _tabEclairage() {
    const avail = this._available();
    const secs = this._sections.map((s, i) => `
      <section class="card" data-sec="${i}">
        <header class="sec-head" draggable="true" data-secdrag="${i}">
          <span class="grip" title="Glisser pour réordonner">⋮⋮</span>
          <input class="sec-name" data-sec="${i}" value="${this._esc(s.nom)}" />
          <button class="ic" data-act="sup" data-sec="${i}" title="Monter">▲</button>
          <button class="ic" data-act="sdown" data-sec="${i}" title="Descendre">▼</button>
          <button class="ic danger" data-act="sdel" data-sec="${i}" title="Supprimer la section">🗑</button>
        </header>
        <div class="lights" data-drop="${i}">
          ${s.lumieres.map((l, k) => this._lightRow(i, k, l)).join("") || `<div class="empty">Section vide : glissez une lumière ici ou utilisez « Ajouter ».</div>`}
        </div>
        <button class="add" data-act="open" data-sec="${i}">${this._open === i ? "Fermer" : "+ Ajouter une lumière"}</button>
        ${this._open === i ? this._picker(i) : ""}
      </section>`).join("");
    const pool = avail.slice(0, 60).map((e) => `<div class="chip" draggable="true" data-pool="${this._esc(e.id)}"><span class="grip">⋮⋮</span><div><b>${this._esc(e.name)}</b><small>${this._esc(e.id)}</small></div></div>`).join("");
    return `<div class="hint">Glissez les sections et les lumières pour les réordonner (ou utilisez ▲ ▼). Cliquez sur un nom pour le changer ; laissez-le vide pour garder le nom de l'entité.</div>
      <div class="two">
        <div class="main">${secs}<button class="newsec" data-act="snew">+ Nouvelle section</button></div>
        <aside class="side"><div class="poolbox" data-pool-drop="1">
          <h2>Lumières disponibles (${avail.length})</h2>
          <p>Glissez-les vers une section. Déposez ici une lumière pour la retirer.</p>
          <input class="pool-search" placeholder="Rechercher…" value="${this._esc(this._search)}" />
          ${pool || `<div class="empty">Tout est déjà placé</div>`}
        </div></aside>
      </div>`;
  }

  _tabRappels() {
    const cards = this._cfg.rappels.map((r, i) => `
      <section class="card">
        <header class="sec-head">
          <input class="r-f" data-r="${i}" data-f="texte" value="${this._esc(r.texte)}" placeholder="Texte du rappel" style="font-weight:600;font-size:16px" />
          <label class="switch" title="Actif"><input type="checkbox" class="r-f" data-r="${i}" data-f="actif" ${r.actif ? "checked" : ""} /><i></i></label>
          <button class="ic danger" data-act="rdel" data-r="${i}" title="Supprimer">🗑</button>
        </header>
        <div class="days">${DAYS.map(([d, l]) => `<button class="day ${r.jours.includes(d) ? "on" : ""}" data-act="rday" data-r="${i}" data-d="${d}">${l}</button>`).join("")}</div>
        <div class="row">
          <label class="field"><span>De</span><input type="time" class="r-f" data-r="${i}" data-f="heure_debut" value="${this._esc((r.heure_debut || "00:00").slice(0, 5))}" /></label>
          <label class="field"><span>À</span><input type="time" class="r-f" data-r="${i}" data-f="heure_fin" value="${this._esc((r.heure_fin || "23:59").slice(0, 5))}" /></label>
          <label class="field"><span>Couleur</span><input type="color" class="r-f" data-r="${i}" data-f="couleur" value="${this._hex(r.couleur)}" /></label>
          <label class="field grow"><span>Icône</span><input class="r-f" data-r="${i}" data-f="icone" value="${this._esc(r.icone)}" placeholder="mdi:trash-can-outline" /></label>
        </div>
      </section>`).join("");
    return `<div class="hint">Les rappels s'affichent sur l'accueil les jours et dans la plage horaire choisis.</div>
      <div class="one">${cards || `<div class="empty">Aucun rappel.</div>`}<button class="newsec" data-act="radd">+ Nouveau rappel</button></div>`;
  }

  _tabMeteo() {
    const c = this._cfg;
    return `<div class="one"><section class="card">
      ${this._entityField("weather_entity", "Entité météo", "weather", "Ex. Météo-France : weather.votre_ville")}
      ${this._entityField("vigilance_entity", "Capteur de vigilance (facultatif)", "sensor", "Laissez vide pour détecter sensor.XX_weather_alert", this._info.vigilance)}
      <label class="field"><span>Afficher l'alerte vigilance</span>
        <select class="sel" data-key="vigilance_min">${Object.entries(MIN_LABELS).map(([k, l]) => `<option value="${k}" ${c.vigilance_min === k ? "selected" : ""}>${l}</option>`).join("")}</select></label>
    </section></div>`;
  }

  _tabClim() {
    const c = this._cfg;
    return `<div class="one"><section class="card">
      ${this._entityField("climate_entity", "Entité de climatisation", "climate", "Les entités liées (ventilation, filtre…) sont déduites de son nom")}
      <label class="check"><input type="checkbox" class="chk" data-key="air_enabled" ${c.air_enabled ? "checked" : ""} /><span>Afficher la qualité de l'air sur l'accueil</span></label>
    </section></div>`;
  }

  _tabAspi() {
    const d = this._info;
    return `<div class="one"><section class="card">
      ${this._entityField("vacuum_entity", "Aspirateur", "vacuum", "Laissez vide pour utiliser le premier aspirateur détecté", d.vacuum)}
      <div class="hint inner">Les mesures ci-dessous sont facultatives : si elles sont vides, le panneau cherche tout seul parmi les entités de l'appareil, puis dans les attributs de l'aspirateur.</div>
      ${VAC_FIELDS.map(([k, l, dom, h]) => this._entityField(k, l, dom, h, d[k])).join("")}
    </section></div>`;
  }

  _tabStyle() {
    const cur = this._cfg.style;
    return `<div class="one"><section class="card">
      ${Object.entries(STYLE_LABELS).map(([k, [l, h]]) => `<label class="radio ${cur === k ? "on" : ""}"><input type="radio" name="style" class="rad" data-key="style" value="${k}" ${cur === k ? "checked" : ""} /><div><b>${l}</b><small>${h}</small></div></label>`).join("")}
      <label class="check"><input type="checkbox" class="chk" data-key="menu_enabled" ${this._cfg.menu_enabled ? "checked" : ""} /><span>Afficher le menu de navigation en bas de l'accueil</span></label>
    </section></div>`;
  }

  _render() {
    if (!this._hass || !this._cfg) return;
    const dirty = this._dirty;
    const tabs = TABS.map(([k, l, ic]) => `<button class="tab ${this._tab === k ? "on" : ""}" data-act="tab" data-tab="${k}"><ha-icon icon="${ic}"></ha-icon><span>${l}</span></button>`).join("");
    const body = { eclairage: () => this._tabEclairage(), rappels: () => this._tabRappels(), meteo: () => this._tabMeteo(), clim: () => this._tabClim(), aspi: () => this._tabAspi(), style: () => this._tabStyle() }[this._tab]();
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;background:var(--primary-background-color);color:var(--primary-text-color);min-height:100vh;font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
        *{box-sizing:border-box}
        .bar{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--app-header-background-color,var(--primary-color));color:var(--app-header-text-color,#fff)}
        .bar h1{font-size:20px;font-weight:500;margin:0;flex:1}
        .menu{background:none;border:0;color:inherit;font-size:24px;cursor:pointer;display:none}
        .save{background:#fff;color:var(--primary-color);border:0;border-radius:18px;padding:8px 18px;font-weight:600;cursor:pointer}
        .save[disabled]{opacity:.45;cursor:default}
        .status{font-size:13px;opacity:.95}
        .tabs{display:flex;gap:4px;overflow-x:auto;padding:8px 12px 0;background:var(--card-background-color);border-bottom:1px solid var(--divider-color)}
        .tab{display:flex;align-items:center;gap:6px;background:none;border:0;border-bottom:3px solid transparent;color:var(--secondary-text-color);padding:10px 12px;cursor:pointer;font-size:14px;white-space:nowrap}
        .tab.on{color:var(--primary-color);border-bottom-color:var(--primary-color);font-weight:600}
        .tab ha-icon{--mdc-icon-size:20px}
        .wrap{padding:16px;max-width:1100px;margin:0 auto}
        .one{max-width:720px}
        .two{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px}
        @media(max-width:800px){.two{grid-template-columns:1fr}.menu{display:block}.tab span{display:none}}
        .hint{background:var(--card-background-color);border-left:4px solid var(--primary-color);border-radius:8px;padding:10px 14px;font-size:14px;color:var(--secondary-text-color);margin-bottom:14px}
        .hint.inner{background:var(--secondary-background-color);margin:6px 0 12px}
        .card,.poolbox{background:var(--card-background-color);border-radius:12px;padding:14px;margin-bottom:14px;box-shadow:var(--ha-card-box-shadow,0 1px 3px rgba(0,0,0,.2))}
        .sec-head{display:flex;align-items:center;gap:6px;margin-bottom:8px}
        .sec-head[draggable=true]{cursor:grab}
        .sec-name,.r-f[data-f=texte]{flex:1;font-size:16px;font-weight:600;letter-spacing:.5px;background:transparent;color:inherit;border:1px solid transparent;border-radius:6px;padding:6px 8px;min-width:0}
        .sec-name:hover,.sec-name:focus,.r-f[data-f=texte]:hover,.r-f[data-f=texte]:focus{border-color:var(--divider-color);outline:none}
        .grip{color:var(--secondary-text-color);cursor:grab;user-select:none;letter-spacing:-3px;padding:0 6px}
        .lights{min-height:44px;border:2px dashed transparent;border-radius:8px;padding:2px}
        .lights.over,.poolbox.over{border-color:var(--primary-color);background:rgba(var(--rgb-primary-color,3,169,244),.08)}
        .light{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:8px;background:var(--secondary-background-color);margin:4px 0}
        .light.dragging,.chip.dragging{opacity:.4}
        .light.missing{outline:1px solid var(--error-color,#db4437)}
        .light.before{box-shadow:0 -3px 0 var(--primary-color)}
        .dot{width:10px;height:10px;border-radius:50%;background:var(--disabled-text-color,#888);flex:none}
        .dot.on{background:#facc15;box-shadow:0 0 6px #facc15}
        .lname{flex:1;min-width:0;display:flex;flex-direction:column}
        .l-name{background:transparent;border:0;border-bottom:1px solid transparent;color:inherit;font-size:14px;padding:2px 0;min-width:0;width:100%}
        .l-name:focus{outline:none;border-bottom-color:var(--primary-color)}
        small{color:var(--secondary-text-color);font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .ic{background:none;border:0;color:var(--secondary-text-color);cursor:pointer;font-size:13px;padding:6px;border-radius:6px}
        .ic:hover{background:var(--divider-color)} .ic.danger:hover{color:var(--error-color,#db4437)}
        .add{width:100%;margin-top:6px;background:none;border:1px dashed var(--divider-color);color:var(--primary-color);border-radius:8px;padding:9px;cursor:pointer;font-size:14px}
        .add:hover{background:var(--secondary-background-color)}
        .newsec{width:100%;background:var(--primary-color);color:#fff;border:0;border-radius:10px;padding:12px;font-size:15px;font-weight:600;cursor:pointer}
        .empty{color:var(--secondary-text-color);font-size:13px;padding:10px;text-align:center}
        .picker{margin-top:8px;border:1px solid var(--divider-color);border-radius:8px;padding:8px}
        input.pick-search,input.pool-search,.field input,.field select,.entity input{width:100%;padding:9px;border-radius:8px;border:1px solid var(--divider-color);background:var(--primary-background-color);color:inherit;font-size:14px}
        .pick-search,.pool-search{margin-bottom:6px}
        .pick-list{max-height:220px;overflow:auto}
        .pick-item{display:flex;flex-direction:column;align-items:flex-start;width:100%;text-align:left;background:none;border:0;color:inherit;padding:7px 8px;border-radius:6px;cursor:pointer}
        .pick-item:hover{background:var(--secondary-background-color)}
        .poolbox h2{font-size:15px;margin:0 0 4px} .poolbox p{margin:0 0 8px;font-size:12px;color:var(--secondary-text-color)}
        .chip{display:flex;align-items:center;gap:4px;padding:6px;border-radius:8px;background:var(--secondary-background-color);margin:4px 0;cursor:grab}
        .chip div{display:flex;flex-direction:column;min-width:0} .chip b{font-size:13px;font-weight:500}
        .side{position:sticky;top:130px;align-self:start}
        .field{display:flex;flex-direction:column;gap:4px;margin:0 0 14px;min-width:0}
        .field>span{font-size:13px;font-weight:600}
        .field.grow{flex:1;min-width:160px}
        .entity{display:flex;align-items:center;gap:4px}
        .row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
        .row .field{margin-bottom:0}
        input[type=color]{height:38px;padding:2px;width:70px}
        .days{display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 12px}
        .day{border:1px solid var(--divider-color);background:none;color:var(--secondary-text-color);border-radius:16px;padding:6px 12px;cursor:pointer;font-size:13px}
        .day.on{background:var(--primary-color);border-color:var(--primary-color);color:#fff}
        .switch input{display:none}.switch i{display:block;width:38px;height:20px;border-radius:10px;background:var(--disabled-text-color,#888);position:relative;cursor:pointer;transition:.2s}
        .switch i::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;transition:.2s}
        .switch input:checked+i{background:var(--primary-color)} .switch input:checked+i::after{left:20px}
        .check{display:flex;align-items:center;gap:10px;font-size:14px;cursor:pointer}
        .radio{display:flex;align-items:flex-start;gap:12px;padding:12px;border:1px solid var(--divider-color);border-radius:10px;margin-bottom:10px;cursor:pointer}
        .radio.on{border-color:var(--primary-color);background:rgba(var(--rgb-primary-color,3,169,244),.08)}
        .radio div{display:flex;flex-direction:column;gap:2px} .radio small{white-space:normal}
        .ok{color:#86efac}.err{color:#fecaca}
      </style>
      <div class="bar">
        <button class="menu" data-act="menu">☰</button>
        <h1>Réglages Maison NSPanel</h1>
        <span class="status ${this._msg === "ok" ? "ok" : this._msg ? "err" : ""}">${this._saving ? "Enregistrement…" : this._msg === "ok" ? "✓ Enregistré – dashboard actualisé (rechargez la page du panneau si besoin)" : this._esc(this._msg)}</span>
        <button class="save" data-act="save" ${dirty && !this._saving ? "" : "disabled"}>Enregistrer</button>
      </div>
      <div class="tabs">${tabs}</div>
      <div class="wrap">${body}</div>`;
    this._bind();
  }

  _rerenderKeepFocus(sel) {
    this._render();
    const n = this.shadowRoot.querySelector(sel);
    if (n) { n.focus(); n.setSelectionRange && n.setSelectionRange(n.value.length, n.value.length); }
  }

  _bind() {
    const r = this.shadowRoot;
    r.querySelectorAll("[data-act]").forEach((el) => {
      el.addEventListener("click", () => {
        const a = el.dataset.act, i = +el.dataset.sec, k = +el.dataset.k;
        if (a === "save") this._save();
        else if (a === "tab") { this._tab = el.dataset.tab; this._render(); }
        else if (a === "snew") this._addSection();
        else if (a === "sdel") this._delSection(i);
        else if (a === "sup") this._moveSection(i, -1);
        else if (a === "sdown") this._moveSection(i, 1);
        else if (a === "ldel") this._delLight(i, k);
        else if (a === "lup") this._moveLight(i, k, -1);
        else if (a === "ldown") this._moveLight(i, k, 1);
        else if (a === "open") { this._open = this._open === i ? null : i; this._pick = ""; this._render(); }
        else if (a === "padd") this._addLight(i, el.dataset.id);
        else if (a === "radd") this._addRappel();
        else if (a === "rdel") { this._cfg.rappels.splice(+el.dataset.r, 1); this._render(); }
        else if (a === "rday") {
          const rp = this._cfg.rappels[+el.dataset.r], d = el.dataset.d;
          rp.jours = rp.jours.includes(d) ? rp.jours.filter((x) => x !== d) : [...rp.jours, d];
          this._render();
        }
        else if (a === "clear") { this._cfg[el.dataset.key] = ""; this._render(); }
        else if (a === "menu") this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
      });
    });
    r.querySelectorAll(".sec-name").forEach((el) => el.addEventListener("input", () => { this._sections[+el.dataset.sec].nom = el.value; this._updateSave(); }));
    r.querySelectorAll(".l-name").forEach((el) => el.addEventListener("input", () => {
      const l = this._sections[+el.dataset.sec].lumieres[+el.dataset.k];
      if (el.value.trim()) l.nom = el.value; else delete l.nom;
      this._updateSave();
    }));
    r.querySelectorAll(".r-f").forEach((el) => el.addEventListener("input", () => {
      const rp = this._cfg.rappels[+el.dataset.r], f = el.dataset.f;
      if (f === "actif") rp.actif = el.checked;
      else if (f === "couleur") rp.couleur = this._rgb(el.value);
      else if (f === "heure_debut" || f === "heure_fin") rp[f] = (el.value || "00:00") + ":00";
      else rp[f] = el.value;
      this._updateSave();
    }));
    r.querySelectorAll("input.ent").forEach((el) => el.addEventListener("change", () => { this._cfg[el.dataset.key] = el.value.trim(); this._render(); }));
    r.querySelectorAll("select.sel").forEach((el) => el.addEventListener("change", () => { this._cfg[el.dataset.key] = el.value; this._updateSave(); }));
    r.querySelectorAll("input.chk").forEach((el) => el.addEventListener("change", () => { this._cfg[el.dataset.key] = el.checked; this._updateSave(); }));
    r.querySelectorAll("input.rad").forEach((el) => el.addEventListener("change", () => { this._cfg[el.dataset.key] = el.value; this._render(); }));
    const ps = r.querySelector(".pool-search");
    if (ps) ps.addEventListener("input", () => { this._search = ps.value; this._rerenderKeepFocus(".pool-search"); });
    const pk = r.querySelector(".pick-search");
    if (pk) pk.addEventListener("input", () => { this._pick = pk.value; this._rerenderKeepFocus(".pick-search"); });

    // --- glisser-déposer (onglet Éclairage) ---
    r.querySelectorAll("[data-secdrag]").forEach((el) => {
      el.addEventListener("dragstart", (e) => { if (e.target !== el) return; this._drag = { type: "section", i: +el.dataset.secdrag }; e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", "s"); });
      el.addEventListener("dragend", () => { this._drag = null; });
    });
    r.querySelectorAll(".light").forEach((el) => {
      el.addEventListener("dragstart", (e) => { e.stopPropagation(); this._drag = { type: "light", from: +el.dataset.sec, k: +el.dataset.k }; el.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", "l"); });
      el.addEventListener("dragend", () => { this._drag = null; el.classList.remove("dragging"); });
      el.addEventListener("dragover", (e) => { if (this._drag && this._drag.type === "light") { e.preventDefault(); e.stopPropagation(); el.classList.add("before"); } });
      el.addEventListener("dragleave", () => el.classList.remove("before"));
      el.addEventListener("drop", (e) => { e.preventDefault(); e.stopPropagation(); this._dropOn(+el.dataset.sec, +el.dataset.k); });
    });
    r.querySelectorAll(".chip").forEach((el) => {
      el.addEventListener("dragstart", (e) => { this._drag = { type: "light", from: "pool", id: el.dataset.pool }; el.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", "p"); });
      el.addEventListener("dragend", () => { this._drag = null; el.classList.remove("dragging"); });
    });
    r.querySelectorAll(".lights").forEach((el) => {
      el.addEventListener("dragover", (e) => { if (this._drag && this._drag.type === "light") { e.preventDefault(); el.classList.add("over"); } });
      el.addEventListener("dragleave", () => el.classList.remove("over"));
      el.addEventListener("drop", (e) => { e.preventDefault(); el.classList.remove("over"); this._dropOn(+el.dataset.drop, null); });
    });
    r.querySelectorAll(".card[data-sec]").forEach((el) => {
      el.addEventListener("dragover", (e) => { if (this._drag && this._drag.type === "section") e.preventDefault(); });
      el.addEventListener("drop", (e) => { if (this._drag && this._drag.type === "section") { e.preventDefault(); this._dropOn(+el.dataset.sec, null); } });
    });
    const pb = r.querySelector("[data-pool-drop]");
    if (pb) {
      pb.addEventListener("dragover", (e) => { if (this._drag && this._drag.type === "light" && this._drag.from !== "pool") { e.preventDefault(); pb.classList.add("over"); } });
      pb.addEventListener("dragleave", () => pb.classList.remove("over"));
      pb.addEventListener("drop", (e) => { e.preventDefault(); pb.classList.remove("over"); this._dropOnPool(); });
    }
  }

  _updateSave() {
    const b = this.shadowRoot.querySelector(".save");
    if (b) b.disabled = !this._dirty || this._saving;
  }
}
customElements.define("maison-nspanel-editeur", MaisonNspanelEditeur);
