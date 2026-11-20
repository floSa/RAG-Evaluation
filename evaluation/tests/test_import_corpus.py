"""Tests de l'import du fichier Excel (kit importer), sur le corpus d'exemple et sur des copies volontairement fausses."""

import shutil
from pathlib import Path

import openpyxl
import pytest

from kit import contrat
from kit.import_corpus import importer, lire_points_cles

EXEMPLE = Path("corpus/exemple/Corpus_evaluation_RAG.xlsx")


def lancer(tmp_path: Path, fichier: Path = EXEMPLE, jour: str = "2026-11-20"):
    return importer(fichier, f"sqlite:///{tmp_path}/base.sqlite", tmp_path / "sorties", "test", aujourd_hui=jour)


def copie_modifiee(tmp_path: Path, modifications: list[tuple[str, int, str, object]], nom="faux.xlsx") -> Path:
    """Copie du corpus d'exemple où l'on change des cellules : (feuille, ligne Excel, titre de colonne, valeur)."""
    chemin = tmp_path / nom
    shutil.copy(EXEMPLE, chemin)
    classeur = openpyxl.load_workbook(chemin)
    for feuille, ligne, titre, valeur in modifications:
        f = classeur[feuille]
        colonne = [c.value for c in f[1]].index(titre) + 1
        f.cell(row=ligne, column=colonne).value = valeur  # cell(value=None) ne viderait pas la cellule
    classeur.save(chemin)
    return chemin


def ligne_de(feuille: str, colonne: str, valeur: str, colonne2: str | None = None, valeur2: str | None = None) -> int:
    """Numéro de ligne Excel de la première ligne où `colonne` vaut `valeur` (et `colonne2` vaut `valeur2`)."""
    f = openpyxl.load_workbook(EXEMPLE)[feuille]
    entetes = [c.value for c in f[1]]
    for n, r in enumerate(f.iter_rows(min_row=2, values_only=True), start=2):
        if r[entetes.index(colonne)] == valeur and (colonne2 is None or r[entetes.index(colonne2)] == valeur2):
            return n
    raise LookupError(valeur)


def test_corpus_exemple_s_importe_sans_erreur(tmp_path):
    r = lancer(tmp_path)
    assert r.erreurs == [] and r.avertissements == []
    assert r.version_corpus == "2026-11-20.1"
    c = contrat.charger_corpus(r.dossier)
    assert (len(c["documents"]), len(c["questions"]), len(c["passages"]), len(c["pages_ocr"])) == (50, 60, 97, 20)
    assert c["corpus"]["colonnes_libres"] == ["service", "site"]
    assert contrat.verifier_dossier(r.dossier) == []


def test_conversion_des_libelles_en_codes(tmp_path):
    c = contrat.charger_corpus(lancer(tmp_path).dossier)
    docs = {d["reference_source"]: d for d in c["documents"]}
    assert docs["NT-031"]["format"] == "pdf_scanne"
    assert docs["OT-24109"]["droits_acces"] == "maintenance"
    assert docs["PR-1104-B"]["en_vigueur"] is False and docs["PR-1104-B"]["remplace_par"] == "PR-1104-C"
    qs = {q["question_id"]: q for q in c["questions"]}
    assert qs["Q-007"]["profil"] == "exploitation" and qs["Q-007"]["reponse_dans_documents"] == "non_accessible"
    assert qs["Q-001"]["reponse_est_dans"] == "plusieurs_un_suffit"
    assert qs["Q-003"]["question_precedente"] == "Q-002" and qs["Q-003"]["reservee_decision"] is True
    assert "points_cles" not in qs["Q-047"]  # question sans réponse : pas de points clés
    assert contrat.historique(qs["Q-003"], qs) == [{"question": qs["Q-002"]["question"],
                                                   "reponse": qs["Q-002"]["reponse_attendue"]}]


def test_passage_id_est_le_numero_de_ligne_au_premier_import(tmp_path):
    passages = contrat.charger_corpus(lancer(tmp_path).dossier)["passages"]
    assert [p["passage_id"] for p in passages] == list(range(2, 99))


def test_meme_fichier_pas_de_nouvelle_version(tmp_path):
    lancer(tmp_path)
    r = lancer(tmp_path, jour="2026-11-21")
    assert r.deja_importe and r.version_corpus == "2026-11-20.1"


