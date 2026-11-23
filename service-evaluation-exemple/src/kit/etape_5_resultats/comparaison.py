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
    a = json.loads((dossier_a / "fichiers_techniques" / "evaluation.json").read_text(encoding="utf-8"))
    b = json.loads((dossier_b / "fichiers_techniques" / "evaluation.json").read_text(encoding="utf-8"))
    if a["version_corpus"] != b["version_corpus"]:
        raise ValueError(f"Corpus différents ({a['version_corpus']} et {b['version_corpus']}) : les évaluations ne se "
                         f"comparent pas.")
    sa = {s["score"]: s for s in json.loads((dossier_a / "fichiers_techniques" / "scores.json").read_text(encoding="utf-8"))["scores"]}
    sb = {s["score"]: s for s in json.loads((dossier_b / "fichiers_techniques" / "scores.json").read_text(encoding="utf-8"))["scores"]}
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


# --- RAPPORT.md de la comparaison -------------------------------------------------------------

# Les scores montrés dans le rapport, dans l'ordre des évaluations (tous sont dans comparaison.json).
PRINCIPAUX = ["n1_passages_rattaches", "n1_erreur_caracteres", "n2_reussite_k", "n2_rappel_k", "n2_fuite_droits",
              "n3_exactitude", "n3_valeurs", "n3_fidelite", "n3_abstention_correcte", "n3_erreurs_graves", "n3_synthese",
              "n4_score_pondere", "n4_temps_median", "n4_cout_moyen"]


def differences(rag_a: dict, rag_b: dict) -> list[str]:
    """Les réglages déclarés par le RAG qui diffèrent entre A et B."""
    champs = [("type_rag", "type", rag_a.get("type_rag"), rag_b.get("type_rag")), ("k", "k", rag_a.get("k"), rag_b.get("k"))]
    va, vb = rag_a.get("versions", {}), rag_b.get("versions", {})
    champs += [(c, c, va.get(c), vb.get(c)) for c in sorted(set(va) | set(vb)) if c != "index"]
    ra, rb = rag_a.get("reglages", {}), rag_b.get("reglages", {})
    champs += [(c, c.replace("_", " "), ra.get(c), rb.get(c)) for c in sorted(set(ra) | set(rb))]
    from kit.etape_5_resultats.rapport import valeur_reglage

    return [f"{nom} : {valeur_reglage(a)} → {valeur_reglage(b)}" for _, nom, a, b in champs if a != b]


def ecart(score: str, a: float, b: float) -> str:
    from kit.etape_5_resultats.rapport import TEMPS, nombre, proportion

    d = b - a
    if round(d, 4) == 0:
        return "aucun"
    signe = "+" if d > 0 else "−"
    if score in TEMPS:
        return f"{signe}{nombre(abs(d) / 1000, 1)} s"
    if score == "n4_cout_moyen":
        return f"{signe}{nombre(abs(d), 2)} €"
    if proportion(score):
        return f"{signe}{nombre(abs(d) * 100)} points"
    return f"{signe}{nombre(abs(d))}"


def markdown(r: dict, questions: dict) -> str:
    from kit.etape_5_resultats.rapport import configuration, libelle, tableau, texte_valeur, nombre

    diff = differences(r["rag_a"], r["rag_b"])
    m = ["# Comparaison de deux configurations", "",
         "Ce rapport compare deux configurations du RAG, évaluées sur le même corpus, avec les mêmes questions. Il "
         "répond à une question : **la configuration B fait-elle mieux que la configuration A ?** Il ne dit pas si "
         "l'une ou l'autre peut partir en production : c'est le métier qui le décide, à la lecture du rapport "
         "d'évaluation de chacune.", "",
         *tableau(["", "A", "B"], [["Configuration", f"`{r['rag_a']['version_rag']}`", f"`{r['rag_b']['version_rag']}`"],
                                   ["Réglages", configuration(r["rag_a"]), configuration(r["rag_b"])]]), "",
         "**Ce qui change de A à B** : " + ("; ".join(diff) if diff else
                                           "aucun des réglages déclarés par le RAG. Seule l'empreinte de version "
                                           "change : un réglage que le RAG ne déclare pas a été modifié") + ".", "",
         "## 1. Les scores", "",
         "Sur les questions de réglage. Un écart plus petit que la marge d'erreur ne prouve rien à lui seul.", ""]
    lignes = []
    for x in sorted((x for x in r["ecarts"] if x["score"] in PRINCIPAUX), key=lambda x: PRINCIPAUX.index(x["score"])):
        reel = {True: "oui : plus grand que la marge", False: "non prouvé : dans la marge"}.get(x["significatif_seul"], "—")
        if round(x["b"] - x["a"], 4) == 0:
            reel = "—"
        lignes.append([libelle(x["score"]), texte_valeur(x["score"], x["a"]), texte_valeur(x["score"], x["b"]),
                       ecart(x["score"], x["a"], x["b"]), reel])
    m += tableau(["Score", "A", "B", "Écart de A à B", "L'écart est-il réel ?"], lignes)
    m += ["", "## 2. Question par question", "",
          "Une moyenne peut cacher des mouvements : on regarde les questions que B gagne et celles qu'il perd par "
          "rapport à A. Le test de McNemar dit si ces mouvements peuvent venir du hasard : au-dessus de 0,05, on ne "
          "peut pas l'exclure.", ""]
    lignes, graves = [], []
    for score, q in r["questions"].items():
        p = q["mcnemar_p"]
        hasard = "—" if p is None else (f"oui (p = {nombre(p, 2)})" if p > 0.05 else f"peu probable (p = {nombre(p, 3)})")
        lignes.append([libelle(score), ", ".join(q["gagnees"]) or "aucune", ", ".join(q["perdues"]) or "aucune",
                       str(q["n"]), hasard])
        graves += [x for x in q["perdues"] if questions.get(x, {}).get("gravite") == "forte" and x not in graves]
    m += tableau(["Score", "Questions gagnées par B", "Questions perdues par B", "Sur", "Peut venir du hasard ?"], lignes)
    if graves:
        m += ["", f"**Attention** : B perd une ou plusieurs questions de gravité forte ({', '.join(graves)}). C'est une "
                  f"régression à regarder avant toute décision, même si la moyenne monte."]
    m += ["", "## 3. En résumé", ""]
    pondere = next((x for x in r["ecarts"] if x["score"] == "n4_score_pondere"), None)
    qp = r["questions"].get("n4_score_pondere")
    if pondere and qp:
        points = round((pondere["b"] - pondere["a"]) * 100)
        mouvement = ("fait jeu égal avec A" if points == 0 else
                     f"{'gagne' if points > 0 else 'perd'} {abs(points)} point(s) par rapport à A")
        resume = (f"Sur le score pondéré, B {mouvement} : {len(qp['gagnees'])} question(s) gagnée(s), "
                  f"{len(qp['perdues'])} perdue(s). ")
        if qp["mcnemar_p"] is None or qp["mcnemar_p"] > 0.05:
            resume += "Cet écart peut venir du hasard : aucune des deux configurations n'est démontrée meilleure."
        else:
            resume += "Cet écart est probablement réel."
        m.append(resume)
    m += ["", "Le détail de tous les scores est dans `fichiers_techniques/comparaison.json`.", ""]
    return "\n".join(m)
