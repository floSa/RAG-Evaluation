"""Niveau 1 — Ingestion (document 3, section 6) : les scores de l'ingestion.

Le rattachement (rattachement.py) dit, pour chaque passage du corpus, quels chunks du RAG le contiennent.
On en tire : la part des passages retrouvés, les métadonnées justes, le taux d'erreur de l'OCR (jiwer) ;
puis on enregistre les liens passage → chunks dans la base, pour le niveau 2.
"""

import jiwer

from kit.etape_1_evaluation_ingestion.rattachement import CHAMPS_METADONNEES, Lien, cause_probable, rattacher
from kit.etape_5_resultats.publication import Evaluation, Ligne


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
        fiche = ev.documents[p["reference_source"]]["format"] == "fiche_base"
        du_doc = par_doc.get(p["reference_source"], [])
        trouves, meilleure = rattacher(p, du_doc, fiche, seuils)
        liens += trouves
        if p["repond"] == "piege":
            continue  # un piège est rattaché pour le niveau 2 (piège retrouvé), mais n'entre pas dans les scores
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

    from kit import base
    from kit.etape_0b_branchement import contrat

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
    from kit.etape_0b_branchement import contrat

    chemin = ev.dossier / "liens_index.jsonl"
    if not chemin.exists():
        raise FileNotFoundError(f"{chemin} absent : lancer d'abord « kit evaluer-ingestion ».")
    return contrat.lire_jsonl(chemin)
