"""Appeler un RAG en boîte noire : un RAG dont on n'a qu'une API compatible OpenAI (/v1/chat/completions).

C'est le cas d'un assistant tout fait, d'un portail, d'un produit du commerce : on ne peut pas lui envoyer les
documents, ni voir ce qu'il a lu ou ramené. Le kit lui pose seulement les questions du corpus, une par une, et range
ses réponses dans resultats/reponses_du_rag/<version_rag>/ : rag.json et reponses.jsonl, au format du contrat.

Ce qui en découle, dit dans le rapport : l'évaluation de l'ingestion et celle de la recherche ne sont pas faites ;
la réponse et le bout en bout le sont (réponses justes, « je ne sais pas », erreurs graves, temps, coût).
Les réglages sont dans config/kit.yaml, section boite_noire ; la clé dans .env.

Comme pour un RAG à quatre endpoints, le kit n'envoie jamais les annotations du métier ; seulement, pour une question
de suite, l'échange précédent (historique).
"""

import datetime as dt
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path

from kit import contrat


def simplifier(texte: str) -> str:
    """Minuscules, sans accents, apostrophes droites : pour reconnaître une phrase d'abstention."""
    texte = unicodedata.normalize("NFKD", (texte or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texte.replace("’", "'"))


def abstention(reponse: str, phrases: list[str]) -> bool:
    """Le RAG dit-il qu'il ne sait pas ? Une boîte noire ne le déclare pas : on le reconnaît à ses mots
    (boite_noire.phrases_abstention de config/kit.yaml), ou à une réponse vide."""
    texte = simplifier(reponse)
    return not texte.strip() or any(simplifier(p) in texte for p in phrases)


def description(reglages: dict) -> dict:
    """rag.json : le nom, et une version calculée sur l'adresse, le modèle et les réglages d'appel ; changer l'un
    d'eux donne une autre version, rangée à part."""
    appel = {c: reglages.get(c) for c in ("adresse", "modele", "temperature", "consigne_systeme", "en_tete_profil")}
    empreinte = hashlib.sha256(json.dumps(appel, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:8]
    libres = {c: v for c, v in (("modele", reglages.get("modele")), ("temperature", reglages.get("temperature")),
                                ("adresse", reglages.get("adresse"))) if v is not None}
    return {"contrat": "1.0", "nom": reglages["nom"], "version_rag": f"{reglages['nom']}-boite-noire-{empreinte}",
            "type_rag": "boite_noire", "date": dt.date.today().isoformat(),
            "filtre_droits": bool(reglages.get("en_tete_profil")), "reglages": libres}


def messages(question: dict, par_id: dict, consigne: str | None) -> list[dict]:
    """La conversation envoyée : la consigne éventuelle, l'historique d'une question de suite, puis la question."""
    m = [{"role": "system", "content": consigne}] if consigne else []
    for echange in contrat.historique(question, par_id):
        m += [{"role": "user", "content": echange["question"]}, {"role": "assistant", "content": echange["reponse"]}]
    return m + [{"role": "user", "content": question["question"]}]


def appeler(reglages: dict, cle_api: str, dossier_corpus: Path, dossier_resultats: Path, afficher=print,
            client=None) -> Path:
    """Pose toutes les questions du corpus à l'API ; rend le dossier reponses_du_rag/<version_rag>/ écrit."""
    from openai import OpenAI

    client = client or OpenAI(base_url=reglages["adresse"], api_key=cle_api, timeout=600)
    corpus = contrat.charger_corpus(dossier_corpus)
    rag = description(reglages)
    dossier = Path(dossier_resultats) / "reponses_du_rag" / rag["version_rag"]
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "rag.json").write_text(json.dumps(rag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    prix_entree = (reglages.get("prix_entree_eur_par_million") or 0) / 1e6
    prix_sortie = (reglages.get("prix_sortie_eur_par_million") or 0) / 1e6
    par_id = {q["question_id"]: q for q in corpus["questions"]}
    afficher(f"RAG en boîte noire {rag['version_rag']} ({reglages['adresse']}, modèle {reglages['modele']}) : "
             f"{len(corpus['questions'])} questions…")
    reponses = []
    for q in corpus["questions"]:                      # toutes, y compris les réservées à la décision
        en_tetes = {reglages["en_tete_profil"]: q["profil"]} if reglages.get("en_tete_profil") else None
        debut = time.monotonic()
        try:
            r = client.chat.completions.create(model=reglages["modele"], temperature=reglages.get("temperature", 0),
                                               messages=messages(q, par_id, reglages.get("consigne_systeme")),
                                               extra_headers=en_tetes)
        except Exception as e:
            if type(e).__name__ in ("APIConnectionError", "APITimeoutError"):
                raise RuntimeError(f"L'API du RAG ne répond pas à {reglages['adresse']} : est-elle lancée, et l'adresse "
                                   f"est-elle juste (section boite_noire de config/kit.yaml) ?") from None
            raise RuntimeError(f"L'API du RAG a refusé la question {q['question_id']} : {e}") from None
        duree = int((time.monotonic() - debut) * 1000)
        texte = r.choices[0].message.content or ""
        usage = getattr(r, "usage", None)
        entree, sortie = (usage.prompt_tokens, usage.completion_tokens) if usage else (None, None)
        reponses.append({"question_id": q["question_id"], "profil": q["profil"], "reponse": texte,
                         "abstention": abstention(texte, reglages.get("phrases_abstention") or []),
                         "chunks_cites": [], "chunks_contexte": [], "duree_ms": duree,
                         "trace_id": getattr(r, "id", None) or f"{rag['version_rag']}-{q['question_id']}",
                         "cout": round((entree or 0) * prix_entree + (sortie or 0) * prix_sortie, 6) if usage else None,
                         "tokens_entree": entree, "tokens_sortie": sortie})
        afficher(f"  {q['question_id']} : {duree} ms{' (abstention)' if reponses[-1]['abstention'] else ''}")
    contrat.ecrire_jsonl(dossier / "reponses.jsonl", reponses)
    return dossier
