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
CONF_VAC_SENSORS = ("vac_battery", "vac_fan", "vac_area", "vac_time", "vac_alert", "vac_mode", "vac_water", "vac_drain", "vac_status")
CONF_SECTIONS = "sections"
CONF_BETA = "beta"

# Réglages du style NSPanel-Beta (valeurs par défaut)
BETA_DEFAULTS = {
    "diorama": True,         # maison animée en fond de l'accueil
    "effets": "auto",        # auto | reduits | complets | aucun (pluie, neige, nuages, brouillard, éclairs)
    "volets": "nuit",        # nuit | jamais | toujours
    "position": 72,          # 0-100 : hauteur de la maison sur un écran en hauteur (téléphone)
    "taille_heure": 13,      # 8-16 : taille de l'heure
    "rappels": True,         # pastilles de rappels (poubelles…) sous la date
    "meteo": "auto",         # auto | clair | eclaircies | nuageux | pluie | averse | orage | neige | brouillard (test)
    "moment": "auto",        # auto | jour | nuit (test)
}
BETA_EFFETS = ("auto", "reduits", "complets", "aucun")
BETA_VOLETS = ("nuit", "jamais", "toujours")
BETA_METEO = ("auto", "clair", "eclaircies", "nuageux", "pluie", "averse", "orage", "neige", "brouillard")
BETA_MOMENT = ("auto", "jour", "nuit")

# Styles du dashboard : "beta" (NSPanel-Beta, inspiré du Dashboard2-Demo), "verre" (verre sombre, défaut), "ardoise" (cartes sobres) ou "liquid" (affiché « iOS » : surfaces plates, menu flottant en verre)
STYLES = ["verre", "ardoise", "liquid", "beta"]
DEFAULT_STYLE = "verre"

# Les images météo du dashboard sont servies à cette adresse
STATIC_URL = "/maison_nspanel/meteo"

PREVISIONS_REFRESH_MINUTES = 30
PREVISIONS_RETRY_SECONDS = 120
