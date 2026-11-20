"""La commande `kit` : une sous-commande par action."""

from pathlib import Path

import typer

from kit import base, contrat, import_corpus, comparaison, lanceur, niveau1, niveau2, niveau3, niveau4, publication, relecture
from kit.config import charger_config, client_langfuse

app = typer.Typer(help="Kit d'évaluation de RAG : corpus, contrat, niveaux 1 à 4, rapport.", no_args_is_help=True)


@app.callback()
def principal():
    """Kit d'évaluation de RAG (la configuration est lue dans evaluation/config/kit.yaml et .env)."""


@app.command("init-base")
def init_base():
    """Crée les tables de la base relationnelle (document 1, section 5)."""
    config = charger_config()
    tables = base.init_base(config["chemins"]["base"])
    typer.echo(f"Base prête ({config['chemins']['base']}) : {', '.join(tables)}")


@app.command("verifier-modeles")
def verifier_modeles():
    """Teste le point d'accès et les modèles de evaluation/config/kit.yaml (juge, embeddings) et Langfuse."""
    from kit import juge

    config = charger_config()
    m = config["modeles"]
    typer.echo(f"Point d'accès : {m['adresse']} (clé lue dans la variable {m['variable_cle']})")
    llm = juge.client(config)
    try:
        r = juge.appeler(config, llm, [{"role": "user", "content": 'Réponds par le JSON {"ok": true}'}])
        typer.echo(f"  juge « {m['juge']['modele']} » : répond ({r.strip()[:40]})")
        e = llm.embeddings.create(model=m["embeddings"]["modele"], input=["essai"])
        typer.echo(f"  embeddings « {m['embeddings']['modele']} » : {len(e.data[0].embedding)} dimensions")
    except Exception as ex:
        typer.echo(f"  ÉCHEC : {ex}", err=True)
        raise typer.Exit(1)
    try:
        ok = client_langfuse(config).auth_check()
        typer.echo(f"  Langfuse : {'connecté' if ok else 'clés refusées'}")
    except Exception as ex:
        typer.echo(f"  Langfuse : injoignable ({ex})", err=True)


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
    """Valide les fichiers d'un dossier contre corpus/contrat/schemas/ et dit précisément ce qui manque."""
    erreurs = contrat.verifier_dossier(dossier, corpus)
    if erreurs:
        typer.echo(f"{dossier} : {len(erreurs)} problème(s).", err=True)
        for e in erreurs[:200]:
            typer.echo(f"  - {e}", err=True)
        if len(erreurs) > 200:
            typer.echo(f"  … et {len(erreurs) - 200} autres.", err=True)
        raise typer.Exit(1)
    typer.echo(f"{dossier} : conforme au contrat {', '.join(v + '.x' for v in contrat.VERSIONS_CONNUES)}.")


@app.command()
def lancer(connecteur: str = typer.Argument(..., help="module:Classe, par exemple rag_demo.connecteur:Connecteur"),
           corpus: Path = typer.Option(..., exists=True, file_okay=False, help="le dossier corpus/<version>/"),
           parametre: list[str] = typer.Option([], "--parametre", "-p",
                                               help="paramètre du connecteur, cle=valeur (répétable), ex. -p k=3")):
    """Fait tourner un RAG Python par son connecteur et écrit ses sorties du contrat."""
    config = charger_config()
    parametres = {}
    for p in parametre:
        cle_, _, valeur = p.partition("=")
        parametres[cle_] = int(valeur) if valeur.isdigit() else valeur
    dossier = lanceur.lancer(lanceur.charger_connecteur(connecteur, parametres), corpus,
                             Path(config["chemins"]["sorties"]), afficher=typer.echo)
    erreurs = contrat.verifier_dossier(dossier, corpus)
    typer.echo(f"Sorties écrites dans {dossier} ; contrat : {'conforme' if not erreurs else f'{len(erreurs)} problème(s)'}.")
    for e in erreurs[:20]:
        typer.echo(f"  - {e}", err=True)


# --- Les niveaux de l'évaluation ------------------------------------------------------------

