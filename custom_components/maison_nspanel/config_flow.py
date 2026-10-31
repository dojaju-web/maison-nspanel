"""Configuration (installation) et options (gestion des rappels) dans l'interface."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector as sel

from .const import CONF_RAPPELS, CONF_WEATHER, DOMAIN
from .rappels import DEFAULT_REMINDER, normalize

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

Tous les réglages (éclairage, rappels, météo, climatisation, aspirateur, apparence) \
se trouvent ensuite dans le panneau **Maison NSPanel** de la barre latérale.
"""


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
    """Simple renvoi : les réglages sont dans le panneau de la barre latérale."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=dict(self._entry.options))
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
