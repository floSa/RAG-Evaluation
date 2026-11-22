"""Tests de l'appel du RAG : un faux RAG, derrière une fausse adresse web, reçoit les documents et les questions."""

import base64
import json
from pathlib import Path

import httpx
import pytest

from kit import contrat
from kit.appel_du_rag import appeler
from kit.etape_0a_corpus.importer import importer

DOCUMENTS = Path("corpus_exemple/documents")
CHUNK = {"chunk_id": "PR-1101#2#0", "type_objet": "chunk", "reference_source": "PR-1101", "version_document": "v3",
         "page": "2", "type_element": "texte", "droits_acces": "tous", "ordre": 0, "texte": "…", "version_index": "x"}
RAG = {"contrat": "1.0", "nom": "faux", "version_rag": "faux-k1", "type_rag": "vectoriel", "date": "2026-11-20",
       "k": 1, "filtre_droits": True,
       "versions": dict.fromkeys(["index", "decoupage", "embedding", "generation", "prompt", "reranker"], "x")}


class FauxRag:
    """Les quatre portes d'un RAG qui renvoie toujours le même chunk, et note ce qu'il reçoit."""

    def __init__(self):
        self.documents, self.questions = [], []

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        corps = json.loads(requete.content) if requete.content else {}
        if requete.url.path == "/ingerer":
            self.documents = corps["documents"]
            return httpx.Response(200, json={"documents": len(self.documents), "chunks": 1, "pages": 1})
        if requete.url.path == "/index":
            return httpx.Response(200, json={"rag": RAG, "chunks": [CHUNK], "graphe": None,
                                             "pages": [{"reference_source": "NT-031", "page": "1", "texte": "…"}]})
        if requete.url.path == "/rechercher":
            return httpx.Response(200, json={"resultats": [{"chunk_id": "PR-1101#2#0", "rang": 1, "score": 1.0}],
                                             "duree_ms": 1})
        self.questions.append(corps)
        return httpx.Response(200, json={"reponse": "…", "abstention": False, "chunks_cites": ["PR-1101#2#0"],
                                         "chunks_contexte": ["PR-1101#2#0"], "duree_ms": 1, "trace_id": "t"})


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("corpus")
    return importer(Path("corpus_exemple/Corpus_evaluation_RAG.xlsx"), f"sqlite:///{tmp}/base.sqlite",
                    tmp / "sorties", "test", aujourd_hui="2026-11-20").dossier


def test_les_quatre_portes(tmp_path, corpus):
    rag = FauxRag()
    client = httpx.Client(base_url="http://faux-rag", transport=httpx.MockTransport(rag))
    dossier = appeler.appeler("http://faux-rag", corpus, DOCUMENTS, tmp_path, afficher=lambda *_: None, client=client)
    assert dossier == tmp_path / "sorties_rag" / "faux-k1"
    assert contrat.verifier_dossier(dossier, corpus) == []

    # 1. les 50 documents, avec leurs fichiers, et rien des annotations
    assert len(rag.documents) == 50
    nt051 = next(d for d in rag.documents if d["reference_source"] == "NT-051")
    assert nt051["droits_acces"] == "maintenance" and nt051["fichier"] == "NT-051.pdf"
    assert base64.b64decode(nt051["contenu"]) == (DOCUMENTS / "NT-051.pdf").read_bytes()
    assert set(nt051) == {"reference_source", "titre", "type_document", "version", "format", "droits_acces",
                          "fichier", "contenu"}

    # 3 et 4. toutes les questions, avec leur profil ; une question de suite reçoit l'échange précédent
    questions = {q["question_id"]: q for q in contrat.lire_jsonl(corpus / "questions.jsonl")}
    assert len(rag.questions) == 60
    q3 = next(q for q in rag.questions if q["question"] == questions["Q-003"]["question"])
    assert q3["historique"] == [{"question": questions["Q-002"]["question"],
                                 "reponse": questions["Q-002"]["reponse_attendue"]}]
    assert next(q for q in rag.questions if q["question"] == questions["Q-007"]["question"])["profil"] == "exploitation"
    assert all(set(q) == {"question", "profil", "historique"} for q in rag.questions)


def test_rag_absent(tmp_path, corpus):
    client = httpx.Client(base_url="http://127.0.0.1:9", timeout=2)
    with pytest.raises(RuntimeError, match="est-il lancé"):
        appeler.appeler("http://127.0.0.1:9", corpus, DOCUMENTS, tmp_path, afficher=lambda *_: None, client=client)
