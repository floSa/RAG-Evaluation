"""Tests de l'extraction et du découpage du RAG de démonstration (sans réseau)."""

from pathlib import Path

from rag_demo import extraction

SOURCES = Path("evaluation/corpus_exemple/sources")

# Page 2 de PR-1101 telle que la rend Docling (extrait réel, raccourci) : légende avant l'image, puis un tableau.
PAGE_NATIVE = """## 5. Déroulement

La consignation comporte cinq étapes, toujours exécutées dans l'ordre. La consignation d'une armoire divisionnaire demande en moyenne 20 minutes.

Figure 1 - Ordre des opérations de consignation : les cinq étapes successives.

<!-- image -->

## Tableau 2 - Variantes selon l'ouvrage consigné

| Point          | Armoire divisionnaire BT | TGBT       |
|----------------|--------------------------|------------|
| Durée moyenne  | 20 minutes               | 90 minutes |
"""

DOC_NATIF = {"reference_source": "PR-1101", "titre": "Consignation d'une armoire basse tension", "version": "v3",
             "droits_acces": "tous", "format": "pdf_natif", "type_document": "Procédure"}


def test_fiche_de_base_un_couple_par_champ():
    champs = dict(extraction.fiche(SOURCES / "OT-24101.pdf"))
    assert champs["Pièces remplacées"] == "1 interrupteur différentiel 4P 40 A 30 mA type A (186 €)"
    assert champs["Coût des pièces (€ HT)"] == "186"
    # une valeur sur plusieurs lignes, qui contient elle-même « … : … », reste entière
    assert champs["Actions réalisées"].endswith("Test de déclenchement selon PR-1115 : conforme.")


def test_chunks_d_une_fiche_page_egale_nom_du_champ():
    doc = {**DOC_NATIF, "reference_source": "OT-24101", "titre": "Déclenchements intempestifs", "version": "1",
           "format": "fiche_base", "type_document": "Compte rendu d'intervention"}
    chunks = extraction.chunks_du_document(doc, {"fiche": extraction.fiche(SOURCES / "OT-24101.pdf")}, 1500)
    piece = next(c for c in chunks if c["page"] == "Pièces remplacées")
    assert piece["texte"].endswith("Pièces remplacées : 1 interrupteur différentiel 4P 40 A 30 mA type A (186 €)")
    assert piece["type_element"] == "texte" and piece["ordre"] == 0


def test_page_native_texte_figure_tableau():
    chunks = extraction.chunks_du_document(DOC_NATIF, {"pages": ["", PAGE_NATIVE]}, 1500)
    types = [(c["page"], c["ordre"], c["type_element"]) for c in chunks]
    assert types == [("2", 0, "texte"), ("2", 1, "image_schema"), ("2", 2, "tableau")]
    assert chunks[0]["texte"].startswith("PR-1101 — Consignation d'une armoire basse tension > 5. Déroulement\n")
    assert chunks[1]["texte"].endswith("Figure 1 - Ordre des opérations de consignation : les cinq étapes successives.")
    # tableau natif : lignes « colonne : valeur », avec le titre du tableau
    assert "Tableau 2 - Variantes selon l'ouvrage consigné\n" \
           "Point : Durée moyenne ; Armoire divisionnaire BT : 20 minutes ; TGBT : 90 minutes" in chunks[2]["texte"]


def test_page_scannee_reste_du_texte():
    doc = {**DOC_NATIF, "format": "pdf_scanne"}
    chunks = extraction.chunks_du_document(doc, {"pages": [PAGE_NATIVE]}, 1500)
    assert {c["type_element"] for c in chunks} == {"texte_scanne", "image_schema"}
    assert "Durée moyenne | 20 minutes | 90 minutes" in chunks[-1]["texte"]


def test_texte_de_page_pour_le_taux_d_erreur_ocr():
    texte = extraction.texte_de_page(PAGE_NATIVE)
    assert "<!--" not in texte and "#" not in texte
    assert "Point | Armoire divisionnaire BT | TGBT\nDurée moyenne | 20 minutes | 90 minutes" in texte


def test_section_trop_longue_recoupee():
    page = "## 1. Objet\n\n" + "\n\n".join(f"Paragraphe {i} " + "x" * 400 for i in range(6))
    chunks = extraction.chunks_du_document(DOC_NATIF, {"pages": [page]}, 1000)
    assert len(chunks) == 3 and [c["ordre"] for c in chunks] == [0, 1, 2]
