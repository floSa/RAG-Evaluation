"""Niveau 1 — Le rattachement (document 3, section 6) : retrouver chaque passage du corpus dans les chunks du RAG.

Règles de rattachement : un chunk de même référence et même page correspond si…
- texte, fiche de base : il contient le passage (exact) ; sinon une partie lui ressemble à 95 % (approché) ;
- tableau : il contient les mêmes mots que le passage, dans n'importe quel ordre, à 90 % (approché) ;
- texte scanné : une partie du chunk ressemble au passage à 90 % (approché) ;
- image ou schéma : c'est un chunk de type « image ou schéma » (image).
Si aucun chunk ne convient seul, deux chunks qui se suivent peuvent contenir le passage à eux deux (coupé).
Fiche de base (DECISIONS.md, décision 7) : la « page » d'un passage est le nom du champ ; on accepte un chunk de même
référence dont la page est ce nom, ou dont le texte contient le nom du champ.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from rapidfuzz import fuzz

CHAMPS_METADONNEES = ("reference_source", "version_document", "page", "type_element", "droits_acces")


def normaliser(texte: str) -> str:
    """Casse, espaces, césures, apostrophes et guillemets (document 3, section 6)."""
    t = unicodedata.normalize("NFKC", texte or "")
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)  # césure en fin de ligne
    for a, b in (("’", "'"), ("‘", "'"), ("`", "'"), ("«", '"'), ("»", '"'), ("“", '"'), ("”", '"'), (" ", " "),
                 (" ", " "), ("–", "-"), ("—", "-")):
        t = t.replace(a, b)
    return " ".join(t.lower().split())


def mots(texte: str) -> list[str]:
    return re.findall(r"\w+", normaliser(texte))


def part_des_mots(passage: str, chunk: str) -> float:
    """Part des mots du passage présents dans le chunk, en tenant compte des répétitions."""
    attendus, presents = Counter(mots(passage)), Counter(mots(chunk))
    total = sum(attendus.values())
    return sum(min(n, presents[m]) for m, n in attendus.items()) / total if total else 0.0


def ressemblance(passage: str, chunk: str) -> float:
    """Ressemblance de 0 à 1 entre le passage et la partie du chunk qui lui ressemble le plus.

    partial_ratio cherche la plus courte des deux chaînes dans la plus longue : si le chunk est plus court que
    le passage, il ne peut pas le contenir, et on compare les deux textes entiers (sinon un chunk qui ne porte
    que la moitié du passage passerait pour rattaché).
    """
    p, c = normaliser(passage), normaliser(chunk)
    return (fuzz.partial_ratio(p, c) if len(c) >= len(p) else fuzz.ratio(p, c)) / 100


@dataclass
class Lien:
    passage_id: int
    chunk_id: str
    version_index: str
    mode: str
    similarite: float


def comparer(passage: dict, texte_chunk: str, seuils: dict) -> tuple[str | None, float]:
    """Le mode de rattachement d'un passage à un texte de chunk, ou None ; avec la ressemblance mesurée."""
    t = passage["type_element"]
    if t == "tableau":
        s = part_des_mots(passage["passage"], texte_chunk)
        return ("approche" if s >= seuils["tableau_mots"] else None), s
    if t == "texte_scanne":
        s = ressemblance(passage["passage"], texte_chunk)
        return ("approche" if s >= seuils["scanne_partiel"] else None), s
    if normaliser(passage["passage"]) in normaliser(texte_chunk):
        return "exact", 1.0
    s = ressemblance(passage["passage"], texte_chunk)
    return ("approche" if s >= seuils["texte_approche"] else None), s


def candidats(passage: dict, chunks_du_doc: list[dict], fiche: bool) -> list[dict]:
    if fiche:
        champ = normaliser(passage["page"])
        return [c for c in chunks_du_doc if normaliser(c["page"]) == champ or champ in normaliser(c["texte"])]
    return [c for c in chunks_du_doc if str(c["page"]) == str(passage["page"])]


def cle_ordre(c: dict) -> tuple:
    page = str(c.get("page", ""))
    return (0, int(page), c.get("ordre", 0)) if page.isdigit() else (1, page, c.get("ordre", 0))


def rattacher(passage: dict, chunks_du_doc: list[dict], fiche: bool, seuils: dict) -> tuple[list[Lien], float]:
    """Les liens d'un passage, et la meilleure ressemblance trouvée (pour expliquer un échec)."""
    liens, meilleure = [], 0.0
    if passage["type_element"] == "image_schema":
        for c in candidats(passage, chunks_du_doc, fiche):
            if c.get("type_element") == "image_schema":
                liens.append(Lien(passage["passage_id"], c["chunk_id"], c["version_index"], "image",
                                  round(ressemblance(passage["passage"], c["texte"]), 4)))
        return liens, 1.0 if liens else 0.0
    for c in candidats(passage, chunks_du_doc, fiche):
        mode, s = comparer(passage, c["texte"], seuils)
        meilleure = max(meilleure, s)
        if mode:
            liens.append(Lien(passage["passage_id"], c["chunk_id"], c["version_index"], mode, round(s, 4)))
    if liens:
        return liens, meilleure
    # passage coupé : deux chunks qui se suivent dans le document, dont l'un au moins sur la page du passage
    ordonnes = sorted(chunks_du_doc, key=cle_ordre)
    sur_la_page = {c["chunk_id"] for c in candidats(passage, chunks_du_doc, fiche)}
    for a, b in zip(ordonnes, ordonnes[1:]):
        if a["chunk_id"] in sur_la_page or b["chunk_id"] in sur_la_page:
            mode, s = comparer(passage, a["texte"] + "\n" + b["texte"], seuils)
            if mode:
                return [Lien(passage["passage_id"], c["chunk_id"], c["version_index"], "coupe", round(s, 4))
                        for c in (a, b)], s
    return [], meilleure


def cause_probable(passage: dict, chunks_du_doc: list[dict], fiche: bool, meilleure: float, seuils: dict) -> str:
    """Pourquoi un passage n'est pas rattaché : à examiner un par un (document 3, section 6)."""
    if not chunks_du_doc:
        return "document absent de l'index"
    if not candidats(passage, chunks_du_doc, fiche):
        ailleurs = [c for c in chunks_du_doc if comparer(passage, c["texte"], seuils)[0]]
        if ailleurs:
            pages = ", ".join(sorted({str(c["page"]) for c in ailleurs}))
            return f"aucun chunk sur la page {passage['page']} ; le passage est trouvé page {pages} : page mal notée ?"
        return f"aucun chunk sur la page {passage['page']} : page perdue à l'extraction, ou mal notée"
    if passage["type_element"] == "image_schema":
        return "aucun chunk de type image sur la page : image ni décrite ni légendée"
    if passage["type_element"] == "tableau":
        return f"tableau mal extrait : {meilleure:.0%} des mots du passage retrouvés au mieux"
    if passage["type_element"] == "texte_scanne":
        return f"OCR : ressemblance de {meilleure:.0%} au mieux"
    return f"texte différent dans l'index : ressemblance de {meilleure:.0%} au mieux"
