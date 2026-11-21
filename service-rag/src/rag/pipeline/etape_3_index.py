"""Étape 3 — Index : rendre les chunks cherchables, par le sens et par les mots.

- Par le sens : chaque chunk devient un vecteur (modèle d'embeddings) ; les vecteurs sont gardés dans un fichier
  .npy, pas dans une base vectorielle : quelques milliers de chunks tiennent en mémoire.
- Par les mots : un index BM25, recalculé au chargement.
L'index est écrit dans le dossier de travail (config.yaml, « travail ») : chunks.jsonl, pages.jsonl, vecteurs.npy.
- Avec le graphe (étape 4, optionnelle) : ses éléments « noeud » s'ajoutent aux chunks, cherchables de la même façon.
  Ils sont écrits à part (travail/graphe/) : on passe d'un RAG vectoriel à un RAG hybride sans tout réindexer.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from openai import OpenAI
from rank_bm25 import BM25Okapi

from rag.pipeline import etape_1_extraction, etape_2_decoupage, etape_4_graphe


def empreinte(objet) -> str:
    """Huit caractères qui changent dès que l'objet change : sert à dater une version de l'index ou du RAG."""
    return hashlib.sha256(json.dumps(objet, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]


def mots(texte: str) -> list[str]:
    return re.findall(r"\w+", texte.lower())


def embeddings(client: OpenAI, modele: str, textes: list[str]) -> np.ndarray:
    """Les vecteurs des textes, normés (le produit scalaire est alors la similarité cosinus)."""
    vecteurs = []
    for i in range(0, len(textes), 32):
        r = client.embeddings.create(model=modele, input=textes[i:i + 32])
        vecteurs += [d.embedding for d in r.data]
    v = np.array(vecteurs, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def construire(config: dict, client: OpenAI, afficher=print, documents: list[dict] | None = None) -> dict:
    """Étapes 1 à 3 pour tous les documents : extraire, découper, vectoriser ; écrit l'index sur disque.

    Sans liste de documents, le RAG lit celle de la gestion documentaire (config.yaml, « liste_des_documents »).
    """
    travail = Path(config["travail"])
    chunks, pages = [], []
    for doc in documents if documents is not None else etape_1_extraction.liste_des_documents(config):
        afficher(f"  {doc['reference_source']}")
        extrait = etape_1_extraction.extraire(doc, Path(config["documents"]), travail / "extraction",
                                              config["extraction"]["docling"])
        chunks += etape_2_decoupage.chunks_du_document(doc, extrait, config["decoupage"]["taille_max"])
        pages += etape_1_extraction.pages_extraites(doc, extrait)
    modele = config["modeles"]["embeddings"]["modele"]
    version_index = f"{etape_2_decoupage.VERSION_DECOUPAGE}-{modele}-{empreinte(chunks)}"
    for c in chunks:
        c["chunk_id"] = f"{c['reference_source']}#{c['page']}#{c['ordre']}"
        c["type_objet"] = "chunk"
        c["version_index"] = version_index
    ecrire(travail / "index", chunks, embeddings(client, modele, [c["texte"] for c in chunks]), pages=pages)
    resultat = {"chunks": len(chunks), "pages": len(pages), "version_index": version_index}
    if config["graphe"]["actif"]:                                  # étape 4, optionnelle
        noeuds, graphe = etape_4_graphe.construire(chunks, config, client, empreinte, afficher)
        version_graphe = f"{etape_4_graphe.VERSION_EXTRACTION}-{empreinte(noeuds)}"
        for n in noeuds:
            n["version_index"] = version_graphe
        dossier = travail / "graphe"
        ecrire(dossier, noeuds, embeddings(client, modele, [n["texte"] for n in noeuds]))
        graphe.serialize(dossier / "graphe.ttl", format="turtle")
        resultat |= {"noeuds": len(noeuds), "triplets": len(graphe)}
    return resultat


def ecrire(dossier: Path, objets: list[dict], vecteurs: np.ndarray, pages: list[dict] | None = None) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    np.save(dossier / "vecteurs.npy", vecteurs)
    fichiers = [("chunks.jsonl", objets)] + ([("pages.jsonl", pages)] if pages is not None else [])
    for nom, lignes in fichiers:
        with (dossier / nom).open("w", encoding="utf-8") as f:
            f.writelines(json.dumps(o, ensure_ascii=False) + "\n" for o in lignes)


@dataclass
class Index:
    chunks: list[dict]                 # les chunks, puis les éléments du graphe s'il est actif
    pages: list[dict]
    vecteurs: np.ndarray
    bm25: BM25Okapi
    graphe_ttl: Path | None = None     # le graphe en RDF, s'il est actif


def lire_jsonl(chemin: Path) -> list[dict]:
    with chemin.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def charger(config: dict) -> Index:
    """Relit l'index écrit par `construire` ; avec le graphe actif, y ajoute ses éléments."""
    dossier = Path(config["travail"]) / "index"
    if not (dossier / "chunks.jsonl").exists():
        raise FileNotFoundError("Index absent : lancer d'abord « rag indexer ».")
    chunks, pages, vecteurs = lire_jsonl(dossier / "chunks.jsonl"), lire_jsonl(dossier / "pages.jsonl"), np.load(dossier / "vecteurs.npy")
    graphe_ttl = None
    if config["graphe"]["actif"]:
        dossier_graphe = Path(config["travail"]) / "graphe"
        if not (dossier_graphe / "graphe.ttl").exists():
            raise FileNotFoundError("Graphe absent : lancer d'abord « rag indexer --graphe ».")
        noeuds = lire_jsonl(dossier_graphe / "chunks.jsonl")
        version = f"{chunks[0]['version_index']}+{noeuds[0]['version_index']}"   # une version pour tout l'index
        chunks = [{**c, "version_index": version} for c in chunks + noeuds]
        vecteurs = np.vstack([vecteurs, np.load(dossier_graphe / "vecteurs.npy")])
        graphe_ttl = dossier_graphe / "graphe.ttl"
    return Index(chunks, pages, vecteurs, BM25Okapi([mots(c["texte"]) for c in chunks]), graphe_ttl)
