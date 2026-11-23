"""Les rapports d'une évaluation (document 3, section 3) : ce qu'a donné UNE configuration du RAG.

Deux fichiers, même contenu :
- RAPPORT.md : lisible directement sur GitHub ou dans un éditeur ;
- rapport.html : la même chose en page web.

Le rapport ne décide pas : il donne les scores, chacun écrit en une phrase que le métier comprend, et le métier
tranche (DECISIONS.md, décision 14). Dans l'ordre : la configuration évaluée, les scores clés, tous les scores
évaluation par évaluation, les questions à regarder en premier, le croisement recherche × réponse, les scores par type
de document, puis les fichiers techniques. Aucune question réservée n'y apparaît en détail.
"""

import html

from kit import contrat
from kit.etape_5_resultats.publication import SCORES, Evaluation

# Pour chaque score : son nom, et ce qu'il veut dire, en une phrase.
# {x} = le nombre de cas réussis, {n} = le nombre de cas comptés, {p} = le résultat sur 100, {v} = le résultat tel quel.
LIBELLES = {
    "n1_documents_indexes": ("Documents présents dans la base", "{x} documents sur {n} sont dans la base du RAG"),
    "n1_metadonnees_completes": ("Étiquettes complètes",
                                 "{x} morceaux de texte sur {n} indiquent leur source, leur page et leurs droits "
                                 "d'accès"),
    "n1_passages_rattaches": ("Passages du métier retrouvés",
                              "{x} passages du métier sur {n} se retrouvent dans un morceau de la base"),
    "n1_passages_coupes": ("Passages coupés en deux",
                           "{x} passages du métier sur {n} sont coupés entre deux morceaux"),
    "n1_erreur_caracteres": ("Erreur de lecture des scans (caractères)",
                             "sur les pages scannées, {p} caractères sur 100 sont mal lus"),
    "n1_erreur_mots": ("Erreur de lecture des scans (mots)", "sur les pages scannées, {p} mots sur 100 sont mal lus"),
    "n1_graphe_violations": ("Violations des règles du graphe",
                             "relations du graphe qui ne respectent pas les règles de l'ontologie : {v}"),
    "n1_graphe_justesse": ("Justesse du graphe", "{x} relations du graphe sur {n} relues sont jugées justes"),
    "n2_reussite_k": ("Bon passage ramené",
                      "pour {x} questions sur {n}, la recherche ramène le passage qui contient la réponse"),
    "n2_rappel_k": ("Passages nécessaires ramenés", "{x} passages nécessaires sur {n} sont ramenés par la recherche"),
    "n2_rang_premier": ("Bon morceau en tête",
                        "{p} sur 100 : 100 si le bon morceau arrive toujours 1er, 50 s'il arrive en moyenne 2e"),
    "n2_fuite_droits": ("Fuites de droits",
                        "questions qui ont ramené un document interdit à la personne qui la pose : {v}"),
    "n2_reussite_1": ("Bon passage ramené, si k = 1",
                      "pour {x} questions sur {n}, le bon passage serait ramené avec 1 seul morceau"),
    "n2_reussite_3": ("Bon passage ramené, si k = 3",
                      "pour {x} questions sur {n}, le bon passage serait ramené avec 3 morceaux"),
    "n2_reussite_5": ("Bon passage ramené, si k = 5",
                      "pour {x} questions sur {n}, le bon passage serait ramené avec 5 morceaux"),
    "n2_reussite_10": ("Bon passage ramené, si k = 10",
                       "pour {x} questions sur {n}, le bon passage serait ramené avec 10 morceaux"),
    "n2_reussite_avant_reranking": ("Bon passage ramené, avant reclassement",
                                    "pour {x} questions sur {n}, le bon passage est ramené avant le reclassement"),
    "n2_perimes_pieges": ("Pièges ou version périmée devant le bon",
                          "pour {x} questions sur {n}, un piège ou une ancienne version passe devant le bon passage"),
    "n3_exactitude": ("Réponses justes",
                      "sur {n} questions, l'équivalent de {x} réponses justes (une réponse partielle compte pour "
                      "moitié)"),
    "n3_completude_listes": ("Listes complètes",
                             "quand la réponse est une liste, elle donne {p} éléments attendus sur 100"),
    "n3_valeurs": ("Chiffres exacts", "{p} chiffres attendus sur 100 sont dans la réponse, avec la bonne unité"),
    "n3_abstention_correcte": ("Sait dire « je ne sais pas »",
                               "sur {n} questions sans réponse dans les documents ou interdites à la personne, le RAG "
                               "dit « je ne sais pas » {x} fois"),
    "n3_abstention_a_tort": ("Abstentions à tort",
                             "pour {x} questions sur {n}, le RAG dit « je ne sais pas » alors que la réponse était "
                             "dans ce qu'il a ramené"),
    "n3_fidelite": ("Fidélité aux documents",
                    "{p} affirmations sur 100 des réponses se trouvent dans les documents ramenés"),
    "n3_citations": ("Bonnes sources citées",
                     "pour {x} questions sur {n}, la réponse cite le passage qui contient la réponse"),
    "n3_erreurs_graves": ("Erreurs graves",
                          "réponses fausses, inventées ou données à tort, sur une question où l'erreur a des "
                          "conséquences graves : {v}"),
    "n3_synthese": ("Synthèses", "le juge note les synthèses sur une grille : {p} sur 100"),
    "n3_second_avis": ("Accord avec un second juge",
                       "pour {x} questions sur {n}, un second juge donne le même verdict"),
    "n3_questions_suite": ("Questions de suite justes",
                           "sur {n} questions de suite, l'équivalent de {x} réponses justes"),
    "n3_variantes": ("Reformulations incohérentes",
                     "{x} groupes de questions reformulées sur {n} reçoivent des réponses différentes"),
    "n4_score_pondere": ("Score pondéré",
                         "{p} réponses justes sur 100, en comptant davantage les questions fréquentes et graves"),
    "n4_erreurs_graves": ("Erreurs graves", "les mêmes erreurs graves que dans l'évaluation de la réponse : {v}"),
    "n4_temps_median": ("Temps de réponse médian", "la moitié des réponses arrivent en moins de {v}"),
    "n4_temps_p95": ("Temps de réponse à 95 %", "95 réponses sur 100 arrivent en moins de {v}"),
    "n4_cout_moyen": ("Coût par question", "une réponse coûte en moyenne {v}"),
}
# Pour chaque évaluation : son nom, et ce qu'elle vérifie, en une phrase.
NIVEAUX = {
    1: ("Ingestion", "On vérifie que le RAG n'a rien perdu ni abîmé en lisant les documents, en les découpant en "
                     "morceaux de texte et en les rangeant dans sa base."),
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
    ("evaluation.json", "ce qui a été évalué : versions du corpus, du service, du RAG et du juge"),
]
TEMPS = ("n4_temps_median", "n4_temps_p95")


