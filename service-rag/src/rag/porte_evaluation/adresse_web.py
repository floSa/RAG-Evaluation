"""Les quatre portes, ouvertes à une adresse web : http://127.0.0.1:8100 (config.yaml, « porte_evaluation »).

    POST /ingerer      porte 1   {"documents": [...]}
    GET  /index        porte 2
    POST /rechercher   porte 3   {"question", "profil", "historique"}
    POST /repondre     porte 4   {"question", "profil", "historique"}

La documentation de chaque porte, générée, est à http://127.0.0.1:8100/docs.
Lancement : « rag ouvrir-porte », ou le docker-compose.yml du service.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from rag.assistant import Assistant, charger_config
from rag.porte_evaluation import ESPACE
from rag.porte_evaluation.ingerer import ingerer
from rag.porte_evaluation.montrer_index import montrer_index
from rag.porte_evaluation.rechercher import rechercher
from rag.porte_evaluation.repondre import repondre


class Document(BaseModel):
    reference_source: str
    titre: str
    type_document: str
    version: str
    format: str
    droits_acces: str
    fichier: str
    contenu: str            # le fichier, en base64


class Documents(BaseModel):
    documents: list[Document]


class Echange(BaseModel):
    question: str
    reponse: str


class Question(BaseModel):
    question: str
    profil: str = "tous"
    historique: list[Echange] = []


app = FastAPI(title="Porte d'évaluation du RAG d'exemple",
              description="Les quatre portes que le service d'évaluation appelle.")
etat: dict = {"assistant": None}


def assistant() -> Assistant:
    """L'assistant de l'espace « evaluation », chargé une fois ; erreur claire si rien n'a été ingéré."""
    if etat["assistant"] is None:
        try:
            etat["assistant"] = Assistant(espace=ESPACE)
        except FileNotFoundError:
            raise HTTPException(409, "Aucun document ingéré : appeler d'abord POST /ingerer.")
    return etat["assistant"]


@app.post("/ingerer", summary="Porte 1 — ingérer les documents de l'évaluation")
def porte_ingerer(demande: Documents) -> dict:
    resultat = ingerer(charger_config(), [d.model_dump() for d in demande.documents])
    etat["assistant"] = None                 # le prochain appel relit le nouvel index
    return resultat


@app.get("/index", summary="Porte 2 — montrer l'index")
def porte_index() -> dict:
    return montrer_index(assistant())


@app.post("/rechercher", summary="Porte 3 — rechercher")
def porte_rechercher(q: Question) -> dict:
    return rechercher(assistant(), q.question, q.profil, [h.model_dump() for h in q.historique])


@app.post("/repondre", summary="Porte 4 — répondre")
def porte_repondre(q: Question) -> dict:
    return repondre(assistant(), q.question, q.profil, [h.model_dump() for h in q.historique])
