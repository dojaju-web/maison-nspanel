"""Génère le dashboard (maison_dashboard.yaml) à partir du modèle et des réglages.

Le modèle contient des repères (__SECTIONS__, __LIGHTS_JS__ …) remplacés par :
- les sections d'éclairage choisies dans Configurer,
- l'entité de climatisation choisie (préfixe d'entités Sensibo).
"""

from __future__ import annotations

import json
import re
from urllib.parse import quote
from pathlib import Path
from typing import Any

DEFAULT_CLIMATE = "climate.sejour_climatisation"
DEFAULT_PREFIX = "sejour_climatisation"  # préfixe commun aux entités Sensibo du modèle

FRAGMENTS = {
    "__VAC_NAV__": "aspirateur_nav.yaml",
    "__VAC_NAVB__": "aspirateur_navb.yaml",
    "__VAC_PAGE__": "aspirateur_page.yaml",
}
# Capteurs facultatifs de l'aspirateur : clé de réglage -> repère du modèle
VAC_SENSORS = {
    "vac_battery": "__VAC_BATTERY__",
    "vac_fan": "__VAC_FAN__",
    "vac_area": "__VAC_AREA__",
    "vac_time": "__VAC_TIME__",
    "vac_alert": "__VAC_ALERT__",
}

MENU_TABS = (
    ("accueil", "Accueil", "mdi:home"),
    ("lumieres", "Lumières", "mdi:lightbulb-group"),
    ("climat", "Climat", "mdi:air-conditioner"),
    ("aspirateur", "Aspirateur", "mdi:robot-vacuum"),
)
_STY = "states['sensor.maison_nspanel_rappels']"
_LIQ = f"({_STY} && {_STY}.attributes.style === 'liquid')"
# Reflets « Liquid Glass » : verre dépoli, bord clair et lueur interne
LG_BLUR = "blur(12px) saturate(1.6)"
LG_EDGE = "inset 0 1px 0 rgba(255,255,255,.14), 0 8px 24px rgba(0,0,0,.45)"
LG_ACCENT = "64,156,255"


def _lg_filter(scale: float = 0.12) -> str:
    """Filtre SVG de réfraction « verre liquide » (carte de déplacement : les bords courbent l'image).

    Les unités relatives à l'élément (objectBoundingBox) l'adaptent à toute taille de bulle.
    Utilisé par backdrop-filter: url(#lg-refract) ; sans WebGL ni capture du DOM.
    """
    def grad(i, x2, y2, c):
        return (
            f'<linearGradient id="{i}" x1="0" x2="{x2}" y1="0" y2="{y2}">'
            f'<stop offset="0" stop-color="rgb({c[0]})"/><stop offset="{c[3]}" stop-color="rgb({c[1]})"/>'
            f'<stop offset="{1 - float(c[3]):.2f}" stop-color="rgb({c[1]})"/><stop offset="1" stop-color="rgb({c[2]})"/></linearGradient>'
        )

    m = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100" viewBox="0 0 400 100" preserveAspectRatio="none"><defs>'
        + grad("r", 1, 0, ("255,0,0", "128,0,0", "0,0,0", ".12"))
        + grad("g", 0, 1, ("0,255,0", "0,128,0", "0,0,0", ".32"))
        + '</defs><rect width="400" height="100" fill="rgb(0,0,0)"/>'
        '<rect width="400" height="100" fill="url(#r)"/>'
        '<rect width="400" height="100" fill="url(#g)" style="mix-blend-mode:screen"/></svg>'
    )
    uri = "data:image/svg+xml," + quote(m)
    return (
        '<svg width="0" height="0" style="position:absolute;overflow:hidden" aria-hidden="true">'
        '<filter id="lg-refract" primitiveUnits="objectBoundingBox" x="0" y="0" width="1" height="1" '
        'color-interpolation-filters="sRGB">'
        f'<feImage href="{uri}" x="0" y="0" width="1" height="1" preserveAspectRatio="none" result="map"/>'
        f'<feDisplacementMap in="SourceGraphic" in2="map" scale="{scale}" xChannelSelector="R" yChannelSelector="G"/>'
        "</filter></svg>"
    )



_WX = "(states['sensor.maison_nspanel_previsions'] && states['sensor.maison_nspanel_previsions'].attributes.weather_entity) || 'weather.forecast_maison'"


