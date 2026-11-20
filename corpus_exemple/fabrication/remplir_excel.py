"""Remplit le fichier Excel du métier (copie du modèle docs/Corpus_evaluation_RAG.xlsx) pour le corpus d'exemple.

Lit :
- contenus/*.json : les documents (feuille Documents) et le texte de chaque page ;
- questions.yaml : les questions et leurs passages (feuilles Questions et Passages) ;
- les pages des notes scannées choisies comme pages de référence OCR (feuille Pages OCR).

Avant d'écrire, il vérifie chaque passage contre la source, comme le ferait le métier en relisant :
texte et tableau copiés depuis la bonne page, schéma présent sur la page, fiche : valeur du champ.
Il recalcule enfin le tableau de bord du fichier (les formules ne sont calculées qu'à l'ouverture
dans Excel) et affiche chaque ligne avec son statut.

Usage : uv run python corpus_exemple/fabrication/remplir_excel.py
"""

import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import openpyxl
import yaml

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
MODELE = RACINE / "docs" / "Corpus_evaluation_RAG.xlsx"
SORTIE = ICI.parent / "Corpus_evaluation_RAG.xlsx"

# Pages de référence OCR : les 4 pages de chacune des 5 notes scannées (20 pages, configuration minimale)
NOTES_SCANNEES = ["NT-031", "NT-034", "NT-038", "NT-040", "NT-042"]

LISTES = {
    "A": ["Procédure", "Compte rendu d'intervention", "Note technique"],
    "B": ["GED Valtéra", "GMAO Atlas", "Archives techniques"],
    "E": ["Tous les utilisateurs", "Maintenance", "Exploitation"],
}


# ---------- lecture des sources ----------

def charger_documents() -> dict:
    return {json.loads(f.read_text(encoding="utf-8"))["reference_source"]: json.loads(f.read_text(encoding="utf-8"))
            for f in sorted((ICI / "contenus").glob("*.json"))}


def lignes_page(doc: dict, numero: int) -> list[str]:
    """Le texte d'une page tel qu'on le lit sur le PDF, dans l'ordre de lecture (en-tête et pied compris).

    Sert de texte retapé pour les pages OCR : un tableau ligne par ligne, cellules séparées par « | »."""
    page = doc["pages"][numero - 1]
    scanne = doc["format"] == "PDF scanné"
    lignes = []
    if scanne:
        lignes.append("VALTÉRA INDUSTRIES — Archives techniques")
    elif doc["format"] == "Fiche de base de données":
        lignes.append(f"GMAO Atlas — export de la fiche {doc['reference_source']}")
    else:
        lignes.append(f"Valtéra Industries — {doc['type_document']} {doc['reference_source']} — {doc['version']}")
    if numero == 1:
        lignes.append(f"{doc['reference_source']} — {doc['titre']}")
    for bloc in page["blocs"]:
        t = bloc["type"]
        if t in ("titre", "paragraphe"):
            lignes.append(bloc["texte"])
        elif t == "liste":
            lignes += [f"– {e}" for e in bloc["elements"]]
        elif t == "tableau":
            if bloc.get("titre"):
                lignes.append(bloc["titre"])
            lignes.append(" | ".join(bloc["entetes"]))
            lignes += [" | ".join(str(c) for c in ligne) for ligne in bloc["lignes"]]
        elif t == "figure":
            lignes += [b["texte"] for b in bloc["boites"]] + [l[2] for l in bloc["liens"] if l[2]]
            lignes.append(bloc["legende"])
        elif t == "fiche":
            lignes += [f"{nom} : {valeur}" for nom, valeur in bloc["champs"]]
    lignes.append(f"{doc['reference_source']} — page {numero}/{len(doc['pages'])}")
    return lignes


def normaliser(texte: str) -> str:
    """Casse, espaces, apostrophes et guillemets : la même normalisation que le rattachement du kit."""
    texte = unicodedata.normalize("NFKC", texte).lower()
    texte = texte.replace("’", "'").replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", texte).strip()


# ---------- vérification des passages ----------

