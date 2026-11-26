"""Tests de l'import d'un corpus au format JSON (kit importer corpus.json) : le corpus d'exemple, réécrit en JSON avec
les codes du contrat, donne le même corpus que le fichier Excel ; un fichier faux est refusé avec un message clair."""

import json
from pathlib import Path

import pytest

from kit import contrat
from kit.etape_0a_corpus.importer import importer

EXEMPLE = Path("../service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx")


@pytest.fixture(scope="module")
def depuis_excel(tmp_path_factory) -> dict:
    tmp = tmp_path_factory.mktemp("excel")
    return contrat.charger_corpus(importer(EXEMPLE, f"sqlite:///{tmp}/base.sqlite", tmp, "test",
                                           aujourd_hui="2026-11-20").dossier)


def en_json(corpus: dict, chemin: Path, **changements) -> Path:
    """Le corpus exporté, réécrit comme le produirait un programme : les listes, avec les champs du contrat."""
    donnees = {"documents": corpus["documents"],
               "questions": corpus["questions"],
               "passages": [{k: v for k, v in p.items() if k != "passage_id"} for p in corpus["passages"]],
               "pages_ocr": corpus["pages_ocr"]}
    donnees.update(changements)
    chemin.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
    return chemin


def test_meme_corpus_qu_avec_le_fichier_excel(depuis_excel, tmp_path):
    r = importer(en_json(depuis_excel, tmp_path / "corpus.json"), f"sqlite:///{tmp_path}/base.sqlite", tmp_path, "test",
                 aujourd_hui="2026-11-20")
    assert r.erreurs == []
    c = contrat.charger_corpus(r.dossier)
    assert contrat.verifier_dossier(r.dossier) == []
    for nom in ("documents", "questions", "pages_ocr"):
        assert c[nom] == depuis_excel[nom], nom
    sans_id = lambda ps: [{k: v for k, v in p.items() if k != "passage_id"} for p in ps]  # noqa: E731
    assert sans_id(c["passages"]) == sans_id(depuis_excel["passages"])
    assert c["corpus"]["colonnes_libres"] == ["service", "site"]


def test_libelles_et_points_cles_en_texte_acceptes(depuis_excel, tmp_path):
    q = dict(depuis_excel["questions"][0], reponse_dans_documents="Oui", points_cles="séparation ; condamnation")
    r = importer(en_json(depuis_excel, tmp_path / "c.json", questions=[q] + depuis_excel["questions"][1:]),
                 f"sqlite:///{tmp_path}/base.sqlite", tmp_path, "test")
    assert r.erreurs == []
    premiere = contrat.lire_jsonl(r.dossier / "questions.jsonl")[0]
    assert premiere["reponse_dans_documents"] == "oui" and [p["texte"] for p in premiere["points_cles"]] == \
        ["séparation", "condamnation"]


def test_fichier_faux_refuse_avec_un_message_clair(depuis_excel, tmp_path):
    q = dict(depuis_excel["questions"][0], gravite="enorme", couleur="bleu")
    del q["question"]
    r = importer(en_json(depuis_excel, tmp_path / "faux.json", questions=[q] + depuis_excel["questions"][1:]),
                 f"sqlite:///{tmp_path}/base.sqlite", tmp_path, "test")
    assert any("« questions », élément 1 (Q-001) : champ(s) inconnu(s) : couleur" in e for e in r.erreurs)
    assert any("élément 1 (Q-001) : la colonne « Question » est obligatoire" in e for e in r.erreurs)
    assert any("« enorme » n'est pas une valeur admise" in e for e in r.erreurs)


def test_liste_absente_refusee(tmp_path):
    chemin = tmp_path / "vide.json"
    chemin.write_text(json.dumps({"documents": []}), encoding="utf-8")
    r = importer(chemin, f"sqlite:///{tmp_path}/base.sqlite", tmp_path, "test")
    assert "vide.json : la liste « questions » est absente." in r.erreurs
