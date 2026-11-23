"""Évaluation de l'ingestion, le graphe (document 3, section 6) : seulement si le RAG a un graphe.

- Conformité : le graphe du RAG (graphe.ttl) contrôlé par les règles SHACL de l'ontologie du projet, avec pySHACL.
  Chaque règle non respectée est une violation (score n1_graphe_violations, un nombre).
- Justesse : 50 relations tirées au hasard, chacune avec son passage source, que le métier juge juste ou fausse
  (score n1_graphe_justesse, une part). Il les juge dans un fichier Excel, justesse_graphe.xlsx, ou, s'il préfère,
  dans la file Langfuse « justesse-graphe ». Le service relit les jugements là où ils ont été mis.
"""

import json
import random
from pathlib import Path

from langfuse.api import ConfigCategory
from pyshacl import validate
from rdflib import RDF, RDFS, Graph, Namespace

from kit.etape_3_evaluation_reponse import relecture
from kit.etape_5_resultats.publication import Evaluation, Ligne

SH = Namespace("http://www.w3.org/ns/shacl#")
KIT = Namespace("https://kit-eval-rag/ns#")       # la provenance, fixée par le contrat
FILE = "justesse-graphe"
CONFIG_JUSTESSE = "justesse_relation"
CATEGORIES = {"juste": 1.0, "fausse": 0.0}
FICHIER = "justesse_graphe.xlsx"                  # dans resultats/evaluations/<évaluation>/ : le fichier que le métier remplit
ECHANTILLON = "justesse_graphe.json"              # dans resultats/evaluations/<évaluation>/fichiers_techniques/ : les relations envoyées au métier


def a_un_graphe(ev: Evaluation) -> bool:
    return ev.rag.get("type_rag") in ("graphe", "hybride")


def nom(g: Graph, noeud) -> str:
    """Le libellé d'un nœud s'il en a un, sinon la fin de son adresse."""
    return str(g.value(noeud, RDFS.label) or str(noeud).rsplit("#", 1)[-1].rsplit("/", 1)[-1])


# --- Conformité à l'ontologie ----------------------------------------------------------------------

def violations(chemin_graphe: Path, chemin_formes: Path) -> list[dict]:
    """Les violations des règles SHACL : le nœud en cause, la propriété, le message de pySHACL."""
    donnees = Graph().parse(chemin_graphe)
    _, rapport, _ = validate(donnees, shacl_graph=Graph().parse(chemin_formes), inference="none")
    resultat = []
    for r in rapport.subjects(RDF.type, SH.ValidationResult):
        propriete = rapport.value(r, SH.resultPath)
        resultat.append({"noeud": nom(donnees, rapport.value(r, SH.focusNode)),
                         "propriete": nom(donnees, propriete) if propriete else None,
                         "message": str(rapport.value(r, SH.resultMessage))})
    return sorted(resultat, key=lambda v: (v["noeud"], v["propriete"] or "", v["message"]))


def lignes_violations(ev: Evaluation) -> list[Ligne]:
    """Une ligne par violation (valeur 1), ou une seule ligne à 0 si le graphe est conforme."""
    vs = violations(ev.dossier_rag / "graphe.ttl", Path(ev.config["graphe"]["formes"]))
    if not vs:
        return [Ligne("n1_graphe_violations", 0.0, objet="graphe.ttl", detail="conforme à l'ontologie")]
    return [Ligne("n1_graphe_violations", 1.0, objet=v["noeud"],
                  detail=(f"{v['propriete']} : " if v["propriete"] else "") + v["message"]) for v in vs]


# --- Justesse des relations, jugée par le métier ---------------------------------------------------

def relations(chemin_graphe: Path) -> list[dict]:
    """Les relations réifiées du graphe, avec leur provenance."""
    g = Graph().parse(chemin_graphe)
    return sorted(({"relation_id": str(r), "texte": f"{nom(g, g.value(r, RDF.subject))} "
                    f"{nom(g, g.value(r, RDF.predicate))} {nom(g, g.value(r, RDF.object))}",
                    "reference_source": str(g.value(r, KIT.referenceSource)), "page": str(g.value(r, KIT.page))}
                   for r in g.subjects(RDF.type, RDF.Statement)), key=lambda x: x["relation_id"])


