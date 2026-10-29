"""Panneau « Éclairage » dans la barre latérale : éditeur visuel des sections et lumières."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import CONF_SECTIONS, DOMAIN
from .dashboard import normalize_sections

_LOGGER = logging.getLogger(__name__)

PANEL_URL = "maison-eclairage"
PANEL_COMPONENT = "maison-nspanel-editeur"
STATIC_PANEL = "/maison_nspanel_panel"
WWW = Path(__file__).parent / "www"

LUMIERE = vol.Schema(
    {
        vol.Required("entity"): str,
        vol.Optional("nom"): str,
        vol.Optional("icone"): str,
        vol.Optional("couleur"): str,
    }
)
SECTION = vol.Schema({vol.Required("nom"): str, vol.Required("lumieres"): [LUMIERE]})


def _version() -> str:
    try:
        return json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "0"


def _entry(hass: HomeAssistant):
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


@websocket_api.websocket_command({vol.Required("type"): "maison_nspanel/get_sections"})
@callback
def ws_get_sections(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Intégration non configurée")
        return
    connection.send_result(msg["id"], {"sections": normalize_sections(entry.options.get(CONF_SECTIONS))})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "maison_nspanel/set_sections", vol.Required("sections"): [SECTION]}
)
@callback
def ws_set_sections(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Intégration non configurée")
        return
    sections = normalize_sections(msg["sections"])
    # La mise à jour des options recharge l'entrée et régénère le dashboard.
    hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_SECTIONS: sections})
    connection.send_result(msg["id"], {"sections": sections})


async def async_register_panel(hass: HomeAssistant) -> None:
    """Enregistre les commandes WebSocket et le panneau (une fois)."""
    store = hass.data.setdefault(DOMAIN, {})
    if not store.get("ws_registered"):
        websocket_api.async_register_command(hass, ws_get_sections)
        websocket_api.async_register_command(hass, ws_set_sections)
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
        sidebar_title="Éclairage NSPanel",
        sidebar_icon="mdi:lightbulb-group",
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
