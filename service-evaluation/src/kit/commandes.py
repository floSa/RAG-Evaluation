"""La commande `kit` : une sous-commande par action."""

from pathlib import Path

import json

import typer

from kit import base
from kit import contrat
from kit.appel_du_rag import appeler
from kit.appel_du_rag import boite_noire
from kit.config import charger_config, cle, client_langfuse
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
def importer(fichier: Path = typer.Argument(..., exists=True, dir_okay=False, help="le fichier Excel du métier, ou un fichier .json de même contenu"),
             sans_langfuse: bool = typer.Option(False, help="ne pas créer le jeu de données dans Langfuse")):
    """Importe le corpus (fichier Excel du métier, ou .json) : contrôles, base, export corpus/<version>/, jeu de données Langfuse."""
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


def appeler_la_boite_noire(config: dict, corpus: Path) -> Path:
    """Pose les questions à un RAG en boîte noire (API compatible OpenAI, section boite_noire de config/kit.yaml)."""
    reglages = config.get("boite_noire") or {}
    if not reglages.get("adresse") or not reglages.get("modele"):
        typer.echo("La section « boite_noire » de config/kit.yaml n'a pas d'adresse ou de modèle.", err=True)
        raise typer.Exit(1)
    try:
        dossier = boite_noire.appeler(reglages, cle(reglages["variable_cle"]), corpus, Path(config["chemins"]["resultats"]),
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


OPTION_BOITE_NOIRE = typer.Option(False, "--boite-noire", help="le RAG n'a qu'une API compatible OpenAI (section "
                                  "boite_noire de config/kit.yaml) : on lui pose seulement les questions")


@app.command()
def appeler_rag(rag: str = typer.Option(None, help="l'adresse des endpoints du RAG (http://…) ; par défaut, celle de config/kit.yaml"),
                corpus: Path = typer.Option(None, exists=True, file_okay=False,
                                            help="le dossier corpus/<version>/ ; par défaut, le dernier importé"),
                en_boite_noire: bool = OPTION_BOITE_NOIRE):
    """Appelle les quatre endpoints du RAG : lui envoie les documents, lui pose les questions, range ce qu'il rend.
    Avec --boite-noire : pose seulement les questions à son API compatible OpenAI."""
    config = charger_config()
    corpus = corpus or le_plus_recent(config, "corpus")
    if en_boite_noire:
        appeler_la_boite_noire(config, corpus)
    else:
        appeler_le_rag(config, corpus, rag or config["rag"]["adresse"])


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
        lignes += graphe_n1.lignes_violations(ev) + graphe_n1.lignes_justesse(ev, langfuse or langfuse_si_possible(config))
    resultat = publication.publier(ev, 1, lignes, langfuse)
    typer.echo(f"1. Ingestion — {ev.evaluation_id} → {ev.dossier}")
    afficher_scores(resultat, 1)
    if non_rattaches:
        typer.echo(f"  {len(non_rattaches)} passage(s) non rattaché(s) (passages_non_rattaches.jsonl) :")
        for p in non_rattaches:
            typer.echo(f"    - passage {p['passage_id']} ({p['question_id']}, {p['reference_source']} p. {p['page']}, "
                       f"{p['type_element']}) : {p['cause_probable']}")


def langfuse_si_possible(config: dict):
    """Le client Langfuse si ses clés sont dans .env ; sinon None : le service lit alors seulement les fichiers Excel."""
    try:
        return client_langfuse(config)
    except RuntimeError:
        return None


@app.command("verifier-graphe")
def verifier_graphe(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG,
                    preparer_fichier: bool = typer.Option(False, "--preparer", help="tirer les relations et écrire le "
                                                          "fichier Excel que le métier remplit"),
                    aussi_langfuse: bool = typer.Option(False, "--langfuse", help="avec --preparer : mettre aussi les "
                                                        "relations dans la file Langfuse, pour un métier qui préfère y juger")):
    """Justesse du graphe : --preparer écrit le fichier Excel des relations à juger ; sans option, dit où en est le
    métier. Les jugements entrent dans les résultats à la prochaine évaluation de l'ingestion."""
    from kit.etape_3_evaluation_reponse import fichier_metier

    config, ev = preparer(corpus, rag, ingestion_seule=True)
    if not graphe_n1.a_un_graphe(ev):
        typer.echo(f"Le RAG est de type « {ev.rag.get('type_rag')} » : il n'a pas de graphe.", err=True)
        raise typer.Exit(1)
    fichier = ev.dossier / graphe_n1.FICHIER
    if preparer_fichier:
        if fichier_metier.deja_rempli(fichier, fichier_metier.FEUILLE_GRAPHE, fichier_metier.COLONNES_GRAPHE, "jugement"):
            typer.echo(f"{fichier} est déjà rempli en partie : le supprimer pour tirer d'autres relations.", err=True)
            raise typer.Exit(1)
        tirees = graphe_n1.tirer(ev)
        ev.dossier.mkdir(parents=True, exist_ok=True)
        fichier_metier.ecrire_graphe(fichier, [{"relation": r["texte"], "reference_source": r["reference_source"],
                                                "page": r["page"], "passage": r["passage"]} for r in tirees])
        typer.echo(f"Fichier à faire remplir par le métier : {fichier} ({len(tirees)} relations).")
        if aussi_langfuse:
            n = graphe_n1.envoyer(ev, client_langfuse(config), tirees)
            typer.echo(f"Aussi dans la file Langfuse « {graphe_n1.FILE} » ({n} nouvelles), score « "
                       f"{graphe_n1.CONFIG_JUSTESSE} ».")
        typer.echo("Une fois les relations jugées, relancer « kit evaluer-ingestion ».")
        return
    if not (ev.fichiers / graphe_n1.ECHANTILLON).exists():
        typer.echo("Pas de relations tirées : lancer d'abord « kit verifier-graphe --preparer ».", err=True)
        raise typer.Exit(1)
    lignes = graphe_n1.lignes_justesse(ev, langfuse_si_possible(config))
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
    lignes, croisement, file = scores_reponse.evaluer(ev, [] if ev.boite_noire else scores_ingestion.lire_liens(ev))
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
    if diagnostics:
        typer.echo("  Croisement recherche × réponse (questions non réservées) :")
    for d, n in sorted(diagnostics.items(), key=lambda x: -x[1]):
        typer.echo(f"    {n:>3}  {d}")
    ecrire_relecture(ev, visibles(file), lignes)
    if langfuse:
        traces = publication.experience_langfuse(ev, langfuse).get("traces", {})
        n = relecture.envoyer(langfuse, "relecture-reponses", "Réponses à relire par le métier (document 3, section 8)",
                              [traces.get(f["question_id"]) for f in visibles(file)])
        typer.echo(f"  Aussi dans la file Langfuse « relecture-reponses » : {n} ajoutée(s).")


def ecrire_relecture(ev, file: list[dict], lignes) -> None:
    """Le fichier Excel des réponses à relire par le métier : la question, la bonne réponse, la réponse du RAG, la note
    du juge et ce qu'il a vu. On n'écrase jamais un fichier que le métier a commencé à remplir."""
    from kit.etape_3_evaluation_reponse import fichier_metier

    fichier = ev.dossier / "relecture_reponses.xlsx"
    if fichier_metier.deja_rempli(fichier, fichier_metier.FEUILLE_RELECTURE, fichier_metier.COLONNES_RELECTURE, "accord"):
        typer.echo(f"  {fichier} est déjà rempli en partie par le métier : gardé tel quel.")
        return
    juge = {l.question_id: l for l in lignes if l.score == "n3_exactitude"}
    reponses = {r["question_id"]: r for r in ev.fichier_rag("reponses.jsonl")}
    a_relire = []
    for f in file:
        q, r, j = ev.questions[f["question_id"]], reponses.get(f["question_id"], {}), juge.get(f["question_id"])
        a_relire.append({"question_id": f["question_id"], "motif": f["motif"], "question": q["question"],
                         "reponse_attendue": q.get("reponse_attendue"), "points_cles": fichier_metier.points_cles(q),
                         "reponse_rag": ("(Le RAG dit ne pas savoir.) " if r.get("abstention") else "") + (r.get("reponse") or ""),
                         "note_juge": j.verdict if j else "", "justification": (j.detail or "") if j else ""})
    ev.dossier.mkdir(parents=True, exist_ok=True)
    fichier_metier.ecrire_relecture(fichier, a_relire)
    typer.echo(f"  Réponses à relire par le métier : {len(a_relire)}, dans {fichier}. Une fois rempli, lancer "
               f"« kit lire-relecture ».")


@app.command("lire-relecture")
def lire_relecture(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG):
    """Lit la relecture des réponses par le métier (fichier relecture_reponses.xlsx, ou file Langfuse), et la reporte
    dans le rapport : les réponses où il n'est pas d'accord avec le juge, avec son commentaire."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from kit.etape_3_evaluation_reponse import fichier_metier
    from kit.etape_5_resultats import rapport

    config, ev = preparer(corpus, rag)
    fichier = ev.dossier / "relecture_reponses.xlsx"
    if not fichier.exists():
        typer.echo("Pas de fichier de relecture : lancer d'abord « kit evaluer ».", err=True)
        raise typer.Exit(1)
    r = fichier_metier.lire_relecture(fichier)
    langfuse = langfuse_si_possible(config)
    if langfuse is not None and r["sans_reponse"]:     # un métier qui a relu dans Langfuse plutôt que dans le fichier
        traces = publication.experience_langfuse(ev, langfuse).get("traces", {})
        notes = relecture.notes_metier(langfuse, [traces[q] for q in r["sans_reponse"] if q in traces])
        juges = {l["question_id"]: l.get("note_juge") for l in fichier_metier.lire_tableau(
            fichier, fichier_metier.FEUILLE_RELECTURE, fichier_metier.COLONNES_RELECTURE)}
        for q in list(r["sans_reponse"]):
            note = notes.get(traces.get(q))
            if note:
                r["sans_reponse"].remove(q)
                r["relues"].append(q)
                if note != juges.get(q):
                    r["desaccords"].append({"question_id": q, "juge": juges.get(q), "metier": note, "commentaire": ""})
    (ev.fichiers / "relecture_resultat.json").write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n",
                                                         encoding="utf-8")
    typer.echo(f"Réponses relues par le métier : {len(r['relues'])} sur {len(r['relues']) + len(r['sans_reponse'])} ; "
               f"en désaccord avec le juge : {len(r['desaccords'])}.")
    for d in r["desaccords"]:
        typer.echo(f"  - {d['question_id']} : juge « {d['juge']} », métier « {d['metier']} »"
                   + (f" — {d['commentaire']}" if d["commentaire"] else ""))
    with Session(base.moteur(config["chemins"]["base"])) as session:
        toutes = session.scalars(select(base.Resultat).where(base.Resultat.evaluation_id == ev.evaluation_id)).all()
        rapport.ecrire(ev, json.loads((ev.fichiers / "scores.json").read_text(encoding="utf-8")), toutes)
    typer.echo(f"Rapport mis à jour : {ev.dossier / 'RAPPORT.md'}")


@app.command("verifier-juge")
def verifier_juge(corpus: Path = OPTION_CORPUS, rag: Path = OPTION_RAG,
                  preparer_fichier: bool = typer.Option(False, "--preparer", help="tirer les réponses au hasard et écrire "
                                                        "le fichier Excel que le métier remplit"),
                  aussi_langfuse: bool = typer.Option(False, "--langfuse", help="avec --preparer : mettre aussi les "
                                                      "réponses dans la file Langfuse, pour un métier qui préfère y noter")):
    """Vérification du juge : --preparer écrit le fichier Excel à faire remplir par le métier ; sans option, lit ses
    notes dans ce fichier, calcule l'accord avec le juge, et le reporte en tête du rapport."""
    import json

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from kit.etape_3_evaluation_reponse import fichier_metier
    from kit.etape_5_resultats import rapport

    config, ev = preparer(corpus, rag)
    with Session(base.moteur(config["chemins"]["base"])) as session:
        verdicts = {r.question_id: r.verdict for r in session.scalars(select(base.Resultat).where(
            base.Resultat.evaluation_id == ev.evaluation_id, base.Resultat.score == "n3_exactitude",
            base.Resultat.reservee.is_(False)))}
    if not verdicts:
        typer.echo("Aucun verdict du juge : lancer d'abord « kit evaluer ».", err=True)
        raise typer.Exit(1)
    v = config["verification_juge"]
    fichier = ev.dossier / "verification_juge.xlsx"
    if preparer_fichier:
        if fichier.exists():
            typer.echo(f"{fichier} existe déjà : le supprimer pour tirer d'autres réponses.", err=True)
            raise typer.Exit(1)
        reponses = {r["question_id"]: r for r in ev.fichier_rag("reponses.jsonl")}
        lignes = []
        for q in relecture.echantillon(verdicts, v["taille_echantillon"]):
            question, r = ev.questions[q], reponses.get(q, {})
            texte = ("(Le RAG dit ne pas savoir.) " if r.get("abstention") else "") + (r.get("reponse") or "")
            lignes.append({"question_id": q, "question": question["question"],
                           "reponse_attendue": question.get("reponse_attendue"),
                           "points_cles": fichier_metier.points_cles(question), "reponse_rag": texte})
        fichier_metier.ecrire(fichier, lignes)
        typer.echo(f"Fichier à faire remplir par le métier : {fichier} ({len(lignes)} réponses). Une fois rempli, le "
                   f"remettre à la même place, puis relancer « kit verifier-juge ».")
        if aussi_langfuse:
            langfuse = client_langfuse(config)
            traces = publication.experience_langfuse(ev, langfuse).get("traces", {})
            n = relecture.envoyer(langfuse, "verification-juge", "Vérification du juge : noter juste, partielle ou "
                                  "fausse, sans regarder la note du juge (prompt du juge)",
                                  [traces[l["question_id"]] for l in lignes if l["question_id"] in traces])
            typer.echo(f"Aussi dans la file Langfuse « verification-juge » ({n} nouvelles), score « "
                       f"{relecture.CONFIG_VERDICT} ».")
        return
    if not fichier.exists():
        typer.echo("Pas de fichier de vérification : lancer d'abord « kit verifier-juge --preparer ».", err=True)
        raise typer.Exit(1)
    metier, commentaires, manquantes = fichier_metier.lire(fichier)
    langfuse = langfuse_si_possible(config)
    if langfuse is not None and manquantes:     # un métier qui a noté dans Langfuse plutôt que dans le fichier
        traces = publication.experience_langfuse(ev, langfuse).get("traces", {})
        notes = relecture.notes_metier(langfuse, [traces[q] for q in manquantes if q in traces])
        for q in list(manquantes):
            if traces.get(q) in notes:
                metier[q] = notes[traces[q]]
                manquantes.remove(q)
    r = relecture.accord({q: verdicts[q] for q in metier if q in verdicts}, metier)
    r["accord_minimum"] = v["accord_minimum"]
    r["juge"] = {"modele": config["modeles"]["juge"]["modele"], "version_prompt": config["modeles"]["juge"]["version_prompt"]}
    r["valide"] = r["accord"] is not None and not manquantes and r["accord"] >= v["accord_minimum"]
    for d in r["desaccords"]:
        if d["question_id"] in commentaires:
            d["commentaire_metier"] = commentaires[d["question_id"]]
    (ev.fichiers / "verification_juge_resultat.json").write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n",
                                                                 encoding="utf-8")
    typer.echo(f"Notes du métier : {len(metier)} sur {len(metier) + len(manquantes)}."
               + (f" Sans note : {', '.join(manquantes)}." if manquantes else ""))
    if r["n"]:
        typer.echo(f"Accord juge / métier : {r['accord']:.0%} (il en faut {v['accord_minimum']:.0%}) ; kappa de Cohen : "
                   f"{r['kappa']}. Juge {'validé' if r['valide'] else 'NON validé'}.")
        for d in r["desaccords"]:
            typer.echo(f"  - {d['question_id']} : juge « {d['juge']} », métier « {d['metier']} »")
    # le rapport dit désormais si l'on peut croire le juge
    with Session(base.moteur(config["chemins"]["base"])) as session:
        toutes = session.scalars(select(base.Resultat).where(base.Resultat.evaluation_id == ev.evaluation_id)).all()
        resultat = json.loads((ev.fichiers / "scores.json").read_text(encoding="utf-8"))
        rapport.ecrire(ev, resultat, toutes)
    typer.echo(f"Rapport mis à jour : {ev.dossier / 'RAPPORT.md'}")


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
            rag: str = typer.Option(None, help="l'adresse des endpoints du RAG (http://…), ou un dossier reponses_du_rag/<version>/ "
                                               "déjà rempli ; par défaut, l'adresse de config/kit.yaml"),
            sans_langfuse: bool = OPTION_LANGFUSE, en_boite_noire: bool = OPTION_BOITE_NOIRE):
    """Évalue un RAG de bout en bout : appelle ses quatre endpoints, puis enchaîne les évaluations 1 à 4 ; écrit les scores
    et le rapport (RAPPORT.md, rapport.html), et publie dans Langfuse. Avec --boite-noire : pose seulement les questions
    à son API compatible OpenAI, et fait les évaluations 3 et 4."""
    config = charger_config()
    corpus = corpus or le_plus_recent(config, "corpus")
    if en_boite_noire:
        rag = appeler_la_boite_noire(config, corpus)
    else:
        rag = rag or config["rag"]["adresse"]
        rag = appeler_le_rag(config, corpus, rag) if rag.startswith("http") else Path(rag)
    if contrat.boite_noire(rag):
        typer.echo("RAG en boîte noire : pas d'évaluation de l'ingestion ni de la recherche (on ne voit ni ce qu'il a lu, "
                   "ni ce qu'il a ramené).")
    else:
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
