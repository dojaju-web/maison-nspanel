"""Logique des rappels (sans dépendance à Home Assistant, donc testable seule)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

DAY_LABELS = {
    "mon": "Lundi",
    "tue": "Mardi",
    "wed": "Mercredi",
    "thu": "Jeudi",
    "fri": "Vendredi",
    "sat": "Samedi",
    "sun": "Dimanche",
}

DEFAULT_REMINDER: dict[str, Any] = {
    "texte": "Sortir les poubelles",
    "icone": "mdi:trash-can-outline",
    "jours": ["mon"],
    "heure_debut": "00:00:00",
    "heure_fin": "23:59:00",
    "couleur": [250, 204, 21],
    "actif": True,
}


def _parse_time(value: Any, fallback: time) -> time:
    """Convertit « HH:MM[:SS] » en time (au format minute)."""
    try:
        parts = str(value).split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return fallback


def normalize(reminder: dict[str, Any]) -> dict[str, Any]:
    """Complète un rappel avec les valeurs par défaut et nettoie les champs."""
    data = {**DEFAULT_REMINDER, **(reminder or {})}
    data["jours"] = [d for d in data.get("jours") or [] if d in DAYS]
    colour = list(data.get("couleur") or DEFAULT_REMINDER["couleur"])[:3]
    while len(colour) < 3:
        colour.append(0)
    data["couleur"] = [max(0, min(255, int(c))) for c in colour]
    data["actif"] = bool(data.get("actif", True))
    data["texte"] = str(data.get("texte") or "").strip()
    return data


def rgb_string(colour: list[int]) -> str:
    """[250, 204, 21] -> « 250,204,21 » (format attendu par le dashboard)."""
    return ",".join(str(int(c)) for c in colour)


def is_active(reminder: dict[str, Any], now: datetime) -> bool:
    """Le rappel doit-il s'afficher à cet instant ?"""
    r = normalize(reminder)
    if not r["actif"] or not r["texte"]:
        return False
    if DAYS[now.weekday()] not in r["jours"]:
        return False
    start = _parse_time(r["heure_debut"], time(0, 0))
    end = _parse_time(r["heure_fin"], time(23, 59))
    current = time(now.hour, now.minute)
    if start <= end:
        return start <= current <= end
    # plage qui passe minuit (ex. 20:00 -> 06:00)
    return current >= start or current <= end


def active_reminders(reminders: list[dict[str, Any]], now: datetime) -> list[dict[str, str]]:
    """Liste des rappels actifs, au format lu par le dashboard."""
    result = []
    for reminder in reminders or []:
        if is_active(reminder, now):
            r = normalize(reminder)
            result.append(
                {
                    "texte": r["texte"],
                    "icone": r["icone"],
                    "couleur": rgb_string(r["couleur"]),
                }
            )
    return result


def describe(reminder: dict[str, Any]) -> str:
    """Libellé court pour les listes de l'interface."""
    r = normalize(reminder)
    days = ", ".join(DAY_LABELS[d][:3] + "." for d in DAYS if d in r["jours"]) or "aucun jour"
    state = "" if r["actif"] else " (désactivé)"
    return f"{r['texte'] or '(sans texte)'} — {days}{state}"
