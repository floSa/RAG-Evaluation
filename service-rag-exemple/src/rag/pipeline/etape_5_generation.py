"""Étape 5 — Génération : rédiger la réponse à partir des chunks retrouvés, et seulement d'eux.

- Un seul prompt : chaque phrase cite l'extrait qui l'appuie, [1], [2]… ;
- si les extraits ne suffisent pas, le modèle répond une phrase fixe (l'abstention) au lieu d'inventer ;
- une question de suite reçoit l'échange précédent.
"""

import re

from openai import OpenAI

VERSION_PROMPT = "1.0"
ABSTENTION = "Je ne trouve pas cette information dans les documents."

SYSTEME = f"""Tu es l'assistant documentaire du service Maintenance électrique.
Tu réponds uniquement à partir des extraits de documents fournis, jamais de tes connaissances.
Chaque phrase de ta réponse cite l'extrait qui l'appuie par son numéro entre crochets, par exemple [2].
Si les extraits ne permettent pas de répondre, réponds exactement : « {ABSTENTION} »
Réponds en français, de façon concise et précise (valeurs, unités, références)."""


def messages(question: str, historique: list[dict], contexte: list[dict]) -> list[dict]:
    """Le prompt : consignes, échange précédent, extraits numérotés, question."""
    extraits = "\n\n".join(f"[{n}] (document {c['reference_source']}, version {c['version_document']}, "
                           f"page {c['page']})\n{c['texte']}" for n, c in enumerate(contexte, start=1))
    resultat = [{"role": "system", "content": SYSTEME}]
    for h in historique:
        resultat += [{"role": "user", "content": h["question"]}, {"role": "assistant", "content": h["reponse"]}]
    resultat.append({"role": "user", "content": f"Extraits :\n\n{extraits}\n\nQuestion : {question}"})
    return resultat


def generer(client: OpenAI, config: dict, question: str, historique: list[dict], contexte: list[dict],
            langfuse=None) -> tuple[str, tuple[int, int]]:
    """Rend la réponse et les tokens (entrée, sortie). Avec Langfuse, l'appel est tracé comme une génération."""
    m = config["modeles"]["generation"]
    prompt = messages(question, historique, contexte)
    parametres = {"model": m["modele"], "temperature": m["temperature"], "max_tokens": m["max_tokens"]}
    # Sans réflexion : sinon le modèle « réfléchit » avant d'écrire, cette réflexion consomme les max_tokens,
    # et la réponse revient vide ou coupée en cours de phrase.
    extra = {"chat_template_kwargs": {"enable_thinking": False}} if m.get("sans_reflexion") else None
    if langfuse:
        with langfuse.start_as_current_observation(name="generation", as_type="generation", input=prompt,
                                                   model=m["modele"], model_parameters=parametres) as g:
            r = client.chat.completions.create(messages=prompt, extra_body=extra, **parametres)
            usage = (r.usage.prompt_tokens, r.usage.completion_tokens) if r.usage else (0, 0)
            g.update(output=r.choices[0].message.content, usage_details={"input": usage[0], "output": usage[1]})
    else:
        r = client.chat.completions.create(messages=prompt, extra_body=extra, **parametres)
        usage = (r.usage.prompt_tokens, r.usage.completion_tokens) if r.usage else (0, 0)
    return (r.choices[0].message.content or "").strip(), usage


def citations(reponse: str, nombre_d_extraits: int) -> list[int]:
    """Les numéros d'extraits cités : « [2] », « [1, 3] » ou « [1][3] » ; un numéro qui n'existe pas est ignoré."""
    return sorted({int(n) for groupe in re.findall(r"\[([\d,;\s]+)\]", reponse)
                   for n in re.findall(r"\d+", groupe) if 1 <= int(n) <= nombre_d_extraits})


def est_abstention(reponse: str) -> bool:
    return ABSTENTION.lower().rstrip(".") in reponse.lower()
