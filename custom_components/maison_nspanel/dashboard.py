"""Génère le dashboard (maison_dashboard.yaml) à partir du modèle et des réglages.

Le modèle contient des repères (__SECTIONS__, __LIGHTS_JS__ …) remplacés par :
- les sections d'éclairage choisies dans Configurer,
- l'entité de climatisation choisie (préfixe d'entités Sensibo).
"""

from __future__ import annotations

import json
import re
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
    ("accueil", "Accueil", "mdi:home", "56,189,248"),
    ("lumieres", "Éclairage", "mdi:lightbulb-group", "250,204,21"),
    ("climat", "Climatisation", "mdi:air-conditioner", "34,211,238"),
    ("aspirateur", "Aspirateur", "mdi:robot-vacuum", "74,222,128"),
    ("previsions", "Prévisions", "mdi:weather-partly-cloudy", "147,197,253"),
)
_STY = "states['sensor.maison_nspanel_rappels']"
_ARD = f"({_STY} && {_STY}.attributes.style === 'ardoise')"


def _tpl(a: str, b: str) -> str:
    return f'"[[[ return {_ARD} ? {a} : {b} ]]]"'


def gen_menu(has_vacuum: bool, active: str = "accueil") -> tuple[str, str]:
    """Barre d'onglets du bas : l'onglet actif s'élargit et affiche son nom.

    Renvoie (champ personnalisé, style de zone de grille), à l'indentation zéro.
    """
    tabs = [t for t in MENU_TABS if has_vacuum or t[0] != "aspirateur"]
    ids = [f"t{i}" for i in range(len(tabs))]
    cols = " ".join("2.4fr" if t[0] == active else "1fr" for t in tabs)
    out = [
        "menu:",
        "  card:",
        "    type: custom:button-card",
        "    show_icon: false",
        "    show_name: false",
        "    show_label: false",
        "    triggers_update: [sensor.maison_nspanel_rappels]",
        "    custom_fields:",
    ]
    for (path, name, icon, rgb), tid in zip(tabs, ids):
        on = path == active
        out += [
            f"      {tid}:",
            "        card:",
            "          type: custom:button-card",
            f"          icon: {icon}",
            f"          name: {name}",
            f"          show_name: {'true' if on else 'false'}",
            "          tap_action:",
            "            action: navigate",
            f"            navigation_path: \"[[[ return '/' + window.location.pathname.split('/')[1] + '/{path}'; ]]]\"",
            "          styles:",
            "            grid:",
            f"              - grid-template-areas: '{chr(34) + 'i n' + chr(34) if on else chr(34) + 'i' + chr(34)}'",
            f"              - grid-template-columns: {'min-content auto' if on else '1fr'}",
            "              - justify-content: center",
            "              - align-items: center",
            "              - column-gap: 8px",
            "            card:",
            "              - height: 46px",
            "              - padding: 0 6px",
            "              - border-radius: 23px",
            "              - box-shadow: none",
            f"              - background: {'"linear-gradient(135deg, rgba(' + rgb + ',.30), rgba(' + rgb + ',.10))"' if False else ('linear-gradient(135deg, rgba(' + rgb + ',.30), rgba(' + rgb + ',.10))' if on else 'transparent')}",
            f"              - border: {'1px solid rgba(' + rgb + ',.40)' if on else 'none'}",
            "            icon:",
            f"              - width: {'22px' if on else '24px'}",
            f"              - color: {'rgb(' + rgb + ')' if on else 'rgba(203,213,225,.72)'}",
            "            name:",
            "              - font-family: \"'Inter','Segoe UI',Roboto,sans-serif\"",
            "              - font-size: 12px",
            "              - font-weight: 800",
            "              - color: '#FFFFFF'",
            f"              - letter-spacing: {_tpl(chr(39) + '.3px' + chr(39), chr(39) + '1px' + chr(39))}",
            f"              - text-transform: {_tpl(chr(39) + 'none' + chr(39), chr(39) + 'uppercase' + chr(39))}",
            "              - white-space: nowrap",
        ]
    out += [
        "    styles:",
        "      grid:",
        f"        - grid-template-areas: '\"{' '.join(ids)}\"'",
        f"        - grid-template-columns: {cols}",
        "        - column-gap: 4px",
        "        - align-items: stretch",
        "      card:",
        "        - padding: 5px",
        "        - border-radius: 28px",
        f"        - background: {_tpl(chr(39) + 'linear-gradient(115deg, rgba(9,22,32,.93), rgba(5,12,22,.88) 56%, rgba(13,30,42,.92))' + chr(39), chr(39) + 'rgba(16,23,40,.86)' + chr(39))}",
        f"        - border: {_tpl(chr(39) + '1px solid rgba(184,226,239,.10)' + chr(39), chr(39) + '1px solid rgba(255,255,255,.10)' + chr(39))}",
        "        - box-shadow: 0 6px 22px rgba(0,0,0,.35)",
        "      custom_fields:",
    ]
    for tid in ids:
        out += [f"        {tid}:", "          - grid-area: " + tid, "          - width: 100%"]
    style = ["menu:", "  - grid-area: menu", "  - width: 100%", "  - margin-top: 2px"]
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
    menu: bool = False,
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
    if menu:
        field, style = gen_menu(bool(vacuum))
        text = _inject(text, "__MENU__", field)
        text = _inject(text, "__MENU_STYLE__", style)
        text = text.replace("__MENU_ROW2__", ' \\"menu menu\\"').replace("__MENU_ROW3__", ' \\"menu menu menu\\"')
        text = text.replace("__MENU_ROWS__", " min-content")
    else:
        for token in ("__MENU__", "__MENU_STYLE__"):
            text = _inject(text, token, "")
        for token in ("__MENU_ROW2__", "__MENU_ROW3__", "__MENU_ROWS__"):
            text = text.replace(token, "")
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
    menu: bool = False,
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
    new = render(modele.read_text(encoding="utf-8"), climate_entity, sections, vacuum, fragments, vac_cfg, menu)
    if cible.exists() and cible.read_text(encoding="utf-8") == new:
        return False
    cible.write_text(new, encoding="utf-8")
    return True
