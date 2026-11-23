"""Endpoint 4 — répondre : ENTRÉE une question, SORTIE la réponse, ses sources, l'abstention et la trace.

Ce qu'elle reçoit : question, profil, historique (l'échange précédent).
Ce qu'elle rend :
    reponse, abstention (vrai si le RAG dit ne pas savoir),
    chunks_cites (les chunks cités), chunks_contexte (ceux donnés au modèle),
    duree_ms, cout (en euros), tokens_entree, tokens_sortie,
    trace_id (la trace Langfuse de la réponse, si le RAG en envoie)
"""

import uuid

from rag.assistant import Assistant


def repondre(assistant: Assistant, question: str, profil: str, historique: list[dict]) -> dict:
    r = assistant.demander(question, profil, historique)
    m = assistant.config["modeles"]["generation"]
    entree, sortie = r["tokens"]
    if assistant.langfuse:
        assistant.langfuse.flush()
    return {"reponse": r["reponse"], "abstention": r["abstention"],
            "chunks_cites": [c["chunk_id"] for c in r["cites"]],
            "chunks_contexte": [c["chunk_id"] for c in r["contexte"]],
            "duree_ms": r["duree_ms"],
            "cout": (entree * m["prix_entree_eur_par_million"] + sortie * m["prix_sortie_eur_par_million"]) / 1e6,
            "tokens_entree": entree, "tokens_sortie": sortie,
            "trace_id": r["trace_id"] or uuid.uuid4().hex}
