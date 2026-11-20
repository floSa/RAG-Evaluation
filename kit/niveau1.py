"""Niveau 1 — Ingestion (document 3, section 6) : rattachement des passages aux chunks, et scores de l'ingestion.

Règles de rattachement : un chunk de même référence et même page correspond si…
- texte, fiche de base : il contient le passage (exact) ; sinon une partie lui ressemble à 95 % (approché) ;
- tableau : il contient les mêmes mots que le passage, dans n'importe quel ordre, à 90 % (approché) ;
- texte scanné : une partie du chunk ressemble au passage à 90 % (approché) ;
- image ou schéma : c'est un chunk de type « image ou schéma » (image).
Si aucun chunk ne convient seul, deux chunks qui se suivent peuvent contenir le passage à eux deux (coupé).
Fiche de base (CADRAGE.md, constats) : la « page » d'un passage est le nom du champ ; on accepte un chunk de même
référence dont la page est ce nom, ou dont le texte contient le nom du champ.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

import jiwer
from rapidfuzz import fuzz

from kit.publication import Evaluation, Ligne

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


def taux_erreur(reference: str, extrait: str) -> tuple[float, float]:
    """Taux d'erreur de caractères et de mots (jiwer), après réduction des espaces et retours à la ligne."""
    ref, hyp = " ".join(reference.split()), " ".join((extrait or "").split())
    if not hyp:
        return 1.0, 1.0
    return jiwer.cer(ref, hyp), jiwer.wer(ref, hyp)


def evaluer(ev: Evaluation) -> tuple[list[Ligne], list[Lien], list[dict]]:
    """Rend les lignes de scores, les liens passage ↔ chunk, et les passages non rattachés avec leur cause."""
    seuils = ev.config["rattachement"]
    chunks = [c for c in ev.fichier_rag("chunks.jsonl") if c["type_objet"] != "resume"]
    par_doc: dict[str, list[dict]] = {}
    for c in chunks:
        par_doc.setdefault(c.get("reference_source"), []).append(c)
    lignes: list[Ligne] = []

    for ref, d in ev.documents.items():
        lignes.append(Ligne("n1_documents_indexes", float(ref in par_doc), objet=ref,
                            attributs={"type_document": d["type_document"], "format": d["format"]},
                            detail=None if ref in par_doc else "aucun chunk"))
    for c in chunks:
        manquants = [m for m in CHAMPS_METADONNEES if c.get(m) in (None, "")]
        d = ev.documents.get(c.get("reference_source"))
        lignes.append(Ligne("n1_metadonnees_completes", float(not manquants), objet=c["chunk_id"],
                            attributs={"type_document": d["type_document"] if d else "hors corpus"},
                            detail=f"manque : {', '.join(manquants)}" if manquants else None))

    liens, non_rattaches = [], []
    for p in ev.corpus["passages"]:
        if p["repond"] == "piege":
            continue  # un piège n'a pas à être rattaché ; il sert au niveau 2
        fiche = ev.documents[p["reference_source"]]["format"] == "fiche_base"
        du_doc = par_doc.get(p["reference_source"], [])
        trouves, meilleure = rattacher(p, du_doc, fiche, seuils)
        liens += trouves
        attributs = ev.attributs_passage(p["passage_id"])
        objet = f"passage {p['passage_id']}"
        if trouves:
            detail = f"{trouves[0].mode} : " + ", ".join(l.chunk_id for l in trouves)
        else:
            detail = cause_probable(p, du_doc, fiche, meilleure, seuils)
            non_rattaches.append({"passage_id": p["passage_id"], "question_id": p["question_id"],
                                  "reference_source": p["reference_source"], "page": p["page"],
                                  "type_element": p["type_element"], "cause_probable": detail})
        lignes.append(Ligne("n1_passages_rattaches", float(bool(trouves)), p["question_id"], objet,
                            detail=detail, attributs=attributs))
        lignes.append(Ligne("n1_passages_coupes", float(bool(trouves) and trouves[0].mode == "coupe"),
                            p["question_id"], objet, attributs=attributs))

    extraites = {(x["reference_source"], str(x["page"])): x["texte"] for x in ev.fichier_rag("pages_extraites.jsonl")}
    for o in ev.corpus["pages_ocr"]:
        cer, wer = taux_erreur(o["texte_retape"], extraites.get((o["reference_source"], str(o["page"]))))
        objet = f"{o['reference_source']} page {o['page']}"
        attributs = {"type_document": ev.documents[o["reference_source"]]["type_document"]}
        lignes.append(Ligne("n1_erreur_caracteres", cer, objet=objet, poids=len(o["texte_retape"]),
                            attributs=attributs, detail=None if (o["reference_source"], str(o["page"])) in extraites
                            else "page absente de pages_extraites.jsonl"))
        lignes.append(Ligne("n1_erreur_mots", wer, objet=objet, poids=len(o["texte_retape"].split()),
                            attributs=attributs))
    return lignes, liens, non_rattaches


def enregistrer(ev: Evaluation, liens: list[Lien], non_rattaches: list[dict]) -> None:
    """liens_index.jsonl et passages_non_rattaches.jsonl dans resultats/<evaluation_id>/, et les liens dans la base."""
    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from kit import base, contrat

    ev.dossier.mkdir(parents=True, exist_ok=True)
    contrat.ecrire_jsonl(ev.dossier / "liens_index.jsonl", (vars(l) for l in liens))
    contrat.ecrire_jsonl(ev.dossier / "passages_non_rattaches.jsonl", non_rattaches)
    versions = {l.version_index for l in liens}
    with Session(base.moteur(ev.config["chemins"]["base"])) as session:
        session.execute(delete(base.LienIndex).where(base.LienIndex.version_corpus == ev.version_corpus,
                                                     base.LienIndex.version_index.in_(versions)))
        session.add_all(base.LienIndex(version_corpus=ev.version_corpus, **vars(l)) for l in liens)
        session.commit()


def lire_liens(ev: Evaluation) -> list[dict]:
    """Les liens écrits par le niveau 1 (nécessaires aux niveaux 2 et 3)."""
    from kit import contrat

    chemin = ev.dossier / "liens_index.jsonl"
    if not chemin.exists():
        raise FileNotFoundError(f"{chemin} absent : lancer d'abord « kit niveau1 ».")
    return contrat.lire_jsonl(chemin)
