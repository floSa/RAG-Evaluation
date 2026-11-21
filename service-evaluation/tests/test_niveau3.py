"""Tests du niveau 3 : juge (sortie, verdict recalculé), valeurs, accord du juge, et une évaluation complète avec un
faux juge et un faux Ragas, sur des questions réelles du corpus d'exemple."""

import json
from pathlib import Path

import pytest
import yaml

from kit.appel_du_rag import contrat
from kit.etape_0a_corpus.importer import importer
from kit.etape_3_evaluation_reponse import juge
from kit.etape_3_evaluation_reponse import relecture
from kit.etape_3_evaluation_reponse import scores as niveau3
from kit.etape_5_resultats.publication import Evaluation


# --- Valeurs et calculs ----------------------------------------------------------------------

@pytest.mark.parametrize("point, reponse, attendu", [
    ({"valeur": 162, "unite": "min", "tolerance": 0}, "Au total, 162 minutes de coupure [1].", True),   # Q-022
    ({"valeur": 1384, "unite": "€", "tolerance": 0}, "Le coût est de 1 384 € HT.", True),                # Q-026
    ({"valeur": 2.3, "unite": "ans", "tolerance": 0.1}, "Retour sur investissement en 2,28 ans.", True),  # Q-038
    ({"valeur": 2.3, "unite": "ans", "tolerance": 0.1}, "Retour sur investissement en 2,5 ans.", False),
    ({"valeur": 95, "unite": "mm²", "tolerance": 0}, "Il faut 25 mm² sur une armoire.", False),           # piège Q-004
    ({"valeur": 72, "unite": "A", "tolerance": 0}, "réglé à 72 A, temporisé 500 ms", True),
    ({"valeur": 30, "unite": "minutes", "tolerance": 0}, "pendant 30 secondes", False),
])
def test_valeur_trouvee(point, reponse, attendu):
    assert niveau3.valeur_trouvee(point, reponse) is attendu


# --- Le juge -----------------------------------------------------------------------------------

def test_prompt_lu_dans_juge_md():
    p = juge.prompt_exactitude()
    assert p.startswith("Tu es un évaluateur rigoureux.") and "{points_cles_numerotes}" in p
    rempli = juge.remplir("Q ?", "R.", [{"texte": "a"}, {"texte": "b"}], "réponse")
    assert "1. a\n2. b" in rempli and "{question}" not in rempli and '"verdict": "juste|partielle|fausse"' in rempli


@pytest.mark.parametrize("statuts, contradictions, verdict", [
    (["present", "present"], [], "juste"), (["present", "absent"], [], "partielle"),
    (["present", "contredit"], [], "fausse"), (["absent", "absent"], [], "fausse"),
    (["present", "present"], ["dit 25 mm² au lieu de 95"], "fausse"),
])
def test_verdict_du_kit(statuts, contradictions, verdict):
    assert juge.verdict_du_kit(statuts, contradictions) == verdict


def test_sortie_invalide_redemandee_puis_verdict_recalcule(monkeypatch):
    sorties = iter(['pas du JSON',
                    json.dumps({"points_cles": [{"numero": 1, "statut": "present", "justification": "ok"},
                                                {"numero": 2, "statut": "absent", "justification": "manque"}],
                                "contradictions": [], "verdict": "juste"})])
    monkeypatch.setattr(juge, "appeler", lambda config, llm, messages: next(sorties))
    q = {"question": "réglage ?", "reponse_attendue": "72 A, 500 ms", "points_cles": [{"texte": "72 A"},
                                                                                      {"texte": "500 ms"}]}
    r = juge.juger({}, None, q, "72 A")
    assert r["verdict"] == "partielle" and r["verdict_juge"] == "juste"
    assert r["relecture"] == "verdict du juge « juste » recalculé en « partielle »"


def test_sortie_invalide_deux_fois_part_en_relecture(monkeypatch):
    monkeypatch.setattr(juge, "appeler", lambda config, llm, messages: '{"verdict": "juste"}')
    r = juge.juger({}, None, {"question": "?", "reponse_attendue": "x", "points_cles": [{"texte": "x"}]}, "x")
    assert r["verdict"] is None and r["relecture"].startswith("sortie du juge invalide deux fois")


