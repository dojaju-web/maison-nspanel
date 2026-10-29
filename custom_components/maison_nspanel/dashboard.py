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

VAC_BEGIN = "  # ==========================================================\n  #  PAGE : ASPIRATEUR ROBOT"
VAC_END = "  # ==========================================================\n  #  PRÉVISIONS MÉTÉO"
FRAGMENTS = {"__VAC_NAV__": "aspirateur_nav.yaml", "__VAC_NAVB__": "aspirateur_navb.yaml"}

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
) -> str:
    """Remplace les repères du modèle, puis le préfixe d'entités de climatisation."""
    secs = normalize_sections(sections)
    lights = light_entities(secs)
    trig = all_entities(secs) or ["sun.sun"]
    if vacuum:
        for token, block in (fragments or {}).items():
            text = _inject(text, token, block)
        text = text.replace("__VACUUM__", vacuum).replace("__NAVCOLS__", "3")
    else:
        i = text.find(VAC_BEGIN)
        j = text.find(VAC_END)
        if i != -1 and j > i:
            text = text[:i] + text[j:]
        for token in FRAGMENTS:
            text = _inject(text, token, "")
        text = text.replace("__NAVCOLS__", "2")
    text = text.replace("__SECTIONS__", gen_sections(secs))
    text = text.replace("__LIGHTS_IDS__", json.dumps(lights))
    text = text.replace("__LIGHTS_TRIG__", json.dumps(trig))
    text = text.replace("__LIGHTS_JSQ__", ", ".join(f"''{e}''" for e in lights))
    text = text.replace("__LIGHTS_JS__", ", ".join(f"'{e}'" for e in lights))
    return text.replace(DEFAULT_PREFIX, prefix_of(climate_entity))


def sync(folder: Path, climate_entity: str | None, sections: Any = None, vacuum: str | None = None) -> bool:
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
    new = render(modele.read_text(encoding="utf-8"), climate_entity, sections, vacuum, fragments)
    if cible.exists() and cible.read_text(encoding="utf-8") == new:
        return False
    cible.write_text(new, encoding="utf-8")
    return True
