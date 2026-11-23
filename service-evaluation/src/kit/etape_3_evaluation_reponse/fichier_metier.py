"""Les fichiers Excel que le métier remplit, après une évaluation (prompt_du_juge.md ; document 3, sections 6 et 8).

Le métier ne touche à aucun outil : comme pour le corpus, on lui remet un fichier Excel, et il le rend rempli.
Trois fichiers, écrits dans le dossier de l'évaluation, à côté du RAPPORT.md :
- verification_juge.xlsx : des réponses du RAG tirées au hasard, qu'il note juste, partielle ou fausse, sans voir la
  note du juge ; le service mesure ainsi si le juge note comme lui ;
- relecture_reponses.xlsx : les réponses à relire (fausses ou partielles, questions graves, quelques-unes au hasard),
  avec la note du juge ; il dit s'il est d'accord, et sinon donne sa note ;
- justesse_graphe.xlsx : des relations du graphe du RAG, chacune avec le passage d'où elle vient ; il dit si elle est
  juste ou fausse.
"""

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

NOTES = ("juste", "partielle", "fausse")
CRITERE_NOTE = [
    "Pour chaque réponse, regardez chacun des points clés que vous avez écrits pour cette question :",
    "  - la réponse le dit, avec les mêmes mots ou d'autres de même sens (un chiffre doit être exact, avec la bonne "
    "unité) ;",
    "  - la réponse ne le dit pas ;",
    "  - la réponse dit le contraire.",
    "",
    "Puis choisissez la note :",
    "  - juste : la réponse dit tous les points clés, et ne contredit rien ;",
    "  - partielle : elle en dit au moins un, et ne contredit rien ;",
    "  - fausse : elle contredit quelque chose, ou ne dit aucun point clé.",
    "",
    "Une information juste en plus des points clés ne change pas la note. Si le RAG dit qu'il ne sait pas, la réponse "
    "ne dit aucun point clé : elle est fausse.",
]

# --- La vérification du juge ----------------------------------------------------------------------

FEUILLE = "Réponses à noter"
COLONNES = [("Question", "question_id", 11), ("La question posée", "question", 40),
            ("La bonne réponse (fichier du métier)", "reponse_attendue", 45),
            ("Les points clés (fichier du métier)", "points_cles", 40), ("La réponse du RAG", "reponse_rag", 60),
            ("Votre note", "note", 13), ("Votre commentaire (facultatif)", "commentaire", 35)]
CRITERE = ["Vérifier le juge : noter les réponses du RAG", "",
           "Le juge est le modèle de langage qui note les réponses du RAG. Avant de croire ses notes, on vérifie qu'il "
           "note comme vous. Pour cela, notez vous-même les réponses de la feuille « Réponses à noter », avec le "
           "critère ci-dessous, dans la colonne « Votre note ».", "", *CRITERE_NOTE, "",
           "Notez toutes les lignes, puis rendez le fichier tel quel."]

# --- La relecture des réponses ----------------------------------------------------------------------

FEUILLE_RELECTURE = "Réponses à relire"
COLONNES_RELECTURE = [("Question", "question_id", 11), ("Pourquoi la relire", "motif", 18),
                      ("La question posée", "question", 35), ("La bonne réponse (fichier du métier)", "reponse_attendue", 40),
                      ("Les points clés (fichier du métier)", "points_cles", 35), ("La réponse du RAG", "reponse_rag", 55),
                      ("La note du juge", "note_juge", 12), ("Ce que le juge a vu", "justification", 45),
                      ("D'accord avec le juge ?", "accord", 13), ("Sinon, votre note", "note", 13),
                      ("Votre commentaire (facultatif)", "commentaire", 35)]
