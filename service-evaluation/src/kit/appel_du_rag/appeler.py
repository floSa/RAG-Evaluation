"""Appeler les quatre portes d'un RAG, à son adresse web, et ranger ce qu'il rend.

    1. ingérer         POST /ingerer      le kit envoie les documents du corpus (fichiers et métadonnées)
    2. montrer l'index GET  /index        le kit reçoit la description du RAG, ses chunks, ses pages, son graphe
    3. rechercher      POST /rechercher   pour chaque question : les k chunks retrouvés
    4. répondre        POST /repondre     pour chaque question : la réponse, ses sources, l'abstention, la trace

Le kit n'envoie jamais les annotations du métier : ni réponse attendue, ni points clés, ni passages.
Seule exception, prévue par la règle : pour une question de suite, l'échange précédent (historique).
Ce que le RAG rend est écrit dans sorties/sorties_rag/<version_rag>/, puis vérifié (contrat.py).
"""

import base64
import json
from pathlib import Path

import httpx

from kit.appel_du_rag import contrat

CHAMPS_DOCUMENT = ("reference_source", "titre", "type_document", "version", "format", "droits_acces")


def fichier_du_document(dossier_documents: Path, reference: str) -> Path:
    """Le fichier d'un document : <référence>.<extension> dans le dossier des documents du corpus."""
    trouves = sorted(dossier_documents.glob(f"{reference}.*"))
    if not trouves:
        raise FileNotFoundError(f"Document {reference} : aucun fichier {reference}.* dans {dossier_documents}/.")
    return trouves[0]


def documents_a_envoyer(corpus: dict, dossier_documents: Path) -> list[dict]:
    envoi = []
    for d in corpus["documents"]:
        chemin = fichier_du_document(dossier_documents, d["reference_source"])
        envoi.append({c: d[c] for c in CHAMPS_DOCUMENT}
                     | {"fichier": chemin.name, "contenu": base64.b64encode(chemin.read_bytes()).decode()})
    return envoi


def appeler(adresse: str, dossier_corpus: Path, dossier_documents: Path, dossier_sorties: Path,
            afficher=print, client: httpx.Client | None = None) -> Path:
    """Les quatre portes, dans l'ordre ; rend le dossier sorties_rag/<version_rag>/ écrit."""
    client = client or httpx.Client(base_url=adresse, timeout=3600)   # l'ingestion peut prendre plusieurs minutes
    corpus = contrat.charger_corpus(dossier_corpus)

    # 1. Ingérer
    afficher(f"Porte 1, ingérer : {len(corpus['documents'])} documents envoyés à {adresse}…")
    r = _appel(client.post, "/ingerer", json={"documents": documents_a_envoyer(corpus, dossier_documents)})
    afficher(f"  {'déjà ingérés, index gardé' if r.get('deja_ingere') else 'indexés'} : "
             f"{r.get('chunks', '?')} chunks, {r.get('pages', '?')} pages.")

    # 2. Montrer l'index
    index = _appel(client.get, "/index")
    rag = index["rag"]
    dossier = dossier_sorties / "sorties_rag" / rag["version_rag"]
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "rag.json").write_text(json.dumps(rag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    contrat.ecrire_jsonl(dossier / "chunks.jsonl", index["chunks"])
    if index.get("pages"):
        contrat.ecrire_jsonl(dossier / "pages_extraites.jsonl", index["pages"])
    if index.get("graphe"):
        (dossier / "graphe.ttl").write_text(index["graphe"], encoding="utf-8")
    afficher(f"Porte 2, montrer l'index : {rag['version_rag']} ({rag['type_rag']}, k = {rag['k']}), "
             f"{len(index['chunks'])} éléments.")

    # 3 et 4. Rechercher et répondre, question par question, avec le profil de chacune
    afficher(f"Portes 3 et 4, rechercher et répondre : {len(corpus['questions'])} questions…")
    par_id = {q["question_id"]: q for q in corpus["questions"]}
    recherches, reponses = [], []
    for q in corpus["questions"]:                      # toutes, y compris les réservées à la décision
        demande = {"question": q["question"], "profil": q["profil"], "historique": contrat.historique(q, par_id)}
        recherche = _appel(client.post, "/rechercher", json=demande)
        recherches.append({"question_id": q["question_id"], "profil": q["profil"], "k": rag["k"], **recherche})
        reponse = _appel(client.post, "/repondre", json=demande)
        reponses.append({"question_id": q["question_id"], "profil": q["profil"], **reponse})
        afficher(f"  {q['question_id']} : {reponse['duree_ms']} ms{' (abstention)' if reponse['abstention'] else ''}")
    contrat.ecrire_jsonl(dossier / "recherches.jsonl", recherches)
    contrat.ecrire_jsonl(dossier / "reponses.jsonl", reponses)
    return dossier


def _appel(methode, chemin: str, **arguments) -> dict:
    """Un appel à une porte ; une erreur claire si le RAG ne répond pas ou refuse."""
    try:
        r = methode(chemin, **arguments)
    except httpx.ConnectError:
        raise RuntimeError(f"Le RAG ne répond pas ({chemin}) : est-il lancé ? (temps 1 du README)") from None
    if r.status_code >= 400:
        raise RuntimeError(f"La porte {chemin} du RAG a refusé ({r.status_code}) : {r.text[:300]}")
    return r.json()
