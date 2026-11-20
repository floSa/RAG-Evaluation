"""Tests du niveau 4, de l'agrégation des scores, de la décision et de la comparaison."""

import math

import pytest

from kit.comparaison import mcnemar_exact
from kit.niveau4 import FREQUENCE, GRAVITE
from kit.publication import Ligne, agreger, calculer_scores, marge

SEUILS = {"n4_score_pondere": {"seuil": 0.8, "sens": "min", "bloquant": False},
          "n3_erreurs_graves": {"seuil": 0, "sens": "max", "bloquant": True},
          "n4_temps_median": {"seuil": 15000, "sens": "max", "bloquant": False}}


def ligne(score, valeur, qid, reservee=False, poids=None):
    l = Ligne(score, valeur, qid, poids=poids)
    l.reservee = reservee
    return l


def test_poids_frequence_fois_gravite():
    # document 3, section 9 : fréquente × forte = 9 ; rare × faible = 1
    assert FREQUENCE["frequente"] * GRAVITE["forte"] == 9 and FREQUENCE["rare"] * GRAVITE["faible"] == 1


def test_score_pondere():
    # une question fréquente et grave juste (poids 9), une rare sans gravité fausse (poids 1), une partielle (poids 2)
    lignes = [ligne("n4_score_pondere", 1.0, "A", poids=9), ligne("n4_score_pondere", 0.0, "B", poids=1),
              ligne("n4_score_pondere", 0.5, "C", poids=2)]
    assert agreger("n4_score_pondere", lignes) == (pytest.approx((9 + 1) / 12), 3)


def test_mediane_p95_somme():
    temps = [ligne("n4_temps_p95", float(t), f"Q{t}") for t in range(1, 21)]
    assert agreger("n4_temps_p95", temps)[0] == 19.0          # 95 % des 20 questions répondent en 19 au plus
    assert agreger("n4_temps_median", [ligne("n4_temps_median", v, "q") for v in (1, 2, 10)])[0] == 2
    assert agreger("n3_erreurs_graves", [ligne("n3_erreurs_graves", v, "q") for v in (1, 0, 1)]) == (2, 3)


def test_marge_document_3():
    # ± 1,96 √(p(1−p)/n) : 50 questions à 50 % → ± 13,9 points ; pas de marge pour un nombre
    assert marge("n3_exactitude", 0.5, 50) == pytest.approx(1.96 * math.sqrt(0.25 / 50), abs=1e-4)
    assert marge("n3_erreurs_graves", 2, 50) is None


def test_decision_reservees_et_bloquants():
    lignes = [ligne("n4_score_pondere", 1.0, "R1", poids=1), ligne("n4_score_pondere", 1.0, "R2", poids=1),
              ligne("n4_score_pondere", 0.0, "R3", reservee=True, poids=1),
              ligne("n3_erreurs_graves", 0.0, "R1"), ligne("n3_erreurs_graves", 1.0, "R3", reservee=True)]
    r = calculer_scores(lignes, SEUILS)
    pondere = next(s for s in r["scores"] if s["score"] == "n4_score_pondere")
    assert pondere["valeur"] == 1.0 and pondere["atteint"] is True       # réglage : questions non réservées
    decision = {x["score"]: x for x in r["decision"]["seuils"]}
    assert decision["n4_score_pondere"]["valeur"] == 0.0                # décision : questions réservées
    # une erreur grave sur une question réservée bloque quand même
    assert r["decision"]["criteres_bloquants_declenches"] == [{"score": "n3_erreurs_graves", "valeur": 1.0, "seuil": 0}]
    assert r["decision"]["mise_en_production_possible"] is False


@pytest.mark.parametrize("gagnees, perdues, p", [(0, 0, None), (5, 5, 1.0), (10, 0, 2 / 1024), (6, 1, 0.125)])
def test_mcnemar_exact(gagnees, perdues, p):
    assert mcnemar_exact(gagnees, perdues) == (None if p is None else pytest.approx(p))
