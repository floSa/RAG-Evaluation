"""Inscrit la relecture simulée du métier, pour le banc d'essai.

Dans un vrai projet, le métier note lui-même les réponses du RAG, dans le fichier Excel verification_juge.xlsx que le
service lui prépare (ou, s'il préfère, dans Langfuse). Ici, le corpus et l'entreprise sont fictifs : Claude a joué le
rôle du métier, et ses notes sont écrites dans verdicts_metier.json, chacune avec sa raison. Ce script les écrit dans
le fichier verification_juge.xlsx, comme le métier l'aurait rempli.

Usage, depuis service-evaluation/, après « kit verifier-juge --preparer » :
    uv run python ../service-evaluation-exemple/corpus_annote/notes_du_metier_simulees/publier.py
puis « kit verifier-juge » calcule l'accord du juge.

Par défaut : le dernier corpus importé (--corpus pour un autre), et la version du RAG notée dans verdicts_metier.json
(--rag-juge pour une autre). Les notes correspondent aux réponses du RAG d'exemple obtenues par l'auteur : si votre RAG
a répondu autrement, certaines notes ne vont plus avec la réponse notée, et l'accord mesuré n'a plus de sens.
"""

import argparse
import json
from pathlib import Path

import openpyxl

from kit.commandes import le_plus_recent
from kit.config import charger_config
from kit.etape_3_evaluation_reponse import fichier_metier
from kit.etape_5_resultats import publication

ICI = Path(__file__).resolve().parent
COMMENTAIRE = "Relecture simulée par Claude (banc d'essai, aucun avis métier réel) : "


def main() -> None:
    options = argparse.ArgumentParser(description="Inscrit la relecture simulée du métier dans le fichier Excel.")
    options.add_argument("--dossier", default=".", help="le dossier du service ; par défaut, le dossier courant")
    options.add_argument("--corpus", help="le dossier corpus/<version>/ ; par défaut, le dernier importé")
    options.add_argument("--rag-juge", help="la sortie du RAG notée pour vérifier le juge")
    arguments = options.parse_args()
    config = charger_config(Path(arguments.dossier) / "config" / "kit.yaml")
    corpus = Path(arguments.corpus) if arguments.corpus else le_plus_recent(config, "corpus")

    notes = json.loads((ICI / "verdicts_metier.json").read_text(encoding="utf-8"))
    dossier_rag = Path(arguments.rag_juge) if arguments.rag_juge else \
        Path(config["chemins"]["resultats"]) / "reponses_du_rag" / notes["version_rag"]
    if not dossier_rag.is_dir():
        raise SystemExit(f"{dossier_rag} n'existe pas : les notes visent la version « {notes['version_rag']} » du RAG. "
                         f"Évaluer cette version (kit evaluer), ou donner une autre sortie du RAG avec --rag-juge.")
    ev = publication.Evaluation(config, corpus, dossier_rag)
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


if __name__ == "__main__":
    main()
