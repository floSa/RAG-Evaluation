"""Le branchement sur l'évaluation : la SEULE partie du RAG écrite pour être évalué.

Le reste du dossier rag/ marche sans elle. Ici, on met ce que sait faire l'assistant au format du contrat
(evaluation/documentation/reference/contrat_des_fichiers.md). Le kit n'importe rien du RAG, et le RAG rien du kit : ils se parlent par ce
connecteur, que le kit charge par son nom (`kit lancer rag.utils.branchement_evaluation:Connecteur`), ou par des fichiers
(`rag exporter` puis `rag repondre`).

Les quatre prises :
    1. Ingérer avec métadonnées : exporter les chunks avec leur référence, version, page, type, droits, ordre,
       et le texte de chaque page avant découpage            → exporter_index, exporter_pages
    2. Rechercher : rendre le classement de la recherche, seul, avant la génération     → rechercher
    3. Répondre : la réponse avec l'abstention, les chunks cités et ceux du contexte, la durée, le coût, les tokens
                                                                                           → repondre
    4. Tracer : l'identifiant de la trace Langfuse de chaque réponse, et la version exacte du RAG
                                                                                           → repondre, decrire
"""

import json
import shutil
import time
import uuid
from pathlib import Path

from rag.assistant import Assistant
from rag.pipeline.etape_2_decoupage import VERSION_DECOUPAGE
from rag.pipeline.etape_3_index import empreinte
from rag.pipeline.etape_6_generation import SYSTEME, VERSION_PROMPT

CHAMPS_CHUNK = ("chunk_id", "type_objet", "reference_source", "version_document", "page", "type_element",
                "droits_acces", "ordre", "texte", "version_index", "metadonnees")


class Connecteur:
    """Les six méthodes que le kit appelle par leur nom (CONTRAT.md, « Le connecteur »)."""

    def __init__(self, k: int | None = None, graphe=None):
        self.assistant = Assistant(k=k, graphe=graphe)
        self.derniere_recherche = None

    # --- Prise 4 : la version exacte du RAG évalué -----------------------------------------------

    def decrire(self) -> dict:
        config, m = self.assistant.config, self.assistant.config["modeles"]
        versions = {"index": self.assistant.index.chunks[0]["version_index"], "decoupage": VERSION_DECOUPAGE,
                    "embedding": m["embeddings"]["modele"], "generation": m["generation"]["modele"],
                    "prompt": VERSION_PROMPT, "reranker": "aucun"}
        k = self.assistant.k
        type_rag = "hybride" if self.assistant.index.graphe_ttl else "vectoriel"
        return {"contrat": "1.0", "nom": config["nom"],
                "version_rag": f"{config['nom']}-k{k}-{empreinte([versions, m['generation'], SYSTEME])}",
                "type_rag": type_rag, "date": time.strftime("%Y-%m-%d"), "k": k,
                "versions": versions, "filtre_droits": True}

    # --- Prise 1 : ingérer avec métadonnées -------------------------------------------------------

    def exporter_index(self):
        return ({k: c[k] for k in CHAMPS_CHUNK if k in c} for c in self.assistant.index.chunks)

    def exporter_pages(self):
        return iter(self.assistant.index.pages)

    def exporter_graphe(self, chemin):
        """Copie le graphe en RDF (graphe.ttl) s'il est actif ; sinon, ne fait rien."""
        if self.assistant.index.graphe_ttl:
            shutil.copyfile(self.assistant.index.graphe_ttl, chemin)

    # --- Prise 2 : rechercher -----------------------------------------------------------------------

    def rechercher(self, question: str, profil: str, historique: list) -> list[dict]:
        return [{"chunk_id": t["chunk"]["chunk_id"], "rang": t["rang"], "score": t["score"]}
                for t in self.assistant.rechercher(question, profil, historique)]

    # --- Prises 3 et 4 : répondre, avec la trace ----------------------------------------------------

    def repondre(self, question: str, profil: str, historique: list) -> dict:
        r = self.assistant.demander(question, profil, historique)
        self.derniere_recherche = {"resultats": [{"chunk_id": t["chunk"]["chunk_id"], "rang": t["rang"],
                                                  "score": t["score"]} for t in r["recherche"]],
                                   "duree_ms": r["duree_recherche_ms"]}
        m = self.assistant.config["modeles"]["generation"]
        entree, sortie = r["tokens"]
        return {"profil": profil, "reponse": r["reponse"], "abstention": r["abstention"],
                "chunks_cites": [c["chunk_id"] for c in r["cites"]],
                "chunks_contexte": [c["chunk_id"] for c in r["contexte"]],
                "duree_ms": r["duree_ms"],
                "cout": (entree * m["prix_entree_eur_par_million"] + sortie * m["prix_sortie_eur_par_million"]) / 1e6,
                "tokens_entree": entree, "tokens_sortie": sortie,
                "trace_id": r["trace_id"] or uuid.uuid4().hex}


