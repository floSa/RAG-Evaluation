"""Tests du niveau 2, vérifiés à la main sur des questions réelles du corpus d'exemple.

Le calcul attendu de chaque cas est écrit en commentaire : c'est la vérification « à la main » demandée à l'étape 6.
"""

import json
from pathlib import Path

import pytest
import yaml

from kit.appel_du_rag import contrat
from kit.etape_0a_corpus.importer import importer
from kit.etape_2_evaluation_recherche import scores as niveau2
from kit.etape_5_resultats.publication import Evaluation, calculer_scores

# Liens du niveau 1, écrits à la main (passage_id → chunks), pour les passages des questions testées :
# Q-001 (plusieurs, un seul suffit) : passages 2 (texte) et 3 (schéma) de PR-1101 page 2
# Q-013 (plusieurs, un seul suffit) : passages 18 (PR-1104-C), 19 (PR-1106) ; 20 est un piège (PR-1104-B, périmée)
# Q-030 (plusieurs à combiner) : passages 49 (OT-24101) et 50 (OT-24112)
# Q-007 (non accessible au profil exploitation) : passage 11 (NT-051, réservé à la maintenance)
LIENS = [(2, "PR-1101#2#0"), (3, "PR-1101#2#1"), (18, "PR-1104-C#2#1"), (19, "PR-1106#1#0"),
         (20, "PR-1104-B#2#1"), (49, "OT-24101#Actions"), (50, "OT-24112#Actions"), (11, "NT-051#2#0")]


@pytest.fixture(scope="module")
def ev(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("n2")
    config = yaml.safe_load(Path("config/kit.yaml").read_text(encoding="utf-8"))
    config["chemins"] = {"base": f"sqlite:///{tmp}/base.sqlite", "sorties": str(tmp), "seuils": "config/seuils.json"}
    corpus = importer(Path("corpus_exemple/Corpus_evaluation_RAG.xlsx"), config["chemins"]["base"], tmp,
                      "test").dossier
    docs = {d["reference_source"]: d for d in contrat.lire_jsonl(corpus / "documents.jsonl")}
    chunks = [{"chunk_id": c, "reference_source": c.split("#")[0], "droits_acces": docs[c.split("#")[0]]["droits_acces"]}
              for c in {c for _, c in LIENS} | {"PR-1101#1#0", "NT-062#1#0"}]
    rag = tmp / "rag"
    rag.mkdir()
    (rag / "rag.json").write_text(json.dumps({"version_rag": "test", "k": 3}), encoding="utf-8")
    contrat.ecrire_jsonl(rag / "chunks.jsonl", chunks)
    return Evaluation(config, corpus, rag)


def recherche(ev, resultats: dict[str, list[str]]):
    """Écrit recherches.jsonl : par défaut, un chunk sans rapport pour chaque question."""
    lignes = []
    for qid, q in ev.questions.items():
        ids = resultats.get(qid, ["NT-062#1#0"])
        lignes.append({"question_id": qid, "profil": q["profil"], "k": 3, "duree_ms": 1,
                       "resultats": [{"chunk_id": c, "rang": n} for n, c in enumerate(ids, start=1)]})
    contrat.ecrire_jsonl(ev.dossier_rag / "recherches.jsonl", lignes)


def scores(lignes, question_id):
    return {l.score: l.valeur for l in lignes if l.question_id == question_id and l.objet is None}


def liens():
    return [{"passage_id": p, "chunk_id": c} for p, c in LIENS]


def test_q001_un_seul_suffit_trouve_au_rang_2(ev):
    # Recherche : [chunk sans rapport, schéma de PR-1101 (passage 3), texte de PR-1101 (passage 2)]
    # Réussite : un passage suffit, le schéma est dans les 3 premiers → 1.
    # Rang du premier bon chunk : 2e → 1/2. Rappel : les deux passages ont un chunk dans les 3 → 1 et 1.
    recherche(ev, {"Q-001": ["PR-1101#1#0", "PR-1101#2#1", "PR-1101#2#0"]})
    lignes = niveau2.evaluer(ev, liens())
    s = scores(lignes, "Q-001")
    assert s["n2_reussite_k"] == 1.0 and s["n2_rang_premier"] == 0.5 and s["n2_fuite_droits"] == 0.0
    assert s["n2_reussite_1"] == 0.0 and s["n2_reussite_3"] == 1.0
    assert [l.valeur for l in lignes if l.question_id == "Q-001" and l.score == "n2_rappel_k"] == [1.0, 1.0]


def test_q013_piege_perime_classe_avant_le_bon(ev):
    # Recherche : [ancienne version PR-1104-B (piège), PR-1104-C (passage 18)]
    # Réussite : 1 (passage 18 trouvé) ; rang premier : 1/2 ; périmé ou piège avant le bon chunk : 1.
    # Rappel : passage 18 trouvé (1), passage 19 absent (0).
    recherche(ev, {"Q-013": ["PR-1104-B#2#1", "PR-1104-C#2#1"]})
    lignes = niveau2.evaluer(ev, liens())
    s = scores(lignes, "Q-013")
    assert (s["n2_reussite_k"], s["n2_rang_premier"], s["n2_perimes_pieges"]) == (1.0, 0.5, 1.0)
    assert [l.valeur for l in lignes if l.question_id == "Q-013" and l.score == "n2_rappel_k"] == [1.0, 0.0]


def test_q030_a_combiner_un_passage_manque(ev):
    # Recherche : [OT-24101 (passage 49), sans rapport] : il manque OT-24112 (passage 50).
    # Réussite (à combiner) : 0 ; rang du premier bon chunk : 1 ; rappel : 1 et 0.
    recherche(ev, {"Q-030": ["OT-24101#Actions", "NT-062#1#0"]})
    lignes = niveau2.evaluer(ev, liens())
    s = scores(lignes, "Q-030")
    assert (s["n2_reussite_k"], s["n2_rang_premier"]) == (0.0, 1.0)
    recherche(ev, {"Q-030": ["OT-24112#Actions", "NT-062#1#0", "OT-24101#Actions"]})
    assert scores(niveau2.evaluer(ev, liens()), "Q-030")["n2_reussite_k"] == 1.0


def test_q007_fuite_de_droits_bloquante(ev):
    # Q-007 est posée avec le profil exploitation ; NT-051 est réservé à la maintenance : fuite = 1.
    # La question « non accessible » n'est pas comptée en réussite.
    recherche(ev, {"Q-007": ["NT-051#2#0"]})
    lignes = niveau2.evaluer(ev, liens())
    s = scores(lignes, "Q-007")
    assert s == {"n2_fuite_droits": 1.0}
    resultat = calculer_scores(lignes, ev.seuils)
    assert resultat["decision"]["criteres_bloquants_declenches"] == [
        {"score": "n2_fuite_droits", "valeur": 1.0, "seuil": 0}]
    assert resultat["decision"]["mise_en_production_possible"] is False


def test_questions_non_comptees(ev):
    recherche(ev, {})
    lignes = niveau2.evaluer(ev, liens())
    comptees = {l.question_id for l in lignes if l.score == "n2_reussite_k"}
    # ni les questions sans réponse (Q-047), ni les synthèses (Q-041), ni les non accessibles (Q-007)
    assert {"Q-047", "Q-041", "Q-007"}.isdisjoint(comptees) and "Q-001" in comptees
    # toutes les questions sont contrôlées pour la fuite de droits
    assert len([l for l in lignes if l.score == "n2_fuite_droits"]) == 60
