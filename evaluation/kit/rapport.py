"""rapport.html : une page lisible par le métier (document 3, section 3).

Dans l'ordre : la décision, les scores niveau par niveau avec leur seuil, les questions à regarder en premier,
le croisement recherche × réponse, puis les scores par type de document. Aucune question réservée à la décision
n'y apparaît en détail.
"""

import html

from kit import contrat
from kit.publication import SCORES, Evaluation

LIBELLES = {
    "n1_documents_indexes": ("Documents indexés", "part des documents du corpus qui ont au moins un chunk"),
    "n1_metadonnees_completes": ("Métadonnées complètes", "part des chunks avec référence, version, page, type, droits"),
    "n1_passages_rattaches": ("Passages retrouvés dans l'index", "part des passages du métier reliés à un chunk"),
    "n1_passages_coupes": ("Passages coupés", "part des passages répartis sur deux chunks"),
    "n1_erreur_caracteres": ("Erreur de l'OCR (caractères)", "caractères à corriger ÷ caractères retapés"),
    "n1_erreur_mots": ("Erreur de l'OCR (mots)", "mots à corriger ÷ mots retapés"),
    "n1_graphe_violations": ("Violations de l'ontologie", "nombre de violations des règles SHACL"),
    "n1_graphe_justesse": ("Justesse du graphe", "part des relations jugées justes par le métier"),
    "n2_reussite_k": ("Bon passage retrouvé (réussite à k)", "part des questions dont la recherche ramène le bon passage"),
    "n2_rappel_k": ("Passages attendus retrouvés (rappel)", "part des passages attendus dans les k premiers"),
    "n2_rang_premier": ("Rang du premier bon passage (MRR)", "1 s'il est 1er, 1/2 s'il est 2e…"),
    "n2_fuite_droits": ("Fuites de droits", "questions où un document interdit au profil est retrouvé"),
    "n2_reussite_1": ("Réussite à 1", ""), "n2_reussite_3": ("Réussite à 3", ""), "n2_reussite_5": ("Réussite à 5", ""),
    "n2_reussite_10": ("Réussite à 10", ""), "n2_reussite_avant_reranking": ("Réussite avant reranking", ""),
    "n2_perimes_pieges": ("Périmé ou piège avant le bon passage", "part des questions concernées"),
    "n3_exactitude": ("Réponses justes", "juste = 1, partielle = 0,5, fausse = 0 (LLM juge)"),
    "n3_completude_listes": ("Listes complètes", "part des éléments attendus présents"),
    "n3_valeurs": ("Valeurs et calculs exacts", "valeurs attendues retrouvées dans la réponse"),
    "n3_abstention_correcte": ("Abstentions correctes", "le RAG dit ne pas savoir quand la réponse n'existe pas ou est interdite"),
    "n3_abstention_a_tort": ("Abstentions à tort", "le RAG ne répond pas alors qu'il avait le bon passage"),
    "n3_fidelite": ("Fidélité aux sources", "part des affirmations appuyées par les chunks (Ragas)"),
    "n3_citations": ("Citations correctes", "au moins une source citée est la bonne, sans piège ni document interdit"),
    "n3_erreurs_graves": ("Erreurs graves", "réponses fausses ou non fidèles à une question de gravité forte"),
    "n3_synthese": ("Synthèses", "note de 1 à 5 ramenée sur 100 % (Ragas)"),
    "n3_questions_suite": ("Questions de suite justes", ""), "n3_variantes": ("Variantes incohérentes", "part des groupes de variantes dont les réponses diffèrent"),
    "n4_score_pondere": ("Score pondéré", "réponses justes pondérées par fréquence × gravité"),
    "n4_erreurs_graves": ("Erreurs graves", "repris du niveau 3"),
    "n4_temps_median": ("Temps de réponse médian (ms)", ""), "n4_temps_p95": ("Temps de réponse à 95 % (ms)", ""),
    "n4_cout_moyen": ("Coût moyen par question (€)", ""),
}
NIVEAUX = {1: "Ingestion", 2: "Recherche", 3: "Réponse", 4: "Bout en bout"}
STYLE = """
body{font-family:system-ui,sans-serif;max-width:1050px;margin:2rem auto;padding:0 1rem;color:#1f2328;line-height:1.45}
h1{font-size:1.6rem}h2{margin-top:2.2rem;border-bottom:2px solid #d0d7de;padding-bottom:.3rem}
table{border-collapse:collapse;width:100%;margin:.6rem 0;font-size:.93rem}
th,td{border:1px solid #d0d7de;padding:.35rem .55rem;text-align:left;vertical-align:top}th{background:#f6f8fa}
.ok{color:#1a7f37;font-weight:600}.ko{color:#cf222e;font-weight:600}.neutre{color:#57606a}
.decision{padding:1rem 1.2rem;border-radius:8px;margin:1rem 0;font-size:1.05rem}
.oui{background:#dafbe1;border:1px solid #1a7f37}.non{background:#ffebe9;border:1px solid #cf222e}
small{color:#57606a}code{background:#f6f8fa;padding:0 .25rem}
"""