CRITERE_RELECTURE = ["Relire les réponses du RAG", "",
                     "Ces réponses méritent un regard humain : le juge les a notées fausses ou partielles, ou la "
                     "question est grave, ou elles ont été tirées au hasard. Pour chacune, lisez la réponse du RAG et la "
                     "note du juge, puis dites dans « D'accord avec le juge ? » si sa note est la bonne (oui ou non). "
                     "Si non, choisissez votre note dans « Sinon, votre note », avec le critère ci-dessous.", "",
                     *CRITERE_NOTE, "",
                     "Le commentaire sert à tout signaler : une bonne réponse que vous auriez mal écrite dans le fichier "
                     "du corpus, un document qui se trompe, une question ambiguë…", "",
                     "Relisez toutes les lignes, puis rendez le fichier tel quel."]

# --- La justesse du graphe ----------------------------------------------------------------------

FEUILLE_GRAPHE = "Relations à juger"
COLONNES_GRAPHE = [("La relation", "relation", 40), ("Document", "reference_source", 14), ("Page", "page", 8),
                   ("Le passage d'où elle vient", "passage", 80), ("Votre jugement", "jugement", 14),
                   ("Votre commentaire (facultatif)", "commentaire", 35)]
JUGEMENTS = ("juste", "fausse")
CRITERE_GRAPHE = ["Juger les relations du graphe", "",
                  "Le RAG a tiré des documents une carte des liens entre équipements, sites et personnes : le graphe. "
                  "Chaque ligne de la feuille « Relations à juger » donne une de ces relations, et le passage du "
                  "document d'où le RAG l'a tirée.", "",
                  "Dans « Votre jugement », choisissez :",
                  "  - juste : le passage dit bien cette relation ;",
                  "  - fausse : le passage ne la dit pas, ou dit autre chose.", "",
                  "Jugez toutes les lignes, puis rendez le fichier tel quel."]


def points_cles(question: dict) -> str:
    """Les points clés d'une question, un par ligne, avec leur tolérance s'il y en a une."""
    lignes = []
    for i, p in enumerate(question.get("points_cles") or [], start=1):
        texte = p.get("texte", "")
        if p.get("tolerance"):    # une valeur chiffrée, avec sa tolérance
            texte += f" (± {p['tolerance']}" + (f" {p['unite']}" if p.get("unite") else "") + ")"
        lignes.append(f"{i}. {texte}")
    return "\n".join(lignes)


def ecrire_tableau(chemin: Path, mode_emploi: list[str], feuille: str, colonnes: list[tuple], lignes: list[dict],
                   listes: dict[str, tuple]) -> None:
    """Un fichier à remettre au métier : le mode d'emploi, puis une ligne par élément ; les colonnes qu'il remplit
    commencent par « Votre », « D'accord » ou « Sinon », et ont une liste de valeurs (listes : clé → valeurs)."""
    classeur = Workbook()
    mode = classeur.active
    mode.title = "Mode d'emploi"
    for n, texte in enumerate(mode_emploi, start=1):
        mode.cell(row=n, column=1, value=texte).alignment = Alignment(wrap_text=True, vertical="top")
    mode["A1"].font = Font(bold=True, size=13)
    mode.column_dimensions["A"].width = 110

    f = classeur.create_sheet(feuille)
    for c, (titre, cle, largeur) in enumerate(colonnes, start=1):
        cellule = f.cell(row=1, column=c, value=titre)
        cellule.font = Font(bold=True)
        a_remplir = titre.startswith(("Votre", "D'accord", "Sinon"))
        cellule.fill = PatternFill("solid", fgColor="DDEBF7" if a_remplir else "EEEEEE")
        cellule.alignment = Alignment(wrap_text=True, vertical="top")
        f.column_dimensions[cellule.column_letter].width = largeur
        if cle in listes and lignes:
            liste = DataValidation(type="list", formula1='"' + ",".join(listes[cle]) + '"', allow_blank=True,
                                   error="Choisir dans la liste : " + ", ".join(listes[cle]) + ".", showErrorMessage=True)
            f.add_data_validation(liste)
            liste.add(f"{cellule.column_letter}2:{cellule.column_letter}{len(lignes) + 1}")
    for n, ligne in enumerate(lignes, start=2):
        for c, (_, cle, _) in enumerate(colonnes, start=1):
            f.cell(row=n, column=c, value=ligne.get(cle)).alignment = Alignment(wrap_text=True, vertical="top")
    f.freeze_panes = "B2"
    classeur.save(chemin)


