/* Maison NSPanel — couche « Apple Design » (style Apple Design uniquement).
 *
 * Principes appliqués (WWDC « Designing Fluid Interfaces », « Principles of Great Design ») :
 *  - Réponse : le retour visuel démarre à l'appui (:active), pas au relâchement ; retour doux (courbe .22,1,.36,1).
 *  - Aucune animation d'entrée ni transformation géométrique : elles faisaient clignoter les pages et décalaient la zone d'appui.
 *  - Matières : les tuiles sont des plaques translucides (backdrop-filter) avec un bord supérieur lumineux ;
 *    jamais de matière claire empilée sur une autre.
 *  - Typographie : police système, interlettrage adapté à la taille, casse « phrase » plutôt que capitales.
 *  - Accessibilité : prefers-reduced-motion (fondu seul), prefers-reduced-transparency (matière pleine),
 *    prefers-contrast (bordure marquée).
 * Les cartes sont dans des shadow roots : la feuille de style est injectée dans chaque <button-card>.
 */
(() => {
  if (window.__maisonAppleLayer) return;
  window.__maisonAppleLayer = true;
  const SENSOR = 'sensor.maison_nspanel_rappels';

  const CSS = `
:host(.ap-tile) ha-card {
  background: linear-gradient(180deg, rgba(255,255,255,.10), rgba(255,255,255,.02) 55%), rgba(18,24,34,.46) !important;
  -webkit-backdrop-filter: blur(24px) saturate(175%); backdrop-filter: blur(24px) saturate(175%);
  border-top-color: rgba(255,255,255,.26) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.14), 0 8px 24px rgba(0,0,0,.26) !important;
  transition: filter .38s cubic-bezier(.22,1,.36,1), border-color .3s ease !important;
  touch-action: manipulation;                         /* pas de zoom au double appui : un appui = un clic */
}
:host(.ap-tile:not(.ap-glass)) ha-card {
  background: rgba(26,32,44,.94) !important; -webkit-backdrop-filter: none; backdrop-filter: none;
}
:host(.ap-tile) ha-card:active { filter: brightness(.82); opacity: 1 !important; transition-duration: .06s !important; }
:host(.ap-tile) #name, :host(.ap-tile) #label, :host(.ap-tile) #state {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', Roboto, system-ui, sans-serif !important;
}
:host(.ap-tile) #name { text-transform: none !important; letter-spacing: -.012em !important; font-weight: 700 !important; font-size: 13px !important; }
:host(.ap-tile) #label { letter-spacing: .005em !important; }
@media (prefers-reduced-motion: reduce) {
  :host(.ap-tile) ha-card { transition: none !important; }
}
@media (prefers-reduced-transparency: reduce) {
  :host(.ap-tile) ha-card { background: rgb(26,32,44) !important; -webkit-backdrop-filter: none; backdrop-filter: none; }
}
@media (prefers-contrast: more) {
  :host(.ap-tile) ha-card { border: 1px solid rgba(255,255,255,.6) !important; }
}`;

  let sheet = null;
  try { sheet = new CSSStyleSheet(); sheet.replaceSync(CSS); } catch (e) { sheet = null; }
  if (!sheet) return;                                    // navigateur sans feuilles constructibles : on reste sur le style de base

  const hass = () => { const h = document.querySelector('home-assistant'); return h && h.hass; };
  const conf = () => {
    const h = hass(), s = h && h.states[SENSOR];
    const a = (s && s.attributes) || {};
    return { apple: a.style === 'apple', glass: !(a.beta && a.beta.materiaux === false) };
  };

  function eachCard(root, fn) {
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) {
        if (el.localName === 'button-card') fn(el);
        eachCard(el.shadowRoot, fn);
      }
    }
  }

  function scan() {
    const { apple, glass } = conf();
    eachCard(document, (host) => {
      const sr = host.shadowRoot, has = sr.adoptedStyleSheets.includes(sheet);
      if (!apple) {
        if (has) { sr.adoptedStyleSheets = sr.adoptedStyleSheets.filter((x) => x !== sheet); host.classList.remove('ap-tile', 'ap-glass'); host.__apDone = false; }
        return;
      }
      if (!has) sr.adoptedStyleSheets = [...sr.adoptedStyleSheets, sheet];
      // une « tuile » est une carte qui ne remplit pas l'écran (la carte d'accueil, plein écran, reste telle quelle) ;
      // décidé une seule fois par carte, pour ne jamais rebasculer pendant une navigation
      if (host.__apDone !== true) {
        const r = host.getBoundingClientRect();
        if (r.height > 0) { host.__apDone = true; if (r.height < window.innerHeight * 0.5) host.classList.add('ap-tile'); }
      }
      host.classList.toggle('ap-glass', glass);
    });
  }

  let timer = null;
  const later = (ms = 150) => { clearTimeout(timer); timer = setTimeout(scan, ms); };
  // nouvelles cartes : à chaque navigation, puis quelques passes rapprochées, puis une passe lente de rattrapage
  window.addEventListener('location-changed', () => { later(200); [800, 1800, 3500].forEach((m) => setTimeout(scan, m)); });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) later(); });
  let last = '';
  setInterval(() => {                                   // changement de style ou de réglage : appliqué sans recharger
    const c = conf(), k = c.apple + '|' + c.glass;
    if (k !== last) { last = k; later(50); [600, 1500].forEach((m) => setTimeout(scan, m)); }
  }, 8000);
  [600, 1500, 3000, 6000].forEach((m) => setTimeout(scan, m));
})();
