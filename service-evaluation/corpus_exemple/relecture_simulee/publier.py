"""Inscrit dans Langfuse la relecture simulée du métier, pour le banc d'essai.

Dans un vrai projet, le métier note lui-même dans Langfuse (Annotation Queues). Ici, le corpus et l'entreprise sont
fictifs : Claude a joué le rôle du métier, et ses notes sont écrites dans deux fichiers de ce dossier, avec leur raison :
- verdicts_metier.json : les réponses de la file « verification-juge », notées juste, partielle ou fausse ;
- justesse_graphe.json : les relations de la file « justesse-graphe », jugées juste ou fausse.
Ce script crée les mêmes scores que le métier créerait dans l'interface (verdict_metier, justesse_relation).

Usage, depuis service-evaluation/, après « kit verifier-juge --envoyer » et « kit verifier-graphe --envoyer » :
    uv run python corpus_exemple/relecture_simulee/publier.py
puis « kit verifier-juge » et « kit verifier-graphe » calculent l'accord du juge et la justesse du graphe.

Par défaut : le dernier corpus importé (--corpus pour un autre), et les versions du RAG notées dans les deux fichiers
(--rag-juge, --rag-graphe pour d'autres). Les notes correspondent aux réponses du RAG d'exemple obtenues par l'auteur :
si votre RAG a répondu autrement, certaines notes ne vont plus avec la réponse notée, et l'accord mesuré n'a plus de sens.
"""

import argparse

import json
from pathlib import Path

from kit.commandes import le_plus_recent
from kit.config import charger_config, client_langfuse
from kit.etape_1_evaluation_ingestion import graphe
from kit.etape_3_evaluation_reponse import relecture
from kit.etape_5_resultats import publication

ICI = Path(__file__).resolve().parent
COMMENTAIRE = "Relecture simulée par Claude (banc d'essai, aucun avis métier réel) : "


def dossier_rag(option: str | None, notes: dict) -> Path:
    """La sortie du RAG notée : celle donnée en option, sinon celle écrite dans le fichier des notes."""
    dossier = Path(option) if option else Path("sorties/sorties_rag") / notes["version_rag"]
    if not dossier.is_dir():
        raise SystemExit(f"{dossier} n'existe pas : les notes visent la version « {notes['version_rag']} » du RAG. "
                         f"Évaluer cette version (kit evaluer), ou donner une autre sortie du RAG en option.")
    return dossier


def main() -> None:
    options = argparse.ArgumentParser(description="Inscrit dans Langfuse la relecture simulée du métier.")
    options.add_argument("--corpus", help="le dossier corpus/<version>/ ; par défaut, le dernier importé")
    options.add_argument("--rag-juge", help="la sortie du RAG notée pour vérifier le juge")
    options.add_argument("--rag-graphe", help="la sortie du RAG (hybride) dont les relations sont jugées")
    arguments = options.parse_args()
    config = charger_config()
    langfuse = client_langfuse(config)
    corpus = Path(arguments.corpus) if arguments.corpus else le_plus_recent(config, "corpus")

    # 1. Les réponses notées pour vérifier le juge
    notes = json.loads((ICI / "verdicts_metier.json").read_text(encoding="utf-8"))
    ev = publication.Evaluation(config, corpus, dossier_rag(arguments.rag_juge, notes))
    traces = publication.experience_langfuse(ev, langfuse)["traces"]
    config_verdict = relecture.config_verdict(langfuse)
    for q, n in notes["verdicts"].items():
        langfuse.create_score(trace_id=traces[q], name=relecture.CONFIG_VERDICT, value=n["verdict"],
                              data_type="CATEGORICAL", config_id=config_verdict, comment=COMMENTAIRE + n["raison"],
                              score_id=f"simule-verdict-{ev.evaluation_id}-{q}"[:200])
    print(f"verification-juge : {len(notes['verdicts'])} verdicts inscrits.")

    # 2. Les relations du graphe, jugées d'après leur passage source
    notes = json.loads((ICI / "justesse_graphe.json").read_text(encoding="utf-8"))
    ev = publication.Evaluation(config, corpus, dossier_rag(arguments.rag_graphe, notes))
    envoyees = json.loads((ev.dossier / graphe.ECHANTILLON).read_text(encoding="utf-8"))
    par_relation = {(r["texte"], r["reference_source"], r["page"]): r["trace_id"] for r in envoyees}
    config_justesse = graphe.config_justesse(langfuse)
    for i, n in enumerate(notes["relations"]):
        trace = par_relation[(n["relation"], n["reference_source"], n["page"])]
        langfuse.create_score(trace_id=trace, name=graphe.CONFIG_JUSTESSE, value=n["verdict"], data_type="CATEGORICAL",
                              config_id=config_justesse, comment=COMMENTAIRE + n["raison"],
                              score_id=f"simule-justesse-{ev.evaluation_id}-{i}"[:200])
    print(f"justesse-graphe : {len(notes['relations'])} relations jugées inscrites.")
    langfuse.flush()


if __name__ == "__main__":
    main()
