"""Les rapports d'une évaluation (document 3, section 3) : ce qu'a donné UNE configuration du RAG.

Deux fichiers, même contenu :
- RAPPORT.md : lisible directement sur GitHub ou dans un éditeur ;
- rapport.html : la même chose en page web.

Dans l'ordre : la configuration évaluée, la décision, les scores évaluation par évaluation, les questions à regarder en
premier, le croisement recherche × réponse, les scores par type de document, puis les fichiers techniques.
Aucune question réservée à la décision n'y apparaît en détail.
"""

import html

from kit import contrat
from kit.etape_5_resultats.publication import SCORES, Evaluation

# Pour chaque score : son nom, et ce qu'il compte, en clair.
LIBELLES = {
    "n1_documents_indexes": ("Documents présents dans la base",
                             "documents qui ont au moins un morceau dans la base ÷ documents envoyés"),
    "n1_metadonnees_completes": ("Étiquettes complètes",
                                 "morceaux qui indiquent leur document, leur page et leurs droits d'accès ÷ morceaux"),
    "n1_passages_rattaches": ("Passages du métier retrouvés",
                              "passages du métier retrouvés dans un morceau de la base ÷ passages du métier"),
    "n1_passages_coupes": ("Passages coupés en deux",
                           "passages retrouvés seulement à cheval sur deux morceaux ÷ passages du métier"),
    "n1_erreur_caracteres": ("Erreur de lecture des scans (caractères)",
                             "caractères mal lus ÷ caractères des pages scannées retapées par le métier"),
    "n1_erreur_mots": ("Erreur de lecture des scans (mots)", "mots mal lus ÷ mots des pages scannées retapées"),
    "n1_graphe_violations": ("Violations des règles du graphe", "relations du graphe qui ne respectent pas l'ontologie"),
    "n1_graphe_justesse": ("Justesse du graphe", "relations jugées justes par le métier ÷ relations relues"),
    "n2_reussite_k": ("Bon passage ramené",
                      "questions où un morceau contenant le passage du métier est parmi les k ramenés ÷ questions"),
    "n2_rappel_k": ("Passages nécessaires ramenés", "passages attendus parmi les k morceaux ramenés ÷ passages attendus"),
    "n2_rang_premier": ("Bon morceau en tête", "1 si le premier bon morceau est 1er, 1/2 s'il est 2e… ; moyenne"),
    "n2_fuite_droits": ("Fuites de droits", "questions où un morceau d'un document interdit au profil est ramené"),
    "n2_reussite_1": ("Bon passage ramené, si k = 1", "le même score, si la recherche ne ramenait qu'un morceau"),
    "n2_reussite_3": ("Bon passage ramené, si k = 3", "le même score, si la recherche ramenait 3 morceaux"),
    "n2_reussite_5": ("Bon passage ramené, si k = 5", "le même score, si la recherche ramenait 5 morceaux"),
    "n2_reussite_10": ("Bon passage ramené, si k = 10", "le même score, si la recherche ramenait 10 morceaux"),
    "n2_reussite_avant_reranking": ("Bon passage ramené, avant reclassement", "le même score, avant le reranker"),
    "n2_perimes_pieges": ("Pièges ou version périmée devant le bon",
                          "questions où un piège ou une ancienne version passe devant le bon morceau ÷ questions"),
    "n3_exactitude": ("Réponses justes",
                      "juste = 1, partielle = 0,5, fausse = 0, selon le juge qui compare aux points clés du métier"),
    "n3_completude_listes": ("Listes complètes", "éléments attendus présents dans la réponse ÷ éléments attendus"),
    "n3_valeurs": ("Chiffres exacts", "valeurs attendues présentes dans la réponse, avec la bonne unité ÷ valeurs"),
    "n3_abstention_correcte": ("Sait dire « je ne sais pas »",
                               "abstentions ÷ questions sans réponse dans les documents ou interdites au profil"),
    "n3_abstention_a_tort": ("Abstentions à tort", "abstentions alors que le bon passage était ramené ÷ questions"),
    "n3_fidelite": ("Fidélité aux documents", "affirmations de la réponse appuyées par les morceaux ÷ affirmations"),
    "n3_citations": ("Bonnes sources citées",
                     "questions où une source citée contient le passage du métier, sans piège ni document interdit"),
    "n3_erreurs_graves": ("Erreurs graves",
                          "réponses fausses, inventées ou données au lieu de s'abstenir, sur une question grave"),
    "n3_synthese": ("Synthèses", "note de 1 à 5 donnée par le juge sur une grille, ramenée sur 100 %"),
    "n3_second_avis": ("Accord avec un second juge", "questions où un second juge donne le même verdict ÷ questions"),
    "n3_questions_suite": ("Questions de suite justes", "même note que les réponses justes, sur les questions de suite"),
    "n3_variantes": ("Reformulations incohérentes",
                     "groupes de questions reformulées dont les réponses diffèrent ÷ groupes"),
    "n4_score_pondere": ("Score pondéré",
                         "notes des réponses, chaque question pesant fréquence × gravité (de 1 à 9)"),
    "n4_erreurs_graves": ("Erreurs graves", "repris de l'évaluation de la réponse"),
    "n4_temps_median": ("Temps de réponse médian", "la moitié des questions ont leur réponse en moins de ce temps"),
    "n4_temps_p95": ("Temps de réponse à 95 %", "95 % des questions ont leur réponse en moins de ce temps"),
    "n4_cout_moyen": ("Coût par question", "coût moyen d'une réponse"),
}
# Pour chaque évaluation : son nom, et ce qu'elle vérifie, en une phrase.
NIVEAUX = {
    1: ("Ingestion", "On vérifie que le service d'ingestion n'a rien perdu ni abîmé en découpant les documents, en les "
                     "vectorisant et en les rangeant dans la base vectorielle."),
    2: ("Recherche", "On vérifie que, pour chaque question, la recherche ramène les morceaux qui contiennent la réponse, "
                     "et jamais un morceau d'un document interdit à la personne qui pose la question."),
    3: ("Réponse", "On vérifie que la réponse écrite par le RAG est juste, qu'elle ne dit que ce que disent les "
                   "documents, et que le RAG sait dire « je ne sais pas »."),
    4: ("Bout en bout", "On vérifie que le RAG est bon sur les questions qui comptent le plus, assez rapide et pas "
                        "trop cher."),
}
FICHIERS = [
    ("rapport.html", "ce rapport, en page web"),
    ("scores.json", "tous les scores, avec leur marge d'erreur et leur détail par type de document, de question…"),
    ("resultats_par_question.csv", "une ligne par question et par score, avec la justification du juge : "
                                   "à ouvrir dans un tableur"),
    ("croisement.jsonl", "pour chaque question : bon passage ramené ou non, réponse juste ou non"),
    ("liens_index.jsonl", "chaque passage du métier et le morceau de la base où il a été retrouvé"),
    ("passages_non_rattaches.jsonl", "les passages du métier introuvables dans la base, avec leur cause probable"),
    ("relecture.jsonl", "les réponses que le métier doit relire, et pourquoi"),
    ("evaluation.json", "ce qui a été évalué : versions du corpus, du kit, du RAG, du juge, et les seuils"),
]
TEMPS = ("n4_temps_median", "n4_temps_p95")


