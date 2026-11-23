"""La vérification du juge par le métier, dans un fichier Excel (prompt_du_juge.md ; document 3, section 8).

Le métier ne touche à aucun outil : comme pour le corpus, on lui remet un fichier Excel. Une ligne par réponse du RAG
tirée au hasard : la question, la bonne réponse et ses points clés (ceux qu'il a écrits), la réponse du RAG. Il note
chaque réponse juste, partielle ou fausse, avec le même critère que le juge, sans voir la note du juge.
"""

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

NOTES = ("juste", "partielle", "fausse")
FEUILLE = "Réponses à noter"
COLONNES = [("Question", "question_id", 11), ("La question posée", "question", 40),
            ("La bonne réponse (fichier du métier)", "reponse_attendue", 45),
            ("Les points clés (fichier du métier)", "points_cles", 40), ("La réponse du RAG", "reponse_rag", 60),
            ("Votre note", "note", 13), ("Votre commentaire (facultatif)", "commentaire", 35)]
CRITERE = [
    "Vérifier le juge : noter les réponses du RAG",
    "",
    "Le juge est le modèle de langage qui note les réponses du RAG. Avant de croire ses notes, on vérifie qu'il note "
    "comme vous. Pour cela, notez vous-même les réponses de la feuille « Réponses à noter », avec le critère ci-dessous.",
    "",
    "Pour chaque réponse, regardez chacun des points clés que vous avez écrits pour cette question :",
    "  - la réponse le dit, avec les mêmes mots ou d'autres de même sens (un chiffre doit être exact, avec la bonne "
    "unité) ;",
    "  - la réponse ne le dit pas ;",
    "  - la réponse dit le contraire.",
    "",
    "Puis choisissez la note dans la colonne « Votre note » :",
    "  - juste : la réponse dit tous les points clés, et ne contredit rien ;",
    "  - partielle : elle en dit au moins un, et ne contredit rien ;",
    "  - fausse : elle contredit quelque chose, ou ne dit aucun point clé.",
    "",
    "Une information juste en plus des points clés ne change pas la note. Si le RAG dit qu'il ne sait pas, la réponse "
    "ne dit aucun point clé : elle est fausse.",
    "",
    "Notez toutes les lignes, puis rendez le fichier tel quel.",
]


def points_cles(question: dict) -> str:
    """Les points clés d'une question, un par ligne, avec leur tolérance s'il y en a une."""
    lignes = []
    for i, p in enumerate(question.get("points_cles") or [], start=1):
        texte = p.get("texte", "")
        if p.get("tolerance"):    # une valeur chiffrée, avec sa tolérance
            texte += f" (± {p['tolerance']}" + (f" {p['unite']}" if p.get("unite") else "") + ")"
        lignes.append(f"{i}. {texte}")
    return "\n".join(lignes)


def ecrire(chemin: Path, lignes: list[dict]) -> None:
    """Le fichier à remettre au métier : le mode d'emploi, puis une ligne par réponse à noter."""
    classeur = Workbook()
    mode = classeur.active
    mode.title = "Mode d'emploi"
    for n, texte in enumerate(CRITERE, start=1):
        mode.cell(row=n, column=1, value=texte).alignment = Alignment(wrap_text=True, vertical="top")
    mode["A1"].font = Font(bold=True, size=13)
    mode.column_dimensions["A"].width = 110

    f = classeur.create_sheet(FEUILLE)
    for c, (titre, _, largeur) in enumerate(COLONNES, start=1):
        cellule = f.cell(row=1, column=c, value=titre)
        cellule.font = Font(bold=True)
        cellule.fill = PatternFill("solid", fgColor="DDEBF7" if titre.startswith("Votre") else "EEEEEE")
        cellule.alignment = Alignment(wrap_text=True, vertical="top")
        f.column_dimensions[cellule.column_letter].width = largeur
    for n, ligne in enumerate(lignes, start=2):
        for c, (_, cle, _) in enumerate(COLONNES, start=1):
            f.cell(row=n, column=c, value=ligne.get(cle)).alignment = Alignment(wrap_text=True, vertical="top")
    liste = DataValidation(type="list", formula1='"' + ",".join(NOTES) + '"', allow_blank=True,
                           error="Choisir juste, partielle ou fausse.", showErrorMessage=True)
    f.add_data_validation(liste)
    liste.add(f"F2:F{len(lignes) + 1}")
    f.freeze_panes = "B2"
    classeur.save(chemin)


def lire(chemin: Path) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Les notes du métier : ({question: note}, {question: commentaire}, [questions sans note valable])."""
    f = load_workbook(chemin, read_only=True)[FEUILLE]
    notes, commentaires, manquantes = {}, {}, []
    for ligne in f.iter_rows(min_row=2, values_only=True):
        question_id, note, commentaire = ligne[0], ligne[5], ligne[6]
        if not question_id:
            continue
        note = str(note).strip().lower() if note else ""
        if note in NOTES:
            notes[question_id] = note
            if commentaire:
                commentaires[question_id] = str(commentaire)
        else:
            manquantes.append(question_id)
    return notes, commentaires, manquantes
