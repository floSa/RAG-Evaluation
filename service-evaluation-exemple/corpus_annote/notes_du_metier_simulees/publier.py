"""Inscrit la relecture simulée du métier, pour le banc d'essai.

Dans un vrai projet, le métier note lui-même : les réponses du RAG dans le fichier Excel verification_juge.xlsx, et les
relations du graphe dans Langfuse. Ici, le corpus et l'entreprise sont fictifs : Claude a joué le rôle du métier, et ses
notes sont écrites dans deux fichiers de ce dossier, avec leur raison :
- verdicts_metier.json : les réponses à noter pour vérifier le juge, notées juste, partielle ou fausse ; ce script les
  écrit dans le fichier verification_juge.xlsx, comme le métier l'aurait rempli ;
- justesse_graphe.json : les relations de la file « justesse-graphe », jugées juste ou fausse ; ce script crée les
  scores que le métier créerait dans Langfuse (justesse_relation).

Usage, depuis service-evaluation/, après « kit verifier-juge --preparer » et « kit verifier-graphe --envoyer » :
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
from kit.config import charger_config, client_langfuse
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
    options = argparse.ArgumentParser(description="Inscrit dans Langfuse la relecture simulée du métier.")
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

    # 2. Les relations du graphe, jugées d'après leur passage source
    try:
        langfuse = client_langfuse(config)
    except RuntimeError as erreur:      # sans Langfuse, seule la vérification du juge est faite
        print(f"justesse-graphe : ignorée ({erreur})")
        return
    notes = json.loads((ICI / "justesse_graphe.json").read_text(encoding="utf-8"))
    ev = publication.Evaluation(config, corpus, dossier_rag(arguments.rag_graphe, notes, config))
    envoyees = json.loads((ev.dossier / graphe.ECHANTILLON).read_text(encoding="utf-8"))
    par_relation = {(r["texte"], r["reference_source"], r["page"]): r["trace_id"] for r in envoyees}
    config_justesse = graphe.config_justesse(langfuse)
    absentes = 0
    for i, n in enumerate(notes["relations"]):
        trace = par_relation.get((n["relation"], n["reference_source"], n["page"]))
        if trace is None:  # relation jugée chez l'auteur, mais absente de l'échantillon envoyé ici
            absentes += 1
            continue
        langfuse.create_score(trace_id=trace, name=graphe.CONFIG_JUSTESSE, value=n["verdict"], data_type="CATEGORICAL",
                              config_id=config_justesse, comment=COMMENTAIRE + n["raison"],
                              score_id=f"simule-justesse-{ev.evaluation_id}-{i}"[:200])
    print(f"justesse-graphe : {len(notes['relations']) - absentes} relations jugées inscrites"
          + (f" ; {absentes} absentes de votre échantillon, ignorées." if absentes else "."))
    langfuse.flush()


if __name__ == "__main__":
    main()