def verifier_passage(p: dict, docs: dict) -> str | None:
    """Rend un message d'erreur si le passage ne se retrouve pas dans la source, sinon None."""
    doc = docs.get(p["reference"])
    if doc is None:
        return f"document inconnu {p['reference']}"
    if doc["format"] == "Fiche de base de données":
        champs = dict(doc["pages"][0]["blocs"][0]["champs"])
        if p["page"] not in champs:
            return f"{p['reference']} : champ « {p['page']} » absent"
        if normaliser(p["passage"]) not in normaliser(str(champs[p["page"]])):
            return f"{p['reference']} / {p['page']} : valeur non trouvée"
        return None
    numero = int(p["page"])
    if not 1 <= numero <= len(doc["pages"]):
        return f"{p['reference']} : page {numero} hors du document"
    page = doc["pages"][numero - 1]
    texte = normaliser(" ".join(lignes_page(doc, numero)))
    if p["type"] == "Image ou schéma":
        return None if any(b["type"] == "figure" for b in page["blocs"]) else f"{p['reference']} p.{numero} : pas de figure"
    if p["type"] == "Tableau":
        mots = set(re.findall(r"\w+", normaliser(p["passage"])))
        manquants = [m for m in mots if m not in set(re.findall(r"\w+", texte))]
        return f"{p['reference']} p.{numero} : mots absents du tableau {manquants}" if manquants else None
    if normaliser(p["passage"]) not in texte:
        return f"{p['reference']} p.{numero} : passage non trouvé tel quel"
    return None


# ---------- écriture du fichier ----------

def vider(feuille, colonnes: str, debut: int = 2):
    """Efface les valeurs saisies (pas les formules) des colonnes données, à partir de la ligne debut."""
    for ligne in feuille.iter_rows(min_row=debut, max_row=feuille.max_row):
        for cellule in ligne:
            if cellule.column_letter in colonnes and not (isinstance(cellule.value, str) and cellule.value.startswith("=")):
                cellule.value = None


def remplir(docs: dict, questions: list[dict]):
    shutil.copyfile(MODELE, SORTIE)
    wb = openpyxl.load_workbook(SORTIE)

    listes = wb["Listes"]
    for col, valeurs in LISTES.items():
        for i in range(2, 32):
            listes[f"{col}{i}"].value = valeurs[i - 2] if i - 2 < len(valeurs) else None

    f = wb["Documents"]
    vider(f, "ABCDEFGHIJKLMNO")
    for i, d in enumerate(docs.values(), start=2):
        valeurs = [d["reference_source"], d["titre"], d["type_document"], d["source"], d["version"], d["date"],
                   d["format"], None if d["format"] == "Fiche de base de données" else len(d["pages"]),
                   d["criticite"], d["droits_acces"], "Oui" if d["en_vigueur"] else "Non", d["remplace_par"],
                   d["selection"], d["service"], d["site"]]
        for j, v in enumerate(valeurs):
            f.cell(row=i, column=j + 1, value=v)

    f = wb["Questions"]
    vider(f, "ABCDEFGHIJKLMNOPQS")
    for i, q in enumerate(questions, start=2):
        valeurs = {"A": q["id"], "B": q["question"], "C": q.get("profil", "Tous les utilisateurs"),
                   "D": q.get("redigee_par", "Métier"), "E": q["type_reponse"], "F": q["reponse_dans_documents"],
                   "G": q.get("reponse_est_dans"), "H": q["reponse_attendue"], "I": q.get("points_cles"),
                   "J": q["difficulte"], "K": q["frequence"], "L": q["gravite"],
                   "M": "Oui" if q.get("reservee") else "Non", "N": q.get("precedente"), "O": q.get("variante_de"),
                   "P": q.get("annotateur", "Hélène Morvan"), "Q": q.get("date", "2026-11-18"),
                   "S": q.get("service", "Maintenance électrique")}
        for col, v in valeurs.items():
            f[f"{col}{i}"].value = v

    f = wb["Passages"]
    vider(f, "ABCDEF")
    i = 2
    for q in questions:
        for p in q.get("passages", []):
            for col, v in zip("ABCDEF", [q["id"], p["reference"], str(p["page"]), p["type"], p["passage"], p["repond"]]):
                f[f"{col}{i}"].value = v
            i += 1

    f = wb["Pages OCR"]
    vider(f, "ABCDEF")
    i = 2
    for ref in NOTES_SCANNEES:
        for n in range(1, len(docs[ref]["pages"]) + 1):
            for col, v in zip("ABCDEF", [ref, str(n), "\n".join(lignes_page(docs[ref], n)),
                                         "Thomas Rigaud", "Hélène Morvan", "2026-11-17"]):
                f[f"{col}{i}"].value = v
            i += 1
    wb.save(SORTIE)


# ---------- tableau de bord recalculé ----------

