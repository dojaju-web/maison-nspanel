/* Diorama maison — carte Lovelace
 * Fond (jour/nuit x sec/mouillé/neige) + calques animés (météo, volets).
 * Ressource : /local/diorama/diorama-card.js (module JavaScript)
 */
const VERSION = '1.0.0';
const WX_SENSOR = 'sensor.maison_nspanel_previsions';   // fournit l'entité météo choisie dans Maison NSPanel

// état météo Home Assistant -> ambiance du diorama
const METEO = {
  'sunny': 'clair', 'clear-night': 'clair', 'windy': 'clair',
  'partlycloudy': 'eclaircies', 'cloudy': 'nuageux', 'windy-variant': 'nuageux',
  'fog': 'brouillard',
  'rainy': 'pluie', 'snowy-rainy': 'pluie', 'pouring': 'averse', 'hail': 'averse',
  'lightning': 'orage', 'lightning-rainy': 'orage',
  'snowy': 'neige', 'exceptional': 'nuageux',
};
const AMBIANCES = ['clair', 'eclaircies', 'nuageux', 'pluie', 'averse', 'orage', 'neige', 'brouillard'];

// fenêtres, en pixels du master 1024x1024 : haut-gauche, haut-droit, puis le contour
const FENETRES = [
  { p: [[324,401],[349,409],[349,447],[324,439]] },                         // jardin, étage gauche
  { p: [[415,436],[440,444],[440,492],[426,489],[426,499],[415,496]] },     // jardin, étage (haute)
  { p: [[414,540],[439,547],[439,590],[414,584]] },                         // jardin, rez-de-chaussée
  { p: [[610,481],[640,472],[640,546],[610,555]], rail: [517,508] },        // pignon, gauche
  { p: [[687,449],[727,438],[727,502],[687,514]], rail: [479,468] },        // pignon, milieu
  { p: [[758,422],[792,412],[792,452],[758,461]] },                         // pignon, droite
];

const CSS = `
:host { display:block; }
ha-card { background:var(--diorama-bg,#131415); overflow:hidden; border:none; box-shadow:none; }
.stage { position:relative; width:100%; aspect-ratio:1/1; overflow:hidden; background:var(--diorama-bg,#131415); --s:480px; }
img.fond { position:absolute; inset:0; width:100%; height:100%; display:block; opacity:0; transition:opacity .8s ease, filter .8s ease; }
img.fond.show { opacity:1; }
svg, .layer { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }
#volets { opacity:0; transition:opacity .8s ease; }
#volets.on { opacity:1; }
.cloud { position:absolute; border-radius:50%; filter:blur(calc(var(--s)*.03)); opacity:0; transition:opacity 1.2s ease; will-change:transform; }
.c1 { left:-10%; top:6%;  width:62%; height:16%; animation:drift 46s linear infinite; }
.c2 { left:30%;  top:14%; width:70%; height:15%; animation:drift 64s linear infinite reverse; }
.c3 { left:8%;   top:1%;  width:50%; height:12%; animation:drift 80s linear infinite; }
@keyframes drift { 0%{transform:translate3d(-8%,0,0)} 50%{transform:translate3d(10%,0,0)} 100%{transform:translate3d(-8%,0,0)} }
.drop { position:absolute; top:-12%; width:max(1px,calc(var(--s)*.0022)); height:6%;
  background:linear-gradient(to bottom, rgba(200,220,245,0), rgba(200,220,245,.8));
  transform-origin:top; animation:fall linear infinite; will-change:transform; }
@keyframes fall { from{transform:translate3d(0,0,0) rotate(11deg)} to{transform:translate3d(calc(var(--s)*-.22),calc(var(--s)*1.25),0) rotate(11deg)} }
.flake { position:absolute; top:-4%; border-radius:50%; background:#fff; animation:snow linear infinite; will-change:transform; }
@keyframes snow { 0%{transform:translate3d(0,0,0)} 50%{transform:translate3d(calc(var(--s)*.03),calc(var(--s)*.55),0)} 100%{transform:translate3d(calc(var(--s)*-.02),calc(var(--s)*1.1),0)} }
#fog { opacity:0; transition:opacity 1.2s ease;
  background:
    radial-gradient(60% 22% at 30% 62%, rgba(215,220,226,.42), rgba(215,220,226,0) 70%),
    radial-gradient(70% 26% at 68% 48%, rgba(215,220,226,.38), rgba(215,220,226,0) 70%),
    radial-gradient(80% 30% at 50% 74%, rgba(215,220,226,.34), rgba(215,220,226,0) 72%);
  animation:drift 38s linear infinite; }
#flash { background:#dfe8ff; opacity:0; mix-blend-mode:screen; }
#flash.on { animation:flash 7s linear infinite; }
@keyframes flash { 0%,61%,100%{opacity:0} 62%{opacity:.55} 63%{opacity:.08} 64.5%{opacity:.42} 67%{opacity:0} }
@media (prefers-reduced-motion:reduce){ .drop,.flake,.cloud,#fog,#flash.on{ animation:none !important; } }
`;

