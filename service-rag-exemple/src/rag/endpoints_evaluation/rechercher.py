"""Endpoint 3 — rechercher : ENTRÉE une question, SORTIE les k chunks retrouvés, avant toute génération.

Ce qu'elle reçoit : question, profil (l'utilisateur ne voit que ses documents), historique (l'échange précédent).
Ce qu'elle rend : resultats, une liste de {chunk_id, rang, score}, et duree_ms.
"""

import time

from rag.assistant import Assistant


def rechercher(assistant: Assistant, question: str, profil: str, historique: list[dict]) -> dict:
    debut = time.perf_counter()
    trouves = assistant.rechercher(question, profil, historique)
    return {"resultats": [{"chunk_id": t["chunk"]["chunk_id"], "rang": t["rang"], "score": t["score"]} for t in trouves],
            "duree_ms": round((time.perf_counter() - debut) * 1000)}
