"""Capteurs : rappels actifs et prévisions météo sur 7 jours."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_STYLE,
    DEFAULT_STYLE,
    CONF_RAPPELS,
    CONF_VIGILANCE_ENTITY,
    CONF_VIGILANCE_MIN,
    CONF_WEATHER,
    DOMAIN,
    PREVISIONS_REFRESH_MINUTES,
    PREVISIONS_RETRY_SECONDS,
)
from .rappels import active_reminders, normalize
from .vigilance import DEFAULT_MIN, compute, find_source

_LOGGER = logging.getLogger(__name__)


def _device(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Maison NSPanel",
        manufacturer="Maison",
        model="Tableau de bord NSPanel",
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Crée les trois capteurs."""
    async_add_entities(
        [
            MaisonRappelsSensor(entry),
            MaisonPrevisionsSensor(entry),
            MaisonVigilanceSensor(entry),
        ]
    )


class MaisonRappelsSensor(SensorEntity):
    """Nombre de rappels à afficher maintenant ; la liste est dans l'attribut « rappels »."""

    _attr_has_entity_name = True
    _attr_name = "Rappels"
    _attr_icon = "mdi:bell-ring-outline"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_rappels"
        self._attr_device_info = _device(entry)
        self.entity_id = "sensor.maison_nspanel_rappels"
        self._active: list[dict[str, str]] = []

    def _compute(self) -> list[dict[str, str]]:
        return active_reminders(self._entry.options.get(CONF_RAPPELS, []), dt_util.now())

    async def async_added_to_hass(self) -> None:
        self._active = self._compute()
        # Réévalué chaque minute pile (changement de jour, début / fin de plage horaire)
        self.async_on_remove(async_track_time_change(self.hass, self._tick, second=0))

    @callback
    def _tick(self, _now: datetime) -> None:
        new = self._compute()
        if new != self._active:
            self._active = new
            self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return len(self._active)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "rappels": self._active,
            "style": self._entry.options.get(CONF_STYLE) or DEFAULT_STYLE,
            "tous": [normalize(r) for r in self._entry.options.get(CONF_RAPPELS, [])],
        }


class MaisonPrevisionsSensor(SensorEntity):
    """Prévisions quotidiennes (7 jours) de l'entité météo choisie."""

    _attr_has_entity_name = True
    _attr_name = "Prévisions 7 jours"
    _attr_icon = "mdi:weather-partly-rainy"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_previsions"
        self._attr_device_info = _device(entry)
        self.entity_id = "sensor.maison_nspanel_previsions"
        self._forecast: list[dict[str, Any]] = []
        self._weather = entry.options.get(CONF_WEATHER) or entry.data.get(CONF_WEATHER)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._interval,
                timedelta(minutes=PREVISIONS_REFRESH_MINUTES),
            )
        )
        # Rafraîchit aussi quand l'état de l'entité météo change (condition actuelle)
        if self._weather:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self._weather], self._weather_changed
                )
            )
        # Premier chargement une fois Home Assistant prêt (l'entité météo existe)
        self.async_on_remove(async_call_later(self.hass, 5, self._interval))

    async def _weather_changed(self, _event) -> None:
        await self._refresh()

    async def _interval(self, _now: datetime) -> None:
        await self._refresh()

    async def _refresh(self) -> None:
        try:
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"entity_id": self._weather, "type": "daily"},
                blocking=True,
                return_response=True,
            )
            self._forecast = list(response[self._weather]["forecast"])[:7]
            self.async_write_ha_state()
        except Exception as err:  # noqa: BLE001 - météo pas prête ou sans prévisions
            _LOGGER.warning(
                "Prévisions indisponibles pour %s (%s), nouvel essai dans %s s",
                self._weather,
                err,
                PREVISIONS_RETRY_SECONDS,
            )
            self.async_on_remove(
                async_call_later(self.hass, PREVISIONS_RETRY_SECONDS, self._interval)
            )

    @property
    def native_value(self) -> int:
        return len(self._forecast)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        st = self.hass.states.get(self._weather) if self._weather else None
        return {
            "forecast": self._forecast,
            "weather_entity": self._weather,
            "condition": st.state if st else None,
        }


class MaisonVigilanceSensor(SensorEntity):
    """Vigilance Météo-France : état = couleur (vert, jaune, orange, rouge)."""

    _attr_has_entity_name = True
    _attr_name = "Vigilance"
    _attr_icon = "mdi:weather-cloudy-alert"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_vigilance"
        self._attr_device_info = _device(entry)
        self.entity_id = "sensor.maison_nspanel_vigilance"
        self._source: str | None = None
        self._data: dict[str, Any] = compute(None, None, DEFAULT_MIN)

    def _minimum(self) -> str:
        return self._entry.options.get(CONF_VIGILANCE_MIN) or DEFAULT_MIN

    def _find_source(self) -> str | None:
        configured = self._entry.options.get(CONF_VIGILANCE_ENTITY)
        if configured:
            return configured
        return find_source(self.hass.states.async_entity_ids("sensor"))

    def _update(self) -> bool:
        """Recalcule ; renvoie True si quelque chose a changé."""
        self._source = self._find_source()
        st = self.hass.states.get(self._source) if self._source else None
        if st is None or st.state in ("unknown", "unavailable"):
            data = compute(None, None, self._minimum())
        else:
            data = compute(st.state, dict(st.attributes), self._minimum())
        data["source"] = self._source
        changed = data != self._data
        self._data = data
        return changed

    async def async_added_to_hass(self) -> None:
        self._update()
        # Suit le capteur source (s'il existe déjà) et le recherche régulièrement
        # tant qu'il n'est pas trouvé (Météo-France peut démarrer après nous).
        if self._source:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self._source], self._source_changed
                )
            )
        self.async_on_remove(
            async_track_time_interval(self.hass, self._recheck, timedelta(minutes=5))
        )

    @callback
    def _source_changed(self, _event) -> None:
        if self._update():
            self.async_write_ha_state()

    @callback
    def _recheck(self, _now: datetime) -> None:
        previous = self._source
        changed = self._update()
        if self._source != previous:
            # Source trouvée ou changée : recharge l'intégration pour la suivre
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self._entry.entry_id)
            )
        elif changed:
            self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._data["nom"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return dict(self._data)
