"""Tests de kit verifier-contrat : un dossier de sorties de RAG conforme, puis des fichiers volontairement faux."""

import json
from pathlib import Path

import pytest

from kit import contrat
from kit.etape_0a_corpus.importer import importer

EXEMPLE = Path("corpus_exemple/Corpus_evaluation_RAG.xlsx")


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("corpus")
    return importer(EXEMPLE, f"sqlite:///{tmp}/base.sqlite", tmp / "sorties", "test", aujourd_hui="2026-11-20").dossier


def ecrire(dossier: Path, nom: str, objets) -> None:
    if nom.endswith(".json"):
        (dossier / nom).write_text(json.dumps(objets, ensure_ascii=False), encoding="utf-8")
    else:
        (dossier / nom).write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in objets), encoding="utf-8")


@pytest.fixture
def sorties_rag(tmp_path, corpus) -> Path:
    """Les sorties minimales d'un RAG qui répond « je ne sais pas » à tout, avec un seul chunk (cas réel : PR-1101)."""
    d = tmp_path / "sorties_rag" / "v1"
    d.mkdir(parents=True)
    ecrire(d, "rag.json", {"contrat": "1.0", "nom": "factice", "version_rag": "v1", "type_rag": "vectoriel",
                           "date": "2026-11-20", "k": 1, "filtre_droits": True,
                           "versions": {"index": "i1", "decoupage": "d1", "embedding": "aucun", "generation": "aucun",
                                        "prompt": "aucun", "reranker": "aucun"}})
    ecrire(d, "chunks.jsonl", [{"chunk_id": "PR-1101#2#0", "type_objet": "chunk", "reference_source": "PR-1101",
                                "version_document": "v3", "page": "2", "type_element": "texte",
                                "droits_acces": "tous", "ordre": 0, "version_index": "i1",
                                "texte": "La consignation comporte cinq étapes…"}])
    ecrire(d, "pages_extraites.jsonl", [{"reference_source": "NT-031", "page": "1", "texte": "…"}])
    questions = contrat.lire_jsonl(corpus / "questions.jsonl")
    ecrire(d, "recherches.jsonl", [{"question_id": q["question_id"], "profil": q["profil"], "k": 1, "duree_ms": 5,
                                    "resultats": [{"chunk_id": "PR-1101#2#0", "rang": 1, "score": 0.5}]}
                                   for q in questions])
    ecrire(d, "reponses.jsonl", [{"question_id": q["question_id"], "profil": q["profil"], "reponse": "Je ne sais pas.",
                                  "abstention": True, "chunks_cites": [], "chunks_contexte": ["PR-1101#2#0"],
                                  "duree_ms": 9, "trace_id": f"t-{q['question_id']}"} for q in questions])
    return d


def test_corpus_exporte_conforme(corpus):
    assert contrat.verifier_dossier(corpus) == []


def test_sorties_rag_conformes(sorties_rag, corpus):
    assert contrat.verifier_dossier(sorties_rag, corpus) == []


def test_champ_obligatoire_manquant(sorties_rag):
    lignes = contrat.lire_jsonl(sorties_rag / "reponses.jsonl")
    del lignes[2]["abstention"]
    ecrire(sorties_rag, "reponses.jsonl", lignes)
    assert contrat.verifier_dossier(sorties_rag) == [
        "reponses.jsonl, ligne 3 : champ obligatoire « abstention » absent."]


def test_valeur_hors_liste_et_champ_inconnu(sorties_rag):
    rag = contrat.lire_json(sorties_rag / "rag.json")
    rag["type_rag"] = "magique"
    rag["temperature"] = 0.2
    ecrire(sorties_rag, "rag.json", rag)
    erreurs = contrat.verifier_dossier(sorties_rag)
    assert "rag.json : champ(s) inconnu(s) du contrat : 'temperature'." in erreurs
    assert any("« magique » n'est pas une valeur admise (vectoriel, graphe, hybride, agent)" in e for e in erreurs)


def test_fichier_obligatoire_absent(sorties_rag):
    (sorties_rag / "recherches.jsonl").unlink()
    assert "recherches.jsonl : fichier obligatoire absent." in contrat.verifier_dossier(sorties_rag)


def test_chunk_sans_page_refuse(sorties_rag):
    chunks = contrat.lire_jsonl(sorties_rag / "chunks.jsonl")
    del chunks[0]["page"]
    ecrire(sorties_rag, "chunks.jsonl", chunks)
    assert contrat.verifier_dossier(sorties_rag) == ["chunks.jsonl, ligne 1 : champ obligatoire « page » absent."]


def test_coherence_avec_le_corpus(sorties_rag, corpus):
    reponses = contrat.lire_jsonl(sorties_rag / "reponses.jsonl")
    reponses = [r for r in reponses if r["question_id"] != "Q-010"]
    reponses[0]["chunks_cites"] = ["inconnu"]
    ecrire(sorties_rag, "reponses.jsonl", reponses)
    recherches = contrat.lire_jsonl(sorties_rag / "recherches.jsonl")
    recherches[6]["profil"] = "tous"  # Q-007 est posée avec le profil exploitation
    ecrire(sorties_rag, "recherches.jsonl", recherches)
    erreurs = contrat.verifier_dossier(sorties_rag, corpus)
    assert "reponses.jsonl : 1 question(s) du corpus sans ligne : Q-010." in erreurs
    assert any("chunks_cites contient des chunks absents de chunks.jsonl : inconnu" in e for e in erreurs)
    assert "recherches.jsonl, Q-007 : posée avec le profil « tous » au lieu de « exploitation »." in erreurs


def test_graphe_obligatoire_pour_un_rag_hybride(sorties_rag):
    rag = contrat.lire_json(sorties_rag / "rag.json")
    rag["type_rag"] = "hybride"
    ecrire(sorties_rag, "rag.json", rag)
    assert any(e.startswith("graphe.ttl : obligatoire") for e in contrat.verifier_dossier(sorties_rag))


def test_version_majeure_inconnue(sorties_rag):
    rag = contrat.lire_json(sorties_rag / "rag.json")
    rag["contrat"] = "2.0"
    ecrire(sorties_rag, "rag.json", rag)
    assert any("version du contrat inconnue" in e for e in contrat.verifier_dossier(sorties_rag))
