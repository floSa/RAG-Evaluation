"""Niveau 3 — Réponse (document 3, section 8).

- Le juge du kit (evaluation/documentation/reference/prompt_du_juge.md) : exactitude, complétude des listes.
- Ragas : fidélité (Faithfulness) ; synthèse (RubricsScoreWithReference, grille de JUGE.md).
- Le script : abstention correcte et à tort, citations, valeurs et calculs, erreurs graves.
- Le croisement recherche × réponse, qui dit où chercher la cause (document 3, section 8).
- La file de relecture du métier : réponses fausses ou partielles, gravité forte, 10 au hasard, désaccords.
"""

import asyncio
import random
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from kit.etape_0b_branchement import contrat
from kit.etape_2_evaluation_recherche.scores import liens_par_passage
from kit.etape_3_evaluation_reponse import juge
from kit.etape_5_resultats.publication import Evaluation, Ligne

GRILLE_SYNTHESE = {  # evaluation/documentation/reference/prompt_du_juge.md, « Grille de synthèse »
    "score1_description": "la réponse ne traite pas la question, ou n'est appuyée sur aucune source",
    "score2_description": "moins de la moitié des thèmes attendus, ou une erreur importante",
    "score3_description": "la moitié des thèmes attendus au moins, sans erreur importante",
    "score4_description": "presque tous les thèmes attendus, appuyés par les sources",
    "score5_description": "tous les thèmes attendus, exacts, chacun appuyé par une source citée",
}
NOMBRE = re.compile(r"(?<![\w.,])(\d{1,3}(?:[   ]\d{3})+|\d+)(?:[.,](\d+))?")


# --- Valeurs et calculs (script) --------------------------------------------------------------

def simplifier(texte: str) -> str:
    return unicodedata.normalize("NFKD", texte.lower()).encode("ascii", "ignore").decode() if texte else ""


def nombres(texte: str) -> list[tuple[float, str]]:
    """Les nombres d'un texte (« 1 384 », « 2,3 »), chacun avec les quelques caractères qui le suivent."""
    trouves = []
    for m in NOMBRE.finditer(texte):
        entier = re.sub(r"[   ]", "", m[1])
        trouves.append((float(f"{entier}.{m[2]}" if m[2] else entier), texte[m.end():m.end() + 15]))
    return trouves


def unite_presente(unite: str, suite: str) -> bool:
    """L'unité suit le nombre ; « min » vaut « minutes », « € » vaut « euros »."""
    u, s = simplifier(unite).strip(), simplifier(suite).strip()
    if not u:
        return True
    equivalences = {"€": ["€", "euro"], "%": ["%", "pour"], "ω": ["ω", "ohm"]}
    formes = equivalences.get(unite.strip().lower(), [u, u[:3]])
    return any(s.startswith(simplifier(f) or f) for f in formes) or s.startswith(unite.strip().lower())


def valeur_trouvee(point: dict, reponse: str) -> bool:
    """Le script compare chaque valeur de la réponse à la valeur attendue, avec son unité et sa tolérance."""
    tolerance = point.get("tolerance") or 0
    return any(abs(n - point["valeur"]) <= tolerance + 1e-9 and unite_presente(point.get("unite") or "", suite)
               for n, suite in nombres(reponse))


# --- Ragas ------------------------------------------------------------------------------------

