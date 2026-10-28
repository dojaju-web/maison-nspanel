"""Maison NSPanel : rappels modifiables, prévisions 7 jours et images météo."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CLIMATE, CONF_SECTIONS, DOMAIN, STATIC_URL
from .dashboard import sync

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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Démarre l'intégration."""
    await _async_register_images(hass)
    # Régénère le dashboard avec l'entité de climatisation choisie (dossier « dashboard »)
    try:
        changed = await hass.async_add_executor_job(
            sync,
            Path(__file__).parent / "dashboard",
            entry.options.get(CONF_CLIMATE),
            entry.options.get(CONF_SECTIONS),
        )
        if changed:
            _LOGGER.info("Dashboard régénéré pour %s", entry.options.get(CONF_CLIMATE))
    except OSError as err:
        _LOGGER.warning("Impossible de régénérer le dashboard : %s", err)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Arrête l'intégration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharge quand les rappels ou l'entité météo sont modifiés."""
    await hass.config_entries.async_reload(entry.entry_id)
