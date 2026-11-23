"""Import du fichier Excel du métier (document 1) dans le kit.

Étapes : lire les feuilles, convertir les libellés en codes (documentation/methode_et_contrat/contrat_des_fichiers.md, section 1),
contrôler chaque ligne (section 2), puis, si aucune ligne n'est rejetée :
écrire dans la base, exporter corpus/<version_corpus>/ et créer le jeu de données Langfuse.

Choix : une seule ligne rejetée bloque tout l'import. Un corpus à moitié importé fausserait
l'évaluation sans que personne ne s'en aperçoive ; le métier corrige le fichier et relance.
"""

import datetime as dt
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kit import base
from kit import contrat

VERSION_CONTRAT = "1.0"

# --- Colonnes du fichier Excel → champs du contrat -------------------------------------------

COLONNES = {
    "Documents": {
        "Référence dans la source": "reference_source", "Titre": "titre", "Type de document": "type_document",
        "Source": "source", "Version": "version", "Date": "date", "Format": "format",
        "Nombre de pages": "nb_pages", "Criticité": "criticite", "Droits d'accès": "droits_acces",
        "En vigueur": "en_vigueur", "Remplacé par": "remplace_par", "Sélection": "selection",
    },
    "Questions": {
        "Identifiant": "question_id", "Question": "question", "Profil de l'utilisateur": "profil",
        "Rédigée par": "redigee_par", "Type de réponse": "type_reponse",
        "Réponse dans les documents ?": "reponse_dans_documents", "La réponse est dans": "reponse_est_dans",
        "Réponse attendue": "reponse_attendue", "Points clés attendus": "points_cles",
        "Difficulté": "difficulte", "Fréquence": "frequence", "Gravité d'une erreur": "gravite",
        "Réservée à la décision": "reservee_decision", "Question précédente": "question_precedente",
        "Variante de": "variante_de", "Annotateur": "annotateur", "Date": "date",
    },
    "Passages": {
        "Question": "question_id", "Référence du document": "reference_source", "Page": "page",
        "Type d'élément": "type_element", "Passage": "passage", "Répond": "repond",
    },
    "Pages OCR": {
        "Référence du document": "reference_source", "Page": "page", "Texte retapé": "texte_retape",
        "Retapé par": "retape_par", "Relu par": "relu_par", "Date": "date",
    },
}

# Colonnes calculées par les formules du modèle : ni des données, ni des colonnes libres.
COLONNES_CALCULEES = {"Nombre de passages", "Type du document"}

# Feuilles dont les colonnes ajoutées par le projet sont des « colonnes libres ».
FEUILLES_A_COLONNES_LIBRES = ("Documents", "Questions")

OBLIGATOIRES = {
    "Documents": ["reference_source", "titre", "type_document", "source", "version", "format", "criticite",
                  "droits_acces", "en_vigueur", "selection"],
    "Questions": ["question_id", "question", "profil", "redigee_par", "type_reponse", "reponse_dans_documents",
                  "reponse_attendue", "difficulte", "frequence", "gravite", "reservee_decision"],
    "Passages": ["question_id", "reference_source", "page", "type_element", "passage", "repond"],
    "Pages OCR": ["reference_source", "page", "texte_retape"],
}

# Anciens libellés encore acceptés, mais plus proposés dans les messages d'erreur.
ANCIENS_LIBELLES = {"format": {"Fiche de base de données": "fiche_base"}}

# Listes fermées : libellé du fichier Excel → code du contrat.
CODES = {
    "format": {"PDF natif": "pdf_natif", "PDF scanné": "pdf_scanne", "Word": "word", "Excel": "excel",
               "Fiche de GED": "fiche_base"},
    "criticite": {"C1": "C1", "C2": "C2", "C2 export": "C2_export", "C3": "C3"},
    "selection": {"Tiré au hasard": "hasard", "Choisi par le métier": "choix_metier"},
    "redigee_par": {"Métier": "metier", "IA, relue par le métier": "ia_relue",
                    "Question réelle (production)": "production"},
    "type_reponse": {"Fait": "fait", "Liste": "liste", "Calcul": "calcul", "Explication": "explication",
                     "Synthèse": "synthese"},
    "reponse_dans_documents": {"Oui": "oui", "Non": "non", "Non accessible à ce profil": "non_accessible"},
    "reponse_est_dans": {"Un seul passage": "un_passage", "Plusieurs passages à combiner": "plusieurs_a_combiner",
                         "Plusieurs passages, un seul suffit": "plusieurs_un_suffit",
                         "L'ensemble des documents (synthèse)": "ensemble_documents"},
    "difficulte": {"Facile": "facile", "Moyenne": "moyenne", "Difficile": "difficile"},
    "frequence": {"Fréquente": "frequente", "Occasionnelle": "occasionnelle", "Rare": "rare"},
    "gravite": {"Faible": "faible", "Moyenne": "moyenne", "Forte": "forte"},
    "repond": {"Entièrement": "entierement", "En partie": "en_partie", "Piège": "piege"},
    "type_element": {"Texte": "texte", "Tableau": "tableau", "Texte scanné": "texte_scanne",
                     "Image ou schéma": "image_schema"},
    "en_vigueur": {"Oui": True, "Non": False},
    "reservee_decision": {"Oui": True, "Non": False},
}

