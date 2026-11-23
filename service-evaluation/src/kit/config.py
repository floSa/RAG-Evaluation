"""Lecture de la configuration du kit : config/kit.yaml, config/seuils.json et les clés de .env."""

import json
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Le dossier du service : celui qui contient config/, corpus_annote/ et resultats/. Par défaut, le dossier courant ;
# « kit --dossier ../service-evaluation-exemple … » travaille sur l'exemple.
DOSSIER = Path(".")


def charger_config(chemin: Path | str | None = None) -> dict:
    """Lit <dossier>/config/kit.yaml et charge .env (sans écraser une variable déjà définie).
    Les chemins de kit.yaml sont relatifs au dossier du service : ils sont rendus ici depuis ce dossier."""
    load_dotenv()
    chemin = Path(chemin) if chemin else DOSSIER / "config" / "kit.yaml"
    with open(chemin, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    dossier = chemin.resolve().parent.parent
    for cle_chemin, valeur in config.get("chemins", {}).items():
        if cle_chemin == "base" and valeur.startswith("sqlite:///") and not valeur[10:].startswith("/"):
            config["chemins"]["base"] = f"sqlite:///{dossier / valeur[10:]}"
        elif cle_chemin != "base" and not Path(valeur).is_absolute():
            config["chemins"][cle_chemin] = str(dossier / valeur)
    if config.get("graphe", {}).get("formes") and not Path(config["graphe"]["formes"]).is_absolute():
        config["graphe"]["formes"] = str(dossier / config["graphe"]["formes"])
    return config


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
