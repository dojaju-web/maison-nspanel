"""Logique pure de la vigilance Météo-France (sans dépendance à Home Assistant)."""

from __future__ import annotations

import re
from typing import Any, Iterable

LEVELS = {"vert": 1, "jaune": 2, "orange": 3, "rouge": 4}
NAMES = {1: "vert", 2: "jaune", 3: "orange", 4: "rouge"}
COLORS = {1: "74,222,128", 2: "250,204,21", 3: "251,146,60", 4: "239,68,68"}

# Seuils proposés dans l'interface : valeur -> niveau minimal affiché (0 = jamais)
MIN_CHOICES = {"jamais": 0, "jaune": 2, "orange": 3, "rouge": 4, "toujours": 1}
DEFAULT_MIN = "jaune"

ALERT_ID = re.compile(r"^sensor\.(\d{2}|2a|2b)_weather_alert$")
_IGNORED_ATTRS = {"attribution", "friendly_name", "icon", "device_class", "unit_of_measurement"}


def level_of(value: Any) -> int:
    """Niveau (1 à 4) d'un texte « Vert / Jaune / Orange / Rouge » ; 0 si inconnu."""
    return LEVELS.get(str(value or "").strip().lower(), 0)


def find_source(entity_ids: Iterable[str]) -> str | None:
    """Premier capteur de vigilance Météo-France trouvé (sensor.84_weather_alert…)."""
    for entity_id in sorted(entity_ids):
        if ALERT_ID.match(entity_id):
            return entity_id
    return None


def compute(state: Any, attributes: dict[str, Any] | None, minimum: str) -> dict[str, Any]:
    """Résumé affichable à partir de l'état et des attributs du capteur source."""
    level = level_of(state)
    min_level = MIN_CHOICES.get(minimum, MIN_CHOICES[DEFAULT_MIN])
    phenomena = []
    for key, val in (attributes or {}).items():
        if key in _IGNORED_ATTRS:
            continue
        lv = level_of(val)
        if lv >= 2:
            phenomena.append({"nom": str(key).replace("-", " / "), "niveau": lv})
    phenomena.sort(key=lambda p: (-p["niveau"], p["nom"]))
    return {
        "niveau": level,
        "nom": NAMES.get(level, "inconnu"),
        "couleur": COLORS.get(level, COLORS[1]),
        "phenomenes": phenomena,
        "afficher": bool(level and min_level and level >= min_level),
        "minimum": minimum,
    }
