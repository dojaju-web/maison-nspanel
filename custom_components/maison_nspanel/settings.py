"""Réglages du panneau : lecture, validation et fusion dans les options (sans Home Assistant)."""

from __future__ import annotations

from typing import Any

from .const import (
    BETA_DEFAULTS,
    BETA_EFFETS,
    BETA_METEO,
    BETA_NUAGES,
    BETA_MOMENT,
    BETA_VOLETS,
    CONF_AIR,
    CONF_BETA,
    CONF_CLIMATE,
    CONF_RAPPELS,
    CONF_SECTIONS,
    CONF_STYLE,
    CONF_VAC_SENSORS,
    CONF_VACUUM,
    CONF_VIGILANCE_ENTITY,
    CONF_VIGILANCE_MIN,
    CONF_WEATHER,
    DEFAULT_STYLE,
    STYLES,
)
from .dashboard import DEFAULT_CLIMATE, normalize_sections
from .rappels import normalize
from .vigilance import DEFAULT_MIN, MIN_CHOICES

ENTITY_KEYS = (
    "weather_entity",
    "vigilance_entity",
    "climate_entity",
    "vacuum_entity",
    "vac_battery",
    "vac_fan",
    "vac_area",
    "vac_time",
    "vac_alert",
    "vac_mode",
    "vac_water",
    "vac_drain",
    "vac_status",
)




def beta_settings(raw: Any) -> dict[str, Any]:
    """Réglages NSPanel-Beta : valeurs par défaut + valeurs valides enregistrées."""
    out = dict(BETA_DEFAULTS)
    if not isinstance(raw, dict):
        return out
    for key in ("diorama", "rappels"):
        if isinstance(raw.get(key), bool):
            out[key] = raw[key]
    if raw.get("effets") in BETA_EFFETS:
        out["effets"] = raw["effets"]
    if raw.get("nuages") in BETA_NUAGES:
        out["nuages"] = raw["nuages"]
    if raw.get("meteo") in BETA_METEO:
        out["meteo"] = raw["meteo"]
    if raw.get("moment") in BETA_MOMENT:
        out["moment"] = raw["moment"]
    if raw.get("volets") in BETA_VOLETS:
        out["volets"] = raw["volets"]
    for key, lo, hi in (("position", 0, 100), ("taille_heure", 8, 16)):
        v = raw.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = max(lo, min(hi, int(round(v))))
    return out


def current_settings(entry) -> dict[str, Any]:
    """Réglages affichés dans le panneau (valeurs par défaut comprises)."""
    o = entry.options
    return {
        "weather_entity": o.get(CONF_WEATHER) or entry.data.get(CONF_WEATHER) or "",
        "vigilance_entity": o.get(CONF_VIGILANCE_ENTITY) or "",
        "vigilance_min": o.get(CONF_VIGILANCE_MIN) or DEFAULT_MIN,
        "style": o.get(CONF_STYLE) or DEFAULT_STYLE,
        "climate_entity": o.get(CONF_CLIMATE) or DEFAULT_CLIMATE,
        "air_enabled": bool(o.get(CONF_AIR, True)),
        "beta": beta_settings(o.get(CONF_BETA)),
        "vacuum_entity": o.get(CONF_VACUUM) or "",
        **{k: o.get(k) or "" for k in CONF_VAC_SENSORS},
        "rappels": [normalize(r) for r in o.get(CONF_RAPPELS, [])],
        "sections": normalize_sections(o.get(CONF_SECTIONS)),
    }


def clean_settings(raw: dict[str, Any]) -> dict[str, Any]:
    """Valide et nettoie les réglages reçus du panneau ; les clés inconnues sont ignorées."""
    out: dict[str, Any] = {}
    for key in ENTITY_KEYS:
        if key in raw:
            val = str(raw[key] or "").strip()
            if val and "." not in val:
                raise ValueError(f"Entité invalide : {val}")
            out[key] = val
    if "vigilance_min" in raw:
        if raw["vigilance_min"] not in MIN_CHOICES:
            raise ValueError("Seuil de vigilance invalide")
        out["vigilance_min"] = raw["vigilance_min"]
    if "style" in raw:
        if raw["style"] not in STYLES:
            raise ValueError("Style invalide")
        out["style"] = raw["style"]
    if "air_enabled" in raw:
        out["air_enabled"] = bool(raw["air_enabled"])
    if "beta" in raw:
        if not isinstance(raw["beta"], dict):
            raise ValueError("Réglages NSPanel-Beta invalides")
        out["beta"] = beta_settings(raw["beta"])
    if "rappels" in raw:
        out["rappels"] = [normalize(r) for r in raw["rappels"] if isinstance(r, dict)]
    if "sections" in raw:
        out["sections"] = normalize_sections(raw["sections"])
    return out


def apply_settings(options: dict[str, Any], clean: dict[str, Any]) -> dict[str, Any]:
    """Fusionne les réglages nettoyés dans les options (une valeur vide supprime la clé)."""
    new = dict(options)
    mapping = {
        "weather_entity": CONF_WEATHER,
        "vigilance_entity": CONF_VIGILANCE_ENTITY,
        "vigilance_min": CONF_VIGILANCE_MIN,
        "style": CONF_STYLE,
        "climate_entity": CONF_CLIMATE,
        "air_enabled": CONF_AIR,
        "vacuum_entity": CONF_VACUUM,
        "rappels": CONF_RAPPELS,
        "sections": CONF_SECTIONS,
    }
    for key, val in clean.items():
        target = mapping.get(key, key)
        if val == "" or val is None:
            new.pop(target, None)
        else:
            new[target] = val
    return new
