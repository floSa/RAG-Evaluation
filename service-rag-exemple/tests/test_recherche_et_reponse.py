"""Tests des étapes 5 (recherche) et 6 (génération), et de les endpoints d'évaluation, avec un faux modèle."""

import numpy as np
from rank_bm25 import BM25Okapi

from rag import assistant as module_assistant
from rag.endpoints_evaluation.montrer_index import decrire, montrer_index
from rag.endpoints_evaluation.rechercher import rechercher
from rag.endpoints_evaluation.repondre import repondre
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


def test_filtre_des_droits_pendant_la_recherche(monkeypatch):
    a = faux_assistant(monkeypatch, "")
    # le chunk réservé est le plus proche par le sens, mais le profil exploitation ne doit jamais le voir
    pour_exploitation = [t["chunk"]["chunk_id"] for t in a.rechercher("réglage du relais", "exploitation", [])]
    assert "NT-051#2#0" not in pour_exploitation and len(pour_exploitation) == 2
    pour_maintenance = a.rechercher("réglage du relais", "maintenance", [])
    assert pour_maintenance[0]["chunk"]["chunk_id"] == "NT-051#2#0" and pour_maintenance[0]["rang"] == 1


def test_citations():
    assert etape_6_generation.citations("20 minutes [1], 72 A [2, 9], et [1][3].", 3) == [1, 2, 3]  # [9] n'existe pas


def test_porte_repondre(monkeypatch):
    a = faux_assistant(monkeypatch, "Il faut 20 minutes [1], et le relais est à 72 A [2, 9].")
    rep = repondre(a, "combien de temps ?", "maintenance", [])
    assert rep["chunks_cites"] == [rep["chunks_contexte"][0], rep["chunks_contexte"][1]]
    assert rep["abstention"] is False
    assert rep["cout"] == (1000 * 1.0 + 500 * 2.0) / 1e6


def test_porte_rechercher(monkeypatch):
    a = faux_assistant(monkeypatch, "")
    r = rechercher(a, "réglage du relais", "maintenance", [])
    assert r["resultats"][0] == {"chunk_id": "NT-051#2#0", "rang": 1, "score": r["resultats"][0]["score"]}
    assert len(r["resultats"]) == 2 and r["duree_ms"] >= 0


def test_abstention(monkeypatch):
    rep = repondre(faux_assistant(monkeypatch, f"« {etape_6_generation.ABSTENTION} »"), "budget 2027 ?", "tous", [])
    assert rep["abstention"] is True and rep["chunks_cites"] == []


def test_porte_montrer_index(monkeypatch):
    index = montrer_index(faux_assistant(monkeypatch, ""))
    assert [c["chunk_id"] for c in index["chunks"]] == [c["chunk_id"] for c in CHUNKS]
    assert index["rag"]["type_rag"] == "vectoriel" and index["graphe"] is None


def test_version_rag_change_avec_k(monkeypatch):
    v3, v5 = decrire(faux_assistant(monkeypatch, "", k=3)), decrire(faux_assistant(monkeypatch, "", k=5))
    assert v3["version_rag"] != v5["version_rag"] and v3["k"] == 3


def test_generation_sans_reflexion():
    """Avec sans_reflexion, la réflexion du modèle est coupée : elle ne consomme plus les max_tokens de la réponse."""
    from types import SimpleNamespace

    appels = []

    def create(**parametres):
        appels.append(parametres)
        message = SimpleNamespace(content="Le relais est réglé à 72 A [1].")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    for sans_reflexion, attendu in ((True, {"chat_template_kwargs": {"enable_thinking": False}}), (False, None)):
        config = {"modeles": {"generation": {"modele": "g", "temperature": 0, "max_tokens": 800,
                                             "sans_reflexion": sans_reflexion}}}
        reponse, _ = etape_6_generation.generer(client, config, "réglage ?", [], CHUNKS[1:2])
        assert reponse == "Le relais est réglé à 72 A [1]."
        assert appels[-1]["extra_body"] == attendu
