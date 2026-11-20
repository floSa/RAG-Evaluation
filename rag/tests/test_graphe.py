"""Étape 4, le graphe : extraction contrainte par l'ontologie, provenance, éléments de l'index, recherche par entités."""

from pathlib import Path

import numpy as np
from rdflib import RDF, Literal

from rag.pipeline import etape_4_graphe as graphe
from rag.pipeline.etape_3_index import Index
from rag.pipeline.etape_5_recherche import par_les_entites

ONTOLOGIE = graphe.lire_ontologie(Path("evaluation/corpus_exemple/ontologie/ontologie.ttl"))

# Un chunk réel de NT-051 (réservé au profil Maintenance), page 2
CHUNK = {"chunk_id": "NT-051#2#0", "type_objet": "chunk", "reference_source": "NT-051", "version_document": "v3",
         "page": "2", "type_element": "texte", "droits_acces": "maintenance", "ordre": 0,
         "texte": "Le transformateur TR-A1 alimente le TGBT-A du site A."}


def test_ontologie_lue():
    assert set(ONTOLOGIE["classes"]) == {"Site", "Equipement", "Personne"}
    assert ONTOLOGIE["relations"]["alimente"]["domaine"] == "Equipement"


def test_contraindre_ecarte_ce_que_l_ontologie_ne_connait_pas():
    brut = {"entites": [{"nom": "TR-A1", "classe": "Equipement"}, {"nom": "AD-A01", "classe": "armoire divisionnaire"}],
            "relations": [{"sujet": "TR-A1", "relation": "alimente", "objet": "TGBT-A"},
                          {"sujet": "TR-A1", "relation": "remplace", "objet": "TR-A2"}]}
    r = graphe.contraindre(brut, ONTOLOGIE)
    assert r["entites"] == [{"nom": "TR-A1", "classe": "Equipement"}]
    assert r["relations"] == [{"sujet": "TR-A1", "relation": "alimente", "objet": "TGBT-A"}]


def test_lire_json_tolere_le_bloc_de_code():
    assert graphe.lire_json('```json\n{"entites": [], "relations": []}\n```') == {"entites": [], "relations": []}
    assert graphe.lire_json("pas de JSON") == {}


def test_construire_garde_la_provenance(monkeypatch, tmp_path):
    extrait = {"entites": [{"nom": "TR-A1", "classe": "Equipement"}, {"nom": "TGBT-A", "classe": "Equipement"},
                           {"nom": "Site A", "classe": "Site"}],
               "relations": [{"sujet": "TR-A1", "relation": "alimente", "objet": "TGBT-A"},
                             {"sujet": "TGBT-A", "relation": "situeSur", "objet": "Site A"}]}
    monkeypatch.setattr(graphe, "extraire_page", lambda *a, **k: extrait)
    config = {"graphe": {"ontologie": "evaluation/corpus_exemple/ontologie/ontologie.ttl"}, "travail": str(tmp_path),
              "modeles": {"generation": {"modele": "faux"}}}
    noeuds, g = graphe.construire([CHUNK], config, None, lambda o: "x", afficher=lambda *_: None)

    tgbt = next(n for n in noeuds if n["metadonnees"]["entite"] == "TGBT-A")
    assert tgbt["type_objet"] == "noeud"
    assert (tgbt["reference_source"], tgbt["page"], tgbt["droits_acces"]) == ("NT-051", "2", "maintenance")
    assert "TR-A1 alimente TGBT-A" in tgbt["texte"] and "TGBT-A est situé sur Site A" in tgbt["texte"]
    for relation in g.subjects(RDF.type, RDF.Statement):                    # chaque relation porte sa provenance
        assert g.value(relation, graphe.KIT.referenceSource) == Literal("NT-051")
        assert g.value(relation, graphe.KIT.page) == Literal("2")


def test_recherche_par_les_entites_nommees():
    noeud = {"type_objet": "noeud", "metadonnees": {"entite": "TGBT-A", "relations": ["TR-A1 alimente TGBT-A"]}}
    index = Index([CHUNK, noeud], [], np.zeros((2, 1)), None, graphe_ttl=Path("graphe.ttl"))
    scores = par_les_entites(index, "Quel transformateur alimente le tgbt-a ?")
    assert scores[1] == 1 and scores[0] == -np.inf
    assert par_les_entites(index, "Et le TGBT-B ?")[1] == -np.inf