OPTION_CORPUS = typer.Option(..., exists=True, file_okay=False, help="le dossier corpus/<version>/")
OPTION_RAG = typer.Option(..., exists=True, file_okay=False, help="le dossier sorties_rag/<version_rag>/")
OPTION_LANGFUSE = typer.Option(False, help="ne pas publier dans Langfuse")


def preparer(corpus: Path, rag: Path, ingestion_seule: bool = False):
    """Vérifie le contrat avant toute mesure, puis ouvre l'évaluation (corpus × version du RAG)."""
    config = charger_config()
    erreurs = contrat.verifier_dossier(rag, corpus, ingestion_seule)
    if erreurs:
        typer.echo(f"Sorties du RAG non conformes au contrat ({len(erreurs)} problème(s)) :", err=True)
        for e in erreurs[:20]:
            typer.echo(f"  - {e}", err=True)
        raise typer.Exit(1)
    return config, publication.Evaluation(config, corpus, rag)


def afficher_niveau(resultat: dict, niveau: int) -> None:
    for s in resultat["scores"]:
        if s["niveau"] == niveau:
            marge = f" ± {s['marge']:.2f}" if s["marge"] is not None else ""
            seuil = "" if s["atteint"] is None else (" ✔ seuil atteint" if s["atteint"] else f" ✘ seuil {s['seuil']}")
            typer.echo(f"  {s['score']:<28} {s['valeur']}{marge}  (n = {s['n']}){seuil}")


