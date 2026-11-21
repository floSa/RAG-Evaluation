"""Tests de la porte d'évaluation : ingérer à part de la production, et les quatre portes à l'adresse web."""

import base64

from fastapi.testclient import TestClient

from rag.porte_evaluation import adresse_web, ingerer as porte

CONFIG = {"travail": None, "graphe": {"actif": False}, "modeles": {"embeddings": {"modele": "embed"}}}
DOCUMENT = {"reference_source": "NT-051", "titre": "Relais", "type_document": "Note technique", "version": "v2",
            "format": "pdf_natif", "droits_acces": "maintenance", "fichier": "NT-051.pdf",
            "contenu": base64.b64encode(b"%PDF-1.4 faux").decode()}


def test_ingerer_range_les_documents_a_part(tmp_path, monkeypatch):
    appels = []

    def faux_indexer(config, afficher, documents):
        appels.append((config, documents))
        return {"chunks": 3, "pages": 1, "version_index": "v1"}

    monkeypatch.setattr(porte, "indexer", faux_indexer)
    config = {**CONFIG, "travail": str(tmp_path)}
    r = porte.ingerer(config, [DOCUMENT])
    assert r == {"documents": 1, "chunks": 3, "pages": 1, "version_index": "v1", "deja_ingere": False}
    recu = tmp_path / "evaluation" / "documents" / "NT-051.pdf"      # dans l'espace « evaluation », pas en production
    assert recu.read_bytes() == b"%PDF-1.4 faux"
    assert appels[0][0]["travail"] == str(tmp_path / "evaluation")
    assert appels[0][1] == [{k: v for k, v in DOCUMENT.items() if k != "contenu"}]   # le contenu ne va pas dans l'index
    # les mêmes documents, renvoyés : l'index est gardé
    assert porte.ingerer(config, [DOCUMENT])["deja_ingere"] is True and len(appels) == 1


def test_adresse_web(tmp_path, monkeypatch):
    monkeypatch.setattr(adresse_web, "charger_config", lambda: {**CONFIG, "travail": str(tmp_path)})
    monkeypatch.setattr(porte, "indexer", lambda config, afficher, documents: {"chunks": 1, "pages": 1, "version_index": "v"})
    monkeypatch.setattr(adresse_web, "ingerer", porte.ingerer)
    client = TestClient(adresse_web.app)
    adresse_web.etat["assistant"] = None
    monkeypatch.setattr(adresse_web, "Assistant", lambda espace: (_ for _ in ()).throw(FileNotFoundError()))
    assert client.get("/index").status_code == 409                 # rien d'ingéré : erreur claire
    assert client.post("/ingerer", json={"documents": [DOCUMENT]}).json()["documents"] == 1
    monkeypatch.setattr(adresse_web, "Assistant", lambda espace: "assistant")
    monkeypatch.setattr(adresse_web, "repondre", lambda a, q, p, h: {"assistant": a, "question": q, "profil": p, "historique": h})
    r = client.post("/repondre", json={"question": "et sur le site A ?", "profil": "tous",
                                       "historique": [{"question": "site B ?", "reponse": "30 Ω"}]}).json()
    assert r == {"assistant": "assistant", "question": "et sur le site A ?", "profil": "tous",
                 "historique": [{"question": "site B ?", "reponse": "30 Ω"}]}