def e(x) -> str:
    return html.escape(str(x))


def proportion(score: str) -> bool:
    """Un score entre 0 et 1, affiché en pourcentage (et non un nombre, un temps ou un coût)."""
    return SCORES[score][1] or score in ("n1_erreur_caracteres", "n1_erreur_mots", "n3_synthese")


def format_valeur(s: dict) -> str:
    v = s["valeur"]
    if v is None:
        return "—"
    if s["score"] == "n4_cout_moyen":
        return f"{v:.4f} €"
    if not proportion(s["score"]):
        return f"{v:.0f}"
    texte = f"{v:.0%}"
    return texte + (f" <small>± {s['marge']:.0%}</small>" if s.get("marge") else "")


def etat(atteint) -> str:
    return {True: '<span class="ok">atteint</span>', False: '<span class="ko">non atteint</span>'}.get(
        atteint, '<span class="neutre">pas de seuil</span>')


def seuil(s: dict) -> str:
    if s.get("seuil") is None:
        return "—"
    sens = "≥" if s.get("sens", "min") == "min" else "≤"
    v = s["seuil"]
    return f"{sens} {v:.0%}" if proportion(s["score"]) else f"{sens} {v:g}"


def ecrire(ev: Evaluation, resultat: dict, lignes_base) -> None:
    """Écrit resultats/<evaluation_id>/rapport.html à partir des scores et des lignes de la base."""
    d = resultat["decision"]
    scores = resultat["scores"]
    seuils_sens = {k: v["sens"] for k, v in ev.seuils.items()}
    p = [f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Évaluation {e(ev.evaluation_id)}</title>"
         f"<style>{STYLE}</style></head><body>",
         f"<h1>Évaluation du RAG « {e(ev.rag['nom'] if 'nom' in ev.rag else ev.rag['version_rag'])} »</h1>",
         f"<p>Version du RAG <code>{e(ev.rag['version_rag'])}</code> (type {e(ev.rag.get('type_rag', '?'))}, "
         f"k = {e(ev.rag['k'])}) · corpus <code>{e(ev.version_corpus)}</code> · juge "
         f"<code>{e(ev.config['modeles']['juge']['modele'])}</code>, prompt {e(ev.config['modeles']['juge']['version_prompt'])}"
         f" · {len(ev.questions)} questions dont {sum(q['reservee_decision'] for q in ev.questions.values())} "
         f"réservées à la décision</p>"]

    # 1. La décision
    possible = d["mise_en_production_possible"]
    p.append(f"<h2>1. La décision</h2><div class='decision {'oui' if possible else 'non'}'><b>"
             f"{'Mise en production possible' if possible else 'Mise en production non recommandée'}</b>")
    bloquants = {LIBELLES.get(b["score"], (b["score"],))[0]: b["valeur"] for b in d["criteres_bloquants_declenches"]}
    if bloquants:
        p.append("<br>Critère(s) bloquant(s) déclenché(s), quel que soit le score : " + ", ".join(
            f"{e(nom)} = {v:g}" for nom, v in bloquants.items()))
    manquants = [x for x in d["seuils"] if x["atteint"] is False
                 and LIBELLES.get(x["score"], (x["score"],))[0] not in bloquants]
    if manquants:
        p.append("<br>Seuil(s) non atteint(s) sur les questions réservées : " + ", ".join(
            e(LIBELLES.get(x["score"], (x["score"],))[0]) for x in manquants))
    p.append("</div><p><small>Les seuils se jugent sur les questions <b>réservées à la décision</b>, jamais utilisées "
             "pour régler le RAG ; les critères bloquants (fuite de droits, erreur grave) sur toutes les questions. "
             "Seuils fixés par le métier dans <code>evaluation/config/seuils.json</code>.</small></p>")
    p.append("<table><tr><th>Score (questions réservées)</th><th>Valeur</th><th>n</th><th>Seuil</th><th>État</th></tr>")
    for x in d["seuils"]:
        x2 = {**x, "sens": seuils_sens.get(x["score"], "min")}
        p.append(f"<tr><td>{e(LIBELLES.get(x['score'], (x['score'],))[0])}</td><td>{format_valeur(x2)}</td>"
                 f"<td>{x['n']}</td><td>{seuil(x2)}</td><td>{etat(x['atteint'])}</td></tr>")
    p.append("</table>")

    # 2. Les scores, niveau par niveau
    p.append("<h2>2. Les scores, niveau par niveau</h2><p><small>Sur les questions non réservées. On lit les niveaux "
             "dans l'ordre : une réponse fausse vient souvent d'un passage perdu à l'ingestion ou mal retrouvé. "
             "La marge (±) est l'incertitude à 95 % ; un score calculé sur moins de 10 questions est une "
             "tendance.</small></p>")
    for niveau, nom in NIVEAUX.items():
        du_niveau = [s for s in scores if s["niveau"] == niveau]
        if not du_niveau:
            continue
        p.append(f"<h3>Niveau {niveau} — {nom}</h3><table><tr><th>Score</th><th>Ce qu'il mesure</th><th>Valeur</th>"
                 f"<th>n</th><th>Seuil</th><th>État</th></tr>")
        for s in du_niveau:
            libelle, aide = LIBELLES.get(s["score"], (s["score"], ""))
            s2 = {**s, "sens": seuils_sens.get(s["score"], "min")}
            p.append(f"<tr><td>{e(libelle)}<br><small><code>{e(s['score'])}</code></small></td><td><small>{e(aide)}"
                     f"</small></td><td>{format_valeur(s2)}</td><td>{s['n']}</td><td>{seuil(s2)}</td>"
                     f"<td>{etat(s['atteint']) if s['bloquant'] or s['seuil'] is not None else ''}</td></tr>")
        p.append("</table>")

    # 3. À regarder en premier
    visibles = [l for l in lignes_base if l.question_id and not l.reservee]
    a_voir = []
    for l in visibles:
        if l.score in ("n3_erreurs_graves", "n2_fuite_droits") and l.valeur:
            a_voir.append((0, l.question_id, LIBELLES[l.score][0], l.detail))
        elif l.score == "n3_exactitude" and l.verdict == "fausse":
            a_voir.append((1, l.question_id, "Réponse fausse", l.detail))
        elif l.score == "n3_abstention_correcte" and not l.valeur:
            a_voir.append((1, l.question_id, "A répondu au lieu de s'abstenir", l.detail))
        elif l.score == "n1_passages_rattaches" and not l.valeur:
            a_voir.append((2, l.question_id, "Passage absent de l'index", l.detail))
    p.append("<h2>3. Les questions à regarder en premier</h2><p><small>Erreurs graves et fuites d'abord, puis réponses "
             "fausses, puis passages perdus à l'ingestion. Le détail de chaque question est dans "
             "<code>resultats_par_question.csv</code> et dans Langfuse (expérience "
             f"<code>{e(ev.evaluation_id)}</code>).</small></p>")
    if a_voir:
        p.append("<table><tr><th>Question</th><th>Quoi</th><th>Détail</th></tr>")
        for _, qid, quoi, detail in sorted(a_voir, key=lambda x: (x[0], x[1])):
            p.append(f"<tr><td><b>{e(qid)}</b><br><small>{e(ev.questions[qid]['question'])}</small></td>"
                     f"<td>{e(quoi)}</td><td><small>{e((detail or '')[:400])}</small></td></tr>")
        p.append("</table>")
    else:
        p.append("<p>Rien à signaler.</p>")

    # 4. Croisement recherche × réponse
    chemin = ev.dossier / "croisement.jsonl"
    if chemin.exists():
        compte: dict[str, int] = {}
        for c in contrat.lire_jsonl(chemin):
            compte[c["diagnostic"]] = compte.get(c["diagnostic"], 0) + 1
        p.append("<h2>4. Où chercher la cause : recherche × réponse</h2><p><small>Pour chaque question qui a une "
                 "réponse dans les documents : le bon passage était-il retrouvé, et la réponse est-elle juste ? "
                 "« Recherche » : améliorer l'extraction, le découpage ou la recherche ; « génération » : le prompt, "
                 "les citations, le modèle (document 2).</small></p><table><tr><th>Diagnostic</th>"
                 "<th>Questions</th></tr>")
        for diag, n in sorted(compte.items(), key=lambda x: -x[1]):
            p.append(f"<tr><td>{e(diag)}</td><td>{n}</td></tr>")
        p.append("</table>")

    # 5. Par type de document
    principaux = [s for s in scores if s["score"] in ("n1_passages_rattaches", "n2_reussite_k", "n3_exactitude",
                                                        "n3_fidelite", "n4_score_pondere")]
    if principaux:
        types = sorted({t for s in principaux for t in s["ventilation"].get("type_document", {})})
        p.append("<h2>5. Par type de document</h2><table><tr><th>Score</th>" +
                 "".join(f"<th>{e('questions sans passage' if t == 'aucun' else t)}</th>" for t in types) + "</tr>")
        for s in principaux:
            cases = []
            for t in types:
                v = s["ventilation"].get("type_document", {}).get(t)
                cases.append("<td>—</td>" if not v or v["valeur"] is None else
                             f"<td>{v['valeur']:.0%} <small>(n = {v['n']})</small></td>")
            p.append(f"<tr><td>{e(LIBELLES[s['score']][0])}</td>{''.join(cases)}</tr>")
        p.append("</table><p><small>Toutes les ventilations (difficulté, type de réponse, profil, type d'élément, "
                 "service…) sont dans <code>scores.json</code>.</small></p>")
    p.append(f"<p><small>Fichiers : <code>{e(ev.dossier)}</code> — evaluation.json, scores.json, "
             f"resultats_par_question.csv, liens_index.jsonl, passages_non_rattaches.jsonl, croisement.jsonl, "
             f"relecture.jsonl.</small></p></body></html>")
    (ev.dossier / "rapport.html").write_text("\n".join(p), encoding="utf-8")

