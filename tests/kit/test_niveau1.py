"""Tests du niveau 1 : règles de rattachement, causes probables, taux d'erreur OCR, et cas réels du corpus d'exemple."""

import json
import shutil
from pathlib import Path

import openpyxl
import pytest
import yaml

from kit import contrat, niveau1
from kit.import_corpus import importer
from kit.publication import Evaluation

SEUILS = {"texte_approche": 0.95, "tableau_mots": 0.90, "scanne_partiel": 0.90}
EXEMPLE = Path("corpus_exemple/Corpus_evaluation_RAG.xlsx")


def passage(texte, type_element="texte", page="2", passage_id=1):
    return {"passage_id": passage_id, "passage": texte, "type_element": type_element, "page": page,
            "reference_source": "PR-1101", "question_id": "Q-001"}


def chunk(texte, page="2", ordre=0, type_element="texte"):
    return {"chunk_id": f"PR-1101#{page}#{ordre}", "page": page, "ordre": ordre, "type_element": type_element,
            "texte": texte, "version_index": "i1", "reference_source": "PR-1101"}


def test_normalisation():
    assert niveau1.normaliser("L’armoire  «AD-A07»\nest con-\nsignée") == "l'armoire \"ad-a07\" est consignée"


def test_texte_exact_et_approche():
    p = passage("La consignation d'une armoire divisionnaire demande en moyenne 20 minutes.")
    assert niveau1.comparer(p, "5. Déroulement\nLa consignation d’une armoire divisionnaire demande en moyenne "
                               "20 minutes. Aucune étape…", SEUILS) == ("exact", 1.0)
    mode, s = niveau1.comparer(p, "La consignation d'une armoire divisionaire demande en moyenne 20 minutes.", SEUILS)
    assert mode == "approche" and s >= 0.95
    assert niveau1.comparer(p, "La consignation d'un TGBT demande 90 minutes.", SEUILS)[0] is None


def test_tableau_memes_mots_dans_un_autre_ordre():
    # passage réel de Q-003 (PR-1101 page 3), chunk rendu en « colonne : valeur » par le RAG de démonstration
    p = passage("Point | Armoire divisionnaire BT | TGBT\nDurée moyenne | 20 minutes | 90 minutes", "tableau", "3")
    rendu = "Tableau 2\nPoint : Durée moyenne ; Armoire divisionnaire BT : 20 minutes ; TGBT : 90 minutes"
    assert niveau1.comparer(p, rendu, SEUILS)[0] == "approche"
    assert niveau1.comparer(p, "Point : Section MALT-CC ; Armoire divisionnaire BT : 25 mm²", SEUILS)[0] is None


def test_texte_scanne_avec_erreurs_d_ocr():
    # NT-031 page 2, tel que Docling l'a lu (mots collés, « 1.600 »)
    p = passage("Le courant de court-circuit maximal calculé au jeu de barres du TGBT-A est de 36 kA",
                "texte_scanne")
    ocr = "3. Données d'entrée\nLe courant de court-circuit maximal calculé au jeu de barres du TGBT-Aest de 36 kA, un"
    assert niveau1.comparer(p, ocr, SEUILS)[0] == "approche"


def test_image_rattachee_a_un_chunk_image_de_la_meme_page():
    p = passage("Figure 1 : les cinq opérations de consignation", "image_schema")
    liens, _ = niveau1.rattacher(p, [chunk("texte", ordre=0), chunk("Figure 1 - Ordre des opérations", ordre=1,
                                                                    type_element="image_schema")], False, SEUILS)
    assert [(l.chunk_id, l.mode) for l in liens] == [("PR-1101#2#1", "image")]


def test_fiche_de_base_par_nom_de_champ():
    p = {**passage("1 interrupteur différentiel 4P 40 A 30 mA type A (186 €)", page="Pièces remplacées"),
         "reference_source": "OT-24101"}
    un_chunk_par_champ = [chunk("OT-24101\nPièces remplacées : 1 interrupteur différentiel 4P 40 A 30 mA type A "
                                "(186 €)", page="Pièces remplacées")]
    une_fiche_entiere = [chunk("Numéro OT : OT-24101\nPièces remplacées : 1 interrupteur différentiel 4P 40 A 30 mA "
                               "type A (186 €)\nCoût : 186", page="1")]
    assert niveau1.rattacher(p, un_chunk_par_champ, True, SEUILS)[0][0].mode == "exact"
    assert niveau1.rattacher(p, une_fiche_entiere, True, SEUILS)[0][0].mode == "exact"


