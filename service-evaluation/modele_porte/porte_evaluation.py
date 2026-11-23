"""Modèle de porte d'évaluation, à copier dans votre RAG.

Il ouvre les quatre portes que le service d'évaluation appelle :

    POST /ingerer      ① ENTRÉE : les documents de l'évaluation
    GET  /index        ② SORTIE : la version du RAG, ses chunks, les pages lues
    POST /rechercher   ③ ENTRÉE une question → SORTIE les k chunks retrouvés
    POST /repondre     ④ ENTRÉE une question → SORTIE la réponse, ses sources, l'abstention

Tel quel, il marche : un « RAG » jouet, en mémoire, qui fait un chunk par page et cherche par mots communs.
Il sert à voir la forme exacte de chaque porte, et à tester le kit de bout en bout.
Pour votre RAG : remplacer le contenu des quatre fonctions marquées « À REMPLACER » par l'appel à votre RAG.
Les formes d'entrée et de sortie, elles, ne changent pas.

Lancer (dépendances : fastapi, uvicorn, pypdf) :
    uvicorn porte_evaluation:app --host 127.0.0.1 --port 8100
Guide pas à pas : service-evaluation/documentation/integrer_votre_rag.md
"""

import base64
import hashlib
import io
import re
import time
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pypdf import PdfReader

# --- Les réglages de votre RAG : ils entrent dans sa version ----------------------------------------
NOM = "mon-rag"
K = 5
REGLAGES = {"decoupage": "une-page", "embedding": "aucun", "generation": "aucune", "prompt": "aucun", "reranker": "aucun"}

app = FastAPI(title="Porte d'évaluation", description="Les quatre portes que le service d'évaluation appelle.")
index: dict = {"chunks": [], "pages": [], "version_index": None}   # À REMPLACER : l'index de votre RAG


# --- Ce que le service d'évaluation envoie --------------------------------------------------------

class Document(BaseModel):
    reference_source: str   # identifiant du document : c'est lui que vos chunks doivent porter
    titre: str
    type_document: str
    version: str
    format: str             # pdf_natif, pdf_scanne, word, excel, fiche_base
    droits_acces: str       # le profil qui peut le voir, ou « tous »
    fichier: str            # le nom du fichier
    contenu: str            # le fichier lui-même, en base64


class Documents(BaseModel):
    documents: list[Document]


class Echange(BaseModel):
    question: str
    reponse: str


class Question(BaseModel):
    question: str
    profil: str = "tous"            # le profil de l'utilisateur : la recherche applique ses droits
    historique: list[Echange] = []  # pour une question de suite : l'échange précédent


# --- ① ingérer ------------------------------------------------------------------------------------

@app.post("/ingerer")
def ingerer(demande: Documents) -> dict:
    """À REMPLACER : indexer ces documents avec votre RAG, dans un espace à part de la production."""
    chunks, pages = [], []
    for d in demande.documents:
        lecteur = PdfReader(io.BytesIO(base64.b64decode(d.contenu)))
        for numero, page in enumerate(lecteur.pages, start=1):
            texte = page.extract_text() or ""
            pages.append({"reference_source": d.reference_source, "page": str(numero), "texte": texte})
            if not texte.strip():
                continue    # page vide pour ce RAG jouet (un scan, sans OCR) : l'évaluation 1 le verra
            chunks.append({
                "chunk_id": f"{d.reference_source}-p{numero}-0",
                "type_objet": "chunk",                       # un morceau de document (noeud, relation : un graphe)
                "reference_source": d.reference_source,      # repris tel quel du document reçu
                "version_document": d.version,
                "page": str(numero),                         # la page où le chunk commence, en texte
                "type_element": "texte_scanne" if d.format == "pdf_scanne" else "texte",
                "droits_acces": d.droits_acces,              # repris tel quel : il sert au filtre des droits
                "ordre": 0,                                  # rang du chunk dans la page : 0, 1, 2…
                "texte": texte,
            })
    version_index = hashlib.sha256(repr([c["texte"] for c in chunks]).encode()).hexdigest()[:8]
    for c in chunks:
        c["version_index"] = version_index
    index.update(chunks=chunks, pages=pages, version_index=version_index)
    return {"documents": len(demande.documents), "chunks": len(chunks), "pages": len(pages)}


