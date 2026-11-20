"""Comparer deux évaluations (document 3, section 9) : écarts de scores, questions gagnées et perdues.

Deux évaluations ne se comparent que sur la même version du corpus. Un écart plus petit que la marge d'erreur ne
prouve rien seul : on regarde alors question par question, et le test de McNemar dit si l'écart peut être dû au hasard.
Une question de gravité forte perdue est une régression, même si la moyenne monte.
"""

import json
import math
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from kit import base


def mcnemar_exact(gagnees: int, perdues: int) -> float | None:
    """Valeur p bilatérale du test exact de McNemar (loi binomiale sur les questions qui changent)."""
    n = gagnees + perdues
    if n == 0:
        return None
    k = min(gagnees, perdues)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def verdicts(config: dict, evaluation_id: str, score: str) -> dict[str, float]:
    """Valeur d'un score par question (questions non réservées seulement)."""
    with Session(base.moteur(config["chemins"]["base"])) as session:
        lignes = session.scalars(select(base.Resultat).where(base.Resultat.evaluation_id == evaluation_id,
                                                             base.Resultat.score == score,
                                                             base.Resultat.reservee.is_(False))).all()
    return {l.question_id: l.valeur for l in lignes if l.valeur is not None}


def comparer(config: dict, dossier_a: Path, dossier_b: Path) -> dict:
    a = json.loads((dossier_a / "evaluation.json").read_text(encoding="utf-8"))
    b = json.loads((dossier_b / "evaluation.json").read_text(encoding="utf-8"))
    if a["version_corpus"] != b["version_corpus"]:
        raise ValueError(f"Corpus différents ({a['version_corpus']} et {b['version_corpus']}) : les évaluations ne se "
                         f"comparent pas.")
    sa = {s["score"]: s for s in json.loads((dossier_a / "scores.json").read_text(encoding="utf-8"))["scores"]}
    sb = {s["score"]: s for s in json.loads((dossier_b / "scores.json").read_text(encoding="utf-8"))["scores"]}
    ecarts = []
    for score in [s for s in sa if s in sb]:
        va, vb = sa[score]["valeur"], sb[score]["valeur"]
        if va is None or vb is None:
            continue
        marge = max(sa[score]["marge"] or 0, sb[score]["marge"] or 0) or None
        ecarts.append({"score": score, "a": va, "b": vb, "ecart": round(vb - va, 4), "marge": marge,
                       "significatif_seul": None if marge is None else abs(vb - va) > marge})
    questions = {}
    for score in ("n2_reussite_k", "n3_exactitude", "n4_score_pondere"):
        qa, qb = verdicts(config, a["evaluation_id"], score), verdicts(config, b["evaluation_id"], score)
        communes = sorted(set(qa) & set(qb))
        gagnees = [q for q in communes if qb[q] > qa[q]]
        perdues = [q for q in communes if qb[q] < qa[q]]
        questions[score] = {"gagnees": gagnees, "perdues": perdues, "n": len(communes),
                            "mcnemar_p": mcnemar_exact(len(gagnees), len(perdues))}
    return {"a": a["evaluation_id"], "b": b["evaluation_id"], "rag_a": a["rag"], "rag_b": b["rag"],
            "ecarts": ecarts, "questions": questions}
