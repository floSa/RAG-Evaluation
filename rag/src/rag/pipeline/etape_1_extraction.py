"""Étape 1 — Extraction : lire chaque document et en sortir le texte, page par page.

- PDF natif et PDF scanné : Docling (analyse de mise en page ; OCR forcé pour un scan), en Markdown page par page.
- Fiche de base de données : pypdf en mode « mise en page », qui garde les deux colonnes « champ : valeur ».
Le résultat est mis en cache sur disque : Docling prend quelques secondes par document.
"""

import csv
import json
import re
from pathlib import Path

import httpx
from pypdf import PdfReader

SAUT_DE_PAGE = "<!-- page -->"


# --- La liste des documents à lire ------------------------------------------------------------

# Les libellés de la gestion documentaire, traduits dans les codes du RAG.
FORMATS = {"PDF natif": "pdf_natif", "PDF scanné": "pdf_scanne", "Fiche de base de données": "fiche_base"}


def profil(droits: str) -> str:
    """« Tous les utilisateurs » → tous ; « Maintenance » → maintenance."""
    return "tous" if droits == "Tous les utilisateurs" else droits.strip().lower()


def liste_des_documents(config: dict) -> list[dict]:
    """Les documents à indexer, avec leurs métadonnées, lus dans l'export de la gestion documentaire (un CSV).

    Le RAG garde sur chaque chunk la référence, la version et les droits d'accès : c'est ce qui lui permet de
    citer ses sources et de filtrer les droits pendant la recherche.
    """
    with Path(config["liste_des_documents"]).open(encoding="utf-8", newline="") as f:
        return [{"reference_source": l["reference"], "titre": l["titre"], "type_document": l["type_document"],
                 "version": l["version"], "format": FORMATS[l["format"]], "droits_acces": profil(l["droits_acces"]),
                 "fichier": l["fichier"]}
                for l in csv.DictReader(f, delimiter=";")]


# --- Lire un document ---------------------------------------------------------------------------

def docling(chemin: Path, adresse: str, ocr: bool) -> list[str]:
    """Convertit un PDF en Markdown avec Docling ; rend une chaîne par page."""
    formulaire = {"to_formats": "md", "md_page_break_placeholder": SAUT_DE_PAGE, "image_export_mode": "placeholder",
                  "do_ocr": str(ocr).lower(), "force_ocr": str(ocr).lower(), "ocr_lang": "fr"}
    with chemin.open("rb") as f:
        r = httpx.post(f"{adresse}/v1/convert/file", data=formulaire, files={"files": (chemin.name, f)}, timeout=600)
    r.raise_for_status()
    return r.json()["document"]["md_content"].split(SAUT_DE_PAGE)


CHAMP = re.compile(r"^\s{0,8}(\S[^:]{0,60}?)\s:\s{2,}(\S.*)$")   # « Libellé :      valeur » en début de ligne
SUITE = re.compile(r"^\s{20,}(\S.*)$")                             # suite de la valeur, alignée à droite


def fiche(chemin: Path) -> list[tuple[str, str]]:
    """Lit une fiche de base de données exportée en PDF : liste de (champ, valeur)."""
    champs = []
    for page in PdfReader(chemin).pages:
        for ligne in page.extract_text(extraction_mode="layout").splitlines():
            if m := CHAMP.match(ligne):
                champs.append([m[1].strip(), m[2].strip()])
            elif (m := SUITE.match(ligne)) and champs:
                champs[-1][1] += " " + m[1].strip()
    return [tuple(c) for c in champs]


def extraire(document: dict, dossier_sources: Path, dossier_cache: Path, adresse_docling: str) -> dict:
    """Extrait un document : {"pages": [markdown, …]} ou {"fiche": [(champ, valeur), …]}, avec un cache sur disque."""
    cache = dossier_cache / f"{document['reference_source']}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    chemin = dossier_sources / document["fichier"]
    if document["format"] == "fiche_base":
        extrait = {"fiche": fiche(chemin)}
    else:
        extrait = {"pages": docling(chemin, adresse_docling, ocr=document["format"] == "pdf_scanne")}
    dossier_cache.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(extrait, ensure_ascii=False), encoding="utf-8")
    return extrait


# --- Lire le Markdown de Docling ----------------------------------------------------------------

def blocs(markdown: str) -> list[tuple[str, object]]:
    """Découpe une page Markdown en blocs : ("titre", texte), ("texte", texte), ("tableau", lignes), ("image", None)."""
    resultat, paragraphe, tableau = [], [], []

    def vider():
        if paragraphe:
            resultat.append(("texte", " ".join(paragraphe)))
            paragraphe.clear()
        if tableau:
            lignes = [[c.strip() for c in l.strip().strip("|").split("|")] for l in tableau]
            resultat.append(("tableau", [l for l in lignes if not all(re.fullmatch(r":?-+:?", c) for c in l)]))
            tableau.clear()

    for ligne in markdown.splitlines():
        s = ligne.strip()
        if s.startswith("|"):
            if paragraphe:
                resultat.append(("texte", " ".join(paragraphe)))
                paragraphe.clear()
            tableau.append(s)
            continue
        vider()
        if not s:
            continue
        if s == "<!-- image -->":
            resultat.append(("image", None))
        elif s.startswith("#"):
            resultat.append(("titre", s.lstrip("#").strip()))
        elif s.startswith(("- ", "* ")):
            resultat.append(("texte", s))  # un élément de liste reste sur sa ligne
        else:
            paragraphe.append(s)
    vider()
    return resultat


def texte_de_page(markdown: str) -> str:
    """Texte brut d'une page, tel que sorti de l'extraction : tableaux ligne par ligne, cellules séparées par « | »."""
    lignes = []
    for genre, contenu in blocs(markdown):
        if genre == "tableau":
            lignes += [" | ".join(l) for l in contenu]
        elif genre in ("titre", "texte"):
            lignes.append(contenu)
    return "\n".join(lignes)


def pages_extraites(document: dict, extrait: dict) -> list[dict]:
    """Le texte de chaque page avant découpage (l'évaluation s'en sert pour mesurer les erreurs de l'OCR)."""
    if "fiche" in extrait:
        return [{"reference_source": document["reference_source"], "page": "1",
                 "texte": "\n".join(f"{c} : {v}" for c, v in extrait["fiche"])}]
    return [{"reference_source": document["reference_source"], "page": str(n), "texte": texte_de_page(md)}
            for n, md in enumerate(extrait["pages"], start=1)]
