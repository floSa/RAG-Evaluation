"""Inscrit dans Langfuse la relecture simulée du métier, pour le banc d'essai.

Dans un vrai projet, le métier note lui-même dans Langfuse (Annotation Queues). Ici, le corpus et l'entreprise sont
fictifs : Claude a joué le rôle du métier, et ses notes sont écrites dans deux fichiers de ce dossier, avec leur raison :
- verdicts_metier.json : les réponses de la file « verification-juge », notées juste, partielle ou fausse ;
- justesse_graphe.json : les relations de la file « justesse-graphe », jugées juste ou fausse.
Ce script crée les mêmes scores que le métier créerait dans l'interface (verdict_metier, justesse_relation).

Usage, après « kit verifier-juge --envoyer » et « kit verifier-graphe --envoyer » :
    uv run python corpus_exemple/relecture_simulee/publier.py
puis « kit verifier-juge » et « kit evaluer-ingestion » calculent l'accord du juge et la justesse du graphe.
"""

import json
from pathlib import Path

from kit.config import charger_config, client_langfuse
from kit.etape_1_evaluation_ingestion import graphe
from kit.etape_3_evaluation_reponse import relecture
from kit.etape_5_resultats import publication

ICI = Path(__file__).resolve().parent
CORPUS = Path("sorties/corpus/2026-11-20.1")
COMMENTAIRE = "Relecture simulée par Claude (banc d'essai, aucun avis métier réel) : "


def main() -> None:
    config = charger_config()
    langfuse = client_langfuse(config)

    # 1. Les réponses notées pour vérifier le juge
    notes = json.loads((ICI / "verdicts_metier.json").read_text(encoding="utf-8"))
    ev = publication.Evaluation(config, CORPUS, Path("sorties/sorties_rag") / notes["evaluation"].split("_", 1)[1])
    traces = publication.experience_langfuse(ev, langfuse)["traces"]
    config_verdict = relecture.config_verdict(langfuse)
    for q, n in notes["verdicts"].items():
        langfuse.create_score(trace_id=traces[q], name=relecture.CONFIG_VERDICT, value=n["verdict"],
                              data_type="CATEGORICAL", config_id=config_verdict, comment=COMMENTAIRE + n["raison"],
                              score_id=f"simule-verdict-{ev.evaluation_id}-{q}"[:200])
    print(f"verification-juge : {len(notes['verdicts'])} verdicts inscrits.")

    # 2. Les relations du graphe, jugées d'après leur passage source
    notes = json.loads((ICI / "justesse_graphe.json").read_text(encoding="utf-8"))
    ev = publication.Evaluation(config, CORPUS, Path("sorties/sorties_rag") / notes["evaluation"].split("_", 1)[1])
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
