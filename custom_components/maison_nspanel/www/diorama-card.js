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
ha-card { background:var(--diorama-bg,#121416); overflow:hidden; border:none; box-shadow:none; }
.stage { position:relative; width:100%; aspect-ratio:1/1; overflow:hidden; background:var(--diorama-bg,#121416); --s:480px;
  -webkit-mask-image:linear-gradient(to bottom, transparent 0, #000 12%, #000 88%, transparent 100%);
          mask-image:linear-gradient(to bottom, transparent 0, #000 12%, #000 88%, transparent 100%); }
img.fond { position:absolute; inset:0; width:100%; height:100%; display:block; opacity:0; transition:opacity .8s ease, filter .8s ease; }
img.fond.show { opacity:1; }
svg, .layer { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }
#volets { opacity:0; transition:opacity .8s ease; }
#volets.on { opacity:1; }
.cloud { position:absolute; opacity:0; transition:opacity 1.4s ease; will-change:transform; background:center / 100% 100% no-repeat;
  /* le nuage est coupé en haut de l'image : on fond son bord supérieur dans le ciel */
  -webkit-mask-image:linear-gradient(to bottom, transparent 0, rgba(0,0,0,.6) 10%, #000 26%); mask-image:linear-gradient(to bottom, transparent 0, rgba(0,0,0,.6) 10%, #000 26%); }
/* jour de pluie : le nuage de l'image fournie, tel quel (sans teinte), défile en boucle vers la droite.
   Deux copies côte à côte ; on glisse d'une largeur de carte puis on recommence : la boucle est invisible. */
#band { position:absolute; left:0; top:0; width:200%; height:27.246%; opacity:0; display:none; transition:opacity 1.4s ease; will-change:transform;
  background-repeat:repeat-x; background-size:50% 100%; background-position:left top; animation:bandmove 120s linear infinite; }
@keyframes bandmove { from{transform:translate3d(-50%,0,0)} to{transform:translate3d(0,0,0)} }
.c1 { left:28%;  top:3%;  width:68%; height:18.1%; animation:cdrift 70s ease-in-out infinite; }
.c2 { left:2%;   top:12%; width:56%; height:14.9%; animation:cdrift2 52s ease-in-out infinite; }
@keyframes cdrift  { 0%,100%{transform:translate3d(-4%,0,0)} 50%{transform:translate3d(4%,0,0)} }
@keyframes cdrift2 { 0%,100%{transform:translate3d(6%,0,0) scaleX(-1)} 50%{transform:translate3d(-6%,0,0) scaleX(-1)} }
.drop { position:absolute; top:-12%; width:max(1px,calc(var(--s)*.0022)); height:6%;
  background:linear-gradient(to bottom, rgba(200,220,245,0), rgba(200,220,245,.8));
  transform-origin:top; animation:fall linear infinite; will-change:transform; }
@keyframes fall { from{transform:translate3d(0,0,0) rotate(11deg)} to{transform:translate3d(calc(var(--s)*-.22),calc(var(--s)*1.25),0) rotate(11deg)} }
.flake { position:absolute; top:-4%; border-radius:50%; background:#fff; animation:snow linear infinite; will-change:transform; }
@keyframes snow { 0%{transform:translate3d(0,0,0)} 50%{transform:translate3d(calc(var(--s)*.03),calc(var(--s)*.55),0)} 100%{transform:translate3d(calc(var(--s)*-.02),calc(var(--s)*1.1),0)} }
/* brouillard : voile bas et large (plus large que la carte, fondu en haut et en bas) -> aucun bord visible quand il dérive */
#fog { left:-30%; width:160%; opacity:0; transition:opacity 1.4s ease;
  -webkit-mask-image:linear-gradient(to bottom, transparent 0%, #000 28%, #000 80%, transparent 100%);
          mask-image:linear-gradient(to bottom, transparent 0%, #000 28%, #000 80%, transparent 100%); }
#fog::before, #fog::after { content:''; position:absolute; inset:0; will-change:transform; }
#fog::before { background:
    radial-gradient(34% 20% at 22% 66%, rgba(222,226,232,.55), rgba(222,226,232,0) 100%),
    radial-gradient(40% 22% at 58% 54%, rgba(222,226,232,.48), rgba(222,226,232,0) 100%),
    radial-gradient(36% 20% at 86% 72%, rgba(222,226,232,.50), rgba(222,226,232,0) 100%);
  animation:mist 52s ease-in-out infinite; }
#fog::after { background:
    linear-gradient(to bottom, rgba(222,226,232,0) 30%, rgba(222,226,232,.20) 55%, rgba(222,226,232,.26) 72%, rgba(222,226,232,0) 100%),
    radial-gradient(44% 18% at 40% 78%, rgba(222,226,232,.40), rgba(222,226,232,0) 100%),
    radial-gradient(30% 18% at 76% 44%, rgba(222,226,232,.36), rgba(222,226,232,0) 100%);
  animation:mist 70s ease-in-out infinite reverse; }
@keyframes mist { 0%,100%{transform:translate3d(-6%,0,0)} 50%{transform:translate3d(6%,0,0)} }
/* foudre : un éclair zigzagant (SVG) avec une lueur bleutée locale, à un endroit différent à chaque coup */
#bolt { opacity:0; pointer-events:none; }
#bolt.on { animation:bolt 9s linear infinite; }
#bolt svg { position:absolute; inset:0; width:100%; height:100%; overflow:visible; }
#bolt .gl { fill:none; stroke:#7aa8ff; stroke-width:7; stroke-linejoin:round; stroke-linecap:round; filter:blur(3px); opacity:.85; }
#bolt .co { fill:none; stroke:#f4f8ff; stroke-width:1.9; stroke-linejoin:round; stroke-linecap:round; vector-effect:non-scaling-stroke; }
#bolt .br { fill:none; stroke:#dce8ff; stroke-width:1.1; stroke-linejoin:round; stroke-linecap:round; vector-effect:non-scaling-stroke; }
#glow { position:absolute; inset:0; mix-blend-mode:screen; background:radial-gradient(60% 55% at var(--bx,50%) 22%, rgba(120,160,255,.30), rgba(120,160,255,0) 70%); }
@keyframes bolt { 0%,70%,100%{opacity:0} 71%{opacity:1} 72.5%{opacity:.25} 74%{opacity:.95} 75.5%{opacity:.3} 78%{opacity:.7} 84%{opacity:0} }
/* page cachée : pas d'animation inutile */
:host(.pause) .drop, :host(.pause) .flake, :host(.pause) .cloud, :host(.pause) #band, :host(.pause) #fog::before, :host(.pause) #fog::after, :host(.pause) #bolt.on { animation-play-state:paused !important; }
@media (prefers-reduced-motion:reduce){ .drop,.flake,.cloud,#band,#fog::before,#fog::after,#bolt.on{ animation:none !important; } }
`;

// Nuage : une masse de nuages détourée (image avec transparence), teintée selon l'ambiance (multiplication + éclaircie), mise en cache
const _teintes = {};
function nuageTeinte(url, mul, lift) {
  const key = url + '|' + mul + '|' + lift;
  if (!_teintes[key]) _teintes[key] = new Promise((ok) => {
    const im = new Image();
    im.onload = () => {
      const cv = document.createElement('canvas'); cv.width = im.naturalWidth; cv.height = im.naturalHeight;
      const g = cv.getContext('2d'); g.drawImage(im, 0, 0);
      g.globalCompositeOperation = 'multiply'; g.fillStyle = `rgb(${mul})`; g.fillRect(0, 0, cv.width, cv.height);
      if (lift) { g.globalCompositeOperation = 'screen'; g.fillStyle = `rgba(255,255,255,${lift})`; g.fillRect(0, 0, cv.width, cv.height); }
      g.globalCompositeOperation = 'destination-in'; g.drawImage(im, 0, 0);
      ok(cv.toDataURL('image/png'));
    };
    im.onerror = () => ok(url);
    im.src = url;
  });
  return _teintes[key];
}

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
        <img class="fond" id="fa" decoding="async" alt="Diorama de la maison"><img class="fond" id="fb" decoding="async" alt="">
        <svg id="volets" viewBox="0 0 1024 1024" preserveAspectRatio="none"></svg>
        <div class="layer" id="clouds"><div class="cloud c1"></div><div class="cloud c2"></div><div id="band"></div></div>
        <div class="layer" id="fog"></div><div class="layer" id="fx"></div><div class="layer" id="bolt"><div id="glow"></div><svg viewBox="0 0 100 100" preserveAspectRatio="none"><path class="gl"/><path class="co"/><path class="br"/></svg></div>
      </div></ha-card>`;
    const $ = (id) => this._root.getElementById(id);
    this._stage = this._root.querySelector('.stage');
    this._fa = $('fa'); this._fb = $('fb'); this._front = null;
    this._svg = $('volets'); this._fx = $('fx'); this._fog = $('fog'); this._bolt = $('bolt');
    this._bolt.addEventListener('animationiteration', () => this._strike());
    this._clouds = [...this._root.querySelectorAll('.cloud')];
    this._band = this._root.querySelector('#band');
    this._w = 0;
    const ro = new ResizeObserver(() => {
      const w = this._stage.clientWidth; if (w === this._w) return;
      if (!w) { this._w = 0; return; }
      const before = this._lite(), was = this._w; this._w = w;
      this._stage.style.setProperty('--s', w + 'px');
      if (!was || before !== this._lite()) { this._key = null; this._update(); }
    });
    ro.observe(this._stage);
    // onglet ou écran en veille : on met les animations en pause (économie de batterie et de processeur)
    document.addEventListener('visibilitychange', this._vis = () => this._root.host.classList.toggle('pause', document.hidden));
  }
  disconnectedCallback() { if (this._vis) document.removeEventListener('visibilitychange', this._vis); }

  // réglages choisis dans Maison NSPanel > Apparence > NSPanel-Beta (attribut « beta » du capteur de rappels)
  _beta() { const r = this._hass && this._hass.states['sensor.maison_nspanel_rappels']; return (r && r.attributes && r.attributes.beta) || {}; }
  _lite() {
    const e = this._beta().effets, l = e === 'reduits' ? true : (e === 'complets' ? false : this._c.lite);
    return l === 'auto' ? (this._w > 0 && this._w <= 520) : !!l;
  }
  _state(id) { const s = id && this._hass && this._hass.states[id]; return s ? s.state : null; }

  _resolve() {
    const c = this._c;
    const b = this._beta();
    let moment = this._state(c.sun_entity) === 'below_horizon' ? 'nuit' : 'jour';
    const mo = this._state(c.moment_override);
    if (mo === 'jour' || mo === 'nuit') moment = mo;
    if (b.moment === 'jour' || b.moment === 'nuit') moment = b.moment;   // test depuis les réglages
    const sx = this._hass.states[WX_SENSOR];
    const wx = c.weather_entity || (sx && sx.attributes && sx.attributes.weather_entity) || 'weather.forecast_maison';
    let meteo = METEO[this._state(wx)] || 'clair';
    const wo = this._state(c.weather_override);
    if (AMBIANCES.includes(wo)) meteo = wo;
    if (AMBIANCES.includes(b.meteo)) meteo = b.meteo;                       // test depuis les réglages
    const shut = { nuit: 'night', jamais: 'never', toujours: 'always' }[b.volets] || c.shutters;
    let volets;
    if (shut === 'night') volets = moment === 'nuit';
    else if (shut === 'never') volets = false;
    else if (shut === 'always') volets = true;
    else { const s = this._state(shut); volets = ['closed', 'closing', 'on'].includes(s); }
    return { moment, meteo, volets, lite: this._lite(), fx: b.effets !== 'aucun' };
  }

  _update() {
    if (!this._root || !this._hass || !this._c) return;
    // carte masquée (largeur nulle) : on ne crée ni images ni animations
    if (!this._stage.clientWidth) { this._key = null; return; }
    const st = this._resolve();
    const key = JSON.stringify(st);
    if (key === this._key) return;     // rien n'a changé : on ne touche pas aux animations
    this._key = key;
    const { moment, meteo, volets, lite, fx } = st, night = moment === 'nuit';
    const fxm = fx ? meteo : 'clair';   // effets (nuages, brouillard, éclairs, pluie, neige) coupés : le décor reste
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
      neige: 'none', brouillard: 'brightness(.95) saturate(.75)' }[meteo];
    this._fa.style.filter = this._fb.style.filter = filter;

    // nuages, brouillard, éclairs
    // éclaircies : un seul voile léger ; temps couvert, pluie, orage, neige : deux couches de nuages
    const jourPluie = !night && fxm === 'pluie';   // image « jour de pluie » : son propre nuage défilant, pas les calques génériques
    const vis = jourPluie ? [] : { clair: [], eclaircies: [1], nuageux: [0, 1], pluie: [0, 1], averse: [0, 1], orage: [0, 1], neige: [0, 1], brouillard: [] }[fxm] || [];
    if (jourPluie) {
      this._band.style.backgroundImage = `url(${this._c.path}nuage_pluie_jour.webp?v=${encodeURIComponent(this._c.version)})`;
      this._band.style.display = 'block'; requestAnimationFrame(() => { this._band.style.opacity = 1; });
    } else { this._band.style.opacity = 0; this._band.style.display = 'none'; }
    const [mul, lift] = night
      ? (fxm === 'orage' || fxm === 'averse' ? ['70,76,96', 0] : (fxm === 'pluie' ? ['110,120,146', 0] : ['150,162,190', .08]))
      : (fxm === 'orage' ? ['150,156,172', 0] : (fxm === 'averse' ? ['196,202,214', 0] : (fxm === 'pluie' ? ['232,238,248', .04]
        : (fxm === 'neige' ? ['244,248,255', .45] : (fxm === 'eclaircies' ? ['245,248,255', .38] : ['250,252,255', .3])))));
    const gen = this._gen = (this._gen || 0) + 1;
    this._clouds.forEach((c, i) => {
      c.style.opacity = vis.includes(i) ? (i === 1 ? .78 : .94) : 0;
      if (vis.includes(i)) nuageTeinte(`${this._c.path}nuage.webp`, mul, lift).then((u) => { if (gen === this._gen) c.style.backgroundImage = `url(${u})`; });
    });
    this._fog.style.opacity = fxm === 'brouillard' ? (night ? .7 : 1) : 0;
    this._bolt.classList.toggle('on', fxm === 'orage');
    if (fxm === 'orage') this._strike();

    this._particles(fxm, lite);
    this._shutters(night, sol, volets);
  }

  // trace un nouvel éclair : départ en haut, zigzag vers le bas, une ou deux branches ; durée du cycle variable
  _strike() {
    const r = (a, b) => a + Math.random() * (b - a);
    const left = Math.random() < .5, x0 = left ? r(10, 40) : r(60, 90);
    let x = x0, y = -2; const pts = [[x, y]], endY = r(24, 38);   // reste dans le ciel : l'éclair touche au plus le toit
    while (y < endY) { y += r(4, 7); x += r(-5, 5); pts.push([x, y]); }
    const d = (a) => 'M' + a.map((p) => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' L');
    const brs = [];
    for (let k = 0; k < 2; k++) {
      const at = pts[Math.floor(r(2, pts.length - 2))], dir = Math.random() < .5 ? -1 : 1, b = [at];
      let bx = at[0], by = at[1];
      for (let n = 0; n < 3; n++) { bx += dir * r(3, 8); by += r(4, 8); b.push([bx, by]); }
      brs.push(d(b));
    }
    const [gl, co, br] = this._bolt.querySelectorAll('path');
    gl.setAttribute('d', d(pts)); co.setAttribute('d', d(pts)); br.setAttribute('d', brs.join(' '));
    this._bolt.style.setProperty('--bx', x0.toFixed(0) + '%');
    this._bolt.querySelector('#glow').style.setProperty('--bx', x0.toFixed(0) + '%');
    this._bolt.style.animationDuration = r(6, 12).toFixed(1) + 's';
  }

  _particles(meteo, lite) {
    const fx = this._fx, r = (a, b) => a + Math.random() * (b - a), k = lite ? .4 : 1;
    fx.textContent = '';
    const n = { pluie: 90, averse: 110, orage: 95, neige: 64 }[meteo];
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
