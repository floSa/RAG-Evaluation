# Le monde fictif du corpus d'exemple

Tout est inventé : entreprise, sites, personnes, équipements, références. Aucune donnée réelle. Ce document sert de référence commune à tous les documents sources, pour qu'ils soient cohérents entre eux (mêmes repères d'équipements, mêmes noms, mêmes procédures citées).

## L'entreprise

**Valtéra Industries**, fabricant fictif de pièces mécaniques, deux usines. Service **Maintenance électrique** (12 techniciens, chef de service : Hélène Morvan). Service **Exploitation** (conduite des installations, rondes, premiers constats).

| Site | Lieu | Particularités |
| --- | --- | --- |
| Site A | Usine de Lavernay | poste de livraison 20 kV, 2 transformateurs TR-A1 et TR-A2 (1 000 kVA chacun, 20 kV / 400 V), TGBT-A, 14 armoires divisionnaires AD-A01 à AD-A14, groupe électrogène GE-A (500 kVA), onduleur OND-A (60 kVA) |
| Site B | Usine de Brévannes | poste de livraison 20 kV, 1 transformateur TR-B1 (1 250 kVA, 20 kV / 400 V), TGBT-B, 9 armoires divisionnaires AD-B01 à AD-B09, groupe électrogène GE-B (400 kVA), pas d'onduleur centralisé |