# --- Mise en forme des valeurs ----------------------------------------------------------------

def libelle(score: str) -> str:
    return LIBELLES.get(score, (score, ""))[0]


def proportion(score: str) -> bool:
    """Un score entre 0 et 1, affiché en pourcentage (et non un nombre, un temps ou un coût)."""
    return SCORES.get(score, ("", False))[1] or score in ("n1_erreur_caracteres", "n1_erreur_mots", "n3_synthese")


def nombre(v: float, decimales: int = 0) -> str:
    return f"{v:.{decimales}f}".replace(".", ",")


def texte_valeur(score: str, v, marge=None) -> str:
    """La valeur, et, pour un pourcentage, la fourchette où se trouve le vrai résultat : « 69 % (entre 44 et 94 %) »."""
    if v is None:
        return "—"
    if score == "n4_cout_moyen":
        return f"{nombre(v, 2)} €"
    if score in TEMPS:
        return f"{nombre(v / 1000, 1)} s"
    if proportion(score):
        texte = f"{nombre(v * 100)} %"
        if marge:
            bas, haut = max(0.0, v - marge), min(1.0, v + marge)
            texte += f" (entre {nombre(bas * 100)} et {nombre(haut * 100)} %)"
        return texte
    return nombre(v)


def en_clair(score: str, v, n: int) -> str:
    """Le score en une phrase, avec ses chiffres : « pour 9 questions sur 13, la recherche ramène… »."""
    if v is None:
        return "non mesuré"
    modele = LIBELLES.get(score, (score, "{v}"))[1]
    phrase = modele.format(x=nombre(v * n), n=n, p=nombre(v * 100), v=texte_valeur(score, v))
    return phrase[0].upper() + phrase[1:] + "."


