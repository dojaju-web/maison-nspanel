"""Constantes de l'intégration Maison NSPanel."""

DOMAIN = "maison_nspanel"

CONF_WEATHER = "weather_entity"
CONF_RAPPELS = "rappels"
CONF_VIGILANCE_ENTITY = "vigilance_entity"  # vide = détection automatique
CONF_VIGILANCE_MIN = "vigilance_min"
CONF_STYLE = "style"
CONF_CLIMATE = "climate_entity"
CONF_AIR = "air_enabled"
CONF_VACUUM = "vacuum_entity"
CONF_SECTIONS = "sections"

# Styles du dashboard : "verre" (verre sombre, défaut) ou "ardoise" (cartes sobres, titres en minuscules)
STYLES = ["verre", "ardoise"]
DEFAULT_STYLE = "verre"

# Les images météo du dashboard sont servies à cette adresse
STATIC_URL = "/maison_nspanel/meteo"

PREVISIONS_REFRESH_MINUTES = 30
PREVISIONS_RETRY_SECONDS = 120
