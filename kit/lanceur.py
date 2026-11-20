"""Le lanceur : fait tourner un RAG écrit en Python par son connecteur, et écrit lui-même les fichiers du contrat.

Le connecteur est désigné par son chemin d'import (« rag_demo.connecteur:Connecteur ») : le kit ne l'importe
qu'au moment de l'exécution, par son nom ; il ne dépend d'aucun RAG. Un RAG écrit dans un autre langage
produit lui-même les fichiers de sorties_rag/<version_rag>/ et passe directement à `kit verifier-contrat`.
"""

import importlib
import json
import time
from pathlib import Path

from kit import contrat


def charger_connecteur(chemin: str, parametres: dict):
    """« module:Classe » → une instance de la classe, construite avec les paramètres donnés."""
    module, _, classe = chemin.partition(":")
    if not classe:
        raise ValueError(f"Connecteur « {chemin} » : écrire « module:Classe », par exemple rag_demo.connecteur:Connecteur.")
    return getattr(importlib.import_module(module), classe)(**parametres)


def lancer(connecteur, dossier_corpus: Path, dossier_sorties: Path, afficher=print) -> Path:
    """Exporte l'index, pose toutes les questions du corpus avec leur profil, et écrit sorties_rag/<version_rag>/."""
    rag = connecteur.decrire()
    dossier = dossier_sorties / "sorties_rag" / rag["version_rag"]
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "rag.json").write_text(json.dumps(rag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contrat.ecrire_jsonl(dossier / "chunks.jsonl", connecteur.exporter_index())
    pages = connecteur.exporter_pages()
    if pages:
        contrat.ecrire_jsonl(dossier / "pages_extraites.jsonl", pages)
    connecteur.exporter_graphe(dossier / "graphe.ttl")

    questions = contrat.charger_corpus(dossier_corpus)["questions"]
    par_id = {q["question_id"]: q for q in questions}
    recherches, reponses = [], []
    for q in questions:  # toutes les questions, y compris les réservées à la décision
        historique = contrat.historique(q, par_id)
        debut = time.perf_counter()
        resultats = connecteur.rechercher(q["question"], q["profil"], historique)
        duree = round((time.perf_counter() - debut) * 1000)
        recherches.append({"question_id": q["question_id"], "profil": q["profil"], "k": rag["k"],
                           "resultats": resultats, "duree_ms": duree})
        reponse = connecteur.repondre(q["question"], q["profil"], historique)
        reponses.append({"question_id": q["question_id"], **reponse})
        afficher(f"  {q['question_id']} : {reponse['duree_ms']} ms{' (abstention)' if reponse['abstention'] else ''}")
    contrat.ecrire_jsonl(dossier / "recherches.jsonl", recherches)
    contrat.ecrire_jsonl(dossier / "reponses.jsonl", reponses)
    return dossier