Régime de neutre : TN-S sur le site A, IT sur le site B (avec contrôleur permanent d'isolement CPI-B). Ces différences entre sites sont voulues : elles créent des réponses différentes selon le site.

## Les personnes (fictives)

| Nom | Rôle |
| --- | --- |
| Hélène Morvan | cheffe du service Maintenance électrique |
| Karim Benali | technicien, habilité BR, B2V, H2V (site A) |
| Lucie Ferrand | technicienne, habilitée BR, BC, B2V (site B) |
| Thomas Rigaud | technicien, habilité BR, B1V (site A) |
| Nadia Coste | chargée de consignation HTA, habilitée HC, H2V (deux sites) |
| Paul Verdier | responsable Exploitation, site A |
| Sophie Lenoir | responsable Exploitation, site B |
| Bureau d'études Électrotech Conseil | prestataire (fictif) pour les études de sélectivité et la thermographie |

## Les références des documents

| Type | Préfixe | Source (feuille Listes) | Exemple |
| --- | --- | --- | --- |
| Procédure | `PR-` + 4 chiffres, et un indice de révision pour les versions | GED Valtéra | PR-1101 |
| Compte rendu d'intervention | `OT-` + numéro d'ordre de travail (5 chiffres) | GMAO Atlas | OT-24117 |
| Note technique | `NT-` + 3 chiffres | Archives techniques (notes anciennes, scannées) ou GED Valtéra | NT-042 |

Profils d'accès : `Tous les utilisateurs`, `Maintenance`, `Exploitation`.

## Les procédures (liste fixée : titres et numéros à reprendre tels quels)

| Référence | Titre | Droits |
| --- | --- | --- |
| PR-1101 | Consignation d'une armoire basse tension | Tous les utilisateurs |
| PR-1102 | Consignation d'un poste HTA 20 kV | **Maintenance** |
| PR-1103 | Remplacement d'un disjoncteur de départ dans une armoire divisionnaire | Tous les utilisateurs |
| PR-1104-B | Contrôle périodique des installations électriques (indice B, 2021, **remplacée**) | Tous les utilisateurs |
| PR-1104-C | Contrôle périodique des installations électriques (indice C, 2025, en vigueur) | Tous les utilisateurs |
| PR-1105 | Essais mensuels du groupe électrogène | Tous les utilisateurs |
| PR-1106 | Thermographie infrarouge des armoires électriques | Tous les utilisateurs |
| PR-1107 | Remplacement des batteries de l'onduleur OND-A | Tous les utilisateurs |
| PR-1108 | Recherche d'un défaut d'isolement en régime IT (site B) | Tous les utilisateurs |
| PR-1109 | Mesure de la résistance de la prise de terre | Tous les utilisateurs |
| PR-1110 | Remplacement d'un luminaire de sécurité (BAES) | Tous les utilisateurs |
| PR-1111 | Manœuvre de basculement sur le groupe électrogène | Tous les utilisateurs |
| PR-1112 | Gestion des habilitations électriques du personnel | Tous les utilisateurs |
| PR-1113 | Intervention sur un variateur de vitesse | Tous les utilisateurs |
| PR-1114 | Nettoyage et resserrage des connexions d'un TGBT | Tous les utilisateurs |
| PR-1115 | Contrôle des dispositifs différentiels (DDR) | Tous les utilisateurs |
| PR-1116 | Mise hors tension d'urgence d'un atelier | Tous les utilisateurs |

## Les notes techniques (liste fixée)

| Référence | Titre | Format | Droits |
| --- | --- | --- | --- |
| NT-031 | Étude de sélectivité du TGBT-A (2009) | PDF scanné | Tous les utilisateurs |
| NT-034 | Dimensionnement des câbles des ateliers du site B (2010) | PDF scanné | Tous les utilisateurs |
| NT-038 | Choix du régime de neutre IT pour le site B (2011) | PDF scanné | Tous les utilisateurs |
| NT-040 | Compensation de l'énergie réactive, site A (2013) | PDF scanné | Tous les utilisateurs |
| NT-042 | Règles d'éclairage de sécurité des ateliers (2014) | PDF scanné | Tous les utilisateurs |
| NT-051 | Réglages des protections du poste HTA | PDF natif | **Maintenance** |
| NT-053 | Plan de maintenance préventive électrique 2026 | PDF natif | Tous les utilisateurs |
| NT-055 | Retour d'expérience : échauffements constatés en thermographie 2023-2025 | PDF natif | Tous les utilisateurs |
| NT-057 | Architecture électrique du site A (avec schéma unifilaire simplifié, figure 1) | PDF natif | Tous les utilisateurs |
| NT-058 | Architecture électrique du site B (avec schéma unifilaire simplifié, figure 1) | PDF natif | Tous les utilisateurs |
| NT-060 | Durée de vie et remplacement des batteries d'onduleur | PDF natif | Tous les utilisateurs |
| NT-062 | Analyse des coupures de l'année 2025 | PDF natif | Tous les utilisateurs |
| NT-064 | Consommation électrique des ateliers et objectifs 2026 | PDF natif | Tous les utilisateurs |
| NT-066 | Pièces de rechange critiques : liste et stock minimal | PDF natif | Tous les utilisateurs |
| NT-068 | Mise à la terre des masses : règles et valeurs limites | PDF natif | Tous les utilisateurs |
| NT-070 | Procédure de crise en cas de perte totale d'alimentation | PDF natif | Tous les utilisateurs |

## Les comptes rendus d'intervention (fiches de la GMAO Atlas)

17 fiches, numéros OT-24101 à OT-24117, d'avril 2025 à octobre 2026, réparties sur les deux sites. Chaque fiche est un export « champ : valeur » de la base GMAO. Champs, dans cet ordre :

`Numéro OT`, `Date de l'intervention`, `Site`, `Équipement`, `Type d'intervention` (corrective, préventive, contrôle réglementaire), `Demandeur`, `Intervenant(s)`, `Durée (heures)`, `Symptôme constaté`, `Diagnostic`, `Actions réalisées`, `Pièces remplacées`, `Procédure appliquée` (une référence PR-…, ou « aucune »), `Coût des pièces (€ HT)`, `Remise en service`, `Suite à donner`.

Thèmes à faire revenir sur plusieurs fiches (pour les questions de synthèse) : échauffement de connexions repéré en thermographie ; déclenchements intempestifs de différentiels ; défauts d'isolement sur le site B ; batteries d'onduleur en fin de vie ; démarrage difficile d'un groupe électrogène.

Deux fiches sont réservées au profil **Maintenance** : OT-24109 et OT-24114 (interventions sur le poste HTA).

## Faits de référence (à respecter dans tous les documents)

| Sujet | Valeur en vigueur (PR-1104-C, 2025) | Ancienne valeur (PR-1104-B, 2021, remplacée) |
| --- | --- | --- |
| Thermographie des armoires | tous les 12 mois | tous les 24 mois |
| Test des dispositifs différentiels (DDR) | tous les 3 mois (bouton test) et mesure du temps de déclenchement tous les 12 mois | tous les 6 mois |
| Vérification réglementaire par organisme agréé | tous les 12 mois | tous les 12 mois |
| Essai du groupe électrogène | mensuel, 30 minutes, à au moins 50 % de sa puissance | mensuel, 15 minutes, à vide |
| Mesure de la prise de terre | tous les 12 mois ; valeur limite 10 Ω (site A), 30 Ω (site B) | tous les 24 mois ; valeur limite 10 Ω (les deux sites) |

| Sujet | Valeur |
| --- | --- |
| Écart de température en thermographie | ΔT < 10 °C : surveiller ; 10 à 30 °C : intervenir sous 1 mois ; > 30 °C : intervenir sous 48 heures |
| Couple de serrage des connexions du TGBT | 50 N·m pour les barres de 10 mm, 70 N·m pour les barres de 12 mm |
| Batteries de l'onduleur OND-A | 32 batteries 12 V 9 Ah ; durée de vie prévue 5 ans ; remplacement si autonomie < 8 minutes (autonomie nominale 15 minutes) |
| Seuil d'alarme du contrôleur d'isolement CPI-B (site B) | 50 kΩ (préalarme 100 kΩ) |
| Habilitation pour consigner en HTA | HC (chargé de consignation), avec un second intervenant H2V |
| Délai d'appel du groupe électrogène GE-A | démarrage et prise de charge en moins de 15 secondes |
| Coût horaire interne d'un technicien | 65 € HT |
