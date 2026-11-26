"""Publication des résultats d'une évaluation : base, fichiers de resultats/evaluations/<evaluation_id>/, Langfuse.

Chaque niveau produit des « lignes » : un score pour un objet (une question, un passage, un document, un chunk,
une page OCR). La publication les range dans la base, puis recalcule depuis la base tous les scores globaux,
leur marge et leur ventilation. On peut donc lancer les niveaux un par un, dans l'ordre.

Le service ne décide pas : il donne les scores, et le métier tranche (DECISIONS.md, décision 14).

Questions réservées (DECISIONS.md, décision 5) : les scores de réglage (scores, CSV, Langfuse, rapport) portent sur les
questions non réservées ; le bloc `scores_cles` de scores.json donne les scores clés, à présenter au métier, calculés
sur les questions réservées, sans détail ; leur détail question par question reste dans la base.
"""

import csv
import datetime as dt
import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import kit
from kit import base
from kit import contrat

# Pour chaque score : comment on l'agrège, et si la marge ± 1,96 √(p(1−p)/n) s'applique (score entre 0 et 1).
# moyenne : moyenne des lignes ; ponderee : Σ valeur × poids ÷ Σ poids ; somme : un nombre de cas ;
# mediane, p95 : sur les durées.
SCORES = {
    "n1_documents_indexes": ("moyenne", True), "n1_metadonnees_completes": ("moyenne", True),
    "n1_passages_rattaches": ("moyenne", True), "n1_passages_coupes": ("moyenne", True),
    "n1_erreur_caracteres": ("ponderee", False), "n1_erreur_mots": ("ponderee", False),
    "n1_graphe_violations": ("somme", False), "n1_graphe_justesse": ("moyenne", True),
    "n2_reussite_k": ("moyenne", True), "n2_rappel_k": ("moyenne", True), "n2_rang_premier": ("moyenne", True),
    "n2_fuite_droits": ("somme", False), "n2_reussite_1": ("moyenne", True), "n2_reussite_3": ("moyenne", True),
    "n2_reussite_5": ("moyenne", True), "n2_reussite_10": ("moyenne", True), "n2_perimes_pieges": ("moyenne", True),
    "n2_reussite_avant_reranking": ("moyenne", True), "n2_ndcg_k": ("moyenne", True),
    "n3_exactitude": ("moyenne", True), "n3_completude_listes": ("moyenne", True), "n3_valeurs": ("moyenne", True),
    "n3_abstention_correcte": ("moyenne", True), "n3_abstention_a_tort": ("moyenne", True),
    "n3_fidelite": ("moyenne", True), "n3_citations": ("moyenne", True), "n3_erreurs_graves": ("somme", False),
    "n3_synthese": ("moyenne", False), "n3_second_avis": ("moyenne", True), "n3_questions_suite": ("moyenne", True),
    "n3_variantes": ("moyenne", True),
    "n4_score_pondere": ("ponderee", True), "n4_erreurs_graves": ("somme", False),
    "n4_temps_median": ("mediane", False), "n4_temps_p95": ("p95", False), "n4_cout_moyen": ("moyenne", False),
}
# Les scores clés, à présenter au métier : en tête du rapport, calculés sur les questions réservées.
SCORES_CLES = ["n1_documents_indexes", "n1_metadonnees_completes", "n1_passages_rattaches", "n1_erreur_caracteres",
               "n2_reussite_k", "n2_fuite_droits", "n3_exactitude", "n3_abstention_correcte", "n3_fidelite",
               "n3_erreurs_graves", "n4_score_pondere", "n4_temps_median", "n4_temps_p95", "n4_cout_moyen"]
# Une seule fuite de droits ou erreur grave compte : ces scores se calculent sur toutes les questions.
TOUTES_LES_QUESTIONS = {"n2_fuite_droits", "n3_erreurs_graves", "n4_erreurs_graves"}


@dataclass
class Ligne:
    """Un score pour un objet évalué ; `question_id` vide pour un document, un chunk ou une page."""
    score: str
    valeur: float | None
    question_id: str | None = None
    objet: str | None = None
    verdict: str | None = None
    detail: str | None = None
    poids: float | None = None
    attributs: dict = field(default_factory=dict)
    reservee: bool = False

    @property
    def niveau(self) -> int:
        return int(self.score[1])


# --- Le contexte d'une évaluation -----------------------------------------------------------