# --- Mise en forme des valeurs ----------------------------------------------------------------

def libelle(score: str) -> str:
    return LIBELLES.get(score, (score, ""))[0]


def aide(score: str) -> str:
    return LIBELLES.get(score, (score, ""))[1]


def proportion(score: str) -> bool:
    """Un score entre 0 et 1, affiché en pourcentage (et non un nombre, un temps ou un coût)."""
    return SCORES.get(score, ("", False))[1] or score in ("n1_erreur_caracteres", "n1_erreur_mots", "n3_synthese")


def nombre(v: float, decimales: int = 0) -> str:
    return f"{v:.{decimales}f}".replace(".", ",")


def texte_valeur(score: str, v, marge=None) -> str:
    if v is None:
        return "—"
    if score == "n4_cout_moyen":
        return f"{nombre(v, 2)} €"
    if score in TEMPS:
        return f"{nombre(v / 1000, 1)} s"
    if proportion(score):
        return f"{nombre(v * 100)} %" + (f" ± {nombre(marge * 100)}" if marge else "")
    return nombre(v)


def texte_seuil(score: str, seuil, sens: str) -> str:
    if seuil is None:
        return "—"
    signe = "≥" if sens == "min" else "≤"
    return f"{signe} {texte_valeur(score, seuil)}"