# Listes ouvertes, définies par le projet dans la feuille Listes : champ → colonne de la feuille Listes.
LISTES_PROJET = {"type_document": "Types de documents", "source": "Sources",
                 "droits_acces": "Profils d'accès", "profil": "Profils d'accès"}


def sans_accent(texte: str) -> str:
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()


def cle_libelle(texte: str) -> str:
    """Forme de comparaison d'un libellé : minuscules, sans accent, espaces réduits."""
    return " ".join(sans_accent(str(texte)).lower().replace("’", "'").split())


def code_profil(libelle: str) -> str:
    """« Tous les utilisateurs » → tous ; sinon minuscules, sans accent, mots séparés par « _ »."""
    if cle_libelle(libelle) == "tous les utilisateurs":
        return "tous"
    return re.sub(r"[^a-z0-9]+", "_", cle_libelle(libelle)).strip("_")


# --- Points clés ---------------------------------------------------------------------------

NOMBRE = r"[-+]?\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|[-+]?\d+(?:[.,]\d+)?"
FORME_VALEUR = re.compile(
    rf"^(?P<valeur>{NOMBRE})\s*(?P<unite>[^\d±;]{{0,20}}?)\s*(?:±\s*(?P<tolerance>{NOMBRE})\s*(?P<unite2>[^\d±;]{{0,20}}?))?$")


def nombre(texte: str) -> float:
    valeur = float(re.sub(r"[   ]", "", texte).replace(",", "."))
    return int(valeur) if valeur.is_integer() else valeur


def lire_points_cles(texte: str | None) -> list[dict]:
    """Découpe « Points clés attendus » sur « ; » et reconnaît la forme « nombre unité ± tolérance ».

    « 2,3 ans ± 0,1 » → {texte, valeur: 2.3, unite: "ans", tolerance: 0.1}.
    Un point qui n'est pas de cette forme (« second intervenant H2V ») reste un texte.
    """
    points = []
    for morceau in (texte or "").split(";"):
        morceau = morceau.strip()
        if not morceau:
            continue
        point = {"texte": morceau}
        forme = FORME_VALEUR.match(morceau)
        unite = forme and (forme["unite"] or forme["unite2"] or "").strip()
        if forme and len(unite.split()) <= 2:  # au-delà, c'est une phrase, pas une unité
            point["valeur"] = nombre(forme["valeur"])
            if unite:
                point["unite"] = unite
            point["tolerance"] = nombre(forme["tolerance"]) if forme["tolerance"] else 0
        points.append(point)
    return points


# --- Lecture du fichier --------------------------------------------------------------------

@dataclass
class Ligne:
    """Une ligne d'une feuille : numéro de ligne Excel, champs du contrat, colonnes libres."""
    feuille: str
    numero: int
    champs: dict
    libres: dict = field(default_factory=dict)

    def ou(self) -> str:
        cle = self.champs.get("question_id") or self.champs.get("reference_source") or ""
        return f"feuille {self.feuille}, ligne {self.numero}" + (f" ({cle})" if cle else "")


def valeur_cellule(v):
    """Texte nettoyé ; les dates Excel deviennent des dates ISO ; une cellule vide devient None."""
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    texte = str(v).strip()
    return texte or None


