"""Le RAG de démonstration : indexation, recherche hybride, génération citée. Volontairement minimal.

- Index : les chunks et leurs vecteurs en mémoire (un fichier .jsonl et un .npy), pas de base vectorielle.
- Recherche : sens (embeddings) et mots (BM25), fusionnés par rang réciproque ; filtre des droits avant le classement.
- Génération : un seul prompt, citations [n] obligatoires, phrase d'abstention fixe.
- Suivi : une trace Langfuse par question (recherche et génération).
Le RAG ne connaît que des fichiers : les PDF, le catalogue documents.jsonl, et sa configuration.
"""

import hashlib
import json
import os
import re
import time
import uuid
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import yaml
from dotenv import load_dotenv
from openai import OpenAI
from rank_bm25 import BM25Okapi

from rag_demo import extraction

CONFIG = Path(__file__).resolve().parent / "config.yaml"
VERSION_DECOUPAGE = "sections-1"
VERSION_PROMPT = "1.0"
ABSTENTION = "Je ne trouve pas cette information dans les documents."

SYSTEME = f"""Tu es l'assistant documentaire du service Maintenance électrique.
Tu réponds uniquement à partir des extraits de documents fournis, jamais de tes connaissances.
Chaque phrase de ta réponse cite l'extrait qui l'appuie par son numéro entre crochets, par exemple [2].
Si les extraits ne permettent pas de répondre, réponds exactement : « {ABSTENTION} »
Réponds en français, de façon concise et précise (valeurs, unités, références)."""


# --- Configuration --------------------------------------------------------------------------

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