# --- Le même branchement, par fichiers (pour un RAG qui ne serait pas en Python) -------------------

def ecrire_jsonl(chemin: Path, objets) -> int:
    n = 0
    with chemin.open("w", encoding="utf-8") as f:
        for o in objets:
            f.write(json.dumps({k: v for k, v in o.items() if v is not None}, ensure_ascii=False) + "\n")
            n += 1
    return n


def dossier_de_sortie(c: Connecteur) -> Path:
    dossier = Path(c.assistant.config["sorties"]) / c.decrire()["version_rag"]
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def exporter(c: Connecteur) -> str:
    """Écrit rag.json, chunks.jsonl et pages_extraites.jsonl dans sorties/sorties_rag/<version_rag>/."""
    dossier = dossier_de_sortie(c)
    (dossier / "rag.json").write_text(json.dumps(c.decrire(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = ecrire_jsonl(dossier / "chunks.jsonl", c.exporter_index())
    p = ecrire_jsonl(dossier / "pages_extraites.jsonl", c.exporter_pages())
    c.exporter_graphe(dossier / "graphe.ttl")
    graphe = ", graphe.ttl" if (dossier / "graphe.ttl").exists() else ""
    return f"{dossier} : rag.json, {n} chunks, {p} pages extraites{graphe}."


def repondre_aux_questions(c: Connecteur, questions: Path, afficher=print) -> str:
    """Pose chaque question avec son profil ; écrit recherches.jsonl et reponses.jsonl.

    Du fichier de questions, le RAG ne lit que question_id, question, profil, et pour une question de suite
    la question précédente et sa réponse attendue (l'historique prévu par le contrat). Rien d'autre.
    """
    dossier = dossier_de_sortie(c)
    with questions.open(encoding="utf-8") as f:
        lignes = [json.loads(l) for l in f if l.strip()]
    par_id = {q["question_id"]: q for q in lignes}
    recherches, reponses = [], []
    for q in lignes:
        historique, p = [], q
        while p.get("question_precedente") in par_id:
            p = par_id[p["question_precedente"]]
            historique.insert(0, {"question": p["question"], "reponse": p["reponse_attendue"]})
        r = c.repondre(q["question"], q["profil"], historique)
        recherches.append({"question_id": q["question_id"], "profil": q["profil"], "k": c.assistant.k,
                           **c.derniere_recherche})
        reponses.append({"question_id": q["question_id"], **r})
        afficher(f"  {q['question_id']} ({r['duree_ms']} ms){' — abstention' if r['abstention'] else ''}")
    if c.assistant.langfuse:
        c.assistant.langfuse.flush()
    ecrire_jsonl(dossier / "recherches.jsonl", recherches)
    ecrire_jsonl(dossier / "reponses.jsonl", reponses)
    return f"{dossier} : {len(reponses)} réponses."
