"""Détection des entités liées à l'aspirateur (logique pure, testable sans Home Assistant)."""

from __future__ import annotations

import re
from typing import Any, Iterable

FAN_RE = re.compile(r"(fan|suction|aspiration|power|speed|vitesse|puissance)", re.I)
NOT_FAN_RE = re.compile(r"(water|mop|eau|serpill)", re.I)
AREA_RE = re.compile(r"(area|surface)", re.I)
TIME_RE = re.compile(r"(time|duration|duree|durée)", re.I)
ALERT_RE = re.compile(r"(error|fault|alert|problem|erreur)", re.I)
MODE_RE = re.compile(r"(clean[_ -]?mode|work[_ -]?mode|mode[_ -]de[_ -]nettoyage)", re.I)
WATER_RE = re.compile(r"(clean[_ -]?water|water[_ -]?cistern|eau[_ -]?propre)", re.I)
DRAIN_RE = re.compile(r"(drain[_ -]?cistern|waste[_ -]?water|dirty[_ -]?water|eau[_ -]?sale)", re.I)


def _text(e: dict[str, Any]) -> str:
    return f"{e.get('entity_id', '')} {e.get('name') or ''}"


def pick(entries: Iterable[dict[str, Any]]) -> dict[str, str]:
    """Devine batterie, aspiration, surface, durée et alerte parmi les entités d'un appareil.

    Chaque entrée : {entity_id, device_class, name, unit}.
    """
    entries = list(entries)
    found: dict[str, str] = {}

    def first(pred) -> str | None:
        for e in sorted(entries, key=lambda x: x["entity_id"]):
            if pred(e):
                return e["entity_id"]
        return None

    def dom(e: dict[str, Any]) -> str:
        return e["entity_id"].split(".", 1)[0]

    bat = first(lambda e: dom(e) == "sensor" and e.get("device_class") == "battery") or first(
        lambda e: dom(e) == "sensor" and "battery" in _text(e).lower()
    )
    if bat:
        found["vac_battery"] = bat
    fan = first(lambda e: dom(e) == "select" and FAN_RE.search(_text(e)) and not NOT_FAN_RE.search(_text(e)))
    if fan:
        found["vac_fan"] = fan
    area = first(lambda e: dom(e) == "sensor" and (AREA_RE.search(_text(e)) or e.get("unit") in ("m²", "m2")))
    if area:
        found["vac_area"] = area
    time_ = first(
        lambda e: dom(e) == "sensor"
        and (e.get("device_class") == "duration" or (TIME_RE.search(_text(e)) and e.get("unit") in ("s", "min", "h", None, "")))
        and "battery" not in _text(e).lower()
    )
    if time_:
        found["vac_time"] = time_
    alert = first(lambda e: dom(e) in ("sensor", "binary_sensor") and ALERT_RE.search(_text(e)))
    if alert:
        found["vac_alert"] = alert
    mode = first(lambda e: dom(e) in ("sensor", "select") and MODE_RE.search(_text(e)) and not re.search(r"water|eau|carpet|dock", _text(e), re.I))
    if mode:
        found["vac_mode"] = mode
    water = first(lambda e: dom(e) in ("sensor", "binary_sensor") and WATER_RE.search(_text(e)))
    if water:
        found["vac_water"] = water
    drain = first(lambda e: dom(e) in ("sensor", "binary_sensor") and DRAIN_RE.search(_text(e)))
    if drain:
        found["vac_drain"] = drain
    return found