def test_fichier_modifie_nouvelle_version_et_identifiants_stables(tmp_path):
    lancer(tmp_path)
    n = ligne_de("Passages", "Question", "Q-002")
    modifie = copie_modifiee(tmp_path, [("Passages", n, "Passage", "La consignation d'une armoire divisionnaire "
                                                                   "demande en moyenne 20 minutes")])
    r = lancer(tmp_path, modifie)
    assert r.version_corpus == "2026-11-20.2"
    passages = {p["passage_id"]: p for p in contrat.charger_corpus(r.dossier)["passages"]}
    assert n not in passages                      # la ligne modifiée a perdu son ancien identifiant…
    assert passages[99]["question_id"] == "Q-002"  # …et reçu un identifiant jamais utilisé
    assert passages[2]["question_id"] == "Q-001"   # les lignes inchangées gardent le leur


@pytest.mark.parametrize("modification, attendu", [
    (("Questions", 2, "Profil de l'utilisateur", "Exploit"),
     "feuille Questions, ligne 2 (Q-001) : « Exploit » n'est pas dans la colonne « Profils d'accès »"),
    (("Questions", 2, "Difficulté", "Très dure"), "« Très dure » n'est pas une valeur admise pour « Difficulté »"),
    (("Questions", 2, "Question", None), "la colonne « Question » est obligatoire et elle est vide"),
    (("Questions", 3, "Identifiant", "Q-001"), "l'identifiant « Q-001 » est déjà utilisé ligne 2"),
    (("Questions", 4, "Question précédente", "Q-999"), "« Question précédente » renvoie à « Q-999 »"),
    (("Passages", 2, "Référence du document", "PR-9999"),
     "le document « PR-9999 » n'existe pas dans la feuille Documents"),
])
def test_fichier_faux_rejete_avec_le_bon_message(tmp_path, modification, attendu):
    r = lancer(tmp_path, copie_modifiee(tmp_path, [modification]))
    assert r.version_corpus is None
    assert any(attendu in e for e in r.erreurs), r.erreurs
    assert not (tmp_path / "sorties").exists()  # rien n'est écrit


def test_question_oui_sans_passage_rejetee(tmp_path):
    # Q-002 n'a qu'un passage : on le rattache à une autre question
    n = ligne_de("Passages", "Question", "Q-002")
    r = lancer(tmp_path, copie_modifiee(tmp_path, [("Passages", n, "Question", "Q-001")]))
    assert any("(Q-002) : la réponse est dans les documents, mais aucun passage" in e for e in r.erreurs)


def test_non_accessible_sans_document_interdit_rejetee(tmp_path):
    # Q-007 (Exploitation) : on ouvre à tous le document réservé qui porte sa réponse
    passages = openpyxl.load_workbook(EXEMPLE)["Passages"]
    refs = {r[1] for r in passages.iter_rows(min_row=2, values_only=True) if r[0] == "Q-007"}
    modifs = [("Documents", ligne_de("Documents", "Référence dans la source", ref), "Droits d'accès",
               "Tous les utilisateurs") for ref in refs]
    r = lancer(tmp_path, copie_modifiee(tmp_path, modifs))
    assert any("(Q-007) : la réponse est « non accessible à ce profil », mais aucun passage" in e for e in r.erreurs)


def test_avertissement_configuration_minimale(tmp_path):
    # ne garder que 49 questions : l'import passe, avec un avertissement
    chemin = copie_modifiee(tmp_path, [])
    classeur = openpyxl.load_workbook(chemin)
    f = classeur["Questions"]
    ids = [r[0] for r in f.iter_rows(min_row=2, values_only=True) if r[0]]
    garder = set(ids[:49]) | {"Q-002", "Q-016", "Q-019", "Q-027", "Q-032", "Q-005", "Q-047", "Q-013"}
    for n in range(f.max_row, 1, -1):
        if f.cell(n, 1).value and f.cell(n, 1).value not in garder:
            f.delete_rows(n)
    p = classeur["Passages"]
    for n in range(p.max_row, 1, -1):
        if p.cell(n, 1).value and p.cell(n, 1).value not in garder:
            p.delete_rows(n)
    classeur.save(chemin)
    r = lancer(tmp_path, chemin)
    assert r.erreurs == []
    assert any("questions ; minimum 50" in a for a in r.avertissements), r.avertissements


@pytest.mark.parametrize("texte, attendu", [
    ("2,3 ans ± 0,1", [{"texte": "2,3 ans ± 0,1", "valeur": 2.3, "unite": "ans", "tolerance": 0.1}]),
    ("1 384 €", [{"texte": "1 384 €", "valeur": 1384, "unite": "€", "tolerance": 0}]),
    ("HC ; second intervenant H2V", [{"texte": "HC"}, {"texte": "second intervenant H2V"}]),
    ("12 mois ; à faire avant la remise sous tension", [{"texte": "12 mois", "valeur": 12, "unite": "mois",
                                                         "tolerance": 0},
                                                        {"texte": "à faire avant la remise sous tension"}]),
    (None, []),
])
def test_points_cles(texte, attendu):
    assert lire_points_cles(texte) == attendu
