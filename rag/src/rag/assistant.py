"""L'assistant : il enchaîne les étapes du pipeline pour répondre à une question.

    rag indexer   →  étapes 1, 2, 3 (et 4, le graphe, quand il sera là) : pipeline/etape_3_index.construire
    rag demander  →  étape 5 (recherche) puis étape 6 (génération)       : Assistant.demander

Il lit sa configuration dans rag/config/config.yaml et ses clés dans .env. Il marche seul : il ne sait rien de l'évaluation.
Si Langfuse est configuré, chaque question laisse une trace (recherche et génération) ; sinon, il s'en passe.
"""

import os
import time
from contextlib import nullcontext
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from rag.pipeline import etape_3_index, etape_5_recherche, etape_6_generation

CONFIG = Path(__file__).resolve().parents[2] / "config" / "config.yaml"  # rag/config/config.yaml


def charger_config(chemin: Path = CONFIG) -> dict:
    load_dotenv()
    return yaml.safe_load(Path(chemin).read_text(encoding="utf-8"))


def client_llm(config: dict) -> OpenAI:
    """Client de n'importe quel point d'accès compatible OpenAI."""
    m = config["modeles"]
    return OpenAI(base_url=m["adresse"], api_key=os.environ[m["variable_cle"]])


def client_langfuse(config: dict):
    """Client Langfuse, ou None si les variables ne sont pas renseignées (le RAG marche sans suivi)."""
    lf = config["langfuse"]
    if not all(os.environ.get(lf[v]) for v in ("variable_adresse", "variable_cle_publique", "variable_cle_secrete")):
        return None
    from langfuse import Langfuse

    return Langfuse(public_key=os.environ[lf["variable_cle_publique"]],
                    secret_key=os.environ[lf["variable_cle_secrete"]], base_url=os.environ[lf["variable_adresse"]])


def indexer(config: dict, afficher=print) -> dict:
    return etape_3_index.construire(config, client_llm(config), afficher)


class Assistant:
    def __init__(self, config: dict | None = None, k: int | None = None):
        self.config = config or charger_config()
        if k is not None:
            self.config["recherche"]["k"] = k
        self.index = etape_3_index.charger(self.config)
        self.client = client_llm(self.config)
        self.langfuse = client_langfuse(self.config)

    @property
    def k(self) -> int:
        return self.config["recherche"]["k"]

    def rechercher(self, question: str, profil: str, historique: list[dict]) -> list[dict]:
        """Étape 5 seule : les k meilleurs chunks que le profil a le droit de voir."""
        return etape_5_recherche.rechercher(self.index, self.client, self.config, question, profil, historique)

    def demander(self, question: str, profil: str = "tous", historique: list[dict] | None = None) -> dict:
        """Étapes 5 et 6 : rend la réponse, les extraits donnés au modèle, ceux qu'il cite, les temps et les tokens."""
        historique = historique or []
        debut = time.perf_counter()
        trace = (self.langfuse.start_as_current_observation(name="rag", input={
            "question": question, "profil": profil, "historique": historique}) if self.langfuse else nullcontext())
        with trace as span:
            trouves = self.rechercher(question, profil, historique)
            duree_recherche = round((time.perf_counter() - debut) * 1000)
            contexte = [t["chunk"] for t in trouves]
            if span:
                with self.langfuse.start_as_current_observation(
                        name="recherche", as_type="retriever", input=question,
                        output=[{"chunk_id": t["chunk"]["chunk_id"], "rang": t["rang"], "score": t["score"]}
                                for t in trouves]):
                    pass
            reponse, tokens = etape_6_generation.generer(self.client, self.config, question, historique, contexte,
                                                          self.langfuse)
            cites = [contexte[n - 1] for n in etape_6_generation.citations(reponse, len(contexte))]
            if span:
                span.update(output={"reponse": reponse, "chunks_cites": [c["chunk_id"] for c in cites]})
            trace_id = self.langfuse.get_current_trace_id() if span else None
        return {"reponse": reponse, "abstention": etape_6_generation.est_abstention(reponse),
                "recherche": trouves, "contexte": contexte, "cites": cites, "duree_recherche_ms": duree_recherche,
                "duree_ms": round((time.perf_counter() - debut) * 1000), "tokens": tokens, "trace_id": trace_id}