# --- ② montrer l'index ----------------------------------------------------------------------------

@app.get("/index")
def montrer_index() -> dict:
    """À REMPLACER : lire l'index de votre RAG, et le rendre sous cette forme."""
    if not index["chunks"]:
        raise HTTPException(409, "Aucun document ingéré : appeler d'abord POST /ingerer.")
    versions = {"index": index["version_index"], **REGLAGES}
    empreinte = hashlib.sha256(repr(sorted(versions.items()) + [K]).encode()).hexdigest()[:8]
    return {
        "rag": {"contrat": "1.0", "nom": NOM,
                "version_rag": f"{NOM}-k{K}-{empreinte}",   # change dès que l'index, un modèle, le prompt ou k change
                "type_rag": "vectoriel",                     # vectoriel, graphe, hybride ou agent
                "date": time.strftime("%Y-%m-%d"), "k": K, "versions": versions,
                "filtre_droits": True},
        "chunks": index["chunks"],
        "pages": index["pages"],    # le texte de chaque page, avant découpage : sert à mesurer l'OCR
        "graphe": None,             # le graphe en Turtle, si votre RAG en a un
    }


# --- ③ rechercher ---------------------------------------------------------------------------------

def chercher(question: str, profil: str, historique: list[Echange]) -> list[tuple[dict, float]]:
    """À REMPLACER : la recherche de votre RAG, avec le filtre des droits du profil, sans génération."""
    texte = " ".join([h.question for h in historique] + [question])
    mots = set(re.findall(r"\w{4,}", texte.lower()))
    autorises = [c for c in index["chunks"] if c["droits_acces"] in ("tous", profil)]   # filtre PENDANT la recherche
    notes = [(c, len(mots & set(re.findall(r"\w{4,}", c["texte"].lower())))) for c in autorises]
    return sorted([n for n in notes if n[1] > 0], key=lambda n: -n[1])[:K]


@app.post("/rechercher")
def rechercher(q: Question) -> dict:
    debut = time.perf_counter()
    trouves = chercher(q.question, q.profil, q.historique)
    return {"resultats": [{"chunk_id": c["chunk_id"], "rang": rang, "score": float(score)}
                          for rang, (c, score) in enumerate(trouves, start=1)],
            "duree_ms": round((time.perf_counter() - debut) * 1000)}


# --- ④ répondre -----------------------------------------------------------------------------------

@app.post("/repondre")
def repondre(q: Question) -> dict:
    """À REMPLACER : la réponse de votre RAG (recherche, puis génération), avec ses sources."""
    debut = time.perf_counter()
    trouves = chercher(q.question, q.profil, q.historique)
    abstention = not trouves                       # votre RAG dit lui-même quand il ne sait pas
    reponse = ("Je ne trouve pas cette information dans les documents." if abstention
               else trouves[0][0]["texte"][:500])
    return {
        "reponse": reponse,
        "abstention": abstention,
        "chunks_cites": [] if abstention else [trouves[0][0]["chunk_id"]],   # les sources citées dans la réponse
        "chunks_contexte": [c["chunk_id"] for c, _ in trouves],               # tous les chunks donnés au modèle
        "duree_ms": round((time.perf_counter() - debut) * 1000),
        "cout": 0.0, "tokens_entree": 0, "tokens_sortie": 0,                  # en euros ; 0 pour un modèle local
        "trace_id": uuid.uuid4().hex,              # l'identifiant de la trace Langfuse, si votre RAG en envoie
    }
