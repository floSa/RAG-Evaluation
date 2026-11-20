"""Le LLM juge du kit (evaluation/methode/JUGE.md) : exactitude des réponses, point clé par point clé.

Le prompt est lu tel quel dans evaluation/methode/JUGE.md (le même pour tous les projets). La sortie JSON est validée ;
une sortie invalide est redemandée une fois, puis la question part en relecture. Le kit recalcule le verdict
à partir des statuts ; en cas d'écart avec le verdict du juge, il garde le sien et envoie la question en relecture.
"""

import json
import re
from pathlib import Path

from openai import OpenAI

from kit.config import cle

JUGE_MD = Path(__file__).resolve().parents[2] / "methode" / "JUGE.md"
STATUTS = {"present", "absent", "contredit"}
VERDICTS = {"juste", "partielle", "fausse"}
VALEUR_VERDICT = {"juste": 1.0, "partielle": 0.5, "fausse": 0.0}


def prompt_exactitude() -> str:
    """Le bloc de code qui suit « ## Prompt d'exactitude » dans evaluation/methode/JUGE.md."""
    texte = JUGE_MD.read_text(encoding="utf-8")
    section = texte.split("## Prompt d'exactitude", 1)[1]
    return re.search(r"```text\n(.*?)\n```", section, re.S)[1]


def client(config: dict) -> OpenAI:
    m = config["modeles"]
    return OpenAI(base_url=m["adresse"], api_key=cle(m["variable_cle"]))


def appeler(config: dict, llm: OpenAI, messages: list[dict]) -> str:
    """Un appel au modèle juge, avec les réglages de kit.yaml (température 0, sans réflexion si demandé)."""
    j = config["modeles"]["juge"]
    extra = {"chat_template_kwargs": {"enable_thinking": False}} if j.get("sans_reflexion") else None
    r = llm.chat.completions.create(model=j["modele"], messages=messages, temperature=j["temperature"],
                                    max_tokens=j["max_tokens"], response_format={"type": "json_object"},
                                    extra_body=extra)
    return r.choices[0].message.content or ""


def remplir(question: str, reponse_attendue: str, points_cles: list[dict], reponse_rag: str) -> str:
    numerotes = "\n".join(f"{n}. {p['texte']}" for n, p in enumerate(points_cles, start=1))
    valeurs = {"{question}": question, "{reponse_attendue}": reponse_attendue,
               "{points_cles_numerotes}": numerotes, "{reponse_rag}": reponse_rag}
    texte = prompt_exactitude()
    for cle_, valeur in valeurs.items():  # pas de str.format : le prompt contient des accolades JSON
        texte = texte.replace(cle_, valeur)
    return texte


def valider(sortie: str, nb_points: int) -> tuple[dict | None, str | None]:
    """Contrôle la sortie du juge ; rend (objet, None) ou (None, ce qui ne va pas)."""
    try:
        objet = json.loads(re.sub(r"^```(json)?|```$", "", sortie.strip()).strip())
    except json.JSONDecodeError as e:
        return None, f"JSON illisible ({e.msg})"
    if not isinstance(objet, dict):
        return None, "la sortie n'est pas un objet JSON"
    points = objet.get("points_cles")
    if not isinstance(points, list) or sorted(p.get("numero") for p in points if isinstance(p, dict)) \
            != list(range(1, nb_points + 1)):
        return None, f"« points_cles » doit donner un statut pour chacun des points 1 à {nb_points}"
    if any(p.get("statut") not in STATUTS for p in points):
        return None, "un statut n'est pas present, absent ou contredit"
    if not isinstance(objet.get("contradictions", []), list):
        return None, "« contradictions » doit être une liste"
    if objet.get("verdict") not in VERDICTS:
        return None, "« verdict » doit valoir juste, partielle ou fausse"
    return objet, None


def verdict_du_kit(statuts: list[str], contradictions: list) -> str:
    """Le verdict recalculé par le kit (JUGE.md, « Verdict »)."""
    if statuts and all(s == "present" for s in statuts) and not contradictions:
        return "juste"
    if "present" in statuts and "contredit" not in statuts and not contradictions:
        return "partielle"
    return "fausse"


def juger(config: dict, llm: OpenAI, question: dict, reponse_rag: str) -> dict:
    """Note une réponse ; rend verdict, statuts, justification, et s'il faut la relire (motif)."""
    points = question.get("points_cles") or []
    messages = [{"role": "user", "content": remplir(question["question"], question["reponse_attendue"], points,
                                                    reponse_rag)}]
    objet, erreur = None, None
    for _ in range(2):  # une sortie invalide est redemandée une fois
        sortie = appeler(config, llm, messages)
        objet, erreur = valider(sortie, len(points))
        if objet:
            break
        messages += [{"role": "assistant", "content": sortie},
                     {"role": "user", "content": f"Ta sortie est invalide : {erreur}. Réponds uniquement par le JSON "
                                                 f"demandé."}]
    if objet is None:
        return {"verdict": None, "relecture": f"sortie du juge invalide deux fois : {erreur}"}
    points_juges = sorted(objet["points_cles"], key=lambda p: p["numero"])
    statuts = [p["statut"] for p in points_juges]
    verdict = verdict_du_kit(statuts, objet.get("contradictions", []))
    justification = " ; ".join(f"{p['numero']}. {p['statut']} : {p.get('justification', '')}" for p in points_juges)
    if objet.get("contradictions"):
        justification += " ; contradictions : " + " ; ".join(map(str, objet["contradictions"]))
    return {"verdict": verdict, "verdict_juge": objet["verdict"], "statuts": statuts, "justification": justification,
            "relecture": None if verdict == objet["verdict"]
            else f"verdict du juge « {objet['verdict']} » recalculé en « {verdict} »"}
