"""La commande `kit` : une sous-commande par action."""

from pathlib import Path

import typer

from kit import base
from kit import contrat
from kit.appel_du_rag import appeler
from kit.config import charger_config, client_langfuse
from kit.etape_0a_corpus import importer as import_corpus
from kit.etape_1_evaluation_ingestion import graphe as graphe_n1
from kit.etape_1_evaluation_ingestion import scores as scores_ingestion
from kit.etape_2_evaluation_recherche import scores as scores_recherche
from kit.etape_3_evaluation_reponse import relecture
from kit.etape_3_evaluation_reponse import scores as scores_reponse
from kit.etape_4_evaluation_bout_en_bout import scores as scores_bout_en_bout
from kit.etape_5_resultats import comparaison
from kit.etape_5_resultats import publication

app = typer.Typer(help="Kit d'évaluation de RAG : corpus, endpoints du RAG, évaluations 1 à 4, rapport.", no_args_is_help=True)


@app.callback()
def principal(dossier: Path = typer.Option(Path("."), "--dossier",
                                           help="le dossier du service à utiliser (config/, corpus_annote/, resultats/) ; "
                                                "par défaut, le dossier courant")):
    """Kit d'évaluation de RAG (la configuration est lue dans <dossier>/config/kit.yaml, les clés dans .env)."""
    from kit import config as module_config

    module_config.DOSSIER = dossier


@app.command("init-base")
def init_base():
    """Crée les tables de la base relationnelle (document 1, section 5)."""
    config = charger_config()
    tables = base.init_base(config["chemins"]["base"])
    typer.echo(f"Base prête ({config['chemins']['base']}) : {', '.join(tables)}")


@app.command("verifier-modeles")
def verifier_modeles():
    """Teste le point d'accès et les modèles de config/kit.yaml (juge, embeddings) et Langfuse."""
    from kit.etape_3_evaluation_reponse import juge

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
    resultat = import_corpus.importer(fichier, config["chemins"]["base"], Path(config["chemins"]["resultats"]),
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
                                                    help="corpus/<version>/ ou reponses_du_rag/<version>/"),
                     corpus: Path = typer.Option(None, exists=True, file_okay=False,
                                                 help="le corpus, pour vérifier que chaque question a sa réponse")):
    """Valide les fichiers d'un dossier contre documentation/methode_et_contrat/schemas/ et dit précisément ce qui manque."""
    erreurs = contrat.verifier_dossier(dossier, corpus)
    if erreurs:
        typer.echo(f"{dossier} : {len(erreurs)} problème(s).", err=True)
        for e in erreurs[:200]:
            typer.echo(f"  - {e}", err=True)
        if len(erreurs) > 200:
            typer.echo(f"  … et {len(erreurs) - 200} autres.", err=True)
        raise typer.Exit(1)
    typer.echo(f"{dossier} : conforme au contrat {', '.join(v + '.x' for v in contrat.VERSIONS_CONNUES)}.")


def appeler_le_rag(config: dict, corpus: Path, adresse: str) -> Path:
    """Appelle les quatre endpoints du RAG (appel_du_rag/), vérifie ce qu'il rend ; rend le dossier reponses_du_rag/<version>/."""
    try:
        dossier = appeler.appeler(adresse, corpus, Path(config["chemins"]["corpus_documentaire"]), Path(config["chemins"]["resultats"]),
                                  afficher=typer.echo)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    erreurs = contrat.verifier_dossier(dossier, corpus)
    typer.echo(f"Réponses du RAG rangées dans {dossier} ; règle : {'respectée' if not erreurs else f'{len(erreurs)} écart(s)'}.")
    for e in erreurs[:20]:
        typer.echo(f"  - {e}", err=True)
    if erreurs:
        raise typer.Exit(1)
    return dossier


@app.command()
def appeler_rag(rag: str = typer.Option(None, help="l'adresse de les endpoints du RAG (http://…) ; par défaut, celle de config/kit.yaml"),
                corpus: Path = typer.Option(None, exists=True, file_okay=False,
                                            help="le dossier corpus/<version>/ ; par défaut, le dernier importé")):
    """Appelle les quatre endpoints du RAG : lui envoie les documents, lui pose les questions, range ce qu'il rend."""
    config = charger_config()
    appeler_le_rag(config, corpus or le_plus_recent(config, "corpus"), rag or config["rag"]["adresse"])


