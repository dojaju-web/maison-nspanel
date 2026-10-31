"""Panneau « Maison NSPanel » dans la barre latérale : tous les réglages au même endroit."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .settings import apply_settings, clean_settings, current_settings
from .vigilance import find_source

_LOGGER = logging.getLogger(__name__)

PANEL_URL = "maison-reglages"
PANEL_COMPONENT = "maison-nspanel-editeur"
STATIC_PANEL = "/maison_nspanel_panel"
WWW = Path(__file__).parent / "www"

def _version() -> str:
    try:
        return json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "0"


def _entry(hass: HomeAssistant):
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _detected(hass: HomeAssistant, entry) -> dict[str, str]:
    from . import detect_vacuum

    found = detect_vacuum(hass, entry)
    source = find_source(hass.states.async_entity_ids("sensor"))
    if source:
        found["vigilance"] = source
    return found


@websocket_api.websocket_command({vol.Required("type"): "maison_nspanel/get_settings"})
@callback
def ws_get_settings(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Intégration non configurée")
        return
    connection.send_result(msg["id"], {"settings": current_settings(entry), "detected": _detected(hass, entry)})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "maison_nspanel/set_settings", vol.Required("settings"): dict}
)
@callback
def ws_set_settings(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Intégration non configurée")
        return
    try:
        clean = clean_settings(msg["settings"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    # La mise à jour des options recharge l'entrée et régénère le dashboard.
    hass.config_entries.async_update_entry(entry, options=apply_settings(dict(entry.options), clean))
    connection.send_result(msg["id"], {"settings": current_settings(entry), "detected": _detected(hass, entry)})


async def async_register_panel(hass: HomeAssistant) -> None:
    """Enregistre les commandes WebSocket et le panneau (une fois)."""
    store = hass.data.setdefault(DOMAIN, {})
    if not store.get("ws_registered"):
        websocket_api.async_register_command(hass, ws_get_settings)
        websocket_api.async_register_command(hass, ws_set_settings)
        store["ws_registered"] = True
    if store.get("panel_registered"):
        return
    from homeassistant.components import panel_custom
    from homeassistant.components.http import StaticPathConfig

    if not store.get("panel_static"):
        await hass.http.async_register_static_paths([StaticPathConfig(STATIC_PANEL, str(WWW), False)])
        store["panel_static"] = True
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL,
        module_url=f"{STATIC_PANEL}/maison-editeur.js?v={_version()}",
        sidebar_title="Maison NSPanel",
        sidebar_icon="mdi:tune-variant",
        require_admin=True,
        config={},
    )
    store["panel_registered"] = True


def async_unregister_panel(hass: HomeAssistant) -> None:
    store = hass.data.get(DOMAIN, {})
    if store.get("panel_registered"):
        try:
            from homeassistant.components import frontend

            frontend.async_remove_panel(hass, PANEL_URL)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Panneau déjà retiré")
        store["panel_registered"] = False


async def async_refresh_lovelace(hass: HomeAssistant) -> int:
    """Force Home Assistant à relire maison_dashboard.yaml et prévient les pages ouvertes.

    Sans cela, un tableau de bord YAML garde son ancienne version en cache jusqu'au
    redémarrage. Meilleur effort : s'appuie sur des détails internes de Home Assistant.
    """
    data = hass.data.get("lovelace")
    dashboards = data.get("dashboards") if isinstance(data, dict) else getattr(data, "dashboards", None)
    done = 0
    for url_path, dash in list((dashboards or {}).items()):
        cfg = getattr(dash, "config", None)
        filename = str(cfg.get("filename", "")) if isinstance(cfg, dict) else ""
        if not filename.endswith("maison_dashboard.yaml") or not hasattr(dash, "async_load"):
            continue
        try:
            await dash.async_load(True)
            hass.bus.async_fire("lovelace_updated", {"url_path": url_path})
            done += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Actualisation du dashboard %s impossible : %s", url_path, err)
    return done
