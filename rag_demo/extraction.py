"""Extraction et découpage : des PDF aux chunks.

- PDF natif et PDF scanné : Docling (analyse de mise en page ; OCR forcé pour un scan), en Markdown page par page.
- Fiche de base de données : pypdf en mode « mise en page », qui garde les deux colonnes « champ : valeur ».
- Découpage : par section (chemin de titres en tête du chunk), un chunk par tableau (lignes « colonne : valeur »),
  un chunk par figure (sa légende : pas de modèle de vision ici, c'est une limite connue), un chunk par champ de fiche.
"""

import json
import re
from pathlib import Path

import httpx
from pypdf import PdfReader

SAUT_DE_PAGE = "<!-- page -->"


# --- Extraction ----------------------------------------------------------------------------

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
    """Extrait un document, avec un cache sur disque (Docling prend quelques secondes par document)."""
    cache = dossier_cache / f"{document['reference_source']}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    chemin = dossier_sources / f"{document['reference_source']}.pdf"
    if document["format"] == "fiche_base":
        extrait = {"fiche": fiche(chemin)}
    else:
        extrait = {"pages": docling(chemin, adresse_docling, ocr=document["format"] == "pdf_scanne")}
    dossier_cache.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(extrait, ensure_ascii=False), encoding="utf-8")
    return extrait


# --- Lecture du Markdown de Docling ---------------------------------------------------------

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


# --- Découpage ------------------------------------------------------------------------------

def chunks_du_document(document: dict, extrait: dict, taille_max: int) -> list[dict]:
    """Les chunks d'un document, avec les métadonnées du contrat (sans chunk_id ni version_index)."""
    ref, titre = document["reference_source"], document["titre"]
    commun = {"reference_source": ref, "version_document": document["version"],
              "droits_acces": document["droits_acces"]}
    if "fiche" in extrait:  # un chunk par champ : la « page » d'un passage de fiche est le nom du champ
        return [{**commun, "page": champ, "ordre": 0, "type_element": "texte",
                 "texte": f"{ref} — {titre} ({document['type_document']})\n{champ} : {valeur}",
                 "metadonnees": {"chemin": [titre, champ]}} for champ, valeur in extrait["fiche"]]

    scanne = document["format"] == "pdf_scanne"
    resultat, section = [], ""
    for numero, markdown in enumerate(extrait["pages"], start=1):
        ordre, tampon = 0, []

        def ajouter(type_element: str, texte: str):
            nonlocal ordre
            chemin = [titre] + ([section] if section else [])
            resultat.append({**commun, "page": str(numero), "ordre": ordre,
                             "type_element": "texte_scanne" if scanne and type_element != "image_schema" else type_element,
                             "texte": f"{ref} — {' > '.join(chemin)}\n{texte}", "metadonnees": {"chemin": chemin}})
            ordre += 1

        def vider():
            if tampon:
                ajouter("texte", "\n".join(tampon))
                tampon.clear()

        liste = blocs(markdown)
        i = 0
        while i < len(liste):
            genre, contenu = liste[i]
            if genre == "titre":
                if numero == 1 and i == 0 and contenu.startswith(ref):
                    i += 1
                    continue  # le titre du document, déjà en tête de chaque chunk
                if contenu.lower().startswith("tableau"):
                    tampon.append(contenu)  # titre d'un tableau : il suit le tableau dans son chunk
                else:
                    vider()
                    section = contenu
            elif genre == "texte":
                if sum(map(len, tampon)) + len(contenu) > taille_max:
                    vider()
                tampon.append(contenu)
            elif genre == "tableau":
                titre_tableau = tampon.pop() if tampon and tampon[-1].lower().startswith("tableau") else ""
                vider()
                entetes, lignes = contenu[0], contenu[1:]
                if scanne:  # un scan reste du texte : lignes « a | b | c », comme les pages retapées
                    rendu = [" | ".join(l) for l in contenu]
                else:       # tableau natif : chaque ligne en « colonne : valeur », en-têtes répétés
                    rendu = [" ; ".join(f"{e} : {v}" for e, v in zip(entetes, l)) for l in lignes]
                morceau = [titre_tableau] if titre_tableau else []
                for ligne in rendu:
                    if sum(map(len, morceau)) + len(ligne) > taille_max and len(morceau) > 1:
                        ajouter("tableau", "\n".join(morceau))
                        morceau = [titre_tableau] if titre_tableau else []
                    morceau.append(ligne)
                ajouter("tableau", "\n".join(morceau))
            elif genre == "image":  # la légende « Figure n … » est juste avant ou juste après l'image
                suivant = liste[i + 1] if i + 1 < len(liste) else None
                if tampon and tampon[-1].lower().startswith("figure"):
                    legende = tampon.pop()
                    vider()
                    ajouter("image_schema", legende)
                elif suivant and suivant[0] == "texte" and suivant[1].lower().startswith("figure"):
                    vider()
                    ajouter("image_schema", suivant[1])
                    i += 1
            i += 1
        vider()
    return resultat


def pages_extraites(document: dict, extrait: dict) -> list[dict]:
    """Le texte de chaque page avant découpage (pour le taux d'erreur de l'OCR du niveau 1)."""
    if "fiche" in extrait:
        return [{"reference_source": document["reference_source"], "page": "1",
                 "texte": "\n".join(f"{c} : {v}" for c, v in extrait["fiche"])}]
    return [{"reference_source": document["reference_source"], "page": str(n), "texte": texte_de_page(md)}
            for n, md in enumerate(extrait["pages"], start=1)]
