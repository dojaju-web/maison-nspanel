/* Maison NSPanel – éditeur visuel de la page Éclairage (panneau de la barre latérale) */
class MaisonNspanelEditeur extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._sections = null;
    this._saved = "";
    this._search = "";
    this._open = null; // index de la section dont le sélecteur est ouvert
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
      const r = await this._hass.callWS({ type: "maison_nspanel/get_sections" });
      this._sections = r.sections;
      this._saved = JSON.stringify(this._sections);
    } catch (e) {
      this._msg = "Impossible de charger : " + (e && e.message ? e.message : e);
      this._sections = [];
    }
    this._loading = false;
    this._render();
  }

  get _dirty() { return JSON.stringify(this._sections) !== this._saved; }

  _used() {
    const s = new Set();
    (this._sections || []).forEach((x) => x.lumieres.forEach((l) => s.add(l.entity)));
    return s;
  }

  _name(id) {
    const st = this._hass && this._hass.states[id];
    return (st && st.attributes && st.attributes.friendly_name) || id;
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

  // ---------- actions ----------
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
  _delLight(i, k) {
    this._sections[i].lumieres.splice(k, 1);
    this._render();
  }
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
  async _save() {
    this._saving = true; this._msg = ""; this._render();
    try {
      const payload = this._sections.map((s) => ({
        nom: s.nom.trim() || "SECTION",
        lumieres: s.lumieres.map((l) => {
          const o = { entity: l.entity };
          if (l.nom) o.nom = l.nom;
          if (l.icone) o.icone = l.icone;
          if (l.couleur) o.couleur = l.couleur;
          return o;
        }),
      }));
      const r = await this._hass.callWS({ type: "maison_nspanel/set_sections", sections: payload });
      this._sections = r.sections;
      this._saved = JSON.stringify(this._sections);
      this._msg = "ok";
    } catch (e) {
      this._msg = "Erreur : " + (e && e.message ? e.message : e);
    }
    this._saving = false;
    this._render();
  }

  // ---------- rendu ----------
  _esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
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
    const items = this._available().filter((e) => !this._pick || e.id.toLowerCase().includes(this._pick.toLowerCase()) || e.name.toLowerCase().includes(this._pick.toLowerCase())).slice(0, 40);
    return `<div class="picker">
      <input class="pick-search" data-sec="${i}" placeholder="Rechercher une lumière…" value="${this._esc(this._pick)}" />
      <div class="pick-list">${items.length ? items.map((e) => `<button class="pick-item" data-act="padd" data-sec="${i}" data-id="${this._esc(e.id)}"><b>${this._esc(e.name)}</b><small>${this._esc(e.id)}</small></button>`).join("") : `<div class="empty">Aucune entité disponible</div>`}</div>
    </div>`;
  }

  _render() {
    if (!this._hass || !this._sections) return;
    const dirty = this._dirty;
    const avail = this._available();
    const secs = this._sections.map((s, i) => `
      <section class="card" draggable="false" data-sec="${i}">
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

    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;background:var(--primary-background-color);color:var(--primary-text-color);min-height:100vh;font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
        *{box-sizing:border-box}
        .bar{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--app-header-background-color,var(--primary-color));color:var(--app-header-text-color,#fff)}
        .bar h1{font-size:20px;font-weight:500;margin:0;flex:1}
        .menu{background:none;border:0;color:inherit;font-size:24px;cursor:pointer;display:none}
        .save{background:#fff;color:var(--primary-color);border:0;border-radius:18px;padding:8px 18px;font-weight:600;cursor:pointer}
        .save[disabled]{opacity:.45;cursor:default}
        .status{font-size:13px;opacity:.9}
        .wrap{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;padding:16px;max-width:1100px;margin:0 auto}
        @media(max-width:800px){.wrap{grid-template-columns:1fr}.menu{display:block}}
        .hint{grid-column:1/-1;background:var(--card-background-color);border-left:4px solid var(--primary-color);border-radius:8px;padding:10px 14px;font-size:14px;color:var(--secondary-text-color)}
        .card,.poolbox{background:var(--card-background-color);border-radius:12px;padding:12px;margin-bottom:14px;box-shadow:var(--ha-card-box-shadow,0 1px 3px rgba(0,0,0,.2))}
        .sec-head{display:flex;align-items:center;gap:6px;cursor:grab;margin-bottom:8px}
        .sec-name{flex:1;font-size:16px;font-weight:600;letter-spacing:.5px;background:transparent;color:inherit;border:1px solid transparent;border-radius:6px;padding:6px 8px;min-width:0}
        .sec-name:hover,.sec-name:focus{border-color:var(--divider-color);outline:none}
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
        .pick-search,.pool-search{width:100%;padding:8px;border-radius:6px;border:1px solid var(--divider-color);background:var(--primary-background-color);color:inherit;margin-bottom:6px}
        .pick-list{max-height:220px;overflow:auto}
        .pick-item{display:flex;flex-direction:column;align-items:flex-start;width:100%;text-align:left;background:none;border:0;color:inherit;padding:7px 8px;border-radius:6px;cursor:pointer}
        .pick-item:hover{background:var(--secondary-background-color)}
        .poolbox h2{font-size:15px;margin:0 0 4px} .poolbox p{margin:0 0 8px;font-size:12px;color:var(--secondary-text-color)}
        .chip{display:flex;align-items:center;gap:4px;padding:6px;border-radius:8px;background:var(--secondary-background-color);margin:4px 0;cursor:grab}
        .chip div{display:flex;flex-direction:column;min-width:0} .chip b{font-size:13px;font-weight:500}
        .side{position:sticky;top:72px;align-self:start}
        .ok{color:#86efac}.err{color:#fecaca}
      </style>
      <div class="bar">
        <button class="menu" data-act="menu">☰</button>
        <h1>Éclairage du NSPanel</h1>
        <span class="status ${this._msg === "ok" ? "ok" : this._msg ? "err" : ""}">${this._saving ? "Enregistrement…" : this._msg === "ok" ? "✓ Enregistré – dashboard actualisé (rechargez la page du panneau si besoin)" : this._esc(this._msg)}</span>
        <button class="save" data-act="save" ${dirty && !this._saving ? "" : "disabled"}>Enregistrer</button>
      </div>
      <div class="wrap">
        <div class="hint">Glissez les sections et les lumières pour les réordonner (ou utilisez ▲ ▼). Cliquez sur un nom pour le changer ; laissez-le vide pour garder le nom de l'entité. N'oubliez pas d'enregistrer.</div>
        <div class="main">
          ${secs}
          <button class="newsec" data-act="snew">+ Nouvelle section</button>
        </div>
        <aside class="side">
          <div class="poolbox" data-pool-drop="1">
            <h2>Lumières disponibles (${avail.length})</h2>
            <p>Glissez-les vers une section. Déposez ici une lumière pour la retirer.</p>
            <input class="pool-search" placeholder="Rechercher…" value="${this._esc(this._search)}" />
            ${pool || `<div class="empty">Tout est déjà placé</div>`}
          </div>
        </aside>
      </div>`;
    this._bind();
  }

  _bind() {
    const r = this.shadowRoot;
    r.querySelectorAll("[data-act]").forEach((el) => {
      el.addEventListener("click", () => {
        const a = el.dataset.act, i = +el.dataset.sec, k = +el.dataset.k;
        if (a === "save") this._save();
        else if (a === "snew") this._addSection();
        else if (a === "sdel") this._delSection(i);
        else if (a === "sup") this._moveSection(i, -1);
        else if (a === "sdown") this._moveSection(i, 1);
        else if (a === "ldel") this._delLight(i, k);
        else if (a === "lup") this._moveLight(i, k, -1);
        else if (a === "ldown") this._moveLight(i, k, 1);
        else if (a === "open") { this._open = this._open === i ? null : i; this._pick = ""; this._render(); }
        else if (a === "padd") this._addLight(i, el.dataset.id);
        else if (a === "menu") this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
      });
    });
    r.querySelectorAll(".sec-name").forEach((el) => el.addEventListener("input", () => { this._sections[+el.dataset.sec].nom = el.value; this._updateSave(); }));
    r.querySelectorAll(".l-name").forEach((el) => el.addEventListener("input", () => {
      const l = this._sections[+el.dataset.sec].lumieres[+el.dataset.k];
      if (el.value.trim()) l.nom = el.value; else delete l.nom;
      this._updateSave();
    }));
    const ps = r.querySelector(".pool-search");
    if (ps) ps.addEventListener("input", () => { this._search = ps.value; this._render(); const n = this.shadowRoot.querySelector(".pool-search"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); });
    const pk = r.querySelector(".pick-search");
    if (pk) { pk.addEventListener("input", () => { this._pick = pk.value; this._render(); const n = this.shadowRoot.querySelector(".pick-search"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }); }

    // --- glisser-déposer ---
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
    r.querySelectorAll(".card").forEach((el) => {
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
