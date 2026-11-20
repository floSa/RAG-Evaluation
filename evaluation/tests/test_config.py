"""Configuration : kit.yaml se lit, et seuils.json couvre tous les scores minimaux du contrat."""

from kit.config import charger_config, charger_seuils

SCORES_MINIMAUX = {
    "n1_documents_indexes", "n1_metadonnees_completes", "n1_passages_rattaches", "n1_passages_coupes",
    "n1_erreur_caracteres", "n1_graphe_violations", "n1_graphe_justesse",
    "n2_reussite_k", "n2_rappel_k", "n2_rang_premier", "n2_fuite_droits",
    "n3_exactitude", "n3_completude_listes", "n3_valeurs", "n3_abstention_correcte", "n3_abstention_a_tort",
    "n3_fidelite", "n3_citations", "n3_erreurs_graves", "n3_synthese",
    "n4_score_pondere", "n4_erreurs_graves", "n4_temps_median", "n4_temps_p95", "n4_cout_moyen",
}


def test_kit_yaml_se_lit():
    config = charger_config()
    assert config["modeles"]["juge"]["temperature"] == 0
    assert config["modeles"]["juge"]["modele"]


def test_seuils_couvrent_les_scores_minimaux():
    seuils = charger_seuils(charger_config())
    assert SCORES_MINIMAUX <= set(seuils)
    for score, regle in seuils.items():
        assert set(regle) == {"seuil", "sens", "bloquant"}, score
        assert regle["sens"] in {"min", "max"}, score


def test_criteres_bloquants_du_document_3():
    seuils = charger_seuils(charger_config())
    bloquants = {s for s, r in seuils.items() if r["bloquant"]}
    assert bloquants == {"n2_fuite_droits", "n3_erreurs_graves", "n4_erreurs_graves"}
