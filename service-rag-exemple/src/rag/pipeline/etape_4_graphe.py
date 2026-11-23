"""Étape 4 — Graphe (optionnelle) : extraire des documents un graphe d'équipements, de sites et de personnes.

- Un modèle de langage lit chaque page (chaque champ, pour une fiche de GED) et en sort les entités
  et les relations, **contraint par l'ontologie** : il ne connaît que ses classes et ses relations, et tout ce
  qui n'y est pas est écarté.
- Chaque nœud et chaque relation garde sa **provenance** : le document et la page d'où il vient.
- Le graphe est écrit en RDF (graphe.ttl). Pour la recherche, chaque entité d'une page devient un élément de
  l'index, de type « noeud », qui résume ses relations sur cette page : « TGBT-A (Equipement) : TR-A1 alimente
  TGBT-A ; TGBT-A alimente AD-A03 ». Il porte les métadonnées de la page (référence, version, droits) : la
  recherche le filtre et le modèle le cite exactement comme un chunk.

Les extractions sont gardées en cache : relancer l'indexation ne refait pas les appels au modèle.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI
from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef

VERSION_EXTRACTION = "graphe-1"
KIT = Namespace("https://kit-eval-rag/ns#")       # l'espace de noms de la provenance, fixé par le contrat

PHRASES = {"situeSur": "est situé sur", "alimente": "alimente", "secourt": "secourt", "protege": "protège",
           "intervientSur": "intervient sur"}


# --- L'ontologie ----------------------------------------------------------------------------------

def lire_ontologie(chemin: Path) -> dict:
    """Les classes et les relations de l'ontologie, avec leur commentaire : {"classes": {...}, "relations": {...}}."""
    o = Graph().parse(chemin)
    owl = Namespace("http://www.w3.org/2002/07/owl#")
    def libelle(uri):
        return str(o.value(uri, RDFS.label))
    classes = {libelle(c): {"uri": c, "comment": str(o.value(c, RDFS.comment))} for c in o.subjects(RDF.type, owl.Class)}
    relations = {libelle(r): {"uri": r, "comment": str(o.value(r, RDFS.comment)),
                              "domaine": libelle(o.value(r, RDFS.domain)), "portee": libelle(o.value(r, RDFS.range))}
                 for r in o.subjects(RDF.type, owl.ObjectProperty)}
    return {"classes": classes, "relations": relations, "espace": str(next(o.subjects(RDF.type, owl.Ontology)))}


def consigne(ontologie: dict) -> str:
    """Le prompt système : l'ontologie, et le format de sortie."""
    classes = "\n".join(f"- {n} : {c['comment']}" for n, c in sorted(ontologie["classes"].items()))
    relations = "\n".join(f"- {n} ({r['domaine']} → {r['portee']}) : {r['comment']}"
                          for n, r in sorted(ontologie["relations"].items()))
    return f"""Tu extrais un graphe de connaissances d'un extrait de document de maintenance électrique.
Tu respectes strictement l'ontologie ci-dessous : aucune autre classe, aucune autre relation.

Classes :
{classes}

Relations :
{relations}

Règles :
- N'extrais que ce que le texte dit explicitement. Dans le doute, n'extrais rien.
- Le nom d'une entité est son repère exact tel qu'écrit dans le texte (TGBT-A, TR-A1, AD-A03, Site A, Karim Benali).
- Pas de valeurs, de dates, de documents ni de procédures : seulement des entités des classes ci-dessus.
- "classe" vaut exactement l'un de : {", ".join(sorted(ontologie["classes"]))}. Une armoire, un transformateur, un relais sont des Equipement.
- "relation" vaut exactement l'un de : {", ".join(sorted(ontologie["relations"]))}.
- Chaque relation relie deux entités que tu as listées, dans le sens indiqué (domaine → portée).

- Extrais toutes les relations que le texte permet d'affirmer, en particulier le site de chaque équipement.

Exemple. Texte : « Sur le site A, le TGBT-A est alimenté par le transformateur TR-A1 ; en cas de coupure, le groupe GE-A
reprend la charge. Karim Benali a remplacé le disjoncteur de l'armoire AD-A03. »
Réponse : {{"entites": [{{"nom": "Site A", "classe": "Site"}}, {{"nom": "TGBT-A", "classe": "Equipement"}}, {{"nom": "TR-A1", "classe": "Equipement"}}, {{"nom": "GE-A", "classe": "Equipement"}}, {{"nom": "AD-A03", "classe": "Equipement"}}, {{"nom": "Karim Benali", "classe": "Personne"}}], "relations": [{{"sujet": "TGBT-A", "relation": "situeSur", "objet": "Site A"}}, {{"sujet": "TR-A1", "relation": "alimente", "objet": "TGBT-A"}}, {{"sujet": "GE-A", "relation": "secourt", "objet": "TGBT-A"}}, {{"sujet": "Karim Benali", "relation": "intervientSur", "objet": "AD-A03"}}]}}

Réponds uniquement en JSON compact, sur une ligne, sans commentaire :
{{"entites": [{{"nom": "...", "classe": "..."}}], "relations": [{{"sujet": "...", "relation": "...", "objet": "..."}}]}}
Si l'extrait ne contient rien de tel : {{"entites": [], "relations": []}}"""


