"""Étape 5 — Recherche : trouver les k chunks les plus utiles pour répondre à la question.

- Deux recherches : par le sens (vecteurs) et par les mots (BM25).
- Avec le graphe (étape 4) : une troisième, par les entités. Les éléments du graphe des entités nommées dans la
  question (« TGBT-A », « GE-B ») sont classés, ceux qui ont le plus de relations en tête.
- Fusion par rang réciproque : un chunk bien classé par plusieurs recherches remonte en tête.
- Filtre des droits **pendant** la recherche : un chunk que le profil n'a pas le droit de voir n'est jamais classé,
  donc jamais montré au modèle.
- Question de suite : on cherche avec la question précédente et la nouvelle.
"""

import numpy as np
from openai import OpenAI

from rag.pipeline.etape_3_index import Index, embeddings, mots
from rag.pipeline.etape_4_graphe import cle


def rechercher(index: Index, client: OpenAI, config: dict, question: str, profil: str,
               historique: list[dict]) -> list[dict]:
    """Rend les k meilleurs chunks : [{"chunk": …, "rang": 1, "score": …}, …]."""
    requete = " ".join([h["question"] for h in historique[-1:]] + [question])
    autorises = np.array([c["droits_acces"] in ("tous", profil) for c in index.chunks])
    candidats, k = config["recherche"]["candidats"], config["recherche"]["k"]
    sens = index.vecteurs @ embeddings(client, config["modeles"]["embeddings"]["modele"], [requete])[0]
    mots_cles = index.bm25.get_scores(mots(requete))
    recherches = [sens, mots_cles]
    if index.graphe_ttl:
        recherches.append(par_les_entites(index, requete))
    fusion = {}
    for scores in recherches:
        scores = np.where(autorises, scores, -np.inf)  # filtre des droits pendant la recherche
        for rang, i in enumerate(np.argsort(-scores)[:candidats]):
            if autorises[i] and scores[i] > -np.inf:
                fusion[i] = fusion.get(i, 0) + 1 / (60 + rang + 1)
    meilleurs = sorted(fusion, key=fusion.get, reverse=True)[:k]
    return [{"chunk": index.chunks[i], "rang": r, "score": round(fusion[i], 6)}
            for r, i in enumerate(meilleurs, start=1)]


def par_les_entites(index: Index, requete: str) -> np.ndarray:
    """Score des éléments du graphe dont l'entité est nommée dans la question (son nombre de relations) ;
    -inf pour tout le reste, qui n'est donc pas classé par cette recherche."""
    question = f"-{cle(requete)}-"
    scores = np.full(len(index.chunks), -np.inf)
    for i, c in enumerate(index.chunks):
        if c["type_objet"] == "noeud" and f"-{cle(c['metadonnees']['entite'])}-" in question:
            scores[i] = len(c["metadonnees"]["relations"])
    return scores
