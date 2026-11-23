"""Endpoint 1 — ingérer (ENTRÉE) : le service d'évaluation envoie ses documents, le RAG les indexe.

Ce qu'elle reçoit, pour chaque document :
    reference_source, titre, type_document, version,
    format         pdf_natif, pdf_scanne ou fiche_base
    droits_acces   le profil qui peut le voir : tous, maintenance…
    fichier        le nom du fichier
    contenu        le fichier lui-même, en base64
Ce qu'elle rend : le nombre de documents, de chunks et de pages, et la version de l'index.

Les documents sont rangés dans l'espace « evaluation » (sorties/evaluation/), jamais avec ceux de la production.
Si l'évaluation renvoie exactement les mêmes documents, avec les mêmes réglages, l'index déjà construit est gardé.
"""

import base64
import hashlib
import json
from pathlib import Path

from rag.assistant import dans_l_espace, indexer
from rag.endpoints_evaluation import ESPACE

CHAMPS = ("reference_source", "titre", "type_document", "version", "format", "droits_acces")


def ingerer(config: dict, documents: list[dict], afficher=print) -> dict:
    config = dans_l_espace(config, ESPACE)
    travail = Path(config["travail"])
    dossier = travail / "documents"
    dossier.mkdir(parents=True, exist_ok=True)
    liste = []
    for d in documents:
        nom = Path(d["fichier"]).name                      # le nom seul, jamais un chemin
        (dossier / nom).write_bytes(base64.b64decode(d["contenu"]))
        liste.append({c: d[c] for c in CHAMPS} | {"fichier": nom})

    # Mêmes documents, mêmes réglages : l'index est déjà là
    empreinte = hashlib.sha256(json.dumps(
        [documents, config["graphe"]["actif"], config["modeles"]["embeddings"]["modele"]],
        sort_keys=True).encode()).hexdigest()
    deja = travail / "ingestion.json"
    if deja.exists() and json.loads(deja.read_text(encoding="utf-8"))["empreinte"] == empreinte:
        return json.loads(deja.read_text(encoding="utf-8"))["resultat"] | {"deja_ingere": True}

    resultat = {"documents": len(liste)} | indexer({**config, "documents": str(dossier)}, afficher, liste)
    deja.write_text(json.dumps({"empreinte": empreinte, "resultat": resultat}, ensure_ascii=False), encoding="utf-8")
    return resultat | {"deja_ingere": False}