def test_passage_coupe_entre_deux_chunks():
    p = passage("Aucune étape ne peut être omise ni intervertie. La consignation demande 20 minutes.")
    chunks = [chunk("… dans l'ordre. Aucune étape ne peut être omise", ordre=0),
              chunk("ni intervertie. La consignation demande 20 minutes.", ordre=1)]
    liens, _ = niveau1.rattacher(p, chunks, False, SEUILS)
    assert [(l.chunk_id, l.mode) for l in liens] == [("PR-1101#2#0", "coupe"), ("PR-1101#2#1", "coupe")]


def test_taux_erreur_de_caracteres():
    cer, wer = niveau1.taux_erreur("Maintenance électrique\nsite A", "Maintenanceélectrique site A")
    assert cer == pytest.approx(1 / 29) and wer == pytest.approx(2 / 4)
    assert niveau1.taux_erreur("texte", None) == (1.0, 1.0)


# --- Cas réel : le corpus d'exemple, et un passage volontairement mal noté --------------------

def chunks_parfaits(dossier_corpus: Path) -> list[dict]:
    """Un index idéal : un chunk par passage du corpus, à sa page, avec son texte."""
    docs = {d["reference_source"]: d for d in contrat.lire_jsonl(dossier_corpus / "documents.jsonl")}
    chunks = []
    for p in contrat.lire_jsonl(dossier_corpus / "passages.jsonl"):
        d = docs[p["reference_source"]]
        chunks.append({"chunk_id": f"c{p['passage_id']}", "type_objet": "chunk", "reference_source": p["reference_source"],
                       "version_document": d["version"], "page": p["page"], "type_element": p["type_element"],
                       "droits_acces": d["droits_acces"], "ordre": 0, "texte": p["passage"], "version_index": "i1"})
    return chunks


@pytest.fixture
def evaluation(tmp_path):
    """Corpus d'exemple dont un passage de Q-002 est noté page 4 au lieu de page 2 ; index fait sur les vraies pages."""
    vrai = importer(EXEMPLE, f"sqlite:///{tmp_path}/vrai.sqlite", tmp_path / "vrai", "test").dossier
    faux_xlsx = tmp_path / "faux.xlsx"
    shutil.copy(EXEMPLE, faux_xlsx)
    classeur = openpyxl.load_workbook(faux_xlsx)
    f = classeur["Passages"]
    ligne = next(n for n, r in enumerate(f.iter_rows(min_row=2, values_only=True), start=2) if r[0] == "Q-002")
    f.cell(ligne, 3).value = "4"
    classeur.save(faux_xlsx)
    config = yaml.safe_load(Path("config/kit.yaml").read_text(encoding="utf-8"))
    config["chemins"] = {"base": f"sqlite:///{tmp_path}/base.sqlite", "sorties": str(tmp_path / "sorties"),
                         "seuils": "config/seuils.json"}
    faux = importer(faux_xlsx, config["chemins"]["base"], tmp_path / "sorties", "test").dossier
    rag = tmp_path / "rag"
    rag.mkdir()
    (rag / "rag.json").write_text(json.dumps({"contrat": "1.0", "version_rag": "ideal", "k": 5}), encoding="utf-8")
    contrat.ecrire_jsonl(rag / "chunks.jsonl", chunks_parfaits(vrai))
    return Evaluation(config, faux, rag), ligne


def test_passage_mal_note_signale(evaluation):
    ev, passage_id = evaluation
    lignes, liens, non_rattaches = niveau1.evaluer(ev)
    assert [p["passage_id"] for p in non_rattaches] == [passage_id]
    assert non_rattaches[0]["cause_probable"] == ("aucun chunk sur la page 4 ; le passage est trouvé page 2 : "
                                                  "page mal notée ?")
    rattaches = [l.valeur for l in lignes if l.score == "n1_passages_rattaches"]
    assert len(rattaches) == 91 and sum(rattaches) == 90  # 97 passages dont 6 pièges
    assert all(l.valeur == 1.0 for l in lignes if l.score == "n1_metadonnees_completes")
    # les pages OCR sont absentes de cet index : taux d'erreur de 100 %, signalé
    ocr = [l for l in lignes if l.score == "n1_erreur_caracteres"]
    assert len(ocr) == 20 and all(l.valeur == 1.0 and "absente" in l.detail for l in ocr)
