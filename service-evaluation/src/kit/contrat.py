"""Le contrat entre un RAG et le kit (documentation/reference/contrat_des_fichiers.md) : lecture des fichiers, règles communes, vérification.

`verifier_dossier` contrôle un dossier corpus/<version>/ ou sorties_rag/<version>/ contre les schémas
JSON de documentation/reference/schemas/, puis, si on lui donne le corpus, la cohérence entre les fichiers
(toutes les questions ont une recherche et une réponse, les chunks cités existent…).
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

EVALUATION = Path(__file__).resolve().parents[2]  # le dossier service-evaluation/
SCHEMAS = EVALUATION / "documentation" / "reference" / "schemas"
VERSIONS_CONNUES = {"1"}  # versions majeures du contrat que ce kit sait lire

FICHIERS_CORPUS = {"corpus.json": "corpus", "documents.jsonl": "documents", "questions.jsonl": "questions",
                   "passages.jsonl": "passages", "pages_ocr.jsonl": "pages_ocr"}
FICHIERS_RAG = {"rag.json": "rag", "chunks.jsonl": "chunks", "pages_extraites.jsonl": "pages_extraites",
                "recherches.jsonl": "recherches", "reponses.jsonl": "reponses"}
OBLIGATOIRES_RAG = ["rag.json", "chunks.jsonl", "recherches.jsonl", "reponses.jsonl"]


# --- Règles communes ------------------------------------------------------------------------

def autorise(droits_acces: str, profil: str) -> bool:
    """Un profil voit un document réservé à « tous » ou à ce profil."""
    return droits_acces == "tous" or droits_acces == profil


def historique(question: dict, par_id: dict[str, dict]) -> list[dict]:
    """L'historique envoyé au RAG : les questions précédentes et leurs réponses attendues, de la plus ancienne
    à la plus récente (documentation/reference/contrat_des_fichiers.md, règles d'appel)."""
    chaine, q = [], question
    while q.get("question_precedente") and q["question_precedente"] in par_id and len(chaine) < 20:
        q = par_id[q["question_precedente"]]
        chaine.insert(0, {"question": q["question"], "reponse": q["reponse_attendue"]})
    return chaine


# --- Lecture -------------------------------------------------------------------------------

def lire_jsonl(chemin: Path) -> list[dict]:
    with Path(chemin).open(encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f if ligne.strip()]


def lire_json(chemin: Path) -> dict:
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def ecrire_jsonl(chemin: Path, objets) -> None:
    """Écrit un fichier JSON Lines ; un champ facultatif absent est omis."""
    with Path(chemin).open("w", encoding="utf-8") as f:
        for o in objets:
            f.write(json.dumps({k: v for k, v in o.items() if v is not None}, ensure_ascii=False) + "\n")


def charger_corpus(dossier: Path) -> dict:
    """Le corpus exporté par l'import : {"corpus": {...}, "documents": [...], "questions": [...], ...}."""
    dossier = Path(dossier)
    corpus = {"corpus": lire_json(dossier / "corpus.json")}
    for fichier, nom in FICHIERS_CORPUS.items():
        if fichier.endswith(".jsonl"):
            corpus[nom] = lire_jsonl(dossier / fichier)
    return corpus


# --- Vérification ---------------------------------------------------------------------------

def validateur(nom: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMAS / f"{nom}.schema.json").read_text(encoding="utf-8")))


def message(erreur) -> str:
    """Traduit une erreur jsonschema en une phrase lisible."""
    champ = ".".join(str(p) for p in erreur.absolute_path)
    ou = f"champ « {champ} » : " if champ else ""
    v = erreur.validator
    if v == "required":
        manquant = erreur.message.split("'")[1]
        return f"{ou}champ obligatoire « {manquant} » absent"
    if v == "additionalProperties":
        inconnus = erreur.message.split("(")[1].split(" were")[0].split(" was")[0]
        return f"{ou}champ(s) inconnu(s) du contrat : {inconnus}"
    if v == "enum":
        return f"{ou}« {erreur.instance} » n'est pas une valeur admise ({', '.join(erreur.validator_value)})"
    if v == "type":
        return f"{ou}doit être de type {erreur.validator_value} (reçu : {json.dumps(erreur.instance, ensure_ascii=False)})"
    if v == "minLength":
        return f"{ou}ne doit pas être vide"
    if v == "pattern":
        return f"{ou}« {erreur.instance} » n'est pas une date ISO 8601 (2026-11-20)"
    if v == "anyOf":
        return f"{ou}valeur invalide : {json.dumps(erreur.instance, ensure_ascii=False)}"
    return f"{ou}{erreur.message}"


def verifier_fichier(chemin: Path, schema: str) -> list[str]:
    """Contrôle chaque objet d'un fichier .json ou .jsonl ; rend les erreurs, une par ligne fautive."""
    v, erreurs = validateur(schema), []
    if chemin.suffix == ".json":
        try:
            objets = [(None, lire_json(chemin))]
        except json.JSONDecodeError as e:
            return [f"{chemin.name} : JSON illisible ({e})."]
    else:
        objets = []
        for n, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), start=1):
            if not ligne.strip():
                continue
            try:
                objets.append((n, json.loads(ligne)))
            except json.JSONDecodeError as e:
                erreurs.append(f"{chemin.name}, ligne {n} : JSON illisible ({e.msg}).")
    for n, objet in objets:
        ou = f"{chemin.name}" + (f", ligne {n}" if n else "")
        for e in sorted(v.iter_errors(objet), key=lambda e: list(e.absolute_path)):
            erreurs.append(f"{ou} : {message(e)}.")
    return erreurs