def scores_ragas(config: dict, travaux: list[tuple[str, str, dict]]) -> dict[tuple[str, str], tuple[float, str]]:
    """Calcule les scores Ragas demandés : travaux = [(question_id, "fidelite" | "synthese", arguments)]."""
    if not travaux:
        return {}
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.metrics.collections import Faithfulness, RubricsScoreWithReference

    from kit.config import cle

    m, j = config["modeles"], config["modeles"]["juge"]
    extra = {"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}} if j.get("sans_reflexion") else {}
    llm = llm_factory(j["modele"], client=AsyncOpenAI(base_url=m["adresse"], api_key=cle(m["variable_cle"])),
                      temperature=j["temperature"], max_tokens=4096, **extra)
    metriques = {"fidelite": Faithfulness(llm=llm), "synthese": RubricsScoreWithReference(llm=llm,
                                                                                            rubrics=GRILLE_SYNTHESE)}
    limite = asyncio.Semaphore(4)

    async def un(qid, nom, arguments):
        async with limite:
            try:
                r = await metriques[nom].ascore(**arguments)
                return (qid, nom), (r.value, getattr(r, "reason", None) or "")
            except Exception as e:  # une erreur de Ragas ne doit pas arrêter l'évaluation : la question est relue
                return (qid, nom), (None, f"erreur Ragas : {e}"[:300])

    async def tous():
        return dict(await asyncio.gather(*(un(*t) for t in travaux)))

    return asyncio.run(tous())


# --- Le niveau 3 ------------------------------------------------------------------------------

def evaluer(ev: Evaluation, liens: list[dict], graine: int = 0) -> tuple[list[Ligne], list[dict], list[dict]]:
    """Rend les lignes de scores, le croisement recherche × réponse, et la file de relecture."""
    config = ev.config
    seuil_non_fidele = config["reponse"]["seuil_non_fidele"]
    par_passage = liens_par_passage(liens)
    chunks = {c["chunk_id"]: c for c in ev.fichier_rag("chunks.jsonl")}
    reponses = {r["question_id"]: r for r in ev.fichier_rag("reponses.jsonl")}
    recherches = {r["question_id"]: r for r in ev.fichier_rag("recherches.jsonl")}

    def bons_et_pieges(qid):
        ps = [p for p in ev.corpus["passages"] if p["question_id"] == qid]
        bons = set().union(*[par_passage.get(p["passage_id"], set()) for p in ps if p["repond"] != "piege"])
        pieges = set().union(*[par_passage.get(p["passage_id"], set()) for p in ps if p["repond"] == "piege"])
        return bons, pieges - bons

    # 1. le juge, sur les questions « oui » où le RAG ne s'est pas abstenu
    a_juger = [qid for qid, q in ev.questions.items()
               if q["reponse_dans_documents"] == "oui" and not reponses[qid]["abstention"]]
    llm = juge.client(config)
    with ThreadPoolExecutor(4) as pool:
        jugements = dict(zip(a_juger, pool.map(lambda qid: juge.juger(config, llm, ev.questions[qid],
                                                                      reponses[qid]["reponse"]), a_juger)))

    # 2. Ragas : fidélité de toute réponse donnée ; synthèse des questions de type synthèse
    travaux = []
    for qid, r in reponses.items():
        if not r["abstention"]:
            contexte = [chunks[c]["texte"] for c in r["chunks_contexte"] if c in chunks]
            travaux.append((qid, "fidelite", {"user_input": ev.questions[qid]["question"], "response": r["reponse"],
                                              "retrieved_contexts": contexte}))
            q = ev.questions[qid]
            if q["type_reponse"] == "synthese":
                travaux.append((qid, "synthese", {"user_input": q["question"], "response": r["reponse"],
                                                  "retrieved_contexts": contexte,
                                                  "reference": q["reponse_attendue"]}))
    ragas = scores_ragas(config, travaux)

    lignes, croisement, relecture = [], [], {}
    for qid, q in ev.questions.items():
        r = reponses[qid]
        a = ev.attributs_question(qid)
        bons, pieges = bons_et_pieges(qid)
        abstention = r["abstention"]
        fidelite, raison_fid = ragas.get((qid, "fidelite"), (None, None))
        non_fidele = fidelite is not None and fidelite < seuil_non_fidele
        if fidelite is not None:
            lignes.append(Ligne("n3_fidelite", float(fidelite), qid, attributs=a,
                                detail=(raison_fid or None) if non_fidele else None))
        elif not abstention:
            relecture[qid] = raison_fid or "fidélité non calculée"
        j = jugements.get(qid)
        verdict = j and j["verdict"]

        if q["reponse_dans_documents"] == "oui":
            if j:
                if verdict is None or j.get("relecture"):
                    relecture[qid] = j["relecture"]
                if verdict:
                    lignes.append(Ligne("n3_exactitude", juge.VALEUR_VERDICT[verdict], qid, verdict=verdict,
                                        detail=j["justification"], attributs=a))
                    if q["type_reponse"] == "liste":
                        lignes.append(Ligne("n3_completude_listes", j["statuts"].count("present") / len(j["statuts"]),
                                            qid, attributs=a))
                    if q.get("question_precedente"):
                        lignes.append(Ligne("n3_questions_suite", juge.VALEUR_VERDICT[verdict], qid, verdict=verdict,
                                            attributs=a))
            a_valeurs = [p for p in q.get("points_cles") or [] if p.get("valeur") is not None]
            if a_valeurs and not abstention:
                trouvees = [valeur_trouvee(p, r["reponse"]) for p in a_valeurs]
                lignes.append(Ligne("n3_valeurs", sum(trouvees) / len(trouvees), qid, attributs=a,
                                    detail="; ".join(f"{p['texte']} : {'trouvée' if t else 'absente'}"
                                                     for p, t in zip(a_valeurs, trouvees))))
            dans_contexte = bool(bons & set(r["chunks_contexte"]))
            lignes.append(Ligne("n3_abstention_a_tort", float(abstention and dans_contexte), qid, attributs=a,
                                detail="abstention alors que le bon chunk était dans le contexte"
                                if abstention and dans_contexte else None))
            if not abstention:
                interdits = [c for c in r["chunks_cites"] if c in chunks and not contrat.autorise(
                    ev.documents.get(chunks[c]["reference_source"], {}).get("droits_acces", "tous"), q["profil"])]
                bon_cite = bool(bons & set(r["chunks_cites"]))
                piege_cite = sorted(pieges & set(r["chunks_cites"]))
                ok = bon_cite and not piege_cite and not interdits
                lignes.append(Ligne("n3_citations", float(ok), qid, attributs=a, detail=None if ok else
                                    "aucun chunk cité n'est lié à un passage" if not bon_cite else
                                    f"cite un piège ({', '.join(piege_cite)})" if piege_cite else
                                    f"cite un document interdit ({', '.join(interdits)})"))
            # croisement recherche × réponse (document 3, section 8)
            retrouves = {x["chunk_id"] for x in recherches[qid]["resultats"]}
            trouve = bool(bons & retrouves)
            issue = "abstention" if abstention else verdict or "non notée"
            croisement.append({"question_id": qid, "bon_chunk_retrouve": trouve, "reponse": issue,
                               "diagnostic": diagnostic(trouve, issue, bool(bons))})
        else:
            lignes.append(Ligne("n3_abstention_correcte", float(abstention), qid, attributs=a,
                                detail=None if abstention else "le RAG a répondu au lieu de s'abstenir"))

        if q["type_reponse"] == "synthese" and (qid, "synthese") in ragas:
            note, raison = ragas[(qid, "synthese")]
            if note is not None:
                lignes.append(Ligne("n3_synthese", float(note) / 5, qid, attributs=a, detail=f"note {note}/5"))

        if q["gravite"] == "forte":  # erreur grave : fausse, non fidèle, ou réponse donnée au lieu de s'abstenir
            causes = []
            if verdict == "fausse":
                causes.append("réponse fausse")
            if non_fidele:
                causes.append(f"non fidèle (fidélité {fidelite:.2f})")
            if q["reponse_dans_documents"] != "oui" and not abstention:
                causes.append("réponse donnée au lieu de s'abstenir")
            lignes.append(Ligne("n3_erreurs_graves", float(bool(causes)), qid, attributs=a,
                                detail=", ".join(causes) or None))
            relecture.setdefault(qid, "gravité forte")
        if verdict in ("fausse", "partielle"):
            relecture.setdefault(qid, f"réponse {verdict}")

    lignes += variantes(ev, jugements, reponses)
    autres = [qid for qid in ev.questions if qid not in relecture and not ev.reservee(qid)]
    for qid in random.Random(graine).sample(autres, min(10, len(autres))):
        relecture[qid] = "tirée au hasard"
    file = [{"question_id": qid, "motif": motif} for qid, motif in sorted(relecture.items())]
    return lignes, croisement, file


def diagnostic(trouve: bool, issue: str, rattache: bool) -> str:
    if issue == "juste":
        return "ok" if trouve else "juste sans le bon chunk : connaissance du modèle, ou passage manquant au corpus"
    if trouve:
        return "génération : le bon chunk était retrouvé" + (" (abstention à tort)" if issue == "abstention" else "")
    return "recherche : le bon chunk n'est pas retrouvé" if rattache else "ingestion : aucun passage rattaché à l'index"


def variantes(ev: Evaluation, jugements: dict, reponses: dict) -> list[Ligne]:
    """Groupes de variantes dont les issues diffèrent (recommandé) : une ligne par groupe."""
    groupes: dict[str, list[str]] = {}
    for qid, q in ev.questions.items():
        racine = qid
        while ev.questions[racine].get("variante_de"):
            racine = ev.questions[racine]["variante_de"]
        groupes.setdefault(racine, []).append(qid)
    lignes = []
    for racine, membres in groupes.items():
        if len(membres) < 2:
            continue
        issues = {m: "abstention" if reponses[m]["abstention"] else (jugements.get(m) or {}).get("verdict")
                  for m in membres}
        differe = len(set(issues.values())) > 1
        lignes.append(Ligne("n3_variantes", float(differe), racine, attributs=ev.attributs_question(racine),
                            detail=", ".join(f"{m} : {i}" for m, i in sorted(issues.items()))))
    return lignes