def lire_feuille(classeur, nom: str) -> tuple[list[Ligne], list[str]]:
    """Lit une feuille en repérant les colonnes par leur titre (l'ordre des colonnes est libre)."""
    feuille = classeur[nom]
    entetes = [valeur_cellule(c) for c in next(feuille.iter_rows(min_row=1, max_row=1, values_only=True))]
    connues = COLONNES[nom]
    libres = [e for e in entetes if e and e not in connues and e not in COLONNES_CALCULEES] \
        if nom in FEUILLES_A_COLONNES_LIBRES else []
    lignes = []
    for numero, valeurs in enumerate(feuille.iter_rows(min_row=2, values_only=True), start=2):
        par_titre = {e: valeur_cellule(v) for e, v in zip(entetes, valeurs) if e}
        champs = {connues[e]: par_titre.get(e) for e in connues}
        if all(v is None for v in champs.values()):
            continue  # ligne vide (les formules du modèle descendent bien plus bas que les données)
        lignes.append(Ligne(nom, numero, champs, {code_profil(c): par_titre.get(c) for c in libres
                                                  if par_titre.get(c) is not None}))
    return lignes, libres


def lire_listes(classeur) -> dict[str, list[str]]:
    feuille = classeur["Listes"]
    lignes = list(feuille.iter_rows(values_only=True))
    entetes = [valeur_cellule(c) for c in lignes[0]]
    return {e: [valeur_cellule(r[i]) for r in lignes[1:] if valeur_cellule(r[i])] for i, e in enumerate(entetes) if e}


# --- Conversion et contrôles ---------------------------------------------------------------

def convertir(ligne: Ligne, listes: dict, erreurs: list[str]) -> None:
    """Contrôle les champs obligatoires et convertit les libellés en codes, en place."""
    for nom in OBLIGATOIRES[ligne.feuille]:
        if ligne.champs.get(nom) is None:
            titre = next(t for t, c in COLONNES[ligne.feuille].items() if c == nom)
            erreurs.append(f"{ligne.ou()} : la colonne « {titre} » est obligatoire et elle est vide.")
    for nom, valeur in list(ligne.champs.items()):
        if valeur is None:
            continue
        titre = next(t for t, c in COLONNES[ligne.feuille].items() if c == nom)
        if nom in CODES:
            par_cle = {cle_libelle(lib): code for lib, code in CODES[nom].items()}
            par_cle.update({cle_libelle(str(code)): code for code in CODES[nom].values() if isinstance(code, str)})
            par_cle.update({cle_libelle(lib): code for lib, code in ANCIENS_LIBELLES.get(nom, {}).items()})
            if cle_libelle(valeur) not in par_cle:
                erreurs.append(f"{ligne.ou()} : « {valeur} » n'est pas une valeur admise pour « {titre} » "
                               f"({', '.join(CODES[nom])}).")
            else:
                ligne.champs[nom] = par_cle[cle_libelle(valeur)]
        elif nom in LISTES_PROJET and ligne.feuille in ("Documents", "Questions"):
            admis = listes.get(LISTES_PROJET[nom], [])
            if cle_libelle(valeur) not in {cle_libelle(a) for a in admis}:
                erreurs.append(f"{ligne.ou()} : « {valeur} » n'est pas dans la colonne « {LISTES_PROJET[nom]} » "
                               f"de la feuille Listes ({', '.join(admis)}).")
            elif nom in ("droits_acces", "profil"):
                ligne.champs[nom] = code_profil(valeur)
            else:
                ligne.champs[nom] = next(a for a in admis if cle_libelle(a) == cle_libelle(valeur))
    if ligne.feuille == "Documents" and ligne.champs.get("nb_pages") is not None:
        try:
            ligne.champs["nb_pages"] = int(ligne.champs["nb_pages"])
        except ValueError:
            erreurs.append(f"{ligne.ou()} : « Nombre de pages » doit être un entier "
                           f"(« {ligne.champs['nb_pages']} »).")