def le_plus_recent(config: dict, sous_dossier: str) -> Path:
    """Sans --corpus ou --rag : le dernier corpus importé, ou la dernière sortie du RAG (fichiers les plus récents).
    Le dossier choisi est affiché, pour qu'on sache toujours ce qui est évalué."""
    dossier = Path(config["chemins"]["resultats"]) / sous_dossier
    candidats = [d for d in dossier.glob("*") if d.is_dir() and any(d.iterdir())] if dossier.exists() else []
    if not candidats:
        typer.echo(f"Rien dans {dossier}/ : lancer d'abord « kit importer » (corpus) ou « kit appeler-rag » (réponses du RAG).",
                   err=True)
        raise typer.Exit(1)
    choisi = max(candidats, key=lambda d: max(f.stat().st_mtime for f in d.iterdir()))
    option = "--corpus" if sous_dossier == "corpus" else "--rag"
    typer.echo(f"{option} {choisi} (le plus récent ; préciser {option} pour en choisir un autre)")
    return choisi


# --- Les quatre évaluations (niveaux 1 à 4 du document 3, d'où les préfixes n1_ à n4_ des scores) ---

OPTION_CORPUS = typer.Option(None, exists=True, file_okay=False,
                             help="le dossier corpus/<version>/ ; par défaut, le dernier importé")
OPTION_RAG = typer.Option(None, exists=True, file_okay=False,
                          help="le dossier reponses_du_rag/<version_rag>/ déjà rempli ; par défaut, le plus récent")
OPTION_LANGFUSE = typer.Option(False, help="ne pas publier dans Langfuse")


def preparer(corpus: Path | None, rag: Path | None, ingestion_seule: bool = False):
    """Vérifie le contrat avant toute mesure, puis ouvre l'évaluation (corpus × version du RAG)."""
    config = charger_config()
    corpus = corpus or le_plus_recent(config, "corpus")
    rag = rag or le_plus_recent(config, "reponses_du_rag")
    erreurs = contrat.verifier_dossier(rag, corpus, ingestion_seule)
    if erreurs:
        typer.echo(f"Sorties du RAG non conformes au contrat ({len(erreurs)} problème(s)) :", err=True)
        for e in erreurs[:20]:
            typer.echo(f"  - {e}", err=True)
        raise typer.Exit(1)
    return config, publication.Evaluation(config, corpus, rag)


def afficher_scores(resultat: dict, niveau: int) -> None:
    for s in resultat["scores"]:
        if s["niveau"] == niveau:
            marge = f" ± {s['marge']:.2f}" if s["marge"] is not None else ""
            typer.echo(f"  {s['score']:<28} {s['valeur']}{marge}  (n = {s['n']})")