def _tab_color(path: str, vacuum: str | None) -> str:
    """Expression JS : couleur « R,V,B » de l'état de l'élément, ou null s'il est inactif."""
    if path == "accueil":
        return "'0,145,255'"
    if path == "lumieres":
        return "([__LIGHTS_JS__].some(i => states[i] && states[i].state === 'on') ? '255,214,0' : null)"
    if path == "climat":
        return ("((states['climate.sejour_climatisation'] && ({cool:'60,211,254',heat:'255,146,48',dry:'0,218,195',"
                "fan_only:'142,142,147',heat_cool:'48,209,88',auto:'48,209,88'})[states['climate.sejour_climatisation'].state]) || null)")
    if path == "aspirateur":
        return (f"((states['{vacuum}'] && ({{cleaning:'60,211,254',returning:'109,124,255',paused:'255,214,0',"
                f"error:'255,66,69'}})[states['{vacuum}'].state]) || null)")
    return (f"((states[{_WX}] && ({{sunny:'251,191,36',partlycloudy:'251,191,36',rainy:'96,165,250',pouring:'96,165,250',"
            "lightning:'96,165,250','lightning-rainy':'96,165,250',snowy:'125,211,252'})[states[" + _WX + "].state]) ? "
            "({sunny:'251,191,36',partlycloudy:'251,191,36',rainy:'96,165,250',pouring:'96,165,250',lightning:'96,165,250',"
            "'lightning-rainy':'96,165,250',snowy:'125,211,252'})[states[" + _WX + "].state] : null)")


def _tab_rgb(path: str, vacuum: str | None) -> str:
    return f"\"[[[ const r = {_tab_color(path, vacuum)}; return r ? 'rgb(' + r + ')' : 'rgb(255,255,255)' ]]]\""



def gen_menu(has_vacuum: bool, active: str = "accueil", vacuum: str | None = None) -> tuple[str, str]:
    """Menu flottant « Liquid Glass » (barre d'onglets iOS) pour l'accueil.

    Renvoie (champ personnalisé, style de zone), à l'indentation zéro. La barre flotte
    au-dessus du contenu (position absolue), n'apparaît que dans le thème Liquid Glass,
    et ne compte que des onglets de navigation à libellé court (aucun n'est masqué).
    """
    tabs = [t for t in MENU_TABS if has_vacuum or t[0] != "aspirateur"]
    ids = [f"t{i}" for i in range(len(tabs))]
    out = [
        "menu:",
        "  card:",
        "    type: custom:button-card",
        "    show_icon: false",
        "    show_name: false",
        "    show_label: false",
        "    triggers_update: [sensor.maison_nspanel_rappels]",
        "    custom_fields:",
        f"      defs: '{_lg_filter()}'",
    ]
    for (path, name, icon), tid in zip(tabs, ids):
        on = path == active
        out += [
            f"      {tid}:",
            "        card:",
            "          type: custom:button-card",
            f"          icon: {icon}",
            "          show_icon: true",
            "          show_name: true",
            f"          name: {name}",
            "          tap_action:",
            "            action: navigate",
            f"            navigation_path: \"[[[ return '/' + window.location.pathname.split('/')[1] + '/{path}'; ]]]\"",
            "          styles:",
            "            grid:",
            "              - grid-template-areas: '\"i\" \"n\"'",
            "              - grid-template-rows: 30px auto",
            "              - justify-items: center",
            "              - align-content: center",
            "              - row-gap: 2px",
            "            card:",
            "              - height: 64px",
            "              - padding: 0",
            "              - border-radius: 32px",
            f"              - background: {'rgba(28,28,30,.85)' if on else 'transparent'}",
            f"              - border: {'1px solid rgba(255,255,255,.04)' if on else '1px solid transparent'}",
            f"              - box-shadow: {'inset 0 1px 3px rgba(0,0,0,.5)' if on else 'none'}",
            "            img_cell:",
            "              - width: 30px",
            "              - height: 30px",
            "              - margin: 0",
            "              - overflow: visible",
            "            icon:",
            "              - width: 30px",
            "              - height: 30px",
            f"              - color: {_tab_rgb(path, vacuum)}",
            "            name:",
            "              - font-family: \"'Inter','SF Pro Text','Segoe UI',Roboto,sans-serif\"",
            "              - font-size: 12px",
            "              - font-weight: 500",
            "              - letter-spacing: .1px",
            f"              - color: {_tab_rgb(path, vacuum)}",
            "              - white-space: nowrap",
        ]
    out += [
        "    styles:",
        "      grid:",
        f"        - grid-template-areas: '\"{' '.join(ids)}\"'",
        f"        - grid-template-columns: repeat({len(tabs)}, 1fr)",
        "        - column-gap: 2px",
        "        - align-items: stretch",
        "      card:",
        "        - padding: 4px",
        "        - border-radius: 38px",
        "        - background: linear-gradient(180deg, rgba(58,58,60,.74), rgba(44,44,46,.74))",
        f"        - backdrop-filter: {LG_BLUR}",
        f"        - -webkit-backdrop-filter: {LG_BLUR}",
        "        - backdrop-filter: url(#lg-refract) blur(12px) saturate(1.6)",
        "        - border: 1px solid rgba(255,255,255,.10)",
        f"        - box-shadow: {LG_EDGE}",
        "      custom_fields:",
    ]
    for tid in ids:
        out += [f"        {tid}:", "          - grid-area: " + tid, "          - width: 100%"]
    out += ["        defs:", "          - position: absolute", "          - width: 0", "          - height: 0"]
    style = [
        "menu:",
        "  - position: absolute",
        "  - left: 25px",
        "  - right: 25px",
        "  - bottom: 26px",
        "  - z-index: 5",
        f"  - display: \"[[[ return {_LIQ} ? 'block' : 'none' ]]]\"",
    ]
    return "\n".join(out) + "\n", "\n".join(style) + "\n"