# --- Extraire une page -------------------------------------------------------------------------------

def lire_json(texte: str) -> dict:
    """Le premier objet JSON de la réponse du modèle ; un objet vide si elle n'en contient pas."""
    debut, fin = texte.find("{"), texte.rfind("}")
    try:
        return json.loads(texte[debut:fin + 1]) if debut >= 0 else {}
    except json.JSONDecodeError:
        return {}


def contraindre(brut: dict, ontologie: dict) -> dict:
    """Écarte ce que l'ontologie ne connaît pas : une classe ou une relation inventée, un nom vide."""
    entites = [{"nom": e["nom"].strip(), "classe": e["classe"]} for e in brut.get("entites", [])
               if isinstance(e, dict) and str(e.get("nom", "")).strip() and e.get("classe") in ontologie["classes"]]
    relations = [{"sujet": r["sujet"].strip(), "relation": r["relation"], "objet": r["objet"].strip()}
                 for r in brut.get("relations", [])
                 if isinstance(r, dict) and r.get("relation") in ontologie["relations"]
                 and str(r.get("sujet", "")).strip() and str(r.get("objet", "")).strip()]
    return {"entites": entites, "relations": relations}


def extraire_page(client: OpenAI, modele: str, systeme: str, texte: str, sans_reflexion: bool = False) -> dict:
    extra = {"chat_template_kwargs": {"enable_thinking": False}} if sans_reflexion else None
    r = client.chat.completions.create(model=modele, temperature=0, max_tokens=2000, extra_body=extra,
                                       messages=[{"role": "system", "content": systeme},
                                                 {"role": "user", "content": texte}])
    return lire_json(r.choices[0].message.content or "")


# --- Construire le graphe ------------------------------------------------------------------------

def cle(nom: str) -> str:
    """Le même identifiant pour « TGBT-A », « tgbt-a » ou « TGBT A » : la casse, les accents, les espaces s'effacent."""
    sans_accent = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sans_accent.lower()).strip("-")


