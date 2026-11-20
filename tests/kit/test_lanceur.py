"""Tests du lanceur : un faux RAG branché par son connecteur produit des sorties conformes au contrat."""

from pathlib import Path

import pytest

from kit import contrat, lanceur
from kit.import_corpus import importer


class FauxConnecteur:
    """Un RAG qui renvoie toujours le même chunk et note les appels reçus."""

    def __init__(self, k: int = 1):
        self.k, self.appels = k, []

    def decrire(self):
        return {"contrat": "1.0", "nom": "faux", "version_rag": f"faux-k{self.k}", "type_rag": "vectoriel",
                "date": "2026-11-20", "k": self.k, "filtre_droits": True,
                "versions": dict.fromkeys(["index", "decoupage", "embedding", "generation", "prompt", "reranker"], "x")}

    def exporter_index(self):
        return [{"chunk_id": "PR-1101#2#0", "type_objet": "chunk", "reference_source": "PR-1101",
                 "version_document": "v3", "page": "2", "type_element": "texte", "droits_acces": "tous", "ordre": 0,
                 "texte": "…", "version_index": "x"}]

    def exporter_pages(self):
        return [{"reference_source": "NT-031", "page": "1", "texte": "…"}]

    def exporter_graphe(self, chemin):
        return None

    def rechercher(self, question, profil, historique):
        return [{"chunk_id": "PR-1101#2#0", "rang": 1, "score": 1.0}]

    def repondre(self, question, profil, historique):
        self.appels.append((question, profil, historique))
        return {"profil": profil, "reponse": "…", "abstention": False, "chunks_cites": ["PR-1101#2#0"],
                "chunks_contexte": ["PR-1101#2#0"], "duree_ms": 1, "trace_id": "t"}


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("corpus")
    return importer(Path("corpus_exemple/Corpus_evaluation_RAG.xlsx"), f"sqlite:///{tmp}/base.sqlite",
                    tmp / "sorties", "test", aujourd_hui="2026-11-20").dossier


def test_sorties_conformes_et_regles_d_appel(tmp_path, corpus):
    c = FauxConnecteur()
    dossier = lanceur.lancer(c, corpus, tmp_path, afficher=lambda *_: None)
    assert dossier == tmp_path / "sorties_rag" / "faux-k1"
    assert contrat.verifier_dossier(dossier, corpus) == []
    questions = {q["question_id"]: q for q in contrat.lire_jsonl(corpus / "questions.jsonl")}
    assert len(c.appels) == 60  # toutes les questions, réservées comprises
    # Q-003 est la suite de Q-002 : elle reçoit l'historique ; Q-007 est posée avec le profil exploitation
    q3 = next(a for a in c.appels if a[0] == questions["Q-003"]["question"])
    assert q3[2] == [{"question": questions["Q-002"]["question"], "reponse": questions["Q-002"]["reponse_attendue"]}]
    assert next(a for a in c.appels if a[0] == questions["Q-007"]["question"])[1] == "exploitation"


def test_charger_connecteur_par_son_nom():
    assert lanceur.charger_connecteur("collections:Counter", {"a": 2})["a"] == 2
    with pytest.raises(ValueError, match="module:Classe"):
        lanceur.charger_connecteur("rag_demo.connecteur", {})
