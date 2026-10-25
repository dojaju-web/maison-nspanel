"""Configuration (installation) et options (gestion des rappels) dans l'interface."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector as sel

from .const import (
    CONF_AIR,
    CONF_CLIMATE,
    DEFAULT_STYLE,
    STYLES,
    CONF_RAPPELS,
    CONF_STYLE,
    CONF_VIGILANCE_ENTITY,
    CONF_VIGILANCE_MIN,
    CONF_WEATHER,
    DOMAIN,
)
from .rappels import DAY_LABELS, DAYS, DEFAULT_REMINDER, describe, normalize
from .dashboard import DEFAULT_CLIMATE
from .vigilance import DEFAULT_MIN, MIN_CHOICES

DAY_OPTIONS = [{"value": d, "label": DAY_LABELS[d]} for d in DAYS]

DASHBOARD_HELP = """\
**Maison NSPanel est installé.** Dernière étape pour afficher le dashboard : \
ajoutez ceci dans `configuration.yaml` puis redémarrez Home Assistant.

```yaml
lovelace:
  dashboards:
    maison:
      mode: yaml
      title: Maison
      icon: mdi:home
      show_in_sidebar: true
      filename: custom_components/maison_nspanel/dashboard/maison_dashboard.yaml
```

Les rappels (poubelles, etc.) se gèrent ensuite dans **Paramètres > Appareils et \
services > Maison NSPanel > Configurer**.
"""


def _reminder_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("texte", default=defaults["texte"]): sel.TextSelector(),
            vol.Required("icone", default=defaults["icone"]): sel.IconSelector(),
            vol.Required("jours", default=defaults["jours"]): sel.SelectSelector(
                sel.SelectSelectorConfig(
                    options=DAY_OPTIONS,
                    multiple=True,
                    mode=sel.SelectSelectorMode.LIST,
                )
            ),
            vol.Required("heure_debut", default=defaults["heure_debut"]): sel.TimeSelector(),
            vol.Required("heure_fin", default=defaults["heure_fin"]): sel.TimeSelector(),
            vol.Required("couleur", default=defaults["couleur"]): sel.ColorRGBSelector(),
            vol.Required("actif", default=defaults["actif"]): sel.BooleanSelector(),
        }
    )


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not str(user_input.get("texte", "")).strip():
        errors["texte"] = "texte_requis"
    if not user_input.get("jours"):
        errors["jours"] = "jours_requis"
    return errors


class MaisonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Installation : choix de l'entité météo."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            persistent_notification.async_create(
                self.hass,
                DASHBOARD_HELP,
                title="Maison NSPanel : dernière étape",
                notification_id="maison_nspanel_setup",
            )
            return self.async_create_entry(
                title="Maison NSPanel",
                data={CONF_WEATHER: user_input[CONF_WEATHER]},
                options={CONF_RAPPELS: [normalize(DEFAULT_REMINDER)]},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_WEATHER): sel.EntitySelector(
                    sel.EntitySelectorConfig(domain="weather")
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MaisonOptionsFlow(config_entry)


class MaisonOptionsFlow(OptionsFlow):
    """Gestion des rappels : ajouter, modifier, supprimer."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry
        self._edit_index: int | None = None

    # -- outils -----------------------------------------------------------
    def _rappels(self) -> list[dict[str, Any]]:
        return [normalize(r) for r in self._entry.options.get(CONF_RAPPELS, [])]

    def _save(self, rappels: list[dict[str, Any]] | None = None, **extra: Any) -> FlowResult:
        options = {**self._entry.options, **extra}
        if rappels is not None:
            options[CONF_RAPPELS] = rappels
        return self.async_create_entry(title="", data=options)

    # -- menu principal : 4 catégories ----------------------------------------
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["categorie_rappels", "categorie_meteo", "climatisation", "apparence"],
        )

    async def async_step_categorie_rappels(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        menu = ["ajouter"]
        if self._rappels():
            menu += ["choisir", "supprimer"]
        menu += ["init"]  # retour
        return self.async_show_menu(step_id="categorie_rappels", menu_options=menu)

    async def async_step_categorie_meteo(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="categorie_meteo", menu_options=["meteo", "vigilance", "init"]
        )

    # -- ajouter ------------------------------------------------------------
    async def async_step_ajouter(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        defaults = normalize({**DEFAULT_REMINDER, "texte": "", "jours": []})
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                return self._save(self._rappels() + [normalize(user_input)])
            defaults = normalize(user_input)
        return self.async_show_form(
            step_id="ajouter", data_schema=_reminder_schema(defaults), errors=errors
        )

    # -- modifier -----------------------------------------------------------
    async def async_step_choisir(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        rappels = self._rappels()
        if user_input is not None:
            self._edit_index = int(user_input["rappel"])
            return await self.async_step_modifier()
        schema = vol.Schema(
            {
                vol.Required("rappel", default="0"): sel.SelectSelector(
                    sel.SelectSelectorConfig(
                        options=[
                            {"value": str(i), "label": describe(r)}
                            for i, r in enumerate(rappels)
                        ],
                        mode=sel.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="choisir", data_schema=schema)

    async def async_step_modifier(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        rappels = self._rappels()
        index = self._edit_index
        if index is None or index >= len(rappels):
            return await self.async_step_init()
        errors: dict[str, str] = {}
        defaults = rappels[index]
        if user_input is not None and "texte" in user_input:
            errors = _validate(user_input)
            if not errors:
                rappels[index] = normalize(user_input)
                return self._save(rappels)
            defaults = normalize(user_input)
        return self.async_show_form(
            step_id="modifier", data_schema=_reminder_schema(defaults), errors=errors
        )

    # -- supprimer ----------------------------------------------------------
    async def async_step_supprimer(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        rappels = self._rappels()
        if user_input is not None:
            to_delete = {int(i) for i in user_input.get("rappels", [])}
            return self._save([r for i, r in enumerate(rappels) if i not in to_delete])
        schema = vol.Schema(
            {
                vol.Required("rappels", default=[]): sel.SelectSelector(
                    sel.SelectSelectorConfig(
                        options=[
                            {"value": str(i), "label": describe(r)}
                            for i, r in enumerate(rappels)
                        ],
                        multiple=True,
                        mode=sel.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="supprimer", data_schema=schema)

    # -- météo --------------------------------------------------------------
    async def async_step_meteo(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self._save(**{CONF_WEATHER: user_input[CONF_WEATHER]})
        current = self._entry.options.get(CONF_WEATHER) or self._entry.data.get(CONF_WEATHER)
        schema = vol.Schema(
            {
                vol.Required(CONF_WEATHER, default=current): sel.EntitySelector(
                    sel.EntitySelectorConfig(domain="weather")
                )
            }
        )
        return self.async_show_form(step_id="meteo", data_schema=schema)

    # -- vigilance ----------------------------------------------------------
    async def async_step_vigilance(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self._save(
                **{
                    CONF_VIGILANCE_ENTITY: user_input.get(CONF_VIGILANCE_ENTITY) or "",
                    CONF_VIGILANCE_MIN: user_input[CONF_VIGILANCE_MIN],
                }
            )
        entity = self._entry.options.get(CONF_VIGILANCE_ENTITY) or None
        minimum = self._entry.options.get(CONF_VIGILANCE_MIN) or DEFAULT_MIN
        entity_key = (
            vol.Optional(CONF_VIGILANCE_ENTITY, description={"suggested_value": entity})
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_VIGILANCE_MIN, default=minimum): sel.SelectSelector(
                    sel.SelectSelectorConfig(
                        options=list(MIN_CHOICES),
                        translation_key="vigilance_min",
                        mode=sel.SelectSelectorMode.LIST,
                    )
                ),
                entity_key: sel.EntitySelector(sel.EntitySelectorConfig(domain="sensor")),
            }
        )
        return self.async_show_form(step_id="vigilance", data_schema=schema)

    # -- apparence ----------------------------------------------------------
    async def async_step_apparence(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self._save(**{CONF_STYLE: user_input[CONF_STYLE]})
        current = self._entry.options.get(CONF_STYLE) or DEFAULT_STYLE
        schema = vol.Schema(
            {
                vol.Required(CONF_STYLE, default=current): sel.SelectSelector(
                    sel.SelectSelectorConfig(
                        options=STYLES,
                        translation_key="style",
                        mode=sel.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="apparence", data_schema=schema)

    # -- climatisation --------------------------------------------------------
    async def async_step_climatisation(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self._save(
                **{
                    CONF_CLIMATE: user_input[CONF_CLIMATE],
                    CONF_AIR: bool(user_input.get(CONF_AIR, True)),
                }
            )
        climate = self._entry.options.get(CONF_CLIMATE) or DEFAULT_CLIMATE
        air = self._entry.options.get(CONF_AIR, True)
        schema = vol.Schema(
            {
                vol.Required(CONF_CLIMATE, default=climate): sel.EntitySelector(
                    sel.EntitySelectorConfig(domain="climate")
                ),
                vol.Required(CONF_AIR, default=air): sel.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="climatisation", data_schema=schema)