@app.command("niveau1")
def niveau_1(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """Niveau 1 — ingestion : rattachement des passages, liens_index, scores, passages non rattachés."""
    config, ev = preparer(corpus, rag, ingestion_seule=True)
    lignes, liens, non_rattaches = niveau1.evaluer(ev)
    niveau1.enregistrer(ev, liens, non_rattaches)
    resultat = publication.publier(ev, 1, lignes, None if sans_langfuse else client_langfuse(config))
    typer.echo(f"Niveau 1 — {ev.evaluation_id} → {ev.dossier}")
    afficher_niveau(resultat, 1)
    if non_rattaches:
        typer.echo(f"  {len(non_rattaches)} passage(s) non rattaché(s) (passages_non_rattaches.jsonl) :")
        for p in non_rattaches:
            typer.echo(f"    - passage {p['passage_id']} ({p['question_id']}, {p['reference_source']} p. {p['page']}, "
                       f"{p['type_element']}) : {p['cause_probable']}")


@app.command("niveau2")
def niveau_2(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """Niveau 2 — recherche : réussite à k, rappel, rang du premier bon chunk, fuite de droits."""
    config, ev = preparer(corpus, rag)
    lignes = niveau2.evaluer(ev, niveau1.lire_liens(ev))
    resultat = publication.publier(ev, 2, lignes, None if sans_langfuse else client_langfuse(config))
    typer.echo(f"Niveau 2 — {ev.evaluation_id} → {ev.dossier}")
    afficher_niveau(resultat, 2)
    fuites = [l for l in lignes if l.score == "n2_fuite_droits" and l.valeur]
    for l in fuites:
        typer.echo(f"  FUITE DE DROITS — {l.question_id} : {l.detail}")


@app.command("niveau3")
def niveau_3(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """Niveau 3 — réponse : juge (exactitude), Ragas (fidélité, synthèse), abstention, citations, valeurs."""
    config, ev = preparer(corpus, rag)
    typer.echo("Niveau 3 : le juge et Ragas notent les réponses (quelques minutes)…")
    lignes, croisement, file = niveau3.evaluer(ev, niveau1.lire_liens(ev))
    langfuse = None if sans_langfuse else client_langfuse(config)
    resultat = publication.publier(ev, 3, lignes, langfuse)
    visibles = lambda objets: [o for o in objets if not ev.reservee(o["question_id"])]  # noqa: E731
    contrat.ecrire_jsonl(ev.dossier / "croisement.jsonl", visibles(croisement))
    contrat.ecrire_jsonl(ev.dossier / "relecture.jsonl", visibles(file))
    typer.echo(f"Niveau 3 — {ev.evaluation_id} → {ev.dossier}")
    afficher_niveau(resultat, 3)
    diagnostics: dict[str, int] = {}
    for c in visibles(croisement):
        diagnostics[c["diagnostic"]] = diagnostics.get(c["diagnostic"], 0) + 1
    typer.echo("  Croisement recherche × réponse (questions non réservées) :")
    for d, n in sorted(diagnostics.items(), key=lambda x: -x[1]):
        typer.echo(f"    {n:>3}  {d}")
    if langfuse:
        traces = publication.experience_langfuse(ev, langfuse).get("traces", {})
        n = relecture.envoyer(langfuse, "relecture-reponses", "Réponses à relire par le métier (document 3, section 8)",
                              [traces.get(f["question_id"]) for f in file])
        typer.echo(f"  File « relecture-reponses » : {len(file)} réponse(s) à relire, {n} ajoutée(s) dans Langfuse.")


@app.command("verifier-juge")
def verifier_juge(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG,
                  envoyer: bool = typer.Option(False, help="tirer l'échantillon et l'envoyer au métier dans Langfuse")):
    """Vérification du juge : --envoyer pour faire noter l'échantillon, puis sans option pour calculer l'accord."""
    import json

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    config, ev = preparer(corpus, rag)
    langfuse = client_langfuse(config)
    traces = publication.experience_langfuse(ev, langfuse).get("traces", {})
    chemin = ev.dossier / "verification_juge.json"
    with Session(base.moteur(config["chemins"]["base"])) as session:
        verdicts = {r.question_id: r.verdict for r in session.scalars(select(base.Resultat).where(
            base.Resultat.evaluation_id == ev.evaluation_id, base.Resultat.score == "n3_exactitude",
            base.Resultat.reservee.is_(False)))}
    if not verdicts:
        typer.echo("Aucun verdict du juge : lancer d'abord « kit niveau3 ».", err=True)
        raise typer.Exit(1)
    v = config["verification_juge"]
    if envoyer:
        ids = relecture.echantillon(verdicts, v["taille_echantillon"])
        chemin.write_text(json.dumps({"juge": config["modeles"]["juge"], "questions": ids}, ensure_ascii=False,
                                     indent=2) + "\n", encoding="utf-8")
        n = relecture.envoyer(langfuse, "verification-juge", "Vérification du juge : noter juste, partielle ou fausse, "
                              "sans regarder la note du juge (JUGE.md)", [traces[q] for q in ids])
        typer.echo(f"{len(ids)} réponses envoyées dans la file « verification-juge » ({n} nouvelles). Le métier les "
                   f"note avec le score « {relecture.CONFIG_VERDICT} », puis relancer cette commande sans --envoyer.")
        return
    if not chemin.exists():
        typer.echo("Pas d'échantillon : lancer d'abord « kit verifier-juge --envoyer ».", err=True)
        raise typer.Exit(1)
    ids = json.loads(chemin.read_text(encoding="utf-8"))["questions"]
    par_trace = relecture.notes_metier(langfuse, [traces[q] for q in ids])
    metier = {q: par_trace[traces[q]] for q in ids if traces[q] in par_trace}
    r = relecture.accord({q: verdicts[q] for q in ids}, metier)
    r["valide"] = r["accord"] is not None and len(metier) == len(ids) and r["accord"] >= v["accord_minimum"]
    (ev.dossier / "verification_juge_resultat.json").write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n",
                                                                 encoding="utf-8")
    typer.echo(f"Notes du métier : {len(metier)} sur {len(ids)}.")
    if r["n"]:
        typer.echo(f"Accord juge / métier : {r['accord']:.0%} (seuil {v['accord_minimum']:.0%}) ; kappa de Cohen : "
                   f"{r['kappa']}. Juge {'VALIDÉ' if r['valide'] else 'NON validé'}.")
        for d in r["desaccords"]:
            typer.echo(f"  - {d['question_id']} : juge « {d['juge']} », métier « {d['metier']} »")


def afficher_decision(resultat: dict, ev) -> None:
    d = resultat["decision"]
    typer.echo(f"  DÉCISION : {'mise en production possible' if d['mise_en_production_possible'] else 'mise en production non recommandée'}")
    for b in d["criteres_bloquants_declenches"]:
        typer.echo(f"    critère bloquant déclenché : {b['score']} = {b['valeur']:g} (seuil {b['seuil']})")
    bloquants = {b["score"] for b in d["criteres_bloquants_declenches"]}
    for x in d["seuils"]:
        if x["atteint"] is False and x["score"] not in bloquants:
            typer.echo(f"    seuil non atteint : {x['score']} = {x['valeur']} (seuil {x['seuil']})")
    typer.echo(f"  Rapport : {ev.dossier / 'rapport.html'}")


@app.command("niveau4")
def niveau_4(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """Niveau 4 — bout en bout : score pondéré, erreurs graves, temps, coût, puis décision et rapport."""
    config, ev = preparer(corpus, rag)
    resultat = publication.publier(ev, 4, niveau4.evaluer(ev), None if sans_langfuse else client_langfuse(config))
    typer.echo(f"Niveau 4 — {ev.evaluation_id} → {ev.dossier}")
    afficher_niveau(resultat, 4)
    afficher_decision(resultat, ev)


@app.command()
def evaluer(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """Enchaîne les niveaux 1 à 4 sur les sorties d'un RAG ; écrit scores, rapport.html, et publie dans Langfuse."""
    niveau_1(corpus, rag, sans_langfuse)
    niveau_2(corpus, rag, sans_langfuse)
    niveau_3(corpus, rag, sans_langfuse)
    niveau_4(corpus, rag, sans_langfuse)


@app.command()
def comparer(evaluation_a: Path = typer.Argument(..., exists=True, file_okay=False, help="resultats/<evaluation_a>/"),
             evaluation_b: Path = typer.Argument(..., exists=True, file_okay=False, help="resultats/<evaluation_b>/")):
    """Compare deux évaluations du même corpus : écarts de scores, questions gagnées et perdues, test de McNemar."""
    import json

    config = charger_config()
    try:
        r = comparaison.comparer(config, evaluation_a, evaluation_b)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    (evaluation_b / f"comparaison_avec_{evaluation_a.name}.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    typer.echo(f"A = {r['a']}\nB = {r['b']}\n")
    typer.echo(f"  {'score':<28} {'A':>8} {'B':>8} {'écart':>8}  marge")
    for x in r["ecarts"]:
        marge = "" if x["marge"] is None else f"± {x['marge']:.2f}"
        signe = "" if x["significatif_seul"] is None else ("  > marge" if x["significatif_seul"] else "  < marge : ne prouve rien seul")
        typer.echo(f"  {x['score']:<28} {x['a']:>8.3g} {x['b']:>8.3g} {x['ecart']:>+8.3g}  "
                   f"{marge}{signe}")
    questions = {}
    dossier_corpus = Path(config["chemins"]["sorties"]) / "corpus" / json.loads(
        (evaluation_a / "evaluation.json").read_text(encoding="utf-8"))["version_corpus"]
    if (dossier_corpus / "questions.jsonl").exists():
        questions = {q["question_id"]: q for q in contrat.lire_jsonl(dossier_corpus / "questions.jsonl")}
    for score, q in r["questions"].items():
        p = "—" if q["mcnemar_p"] is None else f"{q['mcnemar_p']:.3f}"
        typer.echo(f"\n  {score} : {len(q['gagnees'])} question(s) gagnée(s), {len(q['perdues'])} perdue(s) sur {q['n']} "
                   f"(McNemar p = {p}{' : écart probablement dû au hasard' if q['mcnemar_p'] and q['mcnemar_p'] > 0.05 else ''})")
        if q["gagnees"]:
            typer.echo(f"    gagnées : {', '.join(q['gagnees'])}")
        if q["perdues"]:
            graves = [x for x in q["perdues"] if questions.get(x, {}).get("gravite") == "forte"]
            typer.echo(f"    perdues : {', '.join(q['perdues'])}"
                       + (f"  — RÉGRESSION sur une question grave : {', '.join(graves)}" if graves else ""))


if __name__ == "__main__":
    app()