def catalogue(config: dict) -> list[dict]:
    """Le catalogue des documents : documents.jsonl du dernier corpus exporté par le kit."""
    versions = sorted(Path(config["catalogue"]).glob("*/documents.jsonl"))
    if not versions:
        raise FileNotFoundError(f"Aucun documents.jsonl dans {config['catalogue']} : importer d'abord le corpus "
                                f"(kit importer).")
    with versions[-1].open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def empreinte(objet) -> str:
    return hashlib.sha256(json.dumps(objet, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]


# --- Indexation -----------------------------------------------------------------------------

def mots(texte: str) -> list[str]:
    return re.findall(r"\w+", texte.lower())


def embeddings(client: OpenAI, modele: str, textes: list[str]) -> np.ndarray:
    vecteurs = []
    for i in range(0, len(textes), 32):
        r = client.embeddings.create(model=modele, input=textes[i:i + 32])
        vecteurs += [d.embedding for d in r.data]
    v = np.array(vecteurs, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def indexer(config: dict, afficher=print) -> dict:
    """Extrait, découpe et vectorise tous les documents du catalogue ; écrit l'index dans le dossier de travail."""
    travail = Path(config["travail"])
    chunks, pages = [], []
    for doc in catalogue(config):
        afficher(f"  {doc['reference_source']}")
        extrait = extraction.extraire(doc, Path(config["documents"]), travail / "extraction",
                                      config["extraction"]["docling"])
        chunks += extraction.chunks_du_document(doc, extrait, config["decoupage"]["taille_max"])
        pages += extraction.pages_extraites(doc, extrait)
    version_index = f"{VERSION_DECOUPAGE}-{config['modeles']['embeddings']['modele']}-{empreinte(chunks)}"
    for c in chunks:
        c["chunk_id"] = f"{c['reference_source']}#{c['page']}#{c['ordre']}"
        c["type_objet"] = "chunk"
        c["version_index"] = version_index
    vecteurs = embeddings(client_llm(config), config["modeles"]["embeddings"]["modele"], [c["texte"] for c in chunks])
    dossier = travail / "index"
    dossier.mkdir(parents=True, exist_ok=True)
    np.save(dossier / "vecteurs.npy", vecteurs)
    for nom, objets in (("chunks.jsonl", chunks), ("pages.jsonl", pages)):
        with (dossier / nom).open("w", encoding="utf-8") as f:
            f.writelines(json.dumps(o, ensure_ascii=False) + "\n" for o in objets)
    return {"chunks": len(chunks), "pages": len(pages), "version_index": version_index}


# --- Le RAG ---------------------------------------------------------------------------------

class Rag:
    def __init__(self, config: dict | None = None, k: int | None = None):
        self.config = config or charger_config()
        if k is not None:
            self.config["recherche"]["k"] = k
        dossier = Path(self.config["travail"]) / "index"
        if not (dossier / "chunks.jsonl").exists():
            raise FileNotFoundError("Index absent : lancer d'abord « rag-demo indexer ».")
        with (dossier / "chunks.jsonl").open(encoding="utf-8") as f:
            self.chunks = [json.loads(l) for l in f]
        with (dossier / "pages.jsonl").open(encoding="utf-8") as f:
            self.pages = [json.loads(l) for l in f]
        self.vecteurs = np.load(dossier / "vecteurs.npy")
        self.bm25 = BM25Okapi([mots(c["texte"]) for c in self.chunks])
        self.client = client_llm(self.config)
        self.langfuse = client_langfuse(self.config)

    @property
    def k(self) -> int:
        return self.config["recherche"]["k"]

    def decrire(self) -> dict:
        m = self.config["modeles"]
        versions = {"index": self.chunks[0]["version_index"], "decoupage": VERSION_DECOUPAGE,
                    "embedding": m["embeddings"]["modele"], "generation": m["generation"]["modele"],
                    "prompt": VERSION_PROMPT, "reranker": "aucun"}
        return {"contrat": "1.0", "nom": self.config["nom"],
                "version_rag": f"{self.config['nom']}-k{self.k}-{empreinte([versions, m['generation'], SYSTEME])}",
                "type_rag": self.config["type_rag"], "date": time.strftime("%Y-%m-%d"), "k": self.k,
                "versions": versions, "filtre_droits": True}

    def rechercher(self, question: str, profil: str, historique: list[dict]) -> list[dict]:
        """Les k chunks les plus utiles, parmi ceux que le profil a le droit de voir."""
        requete = " ".join([h["question"] for h in historique[-1:]] + [question])  # question de suite : avec la précédente
        autorises = np.array([c["droits_acces"] in ("tous", profil) for c in self.chunks])
        n = self.config["recherche"]["candidats"]
        sens = self.vecteurs @ embeddings(self.client, self.config["modeles"]["embeddings"]["modele"], [requete])[0]
        mots_cles = self.bm25.get_scores(mots(requete))
        fusion = {}
        for scores in (sens, mots_cles):
            scores = np.where(autorises, scores, -np.inf)  # filtre des droits pendant la recherche
            for rang, i in enumerate(np.argsort(-scores)[:n]):
                if autorises[i]:
                    fusion[i] = fusion.get(i, 0) + 1 / (60 + rang + 1)
        meilleurs = sorted(fusion, key=fusion.get, reverse=True)[:self.k]
        return [{"chunk_id": self.chunks[i]["chunk_id"], "rang": r, "score": round(fusion[i], 6)}
                for r, i in enumerate(meilleurs, start=1)]

    def repondre(self, question: str, profil: str, historique: list[dict]) -> dict:
        """Recherche puis génération ; rend un objet reponses.jsonl (sans question_id)."""
        debut = time.perf_counter()
        suivi = (self.langfuse.start_as_current_observation(name="rag-demo", input={
            "question": question, "profil": profil, "historique": historique}) if self.langfuse else nullcontext())
        with suivi as span:
            resultats = self.rechercher(question, profil, historique)
            self.derniere_recherche = {"resultats": resultats,
                                       "duree_ms": round((time.perf_counter() - debut) * 1000)}
            par_id = {c["chunk_id"]: c for c in self.chunks}
            contexte = [par_id[r["chunk_id"]] for r in resultats]
            if span:
                with self.langfuse.start_as_current_observation(name="recherche", as_type="retriever",
                                                                input=question, output=resultats):
                    pass
            reponse, usage = self.generer(question, historique, contexte)
            # citations « [2] », « [1, 3] » ou « [1][3] »
            cites = sorted({int(n) for groupe in re.findall(r"\[([\d,;\s]+)\]", reponse)
                            for n in re.findall(r"\d+", groupe) if 1 <= int(n) <= len(contexte)})
            m = self.config["modeles"]["generation"]
            cout = (usage[0] * m["prix_entree_eur_par_million"] + usage[1] * m["prix_sortie_eur_par_million"]) / 1e6
            objet = {"profil": profil, "reponse": reponse,
                     "abstention": ABSTENTION.lower().rstrip(".") in reponse.lower(),
                     "chunks_cites": [contexte[n - 1]["chunk_id"] for n in cites],
                     "chunks_contexte": [c["chunk_id"] for c in contexte],
                     "duree_ms": round((time.perf_counter() - debut) * 1000), "cout": cout,
                     "tokens_entree": usage[0], "tokens_sortie": usage[1],
                     "trace_id": self.langfuse.get_current_trace_id() if span else uuid.uuid4().hex}
            if span:
                span.update(output={"reponse": reponse, "abstention": objet["abstention"],
                                    "chunks_cites": objet["chunks_cites"]})
        return objet

    def generer(self, question: str, historique: list[dict], contexte: list[dict]) -> tuple[str, tuple[int, int]]:
        m = self.config["modeles"]["generation"]
        extraits = "\n\n".join(f"[{n}] (document {c['reference_source']}, version {c['version_document']}, "
                               f"page {c['page']})\n{c['texte']}" for n, c in enumerate(contexte, start=1))
        messages = [{"role": "system", "content": SYSTEME}]
        for h in historique:
            messages += [{"role": "user", "content": h["question"]}, {"role": "assistant", "content": h["reponse"]}]
        messages.append({"role": "user", "content": f"Extraits :\n\n{extraits}\n\nQuestion : {question}"})
        parametres = {"model": m["modele"], "temperature": m["temperature"], "max_tokens": m["max_tokens"]}
        if self.langfuse:
            with self.langfuse.start_as_current_observation(name="generation", as_type="generation", input=messages,
                                                            model=m["modele"], model_parameters=parametres) as g:
                r = self.client.chat.completions.create(messages=messages, **parametres)
                usage = (r.usage.prompt_tokens, r.usage.completion_tokens) if r.usage else (0, 0)
                g.update(output=r.choices[0].message.content, usage_details={"input": usage[0], "output": usage[1]})
        else:
            r = self.client.chat.completions.create(messages=messages, **parametres)
            usage = (r.usage.prompt_tokens, r.usage.completion_tokens) if r.usage else (0, 0)
        return (r.choices[0].message.content or "").strip(), usage
