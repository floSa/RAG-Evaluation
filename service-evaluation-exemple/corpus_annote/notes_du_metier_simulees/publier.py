"""Inscrit la relecture simulée du métier, pour le banc d'essai.

Dans un vrai projet, le métier note lui-même, dans les fichiers Excel que le service lui prépare (ou, s'il préfère,
dans Langfuse) : verification_juge.xlsx pour les réponses du RAG, justesse_graphe.xlsx pour les relations du graphe. Ici, le corpus et l'entreprise sont fictifs : Claude a joué le rôle du métier, et ses
notes sont écrites dans deux fichiers de ce dossier, avec leur raison :
- verdicts_metier.json : les réponses à noter pour vérifier le juge, notées juste, partielle ou fausse ; ce script les
  écrit dans le fichier verification_juge.xlsx, comme le métier l'aurait rempli ;
- justesse_graphe.json : les relations tirées du graphe, jugées juste ou fausse ; ce script les écrit dans le fichier
  justesse_graphe.xlsx, comme le métier l'aurait rempli.

Usage, depuis service-evaluation/, après « kit verifier-juge --preparer » et « kit verifier-graphe --preparer » :
    uv run python ../service-evaluation-exemple/corpus_annote/notes_du_metier_simulees/publier.py
puis « kit verifier-juge » et « kit verifier-graphe » calculent l'accord du juge et la justesse du graphe.

Par défaut : le dernier corpus importé (--corpus pour un autre), et les versions du RAG notées dans les deux fichiers
(--rag-juge, --rag-graphe pour d'autres). Les notes correspondent aux réponses du RAG d'exemple obtenues par l'auteur :
si votre RAG a répondu autrement, certaines notes ne vont plus avec la réponse notée, et l'accord mesuré n'a plus de sens.
"""

import argparse

import openpyxl

import json
from pathlib import Path

from kit.commandes import le_plus_recent
from kit.config import charger_config
from kit.etape_1_evaluation_ingestion import graphe
from kit.etape_3_evaluation_reponse import fichier_metier
from kit.etape_5_resultats import publication

ICI = Path(__file__).resolve().parent
COMMENTAIRE = "Relecture simulée par Claude (banc d'essai, aucun avis métier réel) : "


def dossier_rag(option: str | None, notes: dict, config: dict) -> Path:
    """La sortie du RAG notée : celle donnée en option, sinon celle écrite dans le fichier des notes."""
    dossier = Path(option) if option else Path(config["chemins"]["resultats"]) / "reponses_du_rag" / notes["version_rag"]
    if not dossier.is_dir():
        raise SystemExit(f"{dossier} n'existe pas : les notes visent la version « {notes['version_rag']} » du RAG. "
                         f"Évaluer cette version (kit evaluer), ou donner une autre sortie du RAG en option.")
    return dossier


def main() -> None:
    options = argparse.ArgumentParser(description="Inscrit la relecture simulée du métier dans les fichiers Excel.")
    options.add_argument("--dossier", default=".", help="le dossier du service ; par défaut, le dossier courant")
    options.add_argument("--corpus", help="le dossier corpus/<version>/ ; par défaut, le dernier importé")
    options.add_argument("--rag-juge", help="la sortie du RAG notée pour vérifier le juge")
    options.add_argument("--rag-graphe", help="la sortie du RAG (hybride) dont les relations sont jugées")
    arguments = options.parse_args()
    config = charger_config(Path(arguments.dossier) / "config" / "kit.yaml")
    corpus = Path(arguments.corpus) if arguments.corpus else le_plus_recent(config, "corpus")

    # 1. Les réponses notées pour vérifier le juge : écrites dans le fichier Excel, comme le métier l'aurait rempli
    notes = json.loads((ICI / "verdicts_metier.json").read_text(encoding="utf-8"))
    ev = publication.Evaluation(config, corpus, dossier_rag(arguments.rag_juge, notes, config))
    fichier = ev.dossier / "verification_juge.xlsx"
    if not fichier.exists():
        raise SystemExit(f"{fichier} n'existe pas : lancer d'abord « kit verifier-juge --preparer ».")
    classeur = openpyxl.load_workbook(fichier)
    feuille = classeur[fichier_metier.FEUILLE]
    notees = 0
    for ligne in feuille.iter_rows(min_row=2):
        n = notes["verdicts"].get(ligne[0].value)
        if n:
            ligne[5].value, ligne[6].value = n["verdict"], COMMENTAIRE + n["raison"]
            notees += 1
    classeur.save(fichier)
    print(f"verification_juge.xlsx : {notees} réponses notées.")

    # 2. Les relations du graphe, jugées d'après leur passage source : écrites dans le fichier Excel
    notes = json.loads((ICI / "justesse_graphe.json").read_text(encoding="utf-8"))
    ev = publication.Evaluation(config, corpus, dossier_rag(arguments.rag_graphe, notes, config))
    fichier = ev.dossier / graphe.FICHIER
    if not fichier.exists():
        print(f"justesse-graphe : {fichier} n'existe pas ; lancer d'abord « kit verifier-graphe --preparer ».")
        return
    jugees = {(n["relation"], n["reference_source"], str(n["page"])): n for n in notes["relations"]}
    classeur = openpyxl.load_workbook(fichier)
    feuille = classeur[fichier_metier.FEUILLE_GRAPHE]
    ecrites = 0
    for ligne in feuille.iter_rows(min_row=2):
        n = jugees.get((ligne[0].value, ligne[1].value, str(ligne[2].value)))
        if n:
            ligne[4].value, ligne[5].value = n["verdict"], COMMENTAIRE + n["raison"]
            ecrites += 1
    classeur.save(fichier)
    print(f"justesse_graphe.xlsx : {ecrites} relations jugées, sur {len(notes['relations'])} jugées chez l'auteur.")

if __name__ == "__main__":
    main()
