"""Lecture de la configuration du kit : config/kit.yaml, config/seuils.json et les clés de .env."""

import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

CHEMIN_CONFIG = Path("config/kit.yaml")


def charger_config(chemin: Path | str = CHEMIN_CONFIG) -> dict:
    """Lit kit.yaml et charge .env dans l'environnement (sans écraser une variable déjà définie)."""
    load_dotenv()
    with open(chemin, encoding="utf-8") as f:
        return yaml.safe_load(f)


def charger_seuils(config: dict) -> dict:
    """Lit seuils.json : pour chaque score, {seuil, sens, bloquant}."""
    with open(config["chemins"]["seuils"], encoding="utf-8") as f:
        return json.load(f)


def cle(nom_variable: str) -> str:
    """Rend la clé lue dans l'environnement ; erreur claire si elle manque."""
    valeur = os.environ.get(nom_variable)
    if not valeur:
        raise RuntimeError(f"Variable {nom_variable} absente : la renseigner dans .env (voir .env.example).")
    return valeur


def client_langfuse(config: dict):
    """Client Langfuse, avec l'adresse et les clés lues dans .env (noms de variables dans kit.yaml)."""
    from langfuse import Langfuse

    lf = config["langfuse"]
    return Langfuse(public_key=cle(lf["variable_cle_publique"]), secret_key=cle(lf["variable_cle_secrete"]),
                    base_url=cle(lf["variable_adresse"]))