def tableau_de_bord(docs: dict, questions: list[dict]) -> list[tuple[str, object, str]]:
    """Les mêmes règles que la feuille « Tableau de bord » (configuration minimale)."""
    n = len(questions)
    compte = lambda cond: sum(1 for q in questions if cond(q))
    nb_passages = lambda q: sum(1 for p in q.get("passages", []) if p["repond"] != "Piège")
    lignes = [
        ("Questions annotées", n, "OK minimum" if n >= 50 else "À compléter"),
        ("Sans réponse dans les documents", compte(lambda q: q["reponse_dans_documents"] == "Non"), None),
        ("Plusieurs passages", compte(lambda q: (q.get("reponse_est_dans") or "").startswith("Plusieurs")), None),
        ("Réponse existe mais sans passage", compte(lambda q: q["reponse_dans_documents"] == "Oui" and nb_passages(q) == 0), None),
        ("Réservées à la décision", compte(lambda q: q.get("reservee")), None),
        ("Profil restreint", compte(lambda q: q.get("profil", "Tous les utilisateurs") != "Tous les utilisateurs"), None),
        ("dont non accessible", compte(lambda q: q["reponse_dans_documents"] == "Non accessible à ce profil"), None),
        ("Synthèses", compte(lambda q: q["type_reponse"] == "Synthèse"), None),
        ("Pages de référence OCR", sum(len(docs[r]["pages"]) for r in NOTES_SCANNEES), None),
        ("Questions avec piège", compte(lambda q: any(p["repond"] == "Piège" for p in q.get("passages", []))), None),
        ("Questions de suite", compte(lambda q: q.get("precedente")), None),
        ("Variantes", compte(lambda q: q.get("variante_de")), None),
    ]
    minimums = {"Sans réponse dans les documents": 5, "Plusieurs passages": 5, "Profil restreint": 5,
                "dont non accessible": 2, "Synthèses": 5, "Pages de référence OCR": 20}
    resultat = []
    for nom, valeur, statut in lignes:
        if statut is None and nom in minimums:
            statut = "OK minimum" if valeur >= minimums[nom] else "À compléter"
        elif nom == "Réponse existe mais sans passage":
            statut = "OK" if valeur == 0 else "À compléter"
        elif nom == "Réservées à la décision":
            statut = "OK" if valeur >= n / 3 * 0.8 else "À compléter"
        elif statut is None:
            statut = "OK recommandé" if valeur >= 0.1 * n else "Facultatif"
        resultat.append((nom, valeur, statut))
    for type_doc in LISTES["A"]:
        nb_docs = sum(1 for d in docs.values() if d["type_document"] == type_doc)
        nb_q = compte(lambda q: any(docs[p["reference"]]["type_document"] == type_doc for p in q.get("passages", [])))
        resultat.append((f"{type_doc} : documents", nb_docs, "OK minimum" if nb_docs >= 10 else "À compléter"))
        resultat.append((f"{type_doc} : questions", nb_q, "OK" if nb_q >= 5 else "À compléter"))
    return resultat


def liste_pour_relecture(questions: list[dict]) -> str:
    """La liste des questions en Markdown, pour la relecture par le métier."""
    lignes = ["# Questions du corpus d'exemple — liste pour relecture", "",
              "Générée par `remplir_excel.py` depuis `fabrication/questions.yaml`. "
              "R = réservée à la décision ; S = question de suite de ; V = variante de ; P = avec passage piège.", "",
              "| Id | Question | Profil | Type | Dans les docs ? | La réponse est dans | Réponse attendue | Gravité | Marques |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for q in questions:
        marques = []
        if q.get("reservee"):
            marques.append("R")
        if q.get("precedente"):
            marques.append(f"S {q['precedente']}")
        if q.get("variante_de"):
            marques.append(f"V {q['variante_de']}")
        if any(p["repond"] == "Piège" for p in q.get("passages", [])):
            marques.append("P")
        cellules = [q["id"], q["question"], q.get("profil", "Tous les utilisateurs"), q["type_reponse"],
                    q["reponse_dans_documents"], q.get("reponse_est_dans") or "—", q["reponse_attendue"],
                    q["gravite"], " · ".join(marques)]
        lignes.append("| " + " | ".join(str(c).replace("|", "\\|") for c in cellules) + " |")
    return "\n".join(lignes) + "\n"


if __name__ == "__main__":
    docs = charger_documents()
    questions = yaml.safe_load((ICI / "questions.yaml").read_text(encoding="utf-8"))
    erreurs = [f"{q['id']} : {e}" for q in questions for p in q.get("passages", []) if (e := verifier_passage(p, docs))]
    if erreurs:
        print("Passages à corriger :\n  " + "\n  ".join(erreurs))
        sys.exit(1)
    remplir(docs, questions)
    (ICI.parent / "questions_pour_relecture.md").write_text(liste_pour_relecture(questions), encoding="utf-8")
    print(f"Écrit : {SORTIE.relative_to(RACINE)} et corpus_exemple/questions_pour_relecture.md\n\nTableau de bord (recalculé) :")
    for nom, valeur, statut in tableau_de_bord(docs, questions):
        print(f"  {nom:<45} {valeur!s:>5}  {statut}")
