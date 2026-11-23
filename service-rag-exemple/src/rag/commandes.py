"""La commande `rag`.

Pour se servir du RAG :            rag indexer, puis rag demander "…" --profil maintenance
Pour l'évaluer :                   rag ouvrir-endpoints (ou docker compose up -d) : le service d'évaluation appelle ses endpoints
"""

from pathlib import Path

import typer

from rag.assistant import Assistant, charger_config, dans_l_espace, indexer as construire_index, regler

app = typer.Typer(help="RAG d'exemple : indexer les documents, poser une question, ouvrir ses endpoints à l'évaluation.",
                  no_args_is_help=True)

OPTION_K = typer.Option(None, help="nombre de chunks donnés au modèle, si différent de config/config.yaml")
OPTION_GRAPHE = typer.Option(None, "--graphe/--sans-graphe", help="avec ou sans le graphe (étape 4 du RAG), si différent de config.yaml")


@app.callback()
def principal():
    """RAG d'exemple (configuration : config/config.yaml ; clés : .env)."""


@app.command()
def indexer(graphe: bool = OPTION_GRAPHE):
    """Production : indexe les documents de documents_de_production/ (étapes 1 à 3, et 4 si le graphe est actif)."""
    config = dans_l_espace(regler(charger_config(), graphe=graphe), "production")
    if not Path(config["liste_des_documents"]).exists():
        typer.echo(f"Aucun document de production : mettre les documents et leur liste ({config['liste_des_documents']}) "
                   "dans documents_de_production/. Les documents de l'évaluation arrivent, eux, par l'endpoint « ingérer ».", err=True)
        raise typer.Exit(1)
    resultat = construire_index(config, afficher=typer.echo)
    typer.echo(f"Index prêt : {resultat['chunks']} chunks, {resultat['pages']} pages, "
               f"version {resultat['version_index']}.")
    if "noeuds" in resultat:
        typer.echo(f"Graphe prêt : {resultat['noeuds']} éléments dans l'index, {resultat['triplets']} triplets RDF.")


@app.command()
def demander(question: str = typer.Argument(..., help="la question, entre guillemets"),
             profil: str = typer.Option("tous", help="profil de l'utilisateur : il ne voit que ses documents"),
             k: int = OPTION_K, graphe: bool = OPTION_GRAPHE,
             espace: str = typer.Option("production", help="production, ou evaluation : les documents envoyés par le service d'évaluation")):
    """Étapes 5 et 6 : pose une question et affiche la réponse avec ses sources."""
    r = Assistant(k=k, graphe=graphe, espace=espace).demander(question, profil)
    typer.echo(f"\n{r['reponse']}\n")
    for n, c in enumerate(r["contexte"], start=1):
        marque = "cité" if c in r["cites"] else "    "
        graphe = "  (graphe : " + c["metadonnees"]["entite"] + ")" if c["type_objet"] == "noeud" else ""
        typer.echo(f"  [{n}] {marque}  {c['reference_source']} (version {c['version_document']}), page {c['page']}{graphe}")
    typer.echo(f"\n{r['duree_ms']} ms, {r['tokens'][0]} + {r['tokens'][1]} tokens.")
    if r["trace_id"]:
        typer.echo(f"Trace Langfuse : {r['trace_id']}")


@app.command()
def ouvrir_endpoints():
    """Ouvre les endpoints d'évaluation (src/rag/endpoints_evaluation/) à son adresse : http://127.0.0.1:8100 par défaut."""
    import uvicorn

    endpoints = charger_config()["endpoints_evaluation"]
    uvicorn.run("rag.endpoints_evaluation.adresse_web:app", host=endpoints["hote"], port=endpoints["port"])


if __name__ == "__main__":
    app()
