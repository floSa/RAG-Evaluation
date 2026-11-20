"""Niveau 2 — Recherche (document 3, section 7) : le bon chunk est-il retrouvé, bien classé, sans fuite de droits ?

Un « bon chunk » est un chunk lié par le niveau 1 à un passage de la question qui n'est pas un piège.
Une question est réussie selon « La réponse est dans » :
- un seul passage, ou plusieurs dont un seul suffit : un chunk lié à l'un des passages est dans les k premiers ;
- plusieurs passages à combiner : un chunk lié à chaque passage est dans les k premiers ;
- synthèse, pas de réponse, réponse non accessible : non comptée à ce niveau (sauf pour la fuite de droits).
"""

from kit import contrat
from kit.publication import Evaluation, Ligne

REGLES_COMPTEES = ("un_passage", "plusieurs_un_suffit", "plusieurs_a_combiner")


def liens_par_passage(liens: list[dict]) -> dict[int, set[str]]:
    resultat: dict[int, set[str]] = {}
    for l in liens:
        resultat.setdefault(l["passage_id"], set()).add(l["chunk_id"])
    return resultat


def reussie(regle: str, passages_attendus: list[set[str]], retrouves: list[str]) -> bool:
    """La règle de réussite, sur la liste des chunks retrouvés (déjà coupée à k)."""
    vus = set(retrouves)
    trouves = [bool(chunks & vus) for chunks in passages_attendus]
    if regle == "plusieurs_a_combiner":
        return bool(trouves) and all(trouves)
    return any(trouves)


def rang_premier(bons: set[str], retrouves: list[str]) -> float:
    """1 si le premier bon chunk est 1er, 1/2 s'il est 2e… ; 0 s'il est absent."""
    for rang, chunk_id in enumerate(retrouves, start=1):
        if chunk_id in bons:
            return 1 / rang
    return 0.0


def evaluer(ev: Evaluation, liens: list[dict]) -> list[Ligne]:
    par_passage = liens_par_passage(liens)
    chunks = {c["chunk_id"]: c for c in ev.fichier_rag("chunks.jsonl")}
    recherches = {r["question_id"]: r for r in ev.fichier_rag("recherches.jsonl")}
    k = ev.rag["k"]
    lignes: list[Ligne] = []
    for qid, q in ev.questions.items():
        r = recherches[qid]
        attributs = ev.attributs_question(qid)
        retrouves = [x["chunk_id"] for x in sorted(r["resultats"], key=lambda x: x["rang"])][:k]

        # fuite de droits : toutes les questions ; les droits font foi dans le corpus, sinon sur le chunk
        interdits = []
        for chunk_id in retrouves:
            c = chunks.get(chunk_id, {})
            doc = ev.documents.get(c.get("reference_source"))
            droits = doc["droits_acces"] if doc else c.get("droits_acces", "tous")
            if not contrat.autorise(droits, q["profil"]):
                interdits.append(chunk_id)
        lignes.append(Ligne("n2_fuite_droits", float(bool(interdits)), qid, attributs=attributs,
                            detail=f"chunks interdits au profil « {q['profil']} » : {', '.join(interdits)}"
                            if interdits else None))

        regle = q.get("reponse_est_dans")
        if q["reponse_dans_documents"] != "oui" or regle not in REGLES_COMPTEES:
            continue
        passages = [p for p in ev.corpus["passages"] if p["question_id"] == qid]
        attendus = [p for p in passages if p["repond"] != "piege"]
        par_attendu = [par_passage.get(p["passage_id"], set()) for p in attendus]
        bons = set().union(*par_attendu) if par_attendu else set()

        ok = reussie(regle, par_attendu, retrouves)
        rangs = [n for n, c in enumerate(retrouves, start=1) if c in bons]
        lignes.append(Ligne("n2_reussite_k", float(ok), qid, attributs=attributs,
                            detail=f"bons chunks aux rangs {rangs}" if rangs else "aucun bon chunk dans les k premiers"
                            + ("" if bons else " (aucun passage rattaché au niveau 1)")))
        lignes.append(Ligne("n2_rang_premier", rang_premier(bons, retrouves), qid, attributs=attributs))
        for p, lies in zip(attendus, par_attendu):
            lignes.append(Ligne("n2_rappel_k", float(bool(lies & set(retrouves))), qid, f"passage {p['passage_id']}",
                                attributs=attributs))
        for n in (1, 3, 5, 10):  # recommandé : aide à choisir k
            if n <= len(r["resultats"]):
                lignes.append(Ligne(f"n2_reussite_{n}", float(reussie(regle, par_attendu, retrouves[:n])), qid,
                                    attributs=attributs))
        if r.get("resultats_avant_reranking"):
            avant = [x["chunk_id"] for x in sorted(r["resultats_avant_reranking"], key=lambda x: x["rang"])][:k]
            lignes.append(Ligne("n2_reussite_avant_reranking", float(reussie(regle, par_attendu, avant)), qid,
                                attributs=attributs))

        # recommandé : un chunk périmé ou piège classé avant le premier bon chunk
        pieges = set().union(*[par_passage.get(p["passage_id"], set()) for p in passages if p["repond"] == "piege"])
        perimes = {c for c in retrouves
                   if not ev.documents.get(chunks.get(c, {}).get("reference_source"), {}).get("en_vigueur", True)}
        mauvais = (pieges | perimes) - bons
        premier_bon = rangs[0] if rangs else len(retrouves) + 1
        avant_le_bon = [c for c in retrouves[:premier_bon - 1] if c in mauvais]
        lignes.append(Ligne("n2_perimes_pieges", float(bool(avant_le_bon)), qid, attributs=attributs,
                            detail=f"classés avant le bon chunk : {', '.join(avant_le_bon)}" if avant_le_bon else None))
    return lignes
