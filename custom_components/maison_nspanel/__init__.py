"""Maison NSPanel : rappels modifiables, prévisions 7 jours et images météo."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant

from .const import CONF_CLIMATE, CONF_SECTIONS, CONF_VACUUM, DOMAIN, STATIC_URL
from .dashboard import sync
from .panel import async_refresh_lovelace, async_register_panel, async_unregister_panel

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def _async_register_images(hass: HomeAssistant) -> None:
    """Sert les images météo du dossier « meteo » à /maison_nspanel/meteo/."""
    store = hass.data.setdefault(DOMAIN, {})
    if store.get("static_registered"):
        return
    path = str(Path(__file__).parent / "meteo")
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, path, True)]
        )
    except ImportError:  # Home Assistant plus ancien
        hass.http.register_static_path(STATIC_URL, path, True)
    store["static_registered"] = True


def _vacuum(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Aspirateur choisi dans Configurer, sinon le premier détecté (ou None)."""
    chosen = entry.options.get(CONF_VACUUM)
    if chosen:
        return chosen
    found = sorted(hass.states.async_entity_ids("vacuum"))
    return found[0] if found else None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Démarre l'intégration."""
    await _async_register_images(hass)
    try:
        await async_register_panel(hass)
    except Exception as err:  # noqa: BLE001 - le panneau est facultatif
        _LOGGER.warning("Panneau Éclairage indisponible : %s", err)
    # Régénère le dashboard avec l'entité de climatisation choisie (dossier « dashboard »)
    try:
        changed = await hass.async_add_executor_job(
            sync,
            Path(__file__).parent / "dashboard",
            entry.options.get(CONF_CLIMATE),
            entry.options.get(CONF_SECTIONS),
            _vacuum(hass, entry),
        )
        if changed:
            _LOGGER.info("Dashboard régénéré pour %s", entry.options.get(CONF_CLIMATE))
            if await async_refresh_lovelace(hass):
                _LOGGER.info("Dashboard actualisé sans redémarrage")
    except OSError as err:
        _LOGGER.warning("Impossible de régénérer le dashboard : %s", err)
    if _vacuum(hass, entry) is None and hass.state is not CoreState.running:
        # Les aspirateurs arrivent parfois après nous au démarrage : on réessaie une fois.
        async def _retry(_event) -> None:
            if _vacuum(hass, entry) is not None:
                await hass.config_entries.async_reload(entry.entry_id)

        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _retry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Arrête l'intégration."""
    async_unregister_panel(hass)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharge quand les rappels ou l'entité météo sont modifiés."""
    await hass.config_entries.async_reload(entry.entry_id)
