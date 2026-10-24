# Maison NSPanel

Complément Home Assistant pour le dashboard « verre sombre » du Sonoff NSPanel 86 (480×480).

- **Rappels modifiables dans l'interface** (ex. « Sortir les poubelles » le lundi) : plus besoin de toucher au code.
- **Images météo** fournies par l'intégration (aucune copie dans `/config/www`).
- **Prévisions 7 jours** : capteur `sensor.maison_nspanel_previsions`, sans template à écrire.
- Le dashboard complet (Accueil, Lumières, Climat, Prévisions) est livré dans `dashboard/maison_dashboard.yaml`.

## Prérequis
- HACS : `button-card` et `kiosk-mode`
- Intégration **Heure et date** (capteur `sensor.time`)
- `sun.sun` (par défaut) et une entité `weather.*`

## Installation

### Avec HACS (recommandé)
[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dojaju-web&repository=maison-nspanel&category=integration)

HACS > ⋮ > *Dépôts personnalisés* > `https://github.com/dojaju-web/maison-nspanel` (catégorie *Intégration*) > Télécharger, puis redémarrez Home Assistant.

### À la main
1. Copiez le dossier `custom_components/maison_nspanel` dans `/config/custom_components/`.
2. Redémarrez Home Assistant.
3. **Paramètres > Appareils et services > Ajouter une intégration > Maison NSPanel**, puis choisissez votre entité météo.
4. Une notification donne le bloc à ajouter dans `configuration.yaml` :

```yaml
lovelace:
  mode: storage
  dashboards:
    maison-nspanel:
      mode: yaml
      title: Maison
      icon: mdi:home
      show_in_sidebar: true
      filename: custom_components/maison_nspanel/dashboard/maison_dashboard.yaml
```
5. Redémarrez une dernière fois.

## Modifier les rappels
**Paramètres > Appareils et services > Maison NSPanel > Configurer** : ajouter, modifier ou supprimer un rappel
(texte, icône mdi, jours, plage horaire, couleur). Le changement est visible dans la minute.

## Remarques
- Les entités du dashboard (lumières, Sensibo…) sont celles de ma maison : adaptez-les en tête du fichier YAML.
- Sans l'intégration, le fichier `maison_dashboard.yaml` fonctionne seul (variable `rappels`, images dans `/config/www/meteo/`).

## Utiliser Météo-France (ou une autre météo)
1. Ajoutez l'intégration officielle **Météo-France** (Paramètres > Appareils et services). Elle crée une entité `weather.<votre_ville>`.
2. **Maison NSPanel > Configurer > Météo** : choisissez cette entité. Le dashboard (accueil, images, prévisions) la suit automatiquement, sans modifier le YAML.

## Vigilance Météo-France
L'intégration Météo-France crée un capteur par département (ex. `sensor.84_weather_alert`, activé par défaut).
Le dashboard affiche une pastille « Vigilance JAUNE / ORANGE / ROUGE » avec les phénomènes concernés (orages, vent violent…) sur l'accueil et en haut des prévisions.

**Réglage dans l'interface** : Paramètres > Appareils et services > Maison NSPanel > Configurer > *Vigilance Météo-France*
- **Afficher à partir du niveau** : jamais / jaune (défaut) / orange / rouge / toujours (même vert).
- **Capteur de vigilance** : optionnel, laissez vide pour le détecter automatiquement.

L'intégration expose le résultat dans `sensor.maison_nspanel_vigilance` (état : vert, jaune, orange, rouge).

## Style du dashboard
**Configurer > Apparence** :
- **Verre sombre** (défaut) : cartes teintées, titres en capitales italiques, photo météo en fond d'accueil.
- **Ardoise** : cartes plates et très sombres sans bordure, éclairées d'un dégradé de couleur quand elles sont actives, petits sous-titres en capitales grises, titres en minuscules, pastilles d'icône sans halo, photo météo d'accueil conservée, boutons de l'accueil en larges tuiles horizontales (icône, sous-titre, titre, pastille d'état).

Le changement s'applique après rechargement de la page du panneau.


## Publier une nouvelle version (mainteneur)
Augmentez `version` dans `custom_components/maison_nspanel/manifest.json` puis poussez sur `main` :
l'action *Release* crée seule la release `vX.Y.Z`, ce qui permet à HACS de proposer la mise à jour.