FAN_TAP_SELECT = """tap_action:
  action: perform-action
  perform_action: select.select_next
  target:
    entity_id: {sel}
  data:
    cycle: true
"""
FAN_TAP_VACUUM = """tap_action:
  action: perform-action
  perform_action: vacuum.set_fan_speed
  target:
    entity_id: {vac}
  data:
    fan_speed: >
      [[[
        const list = entity.attributes.fan_speed_list || [];
        if (!list.length) return entity.attributes.fan_speed;
        const i = list.indexOf(entity.attributes.fan_speed);
        return list[(i + 1) % list.length];
      ]]]
"""

MODELE = "modele.yaml"
CIBLE = "maison_dashboard.yaml"

# Sections d'éclairage proposées au départ (modifiables dans Configurer)
DEFAULT_SECTIONS: list[dict[str, Any]] = [
    {
        "nom": "SÉJOUR",
        "lumieres": [
            {"entity": "switch.outlet_1", "nom": "Interrupteur Cuisine", "icone": "mdi:light-switch", "couleur": "45,212,191"},
            {"entity": "light.sejour_cuisine", "nom": "Lampe Cuisine", "icone": "mdi:ceiling-light"},
            {"entity": "light.sejour_mur_tv", "nom": "Mur TV", "icone": "mdi:ceiling-light"},
            {"entity": "light.sejour_mur_sdb", "nom": "Mur Salle de bain", "icone": "mdi:ceiling-light"},
        ],
    },
    {
        "nom": "JARDIN",
        "lumieres": [
            {"entity": "light.jardin_jardin", "nom": "Lampes Jardin", "icone": "mdi:outdoor-lamp", "couleur": "74,222,128"},
        ],
    },
]


def prefix_of(entity_id: str | None) -> str:
    """« climate.salon_clim » -> « salon_clim »."""
    if not entity_id or "." not in entity_id:
        return DEFAULT_PREFIX
    return entity_id.split(".", 1)[1]


def normalize_sections(sections: Any) -> list[dict[str, Any]]:
    """Nettoie la liste de sections ; None -> sections par défaut."""
    if sections is None:
        sections = DEFAULT_SECTIONS
    out = []
    for sec in sections:
        nom = str(sec.get("nom", "")).strip()
        lumieres = []
        seen = set()
        for lum in sec.get("lumieres", []):
            if isinstance(lum, str):
                lum = {"entity": lum}
            ent = str(lum.get("entity", "")).strip()
            if "." not in ent or ent in seen:
                continue
            seen.add(ent)
            lumieres.append({k: v for k, v in lum.items() if v not in (None, "")} | {"entity": ent})
        out.append({"nom": nom, "lumieres": lumieres})
    return out


def all_entities(sections: list[dict[str, Any]]) -> list[str]:
    """Toutes les entités des sections (sans doublon, ordre conservé)."""
    seen: dict[str, None] = {}
    for sec in sections:
        for lum in sec["lumieres"]:
            seen.setdefault(lum["entity"], None)
    return list(seen)


def light_entities(sections: list[dict[str, Any]]) -> list[str]:
    """Seulement les lumières (domaine light) : les interrupteurs ne sont pas comptés."""
    return [e for e in all_entities(sections) if e.startswith("light.")]