def version_majeure(objet: dict) -> str:
    return str(objet.get("contrat", "")).split(".")[0]


def verifier_dossier(dossier: Path, corpus: Path | None = None, ingestion_seule: bool = False) -> list[str]:
    """Vérifie un dossier du contrat ; rend la liste de ce qui ne va pas (vide si tout est conforme).

    `ingestion_seule` : seuls rag.json et chunks.jsonl sont exigés (niveau 1, avant de poser les questions).
    """
    dossier = Path(dossier)
    if (dossier / "corpus.json").exists():
        attendus, obligatoires = FICHIERS_CORPUS, list(FICHIERS_CORPUS)
        tete = "corpus.json"
    elif (dossier / "rag.json").exists():
        attendus = FICHIERS_RAG
        obligatoires = OBLIGATOIRES_RAG[:2] if ingestion_seule else list(OBLIGATOIRES_RAG)
        tete = "rag.json"
    else:
        return [f"{dossier} : ni corpus.json ni rag.json ; ce n'est pas un dossier du contrat."]
    erreurs = [f"{f} : fichier obligatoire absent." for f in obligatoires if not (dossier / f).exists()]
    for fichier, schema in attendus.items():
        if (dossier / fichier).exists():
            erreurs += verifier_fichier(dossier / fichier, schema)
    try:
        if version_majeure(lire_json(dossier / tete)) not in VERSIONS_CONNUES:
            erreurs.append(f"{tete} : version du contrat inconnue de ce kit (versions connues : "
                           f"{', '.join(v + '.x' for v in VERSIONS_CONNUES)}).")
    except (json.JSONDecodeError, OSError):
        pass
    if tete == "rag.json" and not erreurs:
        erreurs += coherence_rag(dossier, Path(corpus) if corpus else None)
    return erreurs


def coherence_rag(dossier: Path, dossier_corpus: Path | None) -> list[str]:
    """Contrôles entre fichiers des sorties d'un RAG, et avec le corpus si on le donne."""
    erreurs = []
    rag = lire_json(dossier / "rag.json")
    chunks = lire_jsonl(dossier / "chunks.jsonl")
    ids = [c["chunk_id"] for c in chunks]
    if len(set(ids)) != len(ids):
        doublons = sorted({i for i in ids if ids.count(i) > 1})
        erreurs.append(f"chunks.jsonl : chunk_id en double : {', '.join(doublons[:10])}.")
    ids = set(ids)
    if rag["type_rag"] in ("graphe", "hybride") and not (dossier / "graphe.ttl").exists():
        erreurs.append(f"graphe.ttl : obligatoire quand type_rag vaut « {rag['type_rag']} », et absent.")
    lire = lambda nom: lire_jsonl(dossier / nom) if (dossier / nom).exists() else None  # noqa: E731
    recherches, reponses = lire("recherches.jsonl"), lire("reponses.jsonl")
    for r in recherches or []:
        if r["k"] != rag["k"]:
            erreurs.append(f"recherches.jsonl, {r['question_id']} : k = {r['k']}, mais rag.json annonce k = {rag['k']} "
                           f"(le même k pour toutes les questions).")
        inconnus = [x["chunk_id"] for x in r["resultats"] if x["chunk_id"] not in ids]
        if inconnus:
            erreurs.append(f"recherches.jsonl, {r['question_id']} : chunk(s) absent(s) de chunks.jsonl : "
                           f"{', '.join(inconnus[:5])}.")
    for r in reponses or []:
        for champ in ("chunks_cites", "chunks_contexte"):
            inconnus = [c for c in r[champ] if c not in ids]
            if inconnus:
                erreurs.append(f"reponses.jsonl, {r['question_id']} : {champ} contient des chunks absents de "
                               f"chunks.jsonl : {', '.join(inconnus[:5])}.")
        hors_contexte = [c for c in r["chunks_cites"] if c not in r["chunks_contexte"]]
        if hors_contexte:
            erreurs.append(f"reponses.jsonl, {r['question_id']} : chunks cités qui n'étaient pas dans le contexte : "
                           f"{', '.join(hors_contexte[:5])}.")
    if dossier_corpus is None:
        return erreurs
    c = charger_corpus(dossier_corpus)
    questions = {q["question_id"]: q for q in c["questions"]}
    for nom, lignes in (("recherches.jsonl", recherches), ("reponses.jsonl", reponses)):
        if lignes is None:
            continue
        vues = [l["question_id"] for l in lignes]
        manquantes = sorted(set(questions) - set(vues))
        if manquantes:
            erreurs.append(f"{nom} : {len(manquantes)} question(s) du corpus sans ligne : {', '.join(manquantes[:10])}"
                           + (" …" if len(manquantes) > 10 else "") + ".")
        inconnues = sorted(set(vues) - set(questions))
        if inconnues:
            erreurs.append(f"{nom} : question(s) absente(s) du corpus : {', '.join(inconnues[:10])}.")
        for l in lignes:
            q = questions.get(l["question_id"])
            if q and l["profil"] != q["profil"]:
                erreurs.append(f"{nom}, {l['question_id']} : posée avec le profil « {l['profil']} » au lieu de "
                               f"« {q['profil']} ».")
    scannes = {d["reference_source"] for d in c["documents"] if d["format"] == "pdf_scanne"}
    if scannes and not (dossier / "pages_extraites.jsonl").exists():
        erreurs.append("pages_extraites.jsonl : obligatoire, le corpus contient des documents scannés.")
    return erreurs