def controler(documents: list[Ligne], questions: list[Ligne], passages: list[Ligne], pages_ocr: list[Ligne],
              erreurs: list[str]) -> None:
    """Contrôles de cohérence entre feuilles (documentation/methode_et_contrat/contrat_des_fichiers.md, section 2)."""
    docs = {d.champs["reference_source"]: d.champs for d in documents}
    vus = {}
    for d in documents:
        ref = d.champs["reference_source"]
        if ref in vus and ref:
            erreurs.append(f"{d.ou()} : la référence « {ref} » est déjà utilisée ligne {vus[ref]}.")
        vus[ref] = d.numero
    for d in documents:
        if d.champs.get("remplace_par") and d.champs["remplace_par"] not in docs:
            erreurs.append(f"{d.ou()} : « Remplacé par » renvoie à « {d.champs['remplace_par']} », "
                           f"absent de la feuille Documents.")
    ids = {}
    for q in questions:
        qid = q.champs["question_id"]
        if qid in ids:
            erreurs.append(f"{q.ou()} : l'identifiant « {qid} » est déjà utilisé ligne {ids[qid]}.")
        ids[qid] = q.numero
    for q in questions:
        for nom, titre in (("question_precedente", "Question précédente"), ("variante_de", "Variante de")):
            if q.champs.get(nom) and q.champs[nom] not in ids:
                erreurs.append(f"{q.ou()} : « {titre} » renvoie à « {q.champs[nom]} », qui n'est pas une question "
                               f"du fichier.")
    for p in passages:
        if p.champs["question_id"] and p.champs["question_id"] not in ids:
            erreurs.append(f"{p.ou()} : la question « {p.champs['question_id']} » n'existe pas dans la feuille "
                           f"Questions.")
        if p.champs["reference_source"] and p.champs["reference_source"] not in docs:
            erreurs.append(f"{p.ou()} : le document « {p.champs['reference_source']} » n'existe pas dans la feuille "
                           f"Documents.")
    for o in pages_ocr:
        doc = docs.get(o.champs["reference_source"])
        if doc is None:
            erreurs.append(f"{o.ou()} : le document « {o.champs['reference_source']} » n'existe pas dans la feuille "
                           f"Documents.")
        elif doc.get("format") != "pdf_scanne":
            erreurs.append(f"{o.ou()} : une page OCR de référence doit venir d'un document « PDF scanné ».")
    for q in questions:
        c = q.champs
        utiles = [p.champs for p in passages if p.champs["question_id"] == c["question_id"]]
        if c["reponse_dans_documents"] == "oui":
            if not c.get("reponse_est_dans"):
                erreurs.append(f"{q.ou()} : la réponse est dans les documents, « La réponse est dans » est "
                               f"obligatoire.")
            if not c.get("points_cles"):
                erreurs.append(f"{q.ou()} : la réponse est dans les documents, « Points clés attendus » est "
                               f"obligatoire.")
            if not [p for p in utiles if p["repond"] != "piege"]:
                erreurs.append(f"{q.ou()} : la réponse est dans les documents, mais aucun passage (hors pièges) "
                               f"n'est annoté dans la feuille Passages.")
        if c["reponse_dans_documents"] == "non_accessible":
            interdits = [p for p in utiles if p["reference_source"] in docs
                         and not contrat.autorise(docs[p["reference_source"]]["droits_acces"], c["profil"])]
            if not interdits:
                erreurs.append(f"{q.ou()} : la réponse est « non accessible à ce profil », mais aucun passage ne vient "
                               f"d'un document interdit au profil « {c['profil']} ».")


def avertissements_configuration(documents: list[dict], questions: list[dict], passages: list[dict],
                                 pages_ocr: list[dict]) -> list[str]:
    """Configuration minimale du document 1 (section 4) : avertit sans rejeter."""
    alertes = []
    type_doc = {d["reference_source"]: d["type_document"] for d in documents}
    for t in sorted(set(type_doc.values())):
        du_type = [d for d in documents if d["type_document"] == t]
        hasard = sum(d["selection"] == "hasard" for d in du_type)
        choix = sum(d["selection"] == "choix_metier" for d in du_type)
        if len(du_type) < 10 or hasard < 8 or choix < 2:
            alertes.append(f"Type « {t} » : {len(du_type)} documents ({hasard} au hasard, {choix} choisis) ; "
                           f"minimum 10, dont 8 au hasard et 2 choisis.")
        avec_type = {p["question_id"] for p in passages if type_doc.get(p["reference_source"]) == t}
        if len(avec_type) < 5:
            alertes.append(f"Type « {t} » : {len(avec_type)} questions ; minimum 5 par type de document.")
    compte = {
        "questions": (len(questions), 50),
        "questions sans réponse dans les documents": (
            sum(q["reponse_dans_documents"] == "non" for q in questions), 5),
        "questions à plusieurs passages": (
            sum(q.get("reponse_est_dans") in ("plusieurs_a_combiner", "plusieurs_un_suffit") for q in questions), 5),
    }
    if any(d["droits_acces"] != "tous" for d in documents):
        compte["questions posées avec un profil restreint"] = (sum(q["profil"] != "tous" for q in questions), 5)
        compte["questions « non accessible à ce profil »"] = (
            sum(q["reponse_dans_documents"] == "non_accessible" for q in questions), 2)
    if any(d["format"] == "pdf_scanne" for d in documents):
        compte["pages OCR de référence"] = (len(pages_ocr), 20)
    for nom, (n, minimum) in compte.items():
        if n < minimum:
            alertes.append(f"{n} {nom} ; minimum {minimum}.")
    return alertes