def _q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def gen_sections(sections: list[dict[str, Any]], indent: int = 10) -> str:
    """YAML des sections (titre + grille de tuiles) pour la page Éclairage."""
    pad = " " * indent
    out: list[str] = []
    for sec in sections:
        out += [
            f"{pad}- type: custom:button-card",
            f"{pad}  template: section_title",
            f"{pad}  variables:",
            f"{pad}    text: {_q(sec['nom'].upper())}",
            "",
        ]
        if not sec["lumieres"]:
            continue
        cols = 2 if len(sec["lumieres"]) > 1 else 1
        out += [f"{pad}- type: grid", f"{pad}  columns: {cols}", f"{pad}  square: false", f"{pad}  cards:"]
        for lum in sec["lumieres"]:
            out += [
                f"{pad}    - type: custom:button-card",
                f"{pad}      template: tile_light",
                f"{pad}      entity: {lum['entity']}",
            ]
            if lum.get("nom"):
                out.append(f"{pad}      name: {_q(str(lum['nom']))}")
            if lum.get("icone"):
                out.append(f"{pad}      icon: {_q(str(lum['icone']))}")
            if lum.get("couleur"):
                out += [f"{pad}      variables:", f"{pad}        rgb: {_q(str(lum['couleur']))}"]
        out.append("")
    return "\n".join(out).lstrip(" ").rstrip("\n")


def _inject(text: str, token: str, block: str) -> str:
    """Remplace la ligne du repère par le bloc, indenté comme le repère (ou la supprime)."""

    def repl(m: re.Match) -> str:
        if not block.strip():
            return ""
        pad = m.group("pad")
        return "\n".join(pad + ln if ln.strip() else ln for ln in block.rstrip("\n").split("\n")) + "\n"

    return re.sub(rf"^(?P<pad>[ ]*){re.escape(token)}[ ]*\n", repl, text, flags=re.M)


def render(
    text: str,
    climate_entity: str | None = None,
    sections: Any = None,
    vacuum: str | None = None,
    fragments: dict[str, str] | None = None,
    vac_cfg: dict[str, str] | None = None,
) -> str:
    """Remplace les repères du modèle, puis le préfixe d'entités de climatisation."""
    secs = normalize_sections(sections)
    lights = light_entities(secs)
    trig = all_entities(secs) or ["sun.sun"]
    if vacuum:
        cfg = vac_cfg or {}
        for token, block in (fragments or {}).items():
            text = _inject(text, token, block)
        fan = cfg.get("vac_fan")
        text = _inject(text, "__VAC_FAN_TAP__", FAN_TAP_SELECT.format(sel=fan) if fan else FAN_TAP_VACUUM.format(vac=vacuum))
        ids = [vacuum] + [cfg[k] for k in VAC_SENSORS if cfg.get(k)]
        text = text.replace("__VAC_TRIG__", ", ".join(json.dumps(e) for e in dict.fromkeys(ids)))
        for key, token in VAC_SENSORS.items():
            text = text.replace(token, str(cfg.get(key) or ""))
        text = text.replace("__VACUUM__", vacuum).replace("__NAVCOLS__", "3")
    else:
        for token in FRAGMENTS:
            text = _inject(text, token, "")
        text = text.replace("__NAVCOLS__", "2")
    field, style = gen_menu(bool(vacuum), vacuum=vacuum)
    text = _inject(text, "__MENU__", field)
    text = _inject(text, "__MENU_STYLE__", style)
    text = text.replace("__LG_DEFS__", _lg_filter())
    pages = ["lumieres", "climat", "previsions"] + (["aspirateur"] if vacuum else [])
    text = text.replace("__WARM_PAGES__", json.dumps(pages))
    text = text.replace("__SECTIONS__", gen_sections(secs))
    text = text.replace("__LIGHTS_IDS__", json.dumps(lights))
    text = text.replace("__LIGHTS_TRIG__", json.dumps(trig))
    text = text.replace("__LIGHTS_JSQ__", ", ".join(f"''{e}''" for e in lights))
    text = text.replace("__LIGHTS_JS__", ", ".join(f"'{e}'" for e in lights))
    return text.replace(DEFAULT_PREFIX, prefix_of(climate_entity))


def sync(
    folder: Path,
    climate_entity: str | None,
    sections: Any = None,
    vacuum: str | None = None,
    vac_cfg: dict[str, str] | None = None,
) -> bool:
    """Écrit maison_dashboard.yaml si son contenu doit changer. True si réécrit."""
    modele = folder / MODELE
    cible = folder / CIBLE
    if not modele.exists():
        return False
    fragments = {}
    if vacuum:
        for token, name in FRAGMENTS.items():
            f = folder / name
            fragments[token] = f.read_text(encoding="utf-8") if f.exists() else ""
    new = render(modele.read_text(encoding="utf-8"), climate_entity, sections, vacuum, fragments, vac_cfg)
    if cible.exists() and cible.read_text(encoding="utf-8") == new:
        return False
    cible.write_text(new, encoding="utf-8")
    return True
