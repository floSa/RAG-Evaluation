"""Tests des rapports lisibles : RAPPORT.md d'une évaluation et RAPPORT.md d'une comparaison."""

from kit.etape_5_resultats import comparaison, rapport

# La configuration de référence du RAG d'exemple, et sa variante k = 3 (resultats_exemple/).
REFERENCE = {"version_rag": "graphrag-vectoriel-k5-5954e822", "type_rag": "vectoriel", "k": 5,
             "versions": {"index": "sections-1-embed-3fc47199", "decoupage": "sections-1", "embedding": "embed",
                          "generation": "gemma-4-e4b", "prompt": "1.0", "reranker": "aucun"}}
K3 = {**REFERENCE, "version_rag": "graphrag-vectoriel-k3-5954e822", "k": 3}


def test_valeurs_en_clair():
    assert rapport.texte_valeur("n4_score_pondere", 0.8037, 0.12) == "80 % ± 12"
    assert rapport.texte_valeur("n4_temps_median", 7412) == "7,4 s"
    assert rapport.texte_valeur("n4_cout_moyen", 0.0) == "0,00 €"
    assert rapport.texte_valeur("n3_erreurs_graves", 1.0) == "1"
    assert rapport.texte_seuil("n1_erreur_caracteres", 0.02, "max") == "≤ 2 %"
    assert rapport.texte_seuil("n4_temps_p95", 30000, "max") == "≤ 30,0 s"


def test_configuration_en_une_ligne():
    assert rapport.configuration(REFERENCE).startswith("RAG vectoriel, k = 5, découpage sections-1")


def test_rapport_evaluation_commence_par_la_decision():
    c = {"titre": "graphrag-vectoriel-k5-5954e822", "configuration": rapport.configuration(REFERENCE),
         "corpus": "2026-11-20.1", "questions": 60, "reservees": 20, "juge": "chat, prompt 1.0", "possible": False,
         "bloquants": [("Erreurs graves", 1.0)], "manquants": ["Score pondéré"],
         "decision": [["Score pondéré", "76 % ± 19", "≥ 80 %", "❌ non", "20"]], "niveaux": [],
         "a_voir": [("Q-046", "quelles règles | de sécurité ?", "Erreur grave", "réponse fausse")],
         "croisement": [], "types": [], "lignes_types": [], "evaluation_id": "x"}
    md = rapport.markdown(c)
    assert "**❌ Mise en production non recommandée.**" in md
    assert "Critère bloquant déclenché : **Erreurs graves = 1**" in md
    assert "les 20 questions réservées" in md
    assert "quelles règles \\| de sécurité" in md   # une barre verticale ne casse pas le tableau


def test_comparaison_dit_ce_qui_change_et_si_c_est_le_hasard():
    r = {"rag_a": REFERENCE, "rag_b": K3,
         "ecarts": [{"score": "n4_score_pondere", "a": 0.8037, "b": 0.7704, "ecart": -0.0333, "marge": 0.12,
                     "significatif_seul": False}],
         "questions": {"n4_score_pondere": {"gagnees": [], "perdues": ["Q-031", "Q-046"], "n": 40,
                                            "mcnemar_p": 0.125}}}
    md = comparaison.markdown(r, {"Q-046": {"gravite": "forte"}})
    assert "**Ce qui change de A à B** : k : 5 → 3." in md
    assert "| Score pondéré | 80 % | 77 % | −3 points | non prouvé : dans la marge |" in md
    assert "B perd 3 point(s) par rapport à A" in md and "peut venir du hasard" in md
    assert "gravité forte (Q-046)" in md


def test_comparaison_sans_reglage_declare_different():
    assert comparaison.differences(REFERENCE, {**REFERENCE, "version_rag": "graphrag-vectoriel-k5-94d362c8"}) == []
