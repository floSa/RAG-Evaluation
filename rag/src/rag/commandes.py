"""La commande `rag`.

Pour se servir du RAG :            rag indexer, puis rag demander "…" --profil maintenance
Pour l'évaluer, par fichiers :     rag exporter, puis rag repondre <questions.jsonl>   (utils/branchement_evaluation.py)
"""

from pathlib import Path

import typer

from rag.utils import branchement_evaluation
from rag.assistant import Assistant, charger_config, indexer as construire_index, regler

app = typer.Typer(help="RAG d'exemple : indexer les documents, poser une question, se brancher sur l'évaluation.",
                  no_args_is_help=True)

OPTION_K = typer.Option(None, help="nombre de chunks donnés au modèle, si différent de rag/config/config.yaml")
OPTION_GRAPHE = typer.Option(None, "--graphe/--sans-graphe", help="avec ou sans le graphe (étape 4), si différent de config.yaml")


@app.callback()
def principal():
    """RAG d'exemple (configuration : rag/config/config.yaml ; clés : .env)."""


@app.command()
def indexer(graphe: bool = OPTION_GRAPHE):
    """Étapes 1 à 3 : extrait (Docling, pypdf), découpe et vectorise les documents ; étape 4 si le graphe est actif."""
    resultat = construire_index(regler(charger_config(), graphe=graphe), afficher=typer.echo)
    typer.echo(f"Index prêt : {resultat['chunks']} chunks, {resultat['pages']} pages, "
               f"version {resultat['version_index']}.")
    if "noeuds" in resultat:
        typer.echo(f"Graphe prêt : {resultat['noeuds']} éléments dans l'index, {resultat['triplets']} triplets RDF.")


@app.command()
def demander(question: str = typer.Argument(..., help="la question, entre guillemets"),
             profil: str = typer.Option("tous", help="profil de l'utilisateur : il ne voit que ses documents"),
             k: int = OPTION_K, graphe: bool = OPTION_GRAPHE):
    """Étapes 5 et 6 : pose une question et affiche la réponse avec ses sources."""
    r = Assistant(k=k, graphe=graphe).demander(question, profil)
    typer.echo(f"\n{r['reponse']}\n")
    for n, c in enumerate(r["contexte"], start=1):
        marque = "cité" if c in r["cites"] else "    "
        graphe = "  (graphe : " + c["metadonnees"]["entite"] + ")" if c["type_objet"] == "noeud" else ""
        typer.echo(f"  [{n}] {marque}  {c['reference_source']} (version {c['version_document']}), page {c['page']}{graphe}")
    typer.echo(f"\n{r['duree_ms']} ms, {r['tokens'][0]} + {r['tokens'][1]} tokens.")
    if r["trace_id"]:
        typer.echo(f"Trace Langfuse : {r['trace_id']}")


@app.command()
def exporter(k: int = OPTION_K, graphe: bool = OPTION_GRAPHE):
    """Évaluation : écrit rag.json, chunks.jsonl, pages_extraites.jsonl (et graphe.ttl) dans sorties/sorties_rag/<version_rag>/."""
    typer.echo(branchement_evaluation.exporter(branchement_evaluation.Connecteur(k=k, graphe=graphe)))


@app.command()
def repondre(questions: Path = typer.Argument(..., exists=True, help="questions.jsonl du corpus exporté par le kit"),
             k: int = OPTION_K, graphe: bool = OPTION_GRAPHE):
    """Évaluation : pose chaque question avec son profil ; écrit recherches.jsonl et reponses.jsonl."""
    c = branchement_evaluation.Connecteur(k=k, graphe=graphe)
    typer.echo(branchement_evaluation.repondre_aux_questions(c, questions, afficher=typer.echo))


if __name__ == "__main__":
    app()
