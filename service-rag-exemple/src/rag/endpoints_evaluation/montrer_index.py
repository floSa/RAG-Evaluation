"""Endpoint 2 — montrer l'index (SORTIE) : ce que le RAG a lu et découpé, et sa version exacte.

Ce qu'elle rend :
    rag      la description du RAG : nom, version_rag, type_rag (vectoriel ou hybride), k, versions des briques,
             et ses autres réglages (« reglages ») : un par fonctionnalité du RAG qu'on peut changer
    chunks   chaque chunk de l'index, avec sa référence, sa version, sa page, son type, ses droits, son ordre
    pages    le texte de chaque page lue, avant découpage (pour mesurer l'OCR)
    graphe   le graphe en RDF (Turtle), si le RAG en a un ; le RAG d'exemple n'en a pas : null
"""

import time

from rag.assistant import Assistant
from rag.pipeline.etape_2_decoupage import VERSION_DECOUPAGE
from rag.pipeline.etape_3_index import empreinte
from rag.pipeline.etape_5_generation import SYSTEME, VERSION_PROMPT

CHAMPS_CHUNK = ("chunk_id", "type_objet", "reference_source", "version_document", "page", "type_element",
                "droits_acces", "ordre", "texte", "version_index", "metadonnees")


def decrire(assistant: Assistant) -> dict:
    """La version exacte du RAG : elle change dès que l'index, les modèles, le prompt ou k changent."""
    config, m = assistant.config, assistant.config["modeles"]
    versions = {"index": assistant.index.chunks[0]["version_index"], "decoupage": VERSION_DECOUPAGE,
                "embedding": m["embeddings"]["modele"], "generation": m["generation"]["modele"],
                "prompt": VERSION_PROMPT, "reranker": "aucun"}
    type_rag = "vectoriel"                    # sans graphe : il cherche des morceaux de texte, par le sens et par les mots
    return {"contrat": "1.0", "nom": config["nom"],
            "version_rag": f"{config['nom']}-{type_rag}-k{assistant.k}-{empreinte([versions, m['generation'], SYSTEME])}",
            "type_rag": type_rag, "date": time.strftime("%Y-%m-%d"), "k": assistant.k,
            "versions": versions, "filtre_droits": True,
            # Les réglages qui n'ont pas de champ à eux dans le contrat : autant qu'en a le RAG
            "reglages": {"réflexion du modèle": not m["generation"].get("sans_reflexion", False),
                         "recherche par mots-clés": True,                 # BM25, toujours fusionnée aux vecteurs
                         "candidats avant fusion": config["recherche"]["candidats"]}}


def montrer_index(assistant: Assistant) -> dict:
    index = assistant.index
    return {"rag": decrire(assistant),
            "chunks": [{k: c[k] for k in CHAMPS_CHUNK if k in c} for c in index.chunks],
            "pages": index.pages,
            "graphe": None}                         # le RAG d'exemple n'a pas de graphe