def configuration(rag: dict) -> str:
    """La configuration évaluée, en une ligne : type, k, puis chaque réglage."""
    v = rag.get("versions", {})
    reglages = [f"RAG {rag.get('type_rag', '?')}", f"k = {rag.get('k', '?')}"]
    for cle, nom in (("decoupage", "découpage"), ("embedding", "embeddings"), ("generation", "génération"),
                     ("prompt", "prompt"), ("reranker", "reranker")):
        if cle in v:
            reglages.append(f"{nom} {v[cle]}")
    reglages += [f"{cle.replace('_', ' ')} {valeur_reglage(x)}" for cle, x in rag.get("reglages", {}).items()]
    return ", ".join(reglages)


# Les réglages déclarés par le RAG (rag.json), en clair, dans l'ordre où on les lit.
REGLAGES = [("type_rag", "Type de recherche"), ("k", "Morceaux de texte ramenés par question (k)"),
            ("decoupage", "Découpage des documents"), ("embedding", "Modèle qui vectorise le texte"),
            ("generation", "Modèle qui écrit la réponse"), ("prompt", "Version du prompt"),
            ("reranker", "Reclassement des morceaux (reranker)")]


def reglages(rag: dict) -> list[list[str]]:
    """La configuration évaluée, un réglage par ligne : [réglage, valeur]."""
    valeurs = {**rag.get("versions", {}), "type_rag": rag.get("type_rag"), "k": rag.get("k")}
    lignes = [[nom, str(valeurs[cle])] for cle, nom in REGLAGES if valeurs.get(cle) is not None]
    connus = {cle for cle, _ in REGLAGES} | {"index"}
    lignes += [[cle, str(v)] for cle, v in valeurs.items() if cle not in connus and v is not None]
    # les autres réglages, déclarés librement par le RAG (champ « reglages » de rag.json)
    lignes += [[(cle[:1].upper() + cle[1:]).replace("_", " "), valeur_reglage(v)] for cle, v in rag.get("reglages", {}).items()]
    return lignes


def valeur_reglage(v) -> str:
    """Une valeur de réglage en clair : oui ou non pour un booléen."""
    return {True: "oui", False: "non"}.get(v, str(v)) if isinstance(v, bool) else str(v)


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