class Evaluation:
    """Une évaluation = un corpus × une version du RAG. Identifiant stable : relancer un niveau le remplace."""

    def __init__(self, config: dict, dossier_corpus: Path, dossier_rag: Path):
        self.config = config
        self.corpus = contrat.charger_corpus(dossier_corpus)
        self.dossier_corpus, self.dossier_rag = Path(dossier_corpus), Path(dossier_rag)
        self.rag = contrat.lire_json(self.dossier_rag / "rag.json")
        # un RAG en boîte noire n'a rendu que ses réponses : ni ingestion ni recherche à évaluer
        self.boite_noire = self.rag.get("type_rag") == "boite_noire"
        self.version_corpus = self.corpus["corpus"]["version_corpus"]
        self.evaluation_id = f"{self.version_corpus}_{self.rag['version_rag']}"
        self.dossier = Path(config["chemins"]["resultats"]) / "evaluations" / self.evaluation_id
        self.fichiers = self.dossier / "fichiers_techniques"   # tout, sauf RAPPORT.md
        self.questions = {q["question_id"]: q for q in self.corpus["questions"]}
        self.documents = {d["reference_source"]: d for d in self.corpus["documents"]}
        self.passages = {p["passage_id"]: p for p in self.corpus["passages"]}

    def fichier_rag(self, nom: str) -> list[dict]:
        chemin = self.dossier_rag / nom
        return contrat.lire_jsonl(chemin) if chemin.exists() else []

    def attributs_question(self, question_id: str) -> dict:
        """Axes de ventilation d'une question (document 3, section 11)."""
        q = self.questions[question_id]
        types = sorted({self.documents[p["reference_source"]]["type_document"] for p in self.corpus["passages"]
                        if p["question_id"] == question_id and p["repond"] != "piege"})
        return {"type_document": types or ["aucun"], "difficulte": q["difficulte"], "type_reponse": q["type_reponse"],
                "profil": q["profil"], **(q.get("colonnes_libres") or {})}

    def attributs_passage(self, passage_id: int) -> dict:
        p = self.passages[passage_id]
        return {"type_document": self.documents[p["reference_source"]]["type_document"],
                "type_element": p["type_element"]}

    def reservee(self, question_id: str | None) -> bool:
        return bool(question_id) and self.questions[question_id]["reservee_decision"]

    def description(self) -> dict:
        juge = self.config["modeles"]["juge"]
        return {"evaluation_id": self.evaluation_id, "date": dt.datetime.now().isoformat(timespec="seconds"),
                "version_corpus": self.version_corpus, "version_kit": kit.__version__, "rag": self.rag,
                "juge": {"modele": juge["modele"], "version_prompt": juge["version_prompt"]}}


# --- Agrégation -----------------------------------------------------------------------------

def agreger(score: str, lignes: list) -> tuple[float | None, int]:
    """Valeur globale d'un score et nombre d'objets pris en compte."""
    valeurs = [l.valeur for l in lignes if l.valeur is not None]
    if not valeurs:
        return (0 if SCORES[score][0] == "somme" else None), 0
    mode = SCORES[score][0]
    if mode == "moyenne":
        return sum(valeurs) / len(valeurs), len(valeurs)
    if mode == "somme":
        return sum(valeurs), len(valeurs)
    if mode == "ponderee":
        poids = sum(l.poids or 0 for l in lignes if l.valeur is not None)
        return (sum(l.valeur * (l.poids or 0) for l in lignes if l.valeur is not None) / poids if poids else None,
                len(valeurs))
    if mode == "mediane":
        return statistics.median(valeurs), len(valeurs)
    if mode == "p95":  # le temps sous lequel répondent 95 % des questions
        triees = sorted(valeurs)
        return triees[min(len(triees) - 1, math.ceil(0.95 * len(triees)) - 1)], len(valeurs)
    raise ValueError(mode)


def marge(score: str, valeur: float | None, n: int) -> float | None:
    """± 1,96 × √(p(1−p)/n) (document 3, section 9) ; seulement pour un score entre 0 et 1."""
    if valeur is None or not n or not SCORES[score][1]:
        return None
    return round(1.96 * math.sqrt(max(valeur * (1 - valeur), 0) / n), 4)