class DioramaCard extends HTMLElement {
  setConfig(config) {
        this._c = Object.assign({
      weather_entity: null,       // vide : entité météo de Maison NSPanel (sinon weather.forecast_maison)
      path: '/maison_nspanel/meteo/diorama/',
      sun_entity: 'sun.sun',
      shutters: 'night',        // 'night' | 'never' | 'always' | un entity_id (cover, binary_sensor, input_boolean…)
      lite: 'auto',             // 'auto' (allégé si la carte fait 520 px ou moins) | true | false
      moment_override: null,    // input_select : auto / jour / nuit
      weather_override: null,   // input_select : auto / clair / nuageux / pluie …
      version: VERSION,         // changer la valeur pour forcer le rechargement des images
    }, config);
    if (!this._c.path.endsWith('/')) this._c.path += '/';
    this._key = null;
    if (this._root) this._update();
  }

  set hass(hass) { this._hass = hass; if (!this._root) this._build(); this._update(); }
  getCardSize() { return 8; }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }

  _build() {
    this._root = this.attachShadow({ mode: 'open' });
    this._root.innerHTML = `<style>${CSS}</style>
      <ha-card><div class="stage">
        <img class="fond" id="fa" alt="Diorama de la maison"><img class="fond" id="fb" alt="">
        <svg id="volets" viewBox="0 0 1024 1024" preserveAspectRatio="none"></svg>
        <div class="layer" id="clouds"><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div></div>
        <div class="layer" id="fog"></div><div class="layer" id="fx"></div><div class="layer" id="flash"></div>
      </div></ha-card>`;
    const $ = (id) => this._root.getElementById(id);
    this._stage = this._root.querySelector('.stage');
    this._fa = $('fa'); this._fb = $('fb'); this._front = null;
    this._svg = $('volets'); this._fx = $('fx'); this._fog = $('fog'); this._flash = $('flash');
    this._clouds = [...this._root.querySelectorAll('.cloud')];
    this._w = 0;
    const ro = new ResizeObserver(() => {
      const w = this._stage.clientWidth; if (w === this._w) return;
      if (!w) { this._w = 0; return; }
      const before = this._lite(), was = this._w; this._w = w;
      this._stage.style.setProperty('--s', w + 'px');
      if (!was || before !== this._lite()) { this._key = null; this._update(); }
    });
    ro.observe(this._stage);
  }

  _lite() { const l = this._c.lite; return l === 'auto' ? (this._w > 0 && this._w <= 520) : !!l; }
  _state(id) { const s = id && this._hass && this._hass.states[id]; return s ? s.state : null; }

  _resolve() {
    const c = this._c;
    let moment = this._state(c.sun_entity) === 'below_horizon' ? 'nuit' : 'jour';
    const mo = this._state(c.moment_override);
    if (mo === 'jour' || mo === 'nuit') moment = mo;
    const sx = this._hass.states[WX_SENSOR];
    const wx = c.weather_entity || (sx && sx.attributes && sx.attributes.weather_entity) || 'weather.forecast_maison';
    let meteo = METEO[this._state(wx)] || 'clair';
    const wo = this._state(c.weather_override);
    if (AMBIANCES.includes(wo)) meteo = wo;
    let volets;
    if (c.shutters === 'night') volets = moment === 'nuit';
    else if (c.shutters === 'never') volets = false;
    else if (c.shutters === 'always') volets = true;
    else { const s = this._state(c.shutters); volets = ['closed', 'closing', 'on'].includes(s); }
    return { moment, meteo, volets, lite: this._lite() };
  }

  _update() {
    if (!this._root || !this._hass || !this._c) return;
    // carte masquée (largeur nulle) : on ne crée ni images ni animations
    if (!this._stage.clientWidth) { this._key = null; return; }
    const st = this._resolve();
    const key = JSON.stringify(st);
    if (key === this._key) return;     // rien n'a changé : on ne touche pas aux animations
    this._key = key;
    const { moment, meteo, volets, lite } = st, night = moment === 'nuit';
    const wet = ['pluie', 'averse', 'orage'].includes(meteo);
    const sol = wet ? 'mouille' : (meteo === 'neige' ? 'neige' : 'sec');

    // fond, avec fondu
    const src = `${this._c.path}${moment}_${sol}.webp?v=${encodeURIComponent(this._c.version)}`;
    if (!this._front) { this._front = this._fa; this._fa.src = src; this._fa.classList.add('show'); }
    else if (this._front.getAttribute('src') !== src) {
      const back = this._front === this._fa ? this._fb : this._fa;
      back.src = src; back.classList.add('show'); this._front.classList.remove('show'); this._front = back;
    }
    const filter = { clair: 'none', eclaircies: 'brightness(.94) saturate(.92)', nuageux: 'brightness(.84) saturate(.78)',
      pluie: 'brightness(.96)', averse: 'brightness(.86)', orage: 'brightness(.78) saturate(.85)',
      neige: 'none', brouillard: 'brightness(.93) saturate(.7) contrast(.92)' }[meteo];
    this._fa.style.filter = this._fb.style.filter = filter;

    // nuages, brouillard, éclairs
    const op = { clair: 0, eclaircies: .28, nuageux: .5, pluie: .62, averse: .72, orage: .8, neige: .5, brouillard: .35 }[meteo];
    const dark = meteo === 'orage' || meteo === 'averse';
    const rgb = night ? (dark ? '20,24,34' : '70,82,104') : (dark ? '70,74,84' : (meteo === 'pluie' ? '150,156,166' : '214,218,224'));
    this._clouds.forEach((c) => { c.style.opacity = op;
      c.style.background = `radial-gradient(closest-side, rgba(${rgb},.95), rgba(${rgb},.55) 55%, rgba(${rgb},0) 100%)`; });
    this._fog.style.opacity = meteo === 'brouillard' ? (night ? .55 : .9) : 0;
    this._flash.classList.toggle('on', meteo === 'orage');

    this._particles(meteo, lite);
    this._shutters(night, sol, volets);
  }

  _particles(meteo, lite) {
    const fx = this._fx, r = (a, b) => a + Math.random() * (b - a), k = lite ? .4 : 1;
    fx.textContent = '';
    const n = { pluie: 70, averse: 110, orage: 95, neige: 64 }[meteo];
    if (!n) return;
    for (let i = 0; i < n * k; i++) {
      const d = document.createElement('div');
      if (meteo === 'neige') {
        const z = r(.5, 1.25); d.className = 'flake';
        d.style.width = d.style.height = `calc(var(--s)*${z / 100})`;
        d.style.left = r(0, 100) + '%';
        d.style.animationDuration = r(5, 10) / (z * .9) + 's';
        d.style.animationDelay = -r(0, 10) + 's';
        d.style.opacity = r(.55, .95);
      } else {
        d.className = 'drop';
        d.style.left = r(0, 125) + '%';
        d.style.animationDuration = r(.55, .95) * (meteo === 'pluie' ? 1 : .85) + 's';
        d.style.animationDelay = -r(0, 1) + 's';
        d.style.opacity = r(.45, 1);
      }
      fx.appendChild(d);
    }
  }

  _shutters(night, sol, closed) {
    const svg = this._svg, NS = 'http://www.w3.org/2000/svg';
    const el = (n, a) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); return e; };
    const pts = (a) => a.map((q) => q.join(',')).join(' ');
    svg.textContent = '';
    const fill = night ? ({ neige: '#8c9bb3', mouille: '#66727f' }[sol] || '#7686a0')
                       : ({ neige: '#d3d1cb', mouille: '#aeaca6' }[sol] || '#c6c4be');
    const slat = night ? 'rgba(10,16,28,.34)' : 'rgba(40,36,30,.26)';
    const box = night ? 'rgba(255,255,255,.10)' : 'rgba(255,255,255,.35)';
    const rail = night ? '#a3b0c4' : '#eeeeec';
    const defs = el('defs', {}); svg.appendChild(defs);
    FENETRES.forEach((w, i) => {
      const [xl, yl] = w.p[0], [xr, yr] = w.p[1];
      const cp = el('clipPath', { id: 'cp' + i }); cp.appendChild(el('polygon', { points: pts(w.p) })); defs.appendChild(cp);
      const g = el('g', { 'clip-path': `url(#cp${i})` });
      g.appendChild(el('polygon', { points: pts(w.p), fill }));
      const h = Math.max(...w.p.map((q) => q[1])) - Math.min(yl, yr);
      for (let t = 3.2; t < h + 6; t += 3.2) g.appendChild(el('line', { x1: xl, y1: yl + t, x2: xr, y2: yr + t, stroke: slat, 'stroke-width': .9 }));
      g.appendChild(el('polygon', { points: pts([[xl, yl], [xr, yr], [xr, yr + 4], [xl, yl + 4]]), fill: box }));
      svg.appendChild(g);
      svg.appendChild(el('polygon', { points: pts(w.p), fill: 'none', stroke: night ? 'rgba(0,0,0,.35)' : 'rgba(0,0,0,.22)', 'stroke-width': .8 }));
      if (w.rail) {   // garde-corps redessiné devant le volet
        const bl = w.p[3], br = w.p[2], r = el('g', { stroke: rail, 'stroke-width': .9, 'stroke-linecap': 'round' });
        r.appendChild(el('line', { x1: xl, y1: w.rail[0], x2: xr, y2: w.rail[1], 'stroke-width': 1.5 }));
        r.appendChild(el('line', { x1: bl[0], y1: bl[1] - 2, x2: br[0], y2: br[1] - 2, 'stroke-width': 1.2 }));
        for (let x = xl + 1.5; x < xr; x += 3.6) { const k = (x - xl) / (xr - xl);
          r.appendChild(el('line', { x1: x, y1: w.rail[0] + (w.rail[1] - w.rail[0]) * k, x2: x, y2: bl[1] - 2 + (br[1] - bl[1]) * k })); }
        svg.appendChild(r);
      }
    });
    svg.classList.toggle('on', closed);
  }
}

if (!customElements.get('diorama-card')) customElements.define('diorama-card', DioramaCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: 'diorama-card', name: 'Diorama maison', description: 'Diorama isométrique jour/nuit avec météo animée' });