def texte_atteint(atteint) -> str:
    return {True: "✅ oui", False: "❌ non"}.get(atteint, "—")


def configuration(rag: dict) -> str:
    """La configuration évaluée, en une ligne : type, k, puis chaque réglage."""
    v = rag.get("versions", {})
    reglages = [f"RAG {rag.get('type_rag', '?')}", f"k = {rag.get('k', '?')}"]
    for cle, nom in (("decoupage", "découpage"), ("embedding", "embeddings"), ("generation", "génération"),
                     ("prompt", "prompt"), ("reranker", "reranker")):
        if cle in v:
            reglages.append(f"{nom} {v[cle]}")
    return ", ".join(reglages)


# --- Le contenu, commun aux deux rapports ------------------------------------------------------

def questions_a_voir(ev: Evaluation, lignes_base) -> list[tuple]:
    """Erreurs graves et fuites d'abord, puis réponses fausses, puis passages perdus à l'ingestion."""
    a_voir = []
    for l in lignes_base:
        if not l.question_id or l.reservee:
            continue
        if l.score in ("n3_erreurs_graves", "n2_fuite_droits") and l.valeur:
            a_voir.append((0, l.question_id, "Erreur grave" if l.score == "n3_erreurs_graves" else "Fuite de droits",
                           l.detail))
        elif l.score == "n3_exactitude" and l.verdict == "fausse":
            a_voir.append((1, l.question_id, "Réponse fausse", l.detail))
        elif l.score == "n3_abstention_correcte" and not l.valeur:
            a_voir.append((1, l.question_id, "A répondu au lieu de s'abstenir", l.detail))
        elif l.score == "n1_passages_rattaches" and not l.valeur:
            a_voir.append((2, l.question_id, "Passage absent de la base", l.detail))
    graves = {qid for prio, qid, _, _ in a_voir if prio == 0}
    # une erreur grave est aussi une réponse fausse : une seule ligne, avec le détail du juge
    details = {qid: detail for prio, qid, _, detail in a_voir if prio == 1}
    a_voir = [(p, q, quoi, details.get(q, d) if p == 0 else d) for p, q, quoi, d in a_voir
              if not (p == 1 and q in graves)]
    return sorted(a_voir, key=lambda x: (x[0], x[1]))


def en_clair(diagnostic: str) -> str:
    return "tout va bien" if diagnostic == "ok" else diagnostic.replace("chunk", "morceau")


def que_corriger(diagnostic: str) -> str:
    if diagnostic.startswith("recherche"):
        return "la lecture des documents, le découpage ou la recherche"
    if diagnostic.startswith("génération"):
        return "le prompt ou le modèle de génération"
    return "—"


def croisement(ev: Evaluation) -> list[tuple[str, int]]:
    chemin = ev.fichiers / "croisement.jsonl"
    if not chemin.exists():
        return []
    compte: dict[str, int] = {}
    for c in contrat.lire_jsonl(chemin):
        compte[c["diagnostic"]] = compte.get(c["diagnostic"], 0) + 1
    return sorted(compte.items(), key=lambda x: -x[1])