def ventiler(score: str, lignes: list) -> dict:
    """Le score par type de document, difficulté, type d'élément, type de réponse, profil, colonne libre."""
    groupes: dict[str, dict[str, list]] = {}
    for l in lignes:
        for axe, valeur in (l.attributs or {}).items():
            for v in (valeur if isinstance(valeur, list) else [valeur]):
                groupes.setdefault(axe, {}).setdefault(str(v), []).append(l)
    resultat = {}
    for axe, par_valeur in sorted(groupes.items()):
        resultat[axe] = {}
        for v, ls in sorted(par_valeur.items()):
            valeur, n = agreger(score, ls)
            resultat[axe][v] = {"valeur": arrondi(valeur), "n": n}
    return resultat


def arrondi(v):
    return round(v, 4) if isinstance(v, float) else v


def calculer_scores(lignes: list) -> dict:
    """scores.json : tous les scores sur les questions de réglage, puis les scores clés sur les questions réservées."""
    par_score: dict[str, list] = {}
    for l in lignes:
        par_score.setdefault(l.score, []).append(l)
    scores, cles = [], []
    for score in sorted(par_score, key=lambda s: list(SCORES).index(s)):
        toutes = par_score[score]
        reglage = [l for l in toutes if not l.reservee]
        valeur, n = agreger(score, reglage)
        scores.append({"score": score, "niveau": int(score[1]), "valeur": arrondi(valeur),
                       "marge": marge(score, valeur, n), "n": n, "ventilation": ventiler(score, reglage)})
    for score in SCORES_CLES:
        if score not in par_score:
            continue
        toutes = par_score[score]
        # scores de documents, morceaux et pages, fuites, erreurs graves : sur tout ; les autres : questions réservées
        base_cle = toutes if score in TOUTES_LES_QUESTIONS or not any(l.question_id for l in toutes) \
            else [l for l in toutes if l.reservee]
        valeur, n = agreger(score, base_cle)
        cles.append({"score": score, "valeur": arrondi(valeur), "marge": marge(score, valeur, n), "n": n})
    return {"scores": scores, "scores_cles": cles,
            "remarque": "scores clés calculés sur les questions réservées (fuites de droits et erreurs graves : sur "
                        "toutes les questions) ; c'est au métier de décider à leur lecture"}


# --- Écritures ------------------------------------------------------------------------------

def publier(ev: Evaluation, niveau: int, lignes: list[Ligne], langfuse=None) -> dict:
    """Remplace les lignes d'un niveau dans la base, puis réécrit tous les fichiers de l'évaluation."""
    for l in lignes:
        l.reservee = ev.reservee(l.question_id)
    moteur = base.moteur(ev.config["chemins"]["base"])
    base.init_base(ev.config["chemins"]["base"])
    with Session(moteur) as session:
        if session.get(base.Evaluation, ev.evaluation_id) is None:
            session.add(base.Evaluation(evaluation_id=ev.evaluation_id, date=dt.date.today().isoformat(),
                                        version_corpus=ev.version_corpus, version_kit=kit.__version__,
                                        version_rag=ev.rag["version_rag"], rag=ev.rag))
            session.flush()
        session.execute(delete(base.Resultat).where(base.Resultat.evaluation_id == ev.evaluation_id,
                                                    base.Resultat.niveau == niveau))
        session.add_all(base.Resultat(evaluation_id=ev.evaluation_id, question_id=l.question_id, niveau=l.niveau,
                                      score=l.score, valeur=l.valeur, verdict=l.verdict, detail=l.detail,
                                      objet=l.objet, attributs=l.attributs, poids=l.poids, reservee=l.reservee)
                        for l in lignes)
        toutes = session.scalars(select(base.Resultat).where(base.Resultat.evaluation_id == ev.evaluation_id)).all()
        resultat = calculer_scores(toutes)
        description = ev.description()
        enregistrement = session.get(base.Evaluation, ev.evaluation_id)
        enregistrement.date, enregistrement.juge = description["date"], description["juge"]
        enregistrement.scores = resultat
        session.commit()
        ecrire_fichiers(ev, description, resultat, toutes)
        from kit.etape_5_resultats import rapport  # ici, pour éviter une importation circulaire

        rapport.ecrire(ev, resultat, toutes)
    if langfuse is not None:
        publier_langfuse(ev, langfuse, lignes, resultat)
    return resultat


