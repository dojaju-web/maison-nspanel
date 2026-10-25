"""Génère le fichier du dashboard à partir du modèle, avec l'entité de climatisation choisie."""

from __future__ import annotations

from pathlib import Path

DEFAULT_CLIMATE = "climate.sejour_climatisation"
DEFAULT_PREFIX = "sejour_climatisation"  # préfixe commun aux entités Sensibo du modèle

MODELE = "modele.yaml"
CIBLE = "maison_dashboard.yaml"


def prefix_of(entity_id: str | None) -> str:
    """« climate.salon_clim » -> « salon_clim »."""
    if not entity_id or "." not in entity_id:
        return DEFAULT_PREFIX
    return entity_id.split(".", 1)[1]


def render(text: str, climate_entity: str | None) -> str:
    """Remplace le préfixe d'entités du modèle par celui de l'entité choisie."""
    return text.replace(DEFAULT_PREFIX, prefix_of(climate_entity))


def sync(folder: Path, climate_entity: str | None) -> bool:
    """Écrit maison_dashboard.yaml si son contenu doit changer. True si réécrit."""
    modele = folder / MODELE
    cible = folder / CIBLE
    if not modele.exists():
        return False
    new = render(modele.read_text(encoding="utf-8"), climate_entity)
    if cible.exists() and cible.read_text(encoding="utf-8") == new:
        return False
    cible.write_text(new, encoding="utf-8")
    return True
