"""La commande `rag-demo` : indexer les documents, exporter l'index, répondre aux questions."""

import json
from pathlib import Path

import typer

from rag_demo.connecteur import Connecteur
from rag_demo.rag import charger_config, indexer as indexer_documents

app = typer.Typer(help="RAG de démonstration : indexer, exporter, répondre.", no_args_is_help=True)


@app.callback()
def principal():
    """RAG de démonstration (configuration : rag_demo/config.yaml et .env)."""


def ecrire_jsonl(chemin: Path, objets) -> int:
    n = 0
    with chemin.open("w", encoding="utf-8") as f:
        for o in objets:
            f.write(json.dumps({k: v for k, v in o.items() if v is not None}, ensure_ascii=False) + "\n")
            n += 1
    return n


def dossier_version(connecteur: Connecteur) -> Path:
    rag = connecteur.decrire()
    dossier = Path(connecteur.rag.config["sorties"]) / rag["version_rag"]
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


@app.command()
def indexer():
    """Extrait (Docling, pypdf), découpe et vectorise les documents du catalogue."""
    resultat = indexer_documents(charger_config(), afficher=typer.echo)
    typer.echo(f"Index prêt : {resultat['chunks']} chunks, {resultat['pages']} pages, "
               f"version {resultat['version_index']}.")


@app.command()
def exporter(k: int = typer.Option(None, help="k, si différent de config.yaml")):
    """Écrit rag.json, chunks.jsonl et pages_extraites.jsonl dans sorties_rag/<version_rag>/."""
    c = Connecteur(k=k)
    dossier = dossier_version(c)
    (dossier / "rag.json").write_text(json.dumps(c.decrire(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = ecrire_jsonl(dossier / "chunks.jsonl", c.exporter_index())
    p = ecrire_jsonl(dossier / "pages_extraites.jsonl", c.exporter_pages())
    typer.echo(f"{dossier} : rag.json, {n} chunks, {p} pages extraites.")


@app.command()
def repondre(questions: Path = typer.Argument(..., exists=True, help="questions.jsonl du corpus"),
             k: int = typer.Option(None, help="k, si différent de config.yaml")):
    """Pose chaque question avec son profil ; écrit recherches.jsonl et reponses.jsonl.

    Du fichier de questions, le RAG ne lit que question_id, question, profil, et pour une question de suite
    la question précédente et sa réponse attendue (l'historique prévu par le contrat).
    """
    c = Connecteur(k=k)
    dossier = dossier_version(c)
    with questions.open(encoding="utf-8") as f:
        lignes = [json.loads(l) for l in f if l.strip()]
    par_id = {q["question_id"]: q for q in lignes}
    recherches, reponses = [], []
    for q in lignes:
        historique, p = [], q
        while p.get("question_precedente") in par_id:
            p = par_id[p["question_precedente"]]
            historique.insert(0, {"question": p["question"], "reponse": p["reponse_attendue"]})
        r = c.repondre(q["question"], q["profil"], historique)
        recherches.append({"question_id": q["question_id"], "profil": q["profil"], "k": c.rag.k,
                           **c.rag.derniere_recherche})
        reponses.append({"question_id": q["question_id"], **r})
        typer.echo(f"  {q['question_id']} ({r['duree_ms']} ms){' — abstention' if r['abstention'] else ''}")
    if c.rag.langfuse:
        c.rag.langfuse.flush()
    ecrire_jsonl(dossier / "recherches.jsonl", recherches)
    ecrire_jsonl(dossier / "reponses.jsonl", reponses)
    typer.echo(f"{dossier} : {len(reponses)} réponses.")


if __name__ == "__main__":
    app()