# --- Version, identifiants des passages ----------------------------------------------------

def empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def cle_passage(p: dict) -> tuple:
    return tuple(p[c] for c in ("question_id", "reference_source", "page", "type_element", "passage", "repond"))


def numeroter_passages(session: Session, projet: str, passages: list[Ligne]) -> list[dict]:
    """Donne à chaque passage son passage_id, stable d'une version à l'autre (DECISIONS.md, décision 1).

    Premier import : le numéro de ligne Excel. Ensuite : une ligne identique à un passage de la version
    précédente garde son identifiant ; une ligne nouvelle ou modifiée reçoit un identifiant jamais utilisé.
    """
    precedente = session.scalar(select(base.Corpus.version_corpus).where(base.Corpus.projet == projet)
                                .order_by(base.Corpus.date.desc(), base.Corpus.version_corpus.desc()))
    connus, plus_grand = {}, 0
    if precedente:
        for p in session.scalars(select(base.Passage).where(base.Passage.version_corpus == precedente)):
            connus[cle_passage(p.__dict__)] = p.passage_id
        plus_grand = session.scalar(select(func.max(base.Passage.passage_id))) or 0
    resultat, pris = [], set()
    for ligne in passages:
        p = dict(ligne.champs)
        ancien = connus.get(cle_passage(p))
        if precedente is None:
            p["passage_id"] = ligne.numero
        elif ancien is not None and ancien not in pris:
            p["passage_id"] = ancien
        else:
            plus_grand += 1
            p["passage_id"] = plus_grand
        pris.add(p["passage_id"])
        resultat.append(p)
    return resultat


def nouvelle_version(session: Session, aujourd_hui: str) -> str:
    """`2026-11-20.1`, puis `.2` pour un second fichier modifié importé le même jour."""
    deja = session.scalars(select(base.Corpus.version_corpus)
                           .where(base.Corpus.version_corpus.like(f"{aujourd_hui}.%"))).all()
    return f"{aujourd_hui}.{max((int(v.rsplit('.', 1)[1]) for v in deja), default=0) + 1}"


# --- Écritures -----------------------------------------------------------------------------

def sans_vide(objet: dict) -> dict:
    """Un champ facultatif absent est omis (documentation/methode_et_contrat/contrat_des_fichiers.md, section 1)."""
    return {k: v for k, v in objet.items() if v is not None and v != {}}


def exporter(dossier: Path, corpus: dict, documents, questions, passages, pages_ocr) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "corpus.json").write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contrat.ecrire_jsonl(dossier / "documents.jsonl", documents)
    contrat.ecrire_jsonl(dossier / "questions.jsonl", questions)
    contrat.ecrire_jsonl(dossier / "passages.jsonl", passages)
    contrat.ecrire_jsonl(dossier / "pages_ocr.jsonl", pages_ocr)


def ecrire_base(session: Session, corpus: dict, documents, questions, passages, pages_ocr) -> None:
    v = corpus["version_corpus"]
    session.add(base.Corpus(**corpus))
    session.add_all(base.Document(version_corpus=v, **d) for d in documents)
    session.add_all(base.Question(version_corpus=v, **q) for q in questions)
    session.add_all(base.Passage(version_corpus=v, **p) for p in passages)
    session.add_all(base.PageOcr(version_corpus=v, **o) for o in pages_ocr)


def creer_jeu_langfuse(langfuse, corpus: dict, questions: list[dict]) -> str:
    """Jeu de données `corpus-<projet>-<version_corpus>` : un élément par question (documentation/methode_et_contrat/contrat_des_fichiers.md, section 4)."""
    nom = f"corpus-{corpus['projet']}-{corpus['version_corpus']}"
    langfuse.create_dataset(name=nom, description=f"Corpus importé de {corpus['fichier_source']}",
                            metadata={"contrat": corpus["contrat"], "version_corpus": corpus["version_corpus"]})
    par_id = {q["question_id"]: q for q in questions}
    entree_sortie = {"question", "profil", "reponse_attendue", "points_cles"}
    for q in questions:
        langfuse.create_dataset_item(
            dataset_name=nom, id=f"{corpus['version_corpus']}_{q['question_id']}",
            input={"question": q["question"], "profil": q["profil"], "historique": contrat.historique(q, par_id)},
            expected_output={"reponse_attendue": q["reponse_attendue"], "points_cles": q.get("points_cles")},
            metadata=sans_vide({k: v for k, v in q.items() if k not in entree_sortie}))
    langfuse.flush()
    return nom


