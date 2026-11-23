"""Évaluation de l'ingestion, le graphe : les règles SHACL d'une ontologie de test, appliquées par pySHACL."""

from pathlib import Path

from kit.etape_1_evaluation_ingestion import graphe

FORMES = Path(__file__).parent / "donnees" / "ontologie_formes.ttl"   # une ontologie de test : le RAG d'exemple n'a pas de graphe

ENTETE = """@prefix vt: <https://valtera.exemple/ontologie#> .
@prefix kit: <https://kit-eval-rag/ns#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""

CONFORME = ENTETE + """
vt:entite-tr-a1 a vt:Equipement ; rdfs:label "TR-A1" ; kit:referenceSource "NT-051" ; kit:page "2" ;
    vt:alimente vt:entite-tgbt-a .
vt:entite-tgbt-a a vt:Equipement ; rdfs:label "TGBT-A" ; kit:referenceSource "NT-051" ; kit:page "2" .
vt:relation-1 a rdf:Statement ; rdf:subject vt:entite-tr-a1 ; rdf:predicate vt:alimente ; rdf:object vt:entite-tgbt-a ;
    kit:referenceSource "NT-051" ; kit:page "2" .
"""


def ecrire(tmp_path: Path, texte: str) -> Path:
    chemin = tmp_path / "graphe.ttl"
    chemin.write_text(texte, encoding="utf-8")
    return chemin


def test_graphe_conforme(tmp_path):
    assert graphe.violations(ecrire(tmp_path, CONFORME), FORMES) == []


def test_violations_classe_et_provenance(tmp_path):
    # Un site qui « alimente » un équipement (mauvaise classe), et une relation sans page (provenance incomplète)
    faux = CONFORME + """
vt:entite-site-a a vt:Site ; rdfs:label "Site A" ; kit:referenceSource "PR-1101" ; kit:page "1" ;
    vt:alimente vt:entite-tgbt-a .
vt:relation-2 a rdf:Statement ; rdf:subject vt:entite-site-a ; rdf:predicate vt:alimente ; rdf:object vt:entite-tgbt-a ;
    kit:referenceSource "PR-1101" .
"""
    vs = graphe.violations(ecrire(tmp_path, faux), FORMES)
    assert any(v["noeud"] == "Site A" for v in vs)                         # le sujet de « alimente » doit être un Equipement
    assert any(v["noeud"] == "relation-2" and v["propriete"] == "page" for v in vs)   # kit:page manque


def test_relations_avec_provenance(tmp_path):
    [r] = graphe.relations(ecrire(tmp_path, CONFORME))
    assert (r["texte"], r["reference_source"], r["page"]) == ("TR-A1 alimente TGBT-A", "NT-051", "2")
