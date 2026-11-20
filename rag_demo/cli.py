"""La commande `rag-demo` : une sous-commande par action (complétée à l'étape 4)."""

import typer

app = typer.Typer(help="RAG de démonstration : indexer, exporter, répondre.", no_args_is_help=True)


@app.callback()
def principal():
    """RAG de démonstration (vectoriel, puis hybride avec graphe)."""


if __name__ == "__main__":
    app()
