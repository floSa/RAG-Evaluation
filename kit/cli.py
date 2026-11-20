"""La commande `kit` : une sous-commande par action."""

import typer

from kit import base
from kit.config import charger_config

app = typer.Typer(help="Kit d'évaluation de RAG : corpus, contrat, niveaux 1 à 4, rapport.", no_args_is_help=True)


@app.callback()
def principal():
    """Kit d'évaluation de RAG (la configuration est lue dans config/kit.yaml et .env)."""


@app.command("init-base")
def init_base():
    """Crée les tables de la base relationnelle (document 1, section 5)."""
    config = charger_config()
    tables = base.init_base(config["chemins"]["base"])
    typer.echo(f"Base prête ({config['chemins']['base']}) : {', '.join(tables)}")


if __name__ == "__main__":
    app()