def par_type(scores: list[dict]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    principaux = [s for s in scores if s["score"] in ("n1_passages_rattaches", "n2_reussite_k", "n3_exactitude",
                                                        "n3_fidelite", "n4_score_pondere")]
    types = sorted({t for s in principaux for t in s["ventilation"].get("type_document", {})})
    lignes = []
    for s in principaux:
        cases = []
        for t in types:
            v = s["ventilation"].get("type_document", {}).get(t)
            cases.append("—" if not v or v["valeur"] is None else f"{nombre(v['valeur'] * 100)} % (n = {v['n']})")
        lignes.append((libelle(s["score"]), cases))
    return ["questions sans passage" if t == "aucun" else t for t in types], lignes


def contenu(ev: Evaluation, resultat: dict, lignes_base) -> dict:
    """Tout ce que disent les rapports, sans mise en forme."""
    d = resultat["decision"]
    sens = {k: v["sens"] for k, v in ev.seuils.items()}
    # les erreurs graves sont comptées aux évaluations 3 et 4 : un seul critère par nom
    bloquants = list({libelle(b["score"]): b["valeur"] for b in d["criteres_bloquants_declenches"]}.items())
    noms_bloquants = {nom for nom, _ in bloquants}
    vus, decision = set(), []
    for x in d["seuils"]:
        if libelle(x["score"]) in vus:   # les erreurs graves sont comptées aux évaluations 3 et 4 : une seule ligne
            continue
        vus.add(libelle(x["score"]))
        decision.append([libelle(x["score"]), texte_valeur(x["score"], x["valeur"], x.get("marge")),
                         texte_seuil(x["score"], x["seuil"], sens.get(x["score"], "min")), texte_atteint(x["atteint"]),
                         str(x["n"])])
    niveaux = []
    for niveau, (nom, phrase) in NIVEAUX.items():
        lignes = [[libelle(s["score"]), aide(s["score"]), texte_valeur(s["score"], s["valeur"], s.get("marge")),
                   texte_seuil(s["score"], s["seuil"], sens.get(s["score"], "min")),
                   texte_atteint(s["atteint"]) if s["bloquant"] or s["seuil"] is not None else "—", str(s["n"]),
                   s["score"]] for s in resultat["scores"] if s["niveau"] == niveau]
        if lignes:
            niveaux.append((niveau, nom, phrase, lignes))
    types, lignes_types = par_type(resultat["scores"])
    return {
        "titre": ev.rag["version_rag"],
        "configuration": configuration(ev.rag),
        "corpus": ev.version_corpus,
        "questions": len(ev.questions),
        "reservees": sum(q["reservee_decision"] for q in ev.questions.values()),
        "juge": f"{ev.config['modeles']['juge']['modele']}, prompt {ev.config['modeles']['juge']['version_prompt']}",
        "possible": d["mise_en_production_possible"],
        "bloquants": bloquants,
        "manquants": [libelle(x["score"]) for x in d["seuils"]
                      if x["atteint"] is False and libelle(x["score"]) not in noms_bloquants],
        "decision": decision,
        "niveaux": niveaux,
        "a_voir": [(qid, ev.questions[qid]["question"], quoi, (detail or "")[:400])
                   for _, qid, quoi, detail in questions_a_voir(ev, lignes_base)],
        "croisement": [(en_clair(diag), n, que_corriger(diag)) for diag, n in croisement(ev)],
        "types": types,
        "lignes_types": lignes_types,
        "evaluation_id": ev.evaluation_id,
    }


# --- RAPPORT.md ------------------------------------------------------------------------------

def cellule(x) -> str:
    return str(x).replace("|", "\\|").replace("\n", " ")


def tableau(entetes: list[str], lignes: list[list]) -> list[str]:
    t = ["| " + " | ".join(entetes) + " |", "| " + " | ".join("---" for _ in entetes) + " |"]
    return t + ["| " + " | ".join(cellule(x) for x in ligne) + " |" for ligne in lignes]


def markdown(c: dict) -> str:
    reglage = c["questions"] - c["reservees"]
    m = [f"# Évaluation de la configuration `{c['titre']}`", "",
         "Ce rapport évalue **une configuration** du RAG sur le corpus du métier. Il répond à une question : "
         "**cette configuration peut-elle partir en production ?**", "",
         *tableau(["", ""], [["Configuration évaluée", c["configuration"]],
                             ["Corpus", f"version {c['corpus']} : {c['questions']} questions, dont {c['reservees']} "
                                        f"réservées à la décision"],
                             ["Juge", c["juge"]]]), "",
         "## 1. La décision", "",
         "**✅ Mise en production possible.**" if c["possible"] else "**❌ Mise en production non recommandée.**", ""]
    for nom, v in c["bloquants"]:
        m.append(f"- Critère bloquant déclenché : **{nom} = {nombre(v)}**. Un seul suffit à refuser, quel que soit le "
                 f"reste.")
    if c["manquants"]:
        m.append(f"- Seuil(s) non atteint(s) : {', '.join(c['manquants'])}.")
    m += ["", f"Les seuils sont fixés par le métier avant l'évaluation. Ils se jugent sur les {c['reservees']} "
              f"questions réservées à la décision, jamais utilisées pour régler le RAG. Les critères bloquants (fuite "
              f"de droits, erreur grave) se jugent sur toutes les questions.", "",
          *tableau(["Ce qui est vérifié", "Résultat", "Seuil", "Atteint ?", "Compté sur"], c["decision"]), "",
          "## 2. Les scores, évaluation par évaluation", "",
          f"Sur les {reglage} questions de réglage. On les lit dans l'ordre : une réponse fausse vient souvent d'un "
          f"passage perdu à l'ingestion ou mal retrouvé par la recherche. « ± » est la marge d'erreur : un écart plus "
          f"petit ne veut rien dire. Un score compté sur moins de 10 éléments est une tendance, pas une mesure. "
          f"Comment chaque score est calculé : les guides 1 à 4 du service d'évaluation.", ""]
    for niveau, nom, phrase, lignes in c["niveaux"]:
        m += [f"### {niveau}. {nom}", "", phrase, "",
              *tableau(["Score", "Ce qu'il compte", "Résultat", "Seuil", "Atteint ?", "Compté sur", "Code"],
                       [ligne[:6] + [f"`{ligne[6]}`"] for ligne in lignes]), ""]
    m += ["## 3. Les questions à regarder en premier", "",
          "Erreurs graves et fuites d'abord, puis réponses fausses, puis passages perdus à l'ingestion. Le détail de "
          "chaque question est dans `resultats_par_question.csv`.", ""]
    m += tableau(["Question", "Problème", "Détail"],
                 [[f"**{qid}** : {question}", quoi, detail] for qid, question, quoi, detail in c["a_voir"]]) \
        if c["a_voir"] else ["Rien à signaler."]
    if c["croisement"]:
        m += ["", "## 4. La faute est-elle dans la recherche ou dans la réponse ?", "",
              "Pour chaque question qui a une réponse dans les documents : le bon passage a-t-il été ramené, et la "
              "réponse est-elle juste ?", "",
              *tableau(["Diagnostic", "Questions", "Que corriger"], [list(x) for x in c["croisement"]])]
    if c["lignes_types"]:
        m += ["", "## 5. Par type de document", "",
              *tableau(["Score", *c["types"]], [[nom, *cases] for nom, cases in c["lignes_types"]])]
    m += ["", "## Les fichiers techniques de cette évaluation", "",
          "Ils sont dans `fichiers_techniques/`. Ce rapport en est tiré ; on ne les ouvre que pour creuser.", "",
          *tableau(["Fichier", "Contenu"], [[f"`{f}`", quoi] for f, quoi in FICHIERS]), ""]
    return "\n".join(m)


# --- rapport.html ----------------------------------------------------------------------------

STYLE = """
body{font-family:system-ui,sans-serif;max-width:1050px;margin:2rem auto;padding:0 1rem;color:#1f2328;line-height:1.45}
h1{font-size:1.6rem}h2{margin-top:2.2rem;border-bottom:2px solid #d0d7de;padding-bottom:.3rem}
table{border-collapse:collapse;width:100%;margin:.6rem 0;font-size:.93rem}
th,td{border:1px solid #d0d7de;padding:.35rem .55rem;text-align:left;vertical-align:top}th{background:#f6f8fa}
.decision{padding:1rem 1.2rem;border-radius:8px;margin:1rem 0;font-size:1.05rem}
.oui{background:#dafbe1;border:1px solid #1a7f37}.non{background:#ffebe9;border:1px solid #cf222e}
small{color:#57606a}code{background:#f6f8fa;padding:0 .25rem}
"""


def e(x) -> str:
    return html.escape(str(x))


def table_html(entetes: list[str], lignes: list[list]) -> str:
    return ("<table><tr>" + "".join(f"<th>{e(x)}</th>" for x in entetes) + "</tr>" +
            "".join("<tr>" + "".join(f"<td>{e(x)}</td>" for x in ligne) + "</tr>" for ligne in lignes) + "</table>")


def page_html(c: dict) -> str:
    p = [f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Évaluation {e(c['evaluation_id'])}</title>"
         f"<style>{STYLE}</style></head><body>",
         f"<h1>Évaluation de la configuration <code>{e(c['titre'])}</code></h1>",
         "<p>Ce rapport évalue <b>une configuration</b> du RAG sur le corpus du métier. Il répond à une question : "
         "<b>cette configuration peut-elle partir en production ?</b></p>",
         table_html(["", ""], [["Configuration évaluée", c["configuration"]],
                               ["Corpus", f"version {c['corpus']} : {c['questions']} questions, dont "
                                          f"{c['reservees']} réservées à la décision"], ["Juge", c["juge"]]]),
         f"<h2>1. La décision</h2><div class='decision {'oui' if c['possible'] else 'non'}'><b>"
         f"{'Mise en production possible' if c['possible'] else 'Mise en production non recommandée'}</b>"]
    for nom, v in c["bloquants"]:
        p.append(f"<br>Critère bloquant déclenché : {e(nom)} = {e(nombre(v))}")
    if c["manquants"]:
        p.append("<br>Seuil(s) non atteint(s) : " + e(", ".join(c["manquants"])))
    p.append(f"</div><p><small>Seuils jugés sur les {c['reservees']} questions réservées à la décision ; critères "
             f"bloquants sur toutes les questions.</small></p>")
    p.append(table_html(["Ce qui est vérifié", "Résultat", "Seuil", "Atteint ?", "Compté sur"], c["decision"]))
    p.append("<h2>2. Les scores, évaluation par évaluation</h2><p><small>Sur les questions de réglage. « ± » est la "
             "marge d'erreur ; un score compté sur moins de 10 éléments est une tendance.</small></p>")
    for niveau, nom, phrase, lignes in c["niveaux"]:
        p.append(f"<h3>{niveau}. {e(nom)}</h3><p>{e(phrase)}</p>")
        p.append(table_html(["Score", "Ce qu'il compte", "Résultat", "Seuil", "Atteint ?", "Compté sur", "Code"],
                            lignes))
    p.append("<h2>3. Les questions à regarder en premier</h2>")
    p.append(table_html(["Question", "Problème", "Détail"], [[f"{qid} : {q}", quoi, detail]
                                                             for qid, q, quoi, detail in c["a_voir"]])
             if c["a_voir"] else "<p>Rien à signaler.</p>")
    if c["croisement"]:
        p.append("<h2>4. La faute est-elle dans la recherche ou dans la réponse ?</h2>")
        p.append(table_html(["Diagnostic", "Questions", "Que corriger"], [list(x) for x in c["croisement"]]))
    if c["lignes_types"]:
        p.append("<h2>5. Par type de document</h2>")
        p.append(table_html(["Score", *c["types"]], [[nom, *cases] for nom, cases in c["lignes_types"]]))
    p.append("</body></html>")
    return "\n".join(p)


def ecrire(ev: Evaluation, resultat: dict, lignes_base) -> None:
    """Écrit RAPPORT.md dans le dossier de l'évaluation, et rapport.html dans fichiers_techniques/."""
    c = contenu(ev, resultat, lignes_base)
    (ev.dossier / "RAPPORT.md").write_text(markdown(c), encoding="utf-8")
    ev.fichiers.mkdir(parents=True, exist_ok=True)
    (ev.fichiers / "rapport.html").write_text(page_html(c), encoding="utf-8")