def test_accord_et_kappa():
    juge_ = {f"Q{i}": v for i, v in enumerate(["juste"] * 8 + ["fausse"] * 2)}
    metier = dict(juge_, Q9="juste")  # un désaccord sur 10
    r = relecture.accord(juge_, metier)
    assert r["accord"] == 0.9 and r["desaccords"] == [{"question_id": "Q9", "juge": "fausse", "metier": "juste"}]
    # kappa = (0,9 − (0,8×0,9 + 0,2×0,1)) ÷ (1 − 0,74) = 0,615…
    assert r["kappa"] == pytest.approx(0.6154, abs=1e-4)


# --- Évaluation complète, avec un faux juge et un faux Ragas -----------------------------------

@pytest.fixture(scope="module")
def ev(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("n3")
    config = yaml.safe_load(Path("config/kit.yaml").read_text(encoding="utf-8"))
    config["chemins"] = {"base": f"sqlite:///{tmp}/base.sqlite", "sorties": str(tmp), "seuils": "config/seuils.json"}
    corpus = importer(Path("corpus_exemple/Corpus_evaluation_RAG.xlsx"), config["chemins"]["base"], tmp,
                      "test").dossier
    questions = contrat.lire_jsonl(corpus / "questions.jsonl")
    rag = tmp / "rag"
    rag.mkdir()
    (rag / "rag.json").write_text(json.dumps({"version_rag": "test", "k": 1}), encoding="utf-8")
    contrat.ecrire_jsonl(rag / "chunks.jsonl", [
        {"chunk_id": "bon", "reference_source": "PR-1101", "texte": "…"},
        {"chunk_id": "nt051", "reference_source": "NT-051", "texte": "…"}])
    # Q-001 : répond en citant le bon chunk ; Q-007 (non accessible) : s'abstient ;
    # Q-047 (sans réponse) : invente une réponse ; Q-002 : s'abstient alors que le bon chunk était là ; les autres :
    # s'abstiennent.
    reponses = []
    for q in questions:
        qid = q["question_id"]
        repond = qid in ("Q-001", "Q-047")
        reponses.append({"question_id": qid, "profil": q["profil"], "reponse": "réponse" if repond else "Je ne sais pas",
                         "abstention": not repond, "chunks_cites": ["bon"] if qid == "Q-001" else [],
                         "chunks_contexte": ["bon"], "duree_ms": 1000, "trace_id": f"t-{qid}"})
    contrat.ecrire_jsonl(rag / "reponses.jsonl", reponses)
    contrat.ecrire_jsonl(rag / "recherches.jsonl", [{"question_id": q["question_id"], "profil": q["profil"], "k": 1,
                                                     "duree_ms": 1, "resultats": [{"chunk_id": "bon", "rang": 1}]}
                                                    for q in questions])
    return Evaluation(config, corpus, rag)


def test_evaluation_complete(ev, monkeypatch):
    monkeypatch.setattr(juge, "client", lambda config: None)
    monkeypatch.setattr(juge, "juger", lambda config, llm, q, reponse: {
        "verdict": "juste", "verdict_juge": "juste", "statuts": ["present"] * len(q["points_cles"]),
        "justification": "ok", "relecture": None})
    monkeypatch.setattr(niveau3, "scores_ragas", lambda config, travaux: {(qid, nom): (1.0 if qid == "Q-001" else 0.0, "")
                                                                         for qid, nom, _ in travaux})
    liens = [{"passage_id": 2, "chunk_id": "bon"}, {"passage_id": 4, "chunk_id": "bon"}]  # Q-001 et Q-002
    lignes, croisement, file = niveau3.evaluer(ev, liens)
    par = {(l.score, l.question_id): l for l in lignes}
    assert par[("n3_exactitude", "Q-001")].verdict == "juste"
    assert par[("n3_citations", "Q-001")].valeur == 1.0
    assert par[("n3_abstention_correcte", "Q-007")].valeur == 1.0
    assert par[("n3_abstention_correcte", "Q-047")].valeur == 0.0          # a inventé une réponse
    assert par[("n3_fidelite", "Q-047")].valeur == 0.0
    assert par[("n3_abstention_a_tort", "Q-002")].valeur == 1.0           # le bon chunk était dans le contexte
    assert ("n3_exactitude", "Q-002") not in par                          # abstention : pas notée par le juge
    graves = {qid for (s, qid), l in par.items() if s == "n3_erreurs_graves" and l.valeur}
    assert graves == ({"Q-047"} if ev.questions["Q-047"]["gravite"] == "forte" else set())
    assert next(c for c in croisement if c["question_id"] == "Q-002")["diagnostic"] == \
        "génération : le bon chunk était retrouvé (abstention à tort)"
    assert sum(1 for f in file if f["motif"] == "tirée au hasard") == 10