def construire(chunks: list[dict], config: dict, client: OpenAI, empreinte, afficher=print) -> tuple[list[dict], Graph]:
    """Extrait le graphe des pages des chunks ; rend les éléments « noeud » de l'index et le graphe RDF."""
    reglages = config["graphe"]
    ontologie = lire_ontologie(Path(reglages["ontologie"]))
    systeme = consigne(ontologie)
    modele = config["modeles"]["generation"]["modele"]
    cache = Path(config["travail"]) / "graphe" / "extraction"
    cache.mkdir(parents=True, exist_ok=True)

    pages = defaultdict(list)                               # (référence, page) → ses chunks, dans l'ordre
    for c in chunks:
        pages[(c["reference_source"], c["page"])].append(c)

    def traiter(cle_page):
        texte = "\n\n".join(c["texte"] for c in pages[cle_page])
        fichier = cache / f"{empreinte([VERSION_EXTRACTION, modele, systeme, texte])}.json"
        if fichier.exists():
            return cle_page, json.loads(fichier.read_text(encoding="utf-8"))
        extrait = contraindre(extraire_page(client, modele, systeme, texte, reglages.get("sans_reflexion", False)),
                              ontologie)
        fichier.write_text(json.dumps(extrait, ensure_ascii=False), encoding="utf-8")
        return cle_page, extrait

    afficher(f"  graphe : {len(pages)} pages à lire")
    with ThreadPoolExecutor(reglages.get("appels_paralleles", 4)) as pool:
        extraits = dict(pool.map(traiter, pages))

    # Les entités, fusionnées d'une page à l'autre par leur nom
    noms, classes, sources = {}, defaultdict(Counter), defaultdict(set)
    relations = []                                           # (sujet, relation, objet, référence, page)
    for (ref, page), extrait in extraits.items():
        for e in extrait["entites"]:
            k = cle(e["nom"])
            noms.setdefault(k, e["nom"]); classes[k][e["classe"]] += 1; sources[k].add((ref, page))
        for r in extrait["relations"]:
            s, o = cle(r["sujet"]), cle(r["objet"])
            for k, nom in ((s, r["sujet"]), (o, r["objet"])):
                noms.setdefault(k, nom); sources[k].add((ref, page))
            if (s, r["relation"], o, ref, page) not in relations:
                relations.append((s, r["relation"], o, ref, page))
    classe = {k: classes[k].most_common(1)[0][0] for k in noms if classes[k]}   # une entité sans classe le reste

    graphe = rdf(ontologie, noms, classe, sources, relations)
    return elements(pages, noms, classe, relations), graphe


def rdf(ontologie: dict, noms: dict, classe: dict, sources: dict, relations: list) -> Graph:
    """Le graphe en RDF : chaque nœud et chaque relation réifiée porte kit:referenceSource et kit:page."""
    vt = Namespace(ontologie["espace"].rstrip("#") + "#")
    g = Graph()
    g.bind("vt", vt); g.bind("kit", KIT)
    noeud = {k: URIRef(f"{vt}entite-{k}") for k in noms}
    for k, nom in noms.items():
        g.add((noeud[k], RDFS.label, Literal(nom)))
        if k in classe:
            g.add((noeud[k], RDF.type, ontologie["classes"][classe[k]]["uri"]))
        for ref, page in sorted(sources[k]):
            g.add((noeud[k], KIT.referenceSource, Literal(ref)))
            g.add((noeud[k], KIT.page, Literal(page)))
    for i, (s, rel, o, ref, page) in enumerate(relations, start=1):
        predicat = ontologie["relations"][rel]["uri"]
        g.add((noeud[s], predicat, noeud[o]))
        r = URIRef(f"{vt}relation-{i}")
        g.add((r, RDF.type, RDF.Statement))
        g.add((r, RDF.subject, noeud[s])); g.add((r, RDF.predicate, predicat)); g.add((r, RDF.object, noeud[o]))
        g.add((r, KIT.referenceSource, Literal(ref))); g.add((r, KIT.page, Literal(page)))
    return g


def elements(pages: dict, noms: dict, classe: dict, relations: list) -> list[dict]:
    """Un élément « noeud » par entité et par page où elle a des relations, avec les métadonnées de la page."""
    par_page = defaultdict(lambda: defaultdict(list))         # (réf, page) → entité → phrases
    for s, rel, o, ref, page in relations:
        phrase = f"{noms[s]} {PHRASES.get(rel, rel)} {noms[o]}"
        for k in (s, o):
            if phrase not in par_page[(ref, page)][k]:
                par_page[(ref, page)][k].append(phrase)
    resultat = []
    for (ref, page), entites in par_page.items():
        modele_page = pages[(ref, page)][0]
        for n, (k, phrases) in enumerate(sorted(entites.items())):
            resultat.append({
                "chunk_id": f"{ref}#{page}#G{n}", "type_objet": "noeud", "reference_source": ref,
                "version_document": modele_page["version_document"], "page": page,
                "type_element": modele_page["type_element"], "droits_acces": modele_page["droits_acces"],
                "ordre": 1000 + n,                             # après les chunks de la page
                "texte": f"{noms[k]} ({classe.get(k, 'sans classe')}) : " + " ; ".join(phrases) + ".",
                "metadonnees": {"entite": noms[k], "classe": classe.get(k), "relations": phrases}})
    return resultat