# --- Point d'entrée ------------------------------------------------------------------------

@dataclass
class Resultat:
    version_corpus: str | None
    erreurs: list[str]
    avertissements: list[str]
    dossier: Path | None = None
    deja_importe: bool = False
    jeu_langfuse: str | None = None


def importer(chemin: Path, adresse_base: str, dossier_resultats: Path, projet: str, langfuse=None,
             aujourd_hui: str | None = None) -> Resultat:
    """Importe le fichier Excel. `langfuse` : un client Langfuse, ou None pour ne pas créer le jeu de données."""
    aujourd_hui = aujourd_hui or dt.date.today().isoformat()
    classeur = openpyxl.load_workbook(chemin, data_only=False)
    manquantes = [f for f in (*COLONNES, "Listes") if f not in classeur.sheetnames]
    if manquantes:
        return Resultat(None, [f"Feuille(s) absente(s) du fichier : {', '.join(manquantes)}."], [])
    erreurs = []
    for nom in COLONNES:
        entetes = {valeur_cellule(c.value) for c in classeur[nom][1]}
        absentes = [t for t in COLONNES[nom] if t not in entetes]
        if absentes:
            erreurs.append(f"Feuille {nom} : colonne(s) absente(s) : {', '.join(absentes)}.")
    if erreurs:
        return Resultat(None, erreurs, [])
    listes = lire_listes(classeur)
    lus = {nom: lire_feuille(classeur, nom) for nom in COLONNES}
    documents, questions, passages, pages_ocr = (lus[n][0] for n in COLONNES)
    for ligne in documents + questions + passages + pages_ocr:
        convertir(ligne, listes, erreurs)
    for q in questions:
        q.champs["points_cles"] = lire_points_cles(q.champs.get("points_cles")) or None
    if not erreurs:  # les contrôles croisés supposent des valeurs déjà converties
        controler(documents, questions, passages, pages_ocr, erreurs)
    if erreurs:
        return Resultat(None, erreurs, [])

    docs = [{**d.champs, "colonnes_libres": d.libres or None} for d in documents]
    qs = [{**q.champs, "colonnes_libres": q.libres or None} for q in questions]
    ocr = [o.champs for o in pages_ocr]
    moteur = base.moteur(adresse_base)
    base.init_base(adresse_base)
    signature = f"{chemin.name} (sha256:{empreinte(chemin)})"
    with Session(moteur) as session:
        existante = session.scalar(select(base.Corpus).where(base.Corpus.fichier_source == signature))
        if existante:  # même fichier, octet pour octet : pas de nouvelle version
            dossier = dossier_resultats / "corpus" / existante.version_corpus
            resultat = Resultat(existante.version_corpus, [], [], dossier, deja_importe=True)
            if langfuse is not None:  # le jeu de données est recréé à l'identique (identifiants stables)
                deja = contrat.charger_corpus(dossier)
                resultat.jeu_langfuse = creer_jeu_langfuse(langfuse, deja["corpus"], deja["questions"])
            return resultat
        ps = numeroter_passages(session, projet, passages)
        corpus = {"contrat": VERSION_CONTRAT, "version_corpus": nouvelle_version(session, aujourd_hui),
                  "projet": projet, "date": aujourd_hui, "fichier_source": signature,
                  "colonnes_libres": sorted({c for _, libres in (lus["Documents"], lus["Questions"])
                                             for c in map(code_profil, libres)})}
        ecrire_base(session, corpus, docs, qs, ps, ocr)
        session.commit()
    dossier = dossier_resultats / "corpus" / corpus["version_corpus"]
    exporter(dossier, corpus, docs, qs, ps, ocr)
    resultat = Resultat(corpus["version_corpus"], [], avertissements_configuration(docs, qs, ps, ocr), dossier)
    if langfuse is not None:
        resultat.jeu_langfuse = creer_jeu_langfuse(langfuse, corpus, qs)
    return resultat