def lire_tableau(chemin: Path, feuille: str, colonnes: list[tuple]) -> list[dict]:
    """Les lignes du fichier rendu par le métier, une par élément, avec ce qu'il a rempli (en minuscules)."""
    f = load_workbook(chemin, read_only=True)[feuille]
    cles = [cle for _, cle, _ in colonnes]
    lignes = []
    for valeurs in f.iter_rows(min_row=2, values_only=True):
        if not valeurs or valeurs[0] in (None, ""):
            continue
        ligne = dict(zip(cles, valeurs))
        for cle in ("note", "accord", "jugement"):
            if cle in ligne:
                ligne[cle] = str(ligne[cle]).strip().lower() if ligne[cle] not in (None, "") else ""
        lignes.append(ligne)
    return lignes


# --- La vérification du juge ----------------------------------------------------------------------

def ecrire(chemin: Path, lignes: list[dict]) -> None:
    ecrire_tableau(chemin, CRITERE, FEUILLE, COLONNES, lignes, {"note": NOTES})


def lire(chemin: Path) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Les notes du métier : ({question: note}, {question: commentaire}, [questions sans note valable])."""
    notes, commentaires, manquantes = {}, {}, []
    for l in lire_tableau(chemin, FEUILLE, COLONNES):
        if l["note"] in NOTES:
            notes[l["question_id"]] = l["note"]
            if l.get("commentaire"):
                commentaires[l["question_id"]] = str(l["commentaire"])
        else:
            manquantes.append(l["question_id"])
    return notes, commentaires, manquantes


# --- La relecture des réponses ----------------------------------------------------------------------

def ecrire_relecture(chemin: Path, lignes: list[dict]) -> None:
    ecrire_tableau(chemin, CRITERE_RELECTURE, FEUILLE_RELECTURE, COLONNES_RELECTURE, lignes,
                   {"accord": ("oui", "non"), "note": NOTES})


def lire_relecture(chemin: Path) -> dict:
    """Ce que le métier a rendu : les réponses relues, les désaccords avec le juge, et les lignes non relues."""
    relues, desaccords, manquantes = [], [], []
    for l in lire_tableau(chemin, FEUILLE_RELECTURE, COLONNES_RELECTURE):
        if l["accord"] == "oui":
            relues.append(l["question_id"])
        elif l["accord"] == "non" and l["note"] in NOTES:
            relues.append(l["question_id"])
            desaccords.append({"question_id": l["question_id"], "juge": l.get("note_juge"), "metier": l["note"],
                               "commentaire": str(l["commentaire"]) if l.get("commentaire") else ""})
        else:
            manquantes.append(l["question_id"])
    commentaires = [{"question_id": l["question_id"], "commentaire": str(l["commentaire"])}
                    for l in lire_tableau(chemin, FEUILLE_RELECTURE, COLONNES_RELECTURE)
                    if l.get("commentaire") and l["accord"] == "oui"]
    return {"relues": relues, "desaccords": desaccords, "sans_reponse": manquantes, "autres_commentaires": commentaires}


def deja_rempli(chemin: Path, feuille: str, colonnes: list[tuple], cle: str) -> bool:
    """Le métier a-t-il déjà commencé à remplir ce fichier ? On ne l'écrase jamais."""
    return chemin.exists() and any(l.get(cle) for l in lire_tableau(chemin, feuille, colonnes))


# --- La justesse du graphe ----------------------------------------------------------------------

def ecrire_graphe(chemin: Path, lignes: list[dict]) -> None:
    ecrire_tableau(chemin, CRITERE_GRAPHE, FEUILLE_GRAPHE, COLONNES_GRAPHE, lignes, {"jugement": JUGEMENTS})


def lire_graphe(chemin: Path) -> list[dict]:
    """Les relations jugées : relation, document, page, jugement (juste ou fausse), commentaire."""
    return [l for l in lire_tableau(chemin, FEUILLE_GRAPHE, COLONNES_GRAPHE) if l["jugement"] in JUGEMENTS]