@app.command("evaluer-ingestion")
def evaluer_ingestion(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """1. Ingestion : rattachement des passages, liens_index, scores, passages non rattachés."""
    config, ev = preparer(corpus, rag, ingestion_seule=True)
    langfuse = None if sans_langfuse else client_langfuse(config)
    lignes, liens, non_rattaches = scores_ingestion.evaluer(ev)
    scores_ingestion.enregistrer(ev, liens, non_rattaches)
    if graphe_n1.a_un_graphe(ev):
        lignes += graphe_n1.lignes_violations(ev) + graphe_n1.lignes_justesse(ev, langfuse)
    resultat = publication.publier(ev, 1, lignes, langfuse)
    typer.echo(f"1. Ingestion — {ev.evaluation_id} → {ev.dossier}")
    afficher_scores(resultat, 1)
    if non_rattaches:
        typer.echo(f"  {len(non_rattaches)} passage(s) non rattaché(s) (passages_non_rattaches.jsonl) :")
        for p in non_rattaches:
            typer.echo(f"    - passage {p['passage_id']} ({p['question_id']}, {p['reference_source']} p. {p['page']}, "
                       f"{p['type_element']}) : {p['cause_probable']}")


@app.command("verifier-graphe")
def verifier_graphe(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG,
                    envoyer: bool = typer.Option(False, help="tirer les relations et les envoyer au métier dans Langfuse")):
    """Justesse du graphe : --envoyer pour faire juger 50 relations par le métier, puis sans option pour voir où il en est."""
    import json

    config, ev = preparer(corpus, rag, ingestion_seule=True)
    if not graphe_n1.a_un_graphe(ev):
        typer.echo(f"Le RAG est de type « {ev.rag.get('type_rag')} » : il n'a pas de graphe.", err=True)
        raise typer.Exit(1)
    langfuse = client_langfuse(config)
    if envoyer:
        n = graphe_n1.envoyer(ev, langfuse)
        typer.echo(f"Relations envoyées dans la file « {graphe_n1.FILE} » ({n} nouvelles). Le métier juge chacune avec "
                   f"le score « {graphe_n1.CONFIG_JUSTESSE} » (juste ou fausse), puis relancer « kit evaluer-ingestion ».")
        return
    if not (ev.fichiers / graphe_n1.ECHANTILLON).exists():
        typer.echo("Pas d'échantillon : lancer d'abord « kit verifier-graphe --envoyer ».", err=True)
        raise typer.Exit(1)
    lignes = graphe_n1.lignes_justesse(ev, langfuse)
    total = len(json.loads((ev.fichiers / graphe_n1.ECHANTILLON).read_text(encoding="utf-8")))
    typer.echo(f"Relations jugées par le métier : {len(lignes)} sur {total}.")
    if lignes:
        typer.echo(f"Justesse du graphe : {sum(l.valeur for l in lignes) / len(lignes):.0%}. "
                   f"Relancer « kit evaluer-ingestion » pour l'inscrire dans les résultats.")
        for l in lignes:
            if not l.valeur:
                typer.echo(f"  - fausse : {l.objet} ({l.detail})")


@app.command("evaluer-recherche")
def evaluer_recherche(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """2. Recherche : réussite à k, rappel, rang du premier bon chunk, fuite de droits."""
    config, ev = preparer(corpus, rag)
    lignes = scores_recherche.evaluer(ev, scores_ingestion.lire_liens(ev))
    resultat = publication.publier(ev, 2, lignes, None if sans_langfuse else client_langfuse(config))
    typer.echo(f"2. Recherche — {ev.evaluation_id} → {ev.dossier}")
    afficher_scores(resultat, 2)
    fuites = [l for l in lignes if l.score == "n2_fuite_droits" and l.valeur]
    for l in fuites:
        typer.echo(f"  FUITE DE DROITS — {l.question_id} : {l.detail}")


@app.command("evaluer-reponse")
def evaluer_reponse(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """3. Réponse : juge (exactitude), Ragas (fidélité, synthèse), abstention, citations, valeurs."""
    config, ev = preparer(corpus, rag)
    typer.echo("3. Réponse : le juge et Ragas notent les réponses (quelques minutes)…")
    lignes, croisement, file = scores_reponse.evaluer(ev, scores_ingestion.lire_liens(ev))
    langfuse = None if sans_langfuse else client_langfuse(config)
    resultat = publication.publier(ev, 3, lignes, langfuse)
    visibles = lambda objets: [o for o in objets if not ev.reservee(o["question_id"])]  # noqa: E731
    contrat.ecrire_jsonl(ev.fichiers / "croisement.jsonl", visibles(croisement))
    contrat.ecrire_jsonl(ev.fichiers / "relecture.jsonl", visibles(file))
    typer.echo(f"3. Réponse — {ev.evaluation_id} → {ev.dossier}")
    afficher_scores(resultat, 3)
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
    chemin = ev.fichiers / "verification_juge.json"
    with Session(base.moteur(config["chemins"]["base"])) as session:
        verdicts = {r.question_id: r.verdict for r in session.scalars(select(base.Resultat).where(
            base.Resultat.evaluation_id == ev.evaluation_id, base.Resultat.score == "n3_exactitude",
            base.Resultat.reservee.is_(False)))}
    if not verdicts:
        typer.echo("Aucun verdict du juge : lancer d'abord « kit evaluer-reponse ».", err=True)
        raise typer.Exit(1)
    v = config["verification_juge"]
    if envoyer:
        ids = relecture.echantillon(verdicts, v["taille_echantillon"])
        chemin.write_text(json.dumps({"juge": config["modeles"]["juge"], "questions": ids}, ensure_ascii=False,
                                     indent=2) + "\n", encoding="utf-8")
        n = relecture.envoyer(langfuse, "verification-juge", "Vérification du juge : noter juste, partielle ou fausse, "
                              "sans regarder la note du juge (prompt du juge)", [traces[q] for q in ids])
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
    (ev.fichiers / "verification_juge_resultat.json").write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n",
                                                                 encoding="utf-8")
    typer.echo(f"Notes du métier : {len(metier)} sur {len(ids)}.")
    if r["n"]:
        typer.echo(f"Accord juge / métier : {r['accord']:.0%} (seuil {v['accord_minimum']:.0%}) ; kappa de Cohen : "
                   f"{r['kappa']}. Juge {'VALIDÉ' if r['valide'] else 'NON validé'}.")
        for d in r["desaccords"]:
            typer.echo(f"  - {d['question_id']} : juge « {d['juge']} », métier « {d['metier']} »")


def afficher_scores_cles(resultat: dict, ev) -> None:
    """Les scores clés, en clair : c'est au métier de décider à leur lecture."""
    from kit.etape_5_resultats.rapport import en_clair, libelle

    typer.echo("  Les scores clés, à présenter au métier :")
    for s in resultat["scores_cles"]:
        typer.echo(f"    {libelle(s['score'])} : {en_clair(s['score'], s['valeur'], s['n'])}")
    typer.echo(f"  Rapport : {ev.dossier / 'RAPPORT.md'}")


@app.command("evaluer-bout-en-bout")
def evaluer_bout_en_bout(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG, sans_langfuse: bool = OPTION_LANGFUSE):
    """4. Bout en bout : score pondéré, erreurs graves, temps, coût, puis scores clés et rapport."""
    config, ev = preparer(corpus, rag)
    resultat = publication.publier(ev, 4, scores_bout_en_bout.evaluer(ev), None if sans_langfuse else client_langfuse(config))
    typer.echo(f"4. Bout en bout — {ev.evaluation_id} → {ev.dossier}")
    afficher_scores(resultat, 4)
    afficher_scores_cles(resultat, ev)


@app.command()
def evaluer(corpus: Path = OPTION_CORPUS,
            rag: str = typer.Option(None, help="l'adresse de les endpoints du RAG (http://…), ou un dossier reponses_du_rag/<version>/ "
                                               "déjà rempli ; par défaut, l'adresse de config/kit.yaml"),
            sans_langfuse: bool = OPTION_LANGFUSE):
    """Évalue un RAG de bout en bout : appelle ses quatre endpoints, puis enchaîne les évaluations 1 à 4 ; écrit les scores
    et le rapport (RAPPORT.md, rapport.html), et publie dans Langfuse."""
    config = charger_config()
    corpus = corpus or le_plus_recent(config, "corpus")
    rag = rag or config["rag"]["adresse"]
    rag = appeler_le_rag(config, corpus, rag) if rag.startswith("http") else Path(rag)
    evaluer_ingestion(corpus, rag, sans_langfuse)
    evaluer_recherche(corpus, rag, sans_langfuse)
    evaluer_reponse(corpus, rag, sans_langfuse)
    evaluer_bout_en_bout(corpus, rag, sans_langfuse)


@app.command()
def comparer(evaluation_a: Path = typer.Argument(..., exists=True, file_okay=False, help="resultats/evaluations/<evaluation_a>/"),
             evaluation_b: Path = typer.Argument(..., exists=True, file_okay=False, help="resultats/evaluations/<evaluation_b>/")):
    """Compare deux configurations déjà évaluées sur le même corpus : écarts de scores, questions gagnées et perdues,
    test de McNemar. Écrit resultats/comparaisons_de_configurations/<A>_contre_<B>/ : RAPPORT.md, et comparaison.json."""
    import json

    config = charger_config()
    try:
        r = comparaison.comparer(config, evaluation_a, evaluation_b)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    typer.echo(f"A = {r['a']}\nB = {r['b']}\n")
    typer.echo(f"  {'score':<28} {'A':>8} {'B':>8} {'écart':>8}  marge")
    for x in r["ecarts"]:
        marge = "" if x["marge"] is None else f"± {x['marge']:.2f}"
        signe = "" if x["significatif_seul"] is None else ("  > marge" if x["significatif_seul"] else "  < marge : ne prouve rien seul")
        nombre = lambda v, signe="": f"{v:{signe}.0f}" if abs(v) >= 100 else f"{v:{signe}.3f}"  # noqa: E731
        typer.echo(f"  {x['score']:<28} {nombre(x['a']):>8} {nombre(x['b']):>8} {nombre(x['ecart'], '+'):>8}  "
                   f"{marge}{signe}")
    questions = {}
    dossier_corpus = Path(config["chemins"]["resultats"]) / "corpus" / json.loads(
        (evaluation_a / "fichiers_techniques" / "evaluation.json").read_text(encoding="utf-8"))["version_corpus"]
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
    # Une comparaison n'appartient à aucune des deux évaluations : elle a son propre dossier.
    dossier = (Path(config["chemins"]["resultats"]) / "comparaisons_de_configurations" /
               f"{evaluation_a.name}_contre_{r['rag_b']['version_rag']}")
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "fichiers_techniques").mkdir(exist_ok=True)
    (dossier / "fichiers_techniques" / "comparaison.json").write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dossier / "RAPPORT.md").write_text(comparaison.markdown(r, questions), encoding="utf-8")
    typer.echo(f"\n  Rapport : {dossier / 'RAPPORT.md'}")


if __name__ == "__main__":
    app()
