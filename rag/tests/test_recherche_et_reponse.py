"""Tests des étapes 5 (recherche) et 6 (génération), et du branchement sur l'évaluation, avec un faux modèle."""

import numpy as np
from rank_bm25 import BM25Okapi

from rag import assistant as module_assistant
from rag import branchement_evaluation
from rag.pipeline import etape_5_recherche, etape_6_generation
from rag.pipeline.etape_3_index import Index, mots

CHUNKS = [
    {"chunk_id": "PR-1101#2#0", "reference_source": "PR-1101", "version_document": "v3", "page": "2",
     "droits_acces": "tous", "texte": "La consignation d'une armoire divisionnaire demande en moyenne 20 minutes.",
     "version_index": "i1"},
    {"chunk_id": "NT-051#2#0", "reference_source": "NT-051", "version_document": "v2", "page": "2",
     "droits_acces": "maintenance", "texte": "Relais de protection générale : maximum de courant phase réglé à 72 A.",
     "version_index": "i1"},
    {"chunk_id": "PR-1110#1#0", "reference_source": "PR-1110", "version_document": "v1", "page": "1",
     "droits_acces": "tous", "texte": "Essai mensuel du groupe électrogène GE-A pendant 30 minutes.",
     "version_index": "i1"},
]


def faux_assistant(monkeypatch, reponse: str, k: int = 2) -> module_assistant.Assistant:
    """Un assistant sans index sur disque ni modèle : vecteurs à la main, génération remplacée."""
    a = module_assistant.Assistant.__new__(module_assistant.Assistant)
    a.config = {"recherche": {"k": k, "candidats": 10}, "nom": "test", "type_rag": "vectoriel",
                "modeles": {"embeddings": {"modele": "e"},
                            "generation": {"modele": "g", "prix_entree_eur_par_million": 1.0,
                                           "prix_sortie_eur_par_million": 2.0}}}
    a.index = Index(CHUNKS, [], np.eye(3, dtype=np.float32), BM25Okapi([mots(c["texte"]) for c in CHUNKS]))
    a.client, a.langfuse = None, None
    monkeypatch.setattr(etape_5_recherche, "embeddings", lambda client, modele, textes: np.array([[0.2, 1.0, 0.1]]))
    monkeypatch.setattr(etape_6_generation, "generer", lambda *args, **kwargs: (reponse, (1000, 500)))
    return a


def faux_connecteur(monkeypatch, reponse: str, k: int = 2) -> branchement_evaluation.Connecteur:
    c = branchement_evaluation.Connecteur.__new__(branchement_evaluation.Connecteur)
    c.assistant, c.derniere_recherche = faux_assistant(monkeypatch, reponse, k), None
    return c


def test_filtre_des_droits_pendant_la_recherche(monkeypatch):
    a = faux_assistant(monkeypatch, "")
    # le chunk réservé est le plus proche par le sens, mais le profil exploitation ne doit jamais le voir
    pour_exploitation = [t["chunk"]["chunk_id"] for t in a.rechercher("réglage du relais", "exploitation", [])]
    assert "NT-051#2#0" not in pour_exploitation and len(pour_exploitation) == 2
    pour_maintenance = a.rechercher("réglage du relais", "maintenance", [])
    assert pour_maintenance[0]["chunk"]["chunk_id"] == "NT-051#2#0" and pour_maintenance[0]["rang"] == 1


def test_citations():
    assert etape_6_generation.citations("20 minutes [1], 72 A [2, 9], et [1][3].", 3) == [1, 2, 3]  # [9] n'existe pas


def test_reponse_au_format_du_contrat(monkeypatch):
    c = faux_connecteur(monkeypatch, "Il faut 20 minutes [1], et le relais est à 72 A [2, 9].")
    rep = c.repondre("combien de temps ?", "maintenance", [])
    assert rep["chunks_cites"] == [rep["chunks_contexte"][0], rep["chunks_contexte"][1]]
    assert rep["abstention"] is False
    assert rep["cout"] == (1000 * 1.0 + 500 * 2.0) / 1e6
    assert c.derniere_recherche["resultats"][0]["chunk_id"] == rep["chunks_contexte"][0]


def test_abstention(monkeypatch):
    c = faux_connecteur(monkeypatch, f"« {etape_6_generation.ABSTENTION} »")
    rep = c.repondre("budget 2027 ?", "tous", [])
    assert rep["abstention"] is True and rep["chunks_cites"] == []


def test_version_rag_change_avec_k(monkeypatch):
    v3, v5 = faux_connecteur(monkeypatch, "", k=3), faux_connecteur(monkeypatch, "", k=5)
    assert v3.decrire()["version_rag"] != v5.decrire()["version_rag"]
    assert v3.decrire()["k"] == 3
