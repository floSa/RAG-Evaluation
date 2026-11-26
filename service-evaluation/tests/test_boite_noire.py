"""Tests du RAG en boîte noire : une fausse API compatible OpenAI reçoit les questions du corpus d'exemple ; ses réponses
sont rangées au format du contrat, puis évaluées (niveau 3) sans ingestion ni recherche."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from kit import contrat
from kit.appel_du_rag import boite_noire
from kit.etape_0a_corpus.importer import importer
from kit.etape_3_evaluation_reponse import juge
from kit.etape_3_evaluation_reponse import scores as scores_reponse
from kit.etape_5_resultats.publication import Evaluation

REGLAGES = {"nom": "portail", "adresse": "https://portail.exemple/v1", "variable_cle": "X", "modele": "assistant",
            "temperature": 0, "en_tete_profil": "X-Profil", "phrases_abstention": ["je ne sais pas", "je ne trouve pas"],
            "prix_entree_eur_par_million": 1, "prix_sortie_eur_par_million": 2}


class FausseApi:
    """Une API /v1/chat/completions qui répond « 95 mm² » à Q-004, « Je ne trouve pas » au reste, et note ce qu'elle reçoit."""

    def __init__(self):
        self.appels = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, model, temperature, messages, extra_headers):
        self.appels.append({"model": model, "messages": messages, "en_tetes": extra_headers})
        texte = "La section est de 95 mm²." if "TGBT" in messages[-1]["content"] else "Je ne trouve pas cette information."
        return SimpleNamespace(id=f"api-{len(self.appels)}", choices=[SimpleNamespace(message=SimpleNamespace(content=texte))],
                               usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=500))


@pytest.fixture(scope="module")
def appel(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("boite_noire")
    corpus = importer(Path("../service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx"),
                      f"sqlite:///{tmp}/base.sqlite", tmp, "test", aujourd_hui="2026-11-20").dossier
    api = FausseApi()
    dossier = boite_noire.appeler(REGLAGES, "cle", corpus, tmp, afficher=lambda *_: None, client=api)
    return tmp, corpus, dossier, api


@pytest.mark.parametrize("texte, attendu", [
    ("Je ne sais pas.", True), ("Je ne trouve pas cette information dans les documents.", True),
    ("JE NE SAIS PAS", True), ("", True), ("La section est de 95 mm².", False),
])
def test_abstention_reconnue_a_ses_mots(texte, attendu):
    assert boite_noire.abstention(texte, ["je ne sais pas", "je ne trouve pas"]) is attendu


def test_les_reponses_respectent_le_contrat(appel):
    _, corpus, dossier, _ = appel
    assert sorted(f.name for f in dossier.iterdir()) == ["rag.json", "reponses.jsonl"]
    assert contrat.verifier_dossier(dossier, corpus) == []
    rag = contrat.lire_json(dossier / "rag.json")
    assert rag["type_rag"] == "boite_noire" and rag["version_rag"].startswith("portail-boite-noire-") and "k" not in rag


def test_questions_posees_sans_les_annotations_du_metier(appel):
    _, corpus, _, api = appel
    questions = {q["question_id"]: q for q in contrat.lire_jsonl(corpus / "questions.jsonl")}
    assert len(api.appels) == len(questions)
    envoye = json.dumps([a["messages"] for a in api.appels], ensure_ascii=False)
    q = questions["Q-001"]
    assert q["question"] in envoye and "points_cles" not in envoye
    suite = next(q for q in questions.values() if q.get("question_precedente"))   # une question de suite : l'historique
    appel_suite = next(a for a in api.appels if a["messages"][-1]["content"] == suite["question"])
    assert [m["role"] for m in appel_suite["messages"]][-3:] == ["user", "assistant", "user"]
    assert {a["en_tetes"]["X-Profil"] for a in api.appels} == {q["profil"] for q in questions.values()}


def test_reponse_abstention_duree_et_cout(appel):
    _, _, dossier, _ = appel
    reponses = {r["question_id"]: r for r in contrat.lire_jsonl(dossier / "reponses.jsonl")}
    assert reponses["Q-004"]["abstention"] is False and "95 mm²" in reponses["Q-004"]["reponse"]
    assert reponses["Q-047"]["abstention"] is True
    assert reponses["Q-004"]["cout"] == pytest.approx(1000 * 1e-6 + 500 * 2e-6)
    assert reponses["Q-004"]["chunks_cites"] == [] and reponses["Q-004"]["duree_ms"] >= 0


def test_evaluation_de_la_reponse_sans_recherche(appel, monkeypatch):
    tmp, corpus, dossier, _ = appel
    config = yaml.safe_load(Path("config/kit.yaml").read_text(encoding="utf-8"))
    config["chemins"] = {"base": f"sqlite:///{tmp}/base.sqlite", "resultats": str(tmp)}
    ev = Evaluation(config, corpus, dossier)
    assert ev.boite_noire
    monkeypatch.setattr(juge, "client", lambda config: None)
    monkeypatch.setattr(juge, "juger", lambda config, llm, q, reponse: {
        "verdict": "juste", "verdict_juge": "juste", "statuts": ["present"] * len(q["points_cles"]),
        "justification": "ok", "relecture": None})
    travaux_vus = []
    monkeypatch.setattr(scores_reponse, "scores_ragas", lambda config, travaux: travaux_vus.extend(travaux) or {})
    lignes, croisement, _ = scores_reponse.evaluer(ev, [])
    par = {(l.score, l.question_id): l for l in lignes}
    assert par[("n3_exactitude", "Q-004")].verdict == "juste"
    assert par[("n3_abstention_correcte", "Q-047")].valeur == 1.0
    assert not any(s in ("n3_fidelite", "n3_citations", "n3_abstention_a_tort") for s, _ in par)
    assert croisement == [] and not any(nom == "fidelite" for _, nom, _ in travaux_vus)
