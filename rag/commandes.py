"""La commande `rag`.

Pour se servir du RAG :            rag indexer, puis rag demander "…" --profil maintenance
Pour l'évaluer, par fichiers :     rag exporter, puis rag repondre <questions.jsonl>   (branchement_evaluation.py)
"""

from pathlib import Path

import typer

from rag import branchement_evaluation
from rag.assistant import Assistant, charger_config, indexer as construire_index

app = typer.Typer(help="RAG d'exemple : indexer les documents, poser une question, se brancher sur l'évaluation.",
                  no_args_is_help=True)

OPTION_K = typer.Option(None, help="nombre de chunks donnés au modèle, si différent de rag/config.yaml")


@app.callback()
def principal():
    """RAG d'exemple (configuration : rag/config.yaml ; clés : .env)."""


@app.command()
def indexer():
    """Étapes 1 à 3 : extrait (Docling, pypdf), découpe et vectorise les documents."""
    resultat = construire_index(charger_config(), afficher=typer.echo)
    typer.echo(f"Index prêt : {resultat['chunks']} chunks, {resultat['pages']} pages, "
               f"version {resultat['version_index']}.")


@app.command()
def demander(question: str = typer.Argument(..., help="la question, entre guillemets"),
             profil: str = typer.Option("tous", help="profil de l'utilisateur : il ne voit que ses documents"),
             k: int = OPTION_K):
    """Étapes 5 et 6 : pose une question et affiche la réponse avec ses sources."""
    r = Assistant(k=k).demander(question, profil)
    typer.echo(f"\n{r['reponse']}\n")
    for n, c in enumerate(r["contexte"], start=1):
        marque = "cité" if c in r["cites"] else "    "
        typer.echo(f"  [{n}] {marque}  {c['reference_source']} (version {c['version_document']}), page {c['page']}")
    typer.echo(f"\n{r['duree_ms']} ms, {r['tokens'][0]} + {r['tokens'][1]} tokens.")
    if r["trace_id"]:
        typer.echo(f"Trace Langfuse : {r['trace_id']}")


@app.command()
def exporter(k: int = OPTION_K):
    """Évaluation : écrit rag.json, chunks.jsonl et pages_extraites.jsonl dans sorties/sorties_rag/<version_rag>/."""
    typer.echo(branchement_evaluation.exporter(branchement_evaluation.Connecteur(k=k)))


@app.command()
def repondre(questions: Path = typer.Argument(..., exists=True, help="questions.jsonl du corpus exporté par le kit"),
             k: int = OPTION_K):
    """Évaluation : pose chaque question avec son profil ; écrit recherches.jsonl et reponses.jsonl."""
    c = branchement_evaluation.Connecteur(k=k)
    typer.echo(branchement_evaluation.repondre_aux_questions(c, questions, afficher=typer.echo))


if __name__ == "__main__":
    app()