def config_justesse(langfuse) -> str:
    """Le score « justesse_relation » (juste ou fausse), créé s'il n'existe pas ; rend son identifiant."""
    for c in langfuse.api.score_configs.get(limit=100).data:
        if c.name == CONFIG_JUSTESSE and not c.is_archived:
            return c.id
    return langfuse.api.score_configs.create(
        name=CONFIG_JUSTESSE, data_type="CATEGORICAL",
        categories=[ConfigCategory(label=l, value=v) for l, v in CATEGORIES.items()],
        description="Une relation du graphe est-elle juste, d'après son passage source ?").id


def tirer(ev: Evaluation) -> list[dict]:
    """Tire les relations à juger, chacune avec le passage d'où elle vient, et garde le tirage."""
    toutes = relations(ev.dossier_rag / "graphe.ttl")
    tirees = sorted(random.Random(0).sample(toutes, min(ev.config["graphe"]["taille_echantillon"], len(toutes))),
                    key=lambda x: x["relation_id"])
    pages = {}
    for c in ev.fichier_rag("chunks.jsonl"):
        if c.get("type_objet") == "chunk":
            pages.setdefault((c["reference_source"], str(c["page"])), []).append(c["texte"])
    for r in tirees:
        r["passage"] = "\n\n".join(pages.get((r["reference_source"], r["page"]), []))
    ecrire_tirage(ev, tirees)
    return tirees


def ecrire_tirage(ev: Evaluation, tirees: list[dict]) -> None:
    (ev.fichiers / ECHANTILLON).parent.mkdir(parents=True, exist_ok=True)
    (ev.fichiers / ECHANTILLON).write_text(json.dumps(tirees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def envoyer(ev: Evaluation, langfuse, tirees: list[dict]) -> int:
    """Pour un métier qui préfère Langfuse : une trace par relation (la relation et son passage), dans la file."""
    for r in tirees:
        with langfuse.start_as_current_observation(name="relation-graphe", input={
                "relation": r["texte"], "source": f"{r['reference_source']}, page {r['page']}", "passage": r["passage"]},
                metadata={"evaluation": ev.evaluation_id, "relation_id": r["relation_id"]}):
            r["trace_id"] = langfuse.get_current_trace_id()
    langfuse.flush()
    ecrire_tirage(ev, tirees)
    return relecture.envoyer(langfuse, FILE, "Justesse du graphe : chaque relation est-elle juste, d'après son passage "
                             "source ? (document 3, section 6)", [r["trace_id"] for r in tirees],
                             score_config_id=config_justesse(langfuse))


def lignes_justesse(ev: Evaluation, langfuse=None) -> list[Ligne]:
    """Une ligne par relation jugée par le métier, dans le fichier Excel, ou dans Langfuse s'il y a jugé."""
    from kit.etape_3_evaluation_reponse import fichier_metier

    chemin = ev.fichiers / ECHANTILLON
    if not chemin.exists():
        return []
    tirees = json.loads(chemin.read_text(encoding="utf-8"))
    jugements = {}
    fichier = ev.dossier / FICHIER
    if fichier.exists():
        for l in fichier_metier.lire_graphe(fichier):
            jugements[(l["relation"], str(l["reference_source"]), str(l["page"]))] = l["jugement"]
    if langfuse is not None and any(r.get("trace_id") for r in tirees):
        notes = relecture.notes_metier(langfuse, [r["trace_id"] for r in tirees if r.get("trace_id")],
                                       CONFIG_JUSTESSE, CATEGORIES)
        for r in tirees:
            if r.get("trace_id") in notes:
                jugements.setdefault((r["texte"], r["reference_source"], r["page"]), notes[r["trace_id"]])
    return [Ligne("n1_graphe_justesse", CATEGORIES[j], objet=r["texte"], verdict=j,
                  detail=f"{r['reference_source']}, page {r['page']}")
            for r in tirees if (j := jugements.get((r["texte"], r["reference_source"], r["page"])))]