def ecrire_fichiers(ev: Evaluation, description: dict, resultat: dict, toutes) -> None:
    ev.fichiers.mkdir(parents=True, exist_ok=True)
    (ev.fichiers / "evaluation.json").write_text(json.dumps(description, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    (ev.fichiers / "scores.json").write_text(json.dumps({"evaluation_id": ev.evaluation_id, **resultat},
                                                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (ev.fichiers / "resultats_par_question.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["evaluation_id", "question_id", "niveau", "score", "valeur", "detail"])
        for r in sorted(toutes, key=lambda r: (r.question_id or "", r.niveau, r.score, r.objet or "")):
            if r.question_id and not r.reservee:  # une ligne par question et par score, hors questions réservées
                w.writerow([ev.evaluation_id, r.question_id, r.niveau, r.score,
                            r.verdict if r.verdict is not None else arrondi(r.valeur),
                            " — ".join(x for x in (r.objet, r.detail) if x)])  # « passage 12 — exact : … »


# --- Langfuse -------------------------------------------------------------------------------

def experience_langfuse(ev: Evaluation, langfuse) -> dict:
    """L'expérience Langfuse de l'évaluation, créée une fois : {"experiment_id", "traces": {question_id: trace_id}}.

    Langfuse v4 ne relie plus une trace existante à un jeu de données : on rejoue donc, avec run_experiment, les
    réponses déjà produites par le RAG (aucun nouvel appel au RAG). Chaque trace de l'expérience garde l'identifiant
    de la trace du RAG (trace_rag), pour remonter à la recherche et à la génération.
    """
    chemin = ev.fichiers / "langfuse.json"
    if chemin.exists():
        return json.loads(chemin.read_text(encoding="utf-8"))
    reponses = {r["question_id"]: r for r in ev.fichier_rag("reponses.jsonl")}
    if not reponses:
        return {}
    jeu = langfuse.get_dataset(f"corpus-{ev.corpus['corpus']['projet']}-{ev.version_corpus}")
    prefixe = f"{ev.version_corpus}_"

    def tache(*, item, **_):
        r = reponses[item.id.removeprefix(prefixe)]
        return {"reponse": r["reponse"], "abstention": r["abstention"], "chunks_cites": r["chunks_cites"],
                "trace_rag": r["trace_id"], "duree_ms": r["duree_ms"]}

    resultat = langfuse.run_experiment(name=ev.evaluation_id, run_name=ev.evaluation_id, data=jeu.items, task=tache,
                                       description=f"RAG {ev.rag['version_rag']} sur le corpus {ev.version_corpus}",
                                       metadata={"version_rag": ev.rag["version_rag"], "version_kit": kit.__version__},
                                       max_concurrency=8)
    experience = {"experiment_id": resultat.experiment_id, "url": resultat.experiment_url,
                  "traces": {r.item.id.removeprefix(prefixe): r.trace_id for r in resultat.item_results}}
    chemin.write_text(json.dumps(experience, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return experience


def publier_langfuse(ev: Evaluation, langfuse, lignes: list[Ligne], resultat: dict) -> None:
    """Scores par trace de l'expérience (hors questions réservées), et scores globaux sur l'expérience."""
    experience = experience_langfuse(ev, langfuse)
    if not experience:
        return  # niveau 1 avant que le RAG ait répondu : rien à relier
    traces = experience["traces"]
    for l in lignes:
        if l.question_id and not l.reservee and l.question_id in traces and l.valeur is not None:
            langfuse.create_score(trace_id=traces[l.question_id], name=l.score, value=float(l.valeur),
                                  comment=(l.verdict + " — " if l.verdict else "") + (l.detail or "") or None,
                                  score_id=f"{ev.evaluation_id}-{l.score}-{l.question_id}-{l.objet or ''}"[:200])
    niveau = lignes[0].niveau if lignes else None
    for s in resultat["scores"]:
        if s["niveau"] == niveau and s["valeur"] is not None:
            langfuse.create_score(dataset_run_id=experience["experiment_id"], name=s["score"], value=float(s["valeur"]),
                                  score_id=f"{ev.evaluation_id}-{s['score']}-global"[:200],
                                  comment=f"n = {s['n']}" + (f", marge ± {s['marge']}" if s["marge"] else ""))
    langfuse.flush()


def langfuse_acces(config: dict):
    from kit.config import cle

    lf = config["langfuse"]
    return cle(lf["variable_adresse"]), (cle(lf["variable_cle_publique"]), cle(lf["variable_cle_secrete"]))
