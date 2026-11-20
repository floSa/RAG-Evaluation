"""La commande `kit` : une sous-commande par action."""

from pathlib import Path

import typer

from kit import base, contrat, import_corpus
from kit.config import charger_config, client_langfuse

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


@app.command()
def importer(fichier: Path = typer.Argument(..., exists=True, dir_okay=False, help="le fichier Excel du métier"),
             sans_langfuse: bool = typer.Option(False, help="ne pas créer le jeu de données dans Langfuse")):
    """Importe le fichier Excel du corpus : contrôles, base, export corpus/<version>/, jeu de données Langfuse."""
    config = charger_config()
    resultat = import_corpus.importer(fichier, config["chemins"]["base"], Path(config["chemins"]["sorties"]),
                                      config["projet"], None if sans_langfuse else client_langfuse(config))
    if resultat.erreurs:
        typer.echo(f"Import refusé : {len(resultat.erreurs)} ligne(s) à corriger dans {fichier.name}.", err=True)
        for e in resultat.erreurs:
            typer.echo(f"  - {e}", err=True)
        raise typer.Exit(1)
    if resultat.deja_importe:
        typer.echo(f"Fichier déjà importé, sans modification : version {resultat.version_corpus} ({resultat.dossier}).")
        if resultat.jeu_langfuse:
            typer.echo(f"Jeu de données Langfuse à jour : {resultat.jeu_langfuse}")
        return
    typer.echo(f"Corpus importé : version {resultat.version_corpus} → {resultat.dossier}")
    if resultat.jeu_langfuse:
        typer.echo(f"Jeu de données Langfuse : {resultat.jeu_langfuse}")
    for a in resultat.avertissements:
        typer.echo(f"  Attention (configuration minimale du document 1) : {a}")


@app.command("verifier-contrat")
def verifier_contrat(dossier: Path = typer.Argument(..., exists=True, file_okay=False,
                                                    help="corpus/<version>/ ou sorties_rag/<version>/"),
                     corpus: Path = typer.Option(None, exists=True, file_okay=False,
                                                 help="le corpus, pour vérifier que chaque question a sa réponse")):
    """Valide les fichiers d'un dossier contre specs/schemas/ et dit précisément ce qui manque."""
    erreurs = contrat.verifier_dossier(dossier, corpus)
    if erreurs:
        typer.echo(f"{dossier} : {len(erreurs)} problème(s).", err=True)
        for e in erreurs[:200]:
            typer.echo(f"  - {e}", err=True)
        if len(erreurs) > 200:
            typer.echo(f"  … et {len(erreurs) - 200} autres.", err=True)
        raise typer.Exit(1)
    typer.echo(f"{dossier} : conforme au contrat {', '.join(v + '.x' for v in contrat.VERSIONS_CONNUES)}.")


if __name__ == "__main__":
    app()
