"""Les files de relecture du métier dans Langfuse, et la vérification du juge (document 3, section 8 ; JUGE.md).

- `relecture-reponses` : réponses fausses ou partielles, gravité forte, 10 au hasard, désaccords du juge.
- `verification-juge` : 30 réponses tirées au hasard (hors réservées), notées par le métier sans voir la note du juge.
Le métier note dans Langfuse avec le score « verdict_metier » (juste, partielle, fausse).
"""

import math
import random

from langfuse.api import ConfigCategory

CONFIG_VERDICT = "verdict_metier"
CATEGORIES = {"juste": 1.0, "partielle": 0.5, "fausse": 0.0}


def config_verdict(langfuse) -> str:
    """Le score « verdict_metier » (catégoriel), créé s'il n'existe pas ; rend son identifiant."""
    for c in langfuse.api.score_configs.get(limit=100).data:
        if c.name == CONFIG_VERDICT and not c.is_archived:
            return c.id
    return langfuse.api.score_configs.create(
        name=CONFIG_VERDICT, data_type="CATEGORICAL",
        categories=[ConfigCategory(label=l, value=v) for l, v in CATEGORIES.items()],
        description="Verdict du métier sur une réponse du RAG : juste, partielle ou fausse (JUGE.md)").id


def file(langfuse, nom: str, description: str) -> str:
    """La file de relecture, créée si elle n'existe pas ; rend son identifiant."""
    for q in langfuse.api.annotation_queues.list_queues(limit=100).data:
        if q.name == nom:
            return q.id
    return langfuse.api.annotation_queues.create_queue(name=nom, description=description,
                                                       score_config_ids=[config_verdict(langfuse)]).id


def envoyer(langfuse, nom: str, description: str, trace_ids: list[str]) -> int:
    """Ajoute des traces à une file, sans doublon ; rend le nombre d'ajouts."""
    queue_id = file(langfuse, nom, description)
    deja, page = set(), 1
    while True:
        r = langfuse.api.annotation_queues.list_queue_items(queue_id, page=page, limit=100)
        deja |= {i.object_id for i in r.data}
        if page >= (r.meta.total_pages or 1):
            break
        page += 1
    nouveaux = [t for t in trace_ids if t and t not in deja]
    for t in nouveaux:
        langfuse.api.annotation_queues.create_queue_item(queue_id, object_id=t, object_type="TRACE")
    return len(nouveaux)


def echantillon(verdicts_juge: dict[str, str], taille: int, graine: int = 0) -> list[str]:
    """Les réponses à faire noter par le métier : tirées au hasard parmi celles notées par le juge."""
    ids = sorted(verdicts_juge)
    return sorted(random.Random(graine).sample(ids, min(taille, len(ids))))


def notes_metier(langfuse, trace_ids: list[str]) -> dict[str, str]:
    """Les verdicts saisis par le métier dans Langfuse, par trace (le plus récent si plusieurs)."""
    notes = {}
    for t in trace_ids:
        r = langfuse.api.scores.get_many(name=CONFIG_VERDICT, trace_id=t, limit=10)
        humains = sorted((s for s in r.data if libelle(s) in CATEGORIES), key=lambda s: s.timestamp)
        if humains:
            notes[t] = libelle(humains[-1])
    return notes


def libelle(score) -> str | None:
    """Le libellé d'un score catégoriel (selon la version de l'API : value ou string_value)."""
    for champ in ("string_value", "value"):
        v = getattr(score, champ, None)
        if isinstance(v, str):
            return v
    return None


def accord(juge: dict[str, str], metier: dict[str, str]) -> dict:
    """Taux d'accord (JUGE.md, ≥ 90 %) et kappa de Cohen (accord corrigé du hasard, CADRAGE.md décision 12)."""
    communs = sorted(set(juge) & set(metier))
    n = len(communs)
    if not n:
        return {"n": 0, "accord": None, "kappa": None, "desaccords": []}
    egaux = sum(juge[q] == metier[q] for q in communs)
    observe = egaux / n
    attendu = sum((sum(juge[q] == c for q in communs) / n) * (sum(metier[q] == c for q in communs) / n)
                  for c in CATEGORIES)
    kappa = None if math.isclose(attendu, 1) else (observe - attendu) / (1 - attendu)
    return {"n": n, "accord": round(observe, 4), "kappa": None if kappa is None else round(kappa, 4),
            "desaccords": [{"question_id": q, "juge": juge[q], "metier": metier[q]} for q in communs
                           if juge[q] != metier[q]]}
