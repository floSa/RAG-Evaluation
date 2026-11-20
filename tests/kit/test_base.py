"""Base relationnelle : les tables du document 1 (section 5) sont créées, et un document s'y écrit."""

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from kit import base

TABLES_DOCUMENT_1 = {"documents", "questions", "passages", "pages_ocr", "liens_index", "evaluations", "resultats"}


def test_init_base_cree_les_tables(tmp_path):
    adresse = f"sqlite:///{tmp_path}/sous_dossier/base.sqlite"
    tables = base.init_base(adresse)
    assert TABLES_DOCUMENT_1 <= set(tables)
    # relancer ne casse rien (création des seules tables absentes)
    assert base.init_base(adresse) == tables
    colonnes = {c["name"] for c in inspect(base.moteur(adresse)).get_columns("passages")}
    assert {"passage_id", "question_id", "reference_source", "page", "type_element", "passage", "repond"} <= colonnes


def test_ecrire_un_document_du_corpus_exemple(tmp_path):
    """Cas réel du corpus d'exemple : la fiche OT-24109, réservée au profil Maintenance."""
    adresse = f"sqlite:///{tmp_path}/base.sqlite"
    base.init_base(adresse)
    with Session(base.moteur(adresse)) as s:
        s.add(base.Corpus(version_corpus="2026-11-20.1", contrat="1.0", projet="maintenance-electrique",
                          date="2026-11-20", fichier_source="Corpus_evaluation_RAG.xlsx", colonnes_libres=["service", "site"]))
        s.add(base.Document(version_corpus="2026-11-20.1", reference_source="OT-24109",
                            titre="Compte rendu d'intervention OT-24109", type_document="Compte rendu d'intervention",
                            source="GMAO Atlas", version="—", format="fiche_base", criticite="C3",
                            droits_acces="maintenance", en_vigueur=True, selection="hasard",
                            colonnes_libres={"service": "Maintenance électrique", "site": "Site A"}))
        s.commit()
        doc = s.get(base.Document, ("2026-11-20.1", "OT-24109"))
        assert doc.droits_acces == "maintenance"
        assert doc.colonnes_libres["site"] == "Site A"