def en_clair_diagnostic(diagnostic: str) -> str:
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
    cles = [[libelle(x["score"]), texte_valeur(x["score"], x["valeur"], x.get("marge")),
             en_clair(x["score"], x["valeur"], x["n"])] for x in resultat["scores_cles"]]
    niveaux = []
    for niveau, (nom, phrase) in NIVEAUX.items():
        lignes = [[libelle(s["score"]), texte_valeur(s["score"], s["valeur"], s.get("marge")),
                   en_clair(s["score"], s["valeur"], s["n"]), s["score"]]
                  for s in resultat["scores"] if s["niveau"] == niveau]
        if lignes:
            niveaux.append((niveau, nom, phrase, lignes))
    types, lignes_types = par_type(resultat["scores"])
    return {
        "titre": ev.rag["version_rag"],
        "configuration": configuration(ev.rag),
        "reglages": reglages(ev.rag),
        "corpus": ev.version_corpus,
        "questions": len(ev.questions),
        "reservees": sum(q["reservee_decision"] for q in ev.questions.values()),
        "juge": f"{ev.config['modeles']['juge']['modele']}, prompt {ev.config['modeles']['juge']['version_prompt']}",
        "cles": cles,
        "niveaux": niveaux,
        "a_voir": [(qid, ev.questions[qid]["question"], quoi, (detail or "")[:400])
                   for _, qid, quoi, detail in questions_a_voir(ev, lignes_base)],
        "croisement": [(en_clair_diagnostic(diag), n, que_corriger(diag)) for diag, n in croisement(ev)],
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
         "Ce rapport donne les scores d'**une configuration** du RAG sur le corpus du métier. Il ne décide pas : "
         "c'est au métier de dire, à leur lecture, si cette configuration peut partir en production.", "",
         f"Corpus : version {c['corpus']}, {c['questions']} questions, dont {c['reservees']} réservées aux scores "
         f"clés. Juge : {c['juge']}.", "",
         "## La configuration évaluée", "",
         "Les réglages du RAG pendant cette évaluation, tels qu'il les a déclarés.", "",
         *tableau(["Réglage", "Valeur"], c.get("reglages") or [["Configuration", c["configuration"]]]), "",
         "## 1. Les scores clés", "",
         f"Ce sont les scores à présenter au métier. Ils sont calculés sur les {c['reservees']} questions réservées, "
         f"jamais utilisées pour régler le RAG ; les fuites de droits et les erreurs graves, sur toutes les questions. "
         f"Entre parenthèses, la fourchette où se trouve le vrai résultat : avec peu de questions, elle est large.", "",
         *tableau(["Ce qui est mesuré", "Résultat", "Ce que ça veut dire"], c["cles"]), "",
         "## 2. Tous les scores, évaluation par évaluation", "",
         f"Sur les {reglage} autres questions, celles qui servent à régler le RAG. On les lit dans l'ordre : une "
         f"réponse fausse vient souvent d'un passage perdu à l'ingestion ou mal retrouvé par la recherche. Un score "
         f"compté sur moins de 10 cas est une tendance, pas une mesure. Le calcul de chaque score est détaillé dans "
         f"les guides 1 à 4 du service d'évaluation ; le code sert à le retrouver dans les fichiers techniques.", ""]
    for niveau, nom, phrase, lignes in c["niveaux"]:
        m += [f"### {niveau}. {nom}", "", phrase, "",
              *tableau(["Score", "Résultat", "Ce que ça veut dire", "Code"],
                       [ligne[:3] + [f"`{ligne[3]}`"] for ligne in lignes]), ""]
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
         "<p>Ce rapport donne les scores d'<b>une configuration</b> du RAG sur le corpus du métier. Il ne décide pas : "
         "c'est au métier de dire, à leur lecture, si cette configuration peut partir en production.</p>",
         f"<p>Corpus : version {e(c['corpus'])}, {c['questions']} questions, dont {c['reservees']} réservées aux "
         f"scores clés. Juge : {e(c['juge'])}.</p><h2>La configuration évaluée</h2>",
         table_html(["Réglage", "Valeur"], c.get("reglages") or [["Configuration", c["configuration"]]]),
         f"<h2>1. Les scores clés</h2><p><small>Calculés sur les {c['reservees']} questions réservées ; fuites de "
         f"droits et erreurs graves sur toutes les questions. Entre parenthèses, la fourchette où se trouve le vrai "
         f"résultat.</small></p>",
         table_html(["Ce qui est mesuré", "Résultat", "Ce que ça veut dire"], c["cles"]),
         "<h2>2. Tous les scores, évaluation par évaluation</h2><p><small>Sur les questions qui servent à régler le "
         "RAG. Un score compté sur moins de 10 cas est une tendance.</small></p>"]
    for niveau, nom, phrase, lignes in c["niveaux"]:
        p.append(f"<h3>{niveau}. {e(nom)}</h3><p>{e(phrase)}</p>")
        p.append(table_html(["Score", "Résultat", "Ce que ça veut dire", "Code"], lignes))
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
