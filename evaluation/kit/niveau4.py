"""Niveau 4 — Bout en bout (document 3, section 9) : score pondéré, erreurs graves, temps, coût.

Poids d'une question = fréquence × gravité d'une erreur (de 1 à 9).
Valeur d'une question pour le score pondéré (DECISIONS.md, décision 3) :
- réponse dans les documents : juste 1, partielle 0,5, fausse 0 ; une abstention vaut 0 ;
- pas de réponse, ou réponse non accessible au profil : 1 si le RAG s'abstient, 0 sinon.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from kit import base
from kit.juge import VALEUR_VERDICT
from kit.publication import Evaluation, Ligne

FREQUENCE = {"frequente": 3, "occasionnelle": 2, "rare": 1}
GRAVITE = {"forte": 3, "moyenne": 2, "faible": 1}


def lignes_niveau3(ev: Evaluation, scores: tuple[str, ...]) -> list:
    with Session(base.moteur(ev.config["chemins"]["base"])) as session:
        return session.scalars(select(base.Resultat).where(base.Resultat.evaluation_id == ev.evaluation_id,
                                                           base.Resultat.score.in_(scores))).all()


def evaluer(ev: Evaluation) -> list[Ligne]:
    n3 = lignes_niveau3(ev, ("n3_exactitude", "n3_erreurs_graves"))
    if not n3:
        raise RuntimeError("Aucun résultat du niveau 3 : lancer d'abord « kit niveau3 ».")
    verdicts = {r.question_id: r.verdict for r in n3 if r.score == "n3_exactitude"}
    reponses = {r["question_id"]: r for r in ev.fichier_rag("reponses.jsonl")}
    lignes = []
    for qid, q in ev.questions.items():
        r, a = reponses[qid], ev.attributs_question(qid)
        poids = FREQUENCE[q["frequence"]] * GRAVITE[q["gravite"]]
        if q["reponse_dans_documents"] == "oui":
            valeur = 0.0 if r["abstention"] else VALEUR_VERDICT.get(verdicts.get(qid))
            detail = "abstention" if r["abstention"] else verdicts.get(qid) or "non notée par le juge"
        else:
            valeur = float(r["abstention"])
            detail = "abstention correcte" if r["abstention"] else "a répondu au lieu de s'abstenir"
        lignes.append(Ligne("n4_score_pondere", valeur, qid, poids=poids, attributs=a,
                            detail=f"{detail} (poids {poids})"))
        lignes.append(Ligne("n4_temps_median", float(r["duree_ms"]), qid, attributs=a))
        lignes.append(Ligne("n4_temps_p95", float(r["duree_ms"]), qid, attributs=a))
        lignes.append(Ligne("n4_cout_moyen", float(r.get("cout") or 0), qid, attributs=a))
    for g in n3:
        if g.score == "n3_erreurs_graves":  # repris du niveau 3
            lignes.append(Ligne("n4_erreurs_graves", g.valeur, g.question_id, attributs=g.attributs, detail=g.detail))
    return lignes
