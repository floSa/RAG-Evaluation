"""Tests de la recherche et de la réponse du RAG de démonstration, avec un faux modèle (sans réseau)."""

from types import SimpleNamespace

import numpy as np
from rank_bm25 import BM25Okapi

from rag_demo import rag as module

CHUNKS = [
    {"chunk_id": "PR-1101#2#0", "reference_source": "PR-1101", "version_document": "v3", "page": "2",
     "droits_acces": "tous", "texte": "La consignation d'une armoire divisionnaire demande en moyenne 20 minutes."},
    {"chunk_id": "NT-051#2#0", "reference_source": "NT-051", "version_document": "v2", "page": "2",
     "droits_acces": "maintenance", "texte": "Relais de protection générale : maximum de courant phase réglé à 72 A."},
    {"chunk_id": "PR-1110#1#0", "reference_source": "PR-1110", "version_document": "v1", "page": "1",
     "droits_acces": "tous", "texte": "Essai mensuel du groupe électrogène GE-A pendant 30 minutes."},
]


def faux_rag(monkeypatch, reponse: str, k: int = 2) -> module.Rag:
    """Un Rag sans index sur disque ni modèle : vecteurs à la main, génération remplacée."""
    r = module.Rag.__new__(module.Rag)
    r.config = {"recherche": {"k": k, "candidats": 10}, "nom": "test", "type_rag": "vectoriel",
                "modeles": {"embeddings": {"modele": "e"},
                            "generation": {"modele": "g", "prix_entree_eur_par_million": 1.0,
                                           "prix_sortie_eur_par_million": 2.0}}}
    r.chunks = CHUNKS
    r.vecteurs = np.eye(3, dtype=np.float32)
    r.bm25 = BM25Okapi([module.mots(c["texte"]) for c in CHUNKS])
    r.client, r.langfuse = None, None
    monkeypatch.setattr(module, "embeddings", lambda client, modele, textes: np.array([[0.2, 1.0, 0.1]]))
    r.generer = lambda question, historique, contexte: (reponse, (1000, 500))
    return r


def test_filtre_des_droits_pendant_la_recherche(monkeypatch):
    r = faux_rag(monkeypatch, "")
    # le chunk réservé est le plus proche par le sens, mais le profil exploitation ne doit jamais le voir
    pour_exploitation = [x["chunk_id"] for x in r.rechercher("réglage du relais", "exploitation", [])]
    assert "NT-051#2#0" not in pour_exploitation and len(pour_exploitation) == 2
    pour_maintenance = r.rechercher("réglage du relais", "maintenance", [])
    assert pour_maintenance[0]["chunk_id"] == "NT-051#2#0" and pour_maintenance[0]["rang"] == 1


def test_citations_et_cout(monkeypatch):
    r = faux_rag(monkeypatch, "Il faut 20 minutes [1], et le relais est à 72 A [2, 9].")
    rep = r.repondre("combien de temps ?", "maintenance", [])
    assert rep["chunks_cites"] == [rep["chunks_contexte"][0], rep["chunks_contexte"][1]]  # [9] n'existe pas : ignoré
    assert rep["abstention"] is False
    assert rep["cout"] == (1000 * 1.0 + 500 * 2.0) / 1e6
    assert r.derniere_recherche["resultats"][0]["chunk_id"] == rep["chunks_contexte"][0]


def test_abstention(monkeypatch):
    r = faux_rag(monkeypatch, f"« {module.ABSTENTION} »")
    rep = r.repondre("budget 2027 ?", "tous", [])
    assert rep["abstention"] is True and rep["chunks_cites"] == []


def test_version_rag_change_avec_k(monkeypatch):
    v3 = faux_rag(monkeypatch, "", k=3)
    v5 = faux_rag(monkeypatch, "", k=5)
    for r in (v3, v5):
        r.chunks = [{**c, "version_index": "i1"} for c in CHUNKS]
    assert v3.decrire()["version_rag"] != v5.decrire()["version_rag"]
    assert v3.decrire()["k"] == 3
