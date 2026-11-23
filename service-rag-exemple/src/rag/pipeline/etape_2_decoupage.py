"""Étape 2 — Découpage : couper chaque document en morceaux (chunks) qui portent leurs métadonnées.

- Texte : un chunk par section, avec le chemin de titres en tête ; une section trop longue est recoupée.
- Tableau : un chunk par tableau, chaque ligne écrite « colonne : valeur » (en-têtes répétés).
- Figure : un chunk par figure, avec sa légende (pas de modèle de vision ici : c'est une limite connue).
- Fiche de base de données : un chunk par champ.
Chaque chunk garde la référence du document, sa version, sa page, son type d'élément, ses droits d'accès et son
ordre dans la page : sans eux, le RAG ne pourrait ni citer ses sources ni filtrer les droits.
"""

from rag.pipeline.etape_1_extraction import blocs

VERSION_DECOUPAGE = "sections-1"


def chunks_du_document(document: dict, extrait: dict, taille_max: int) -> list[dict]:
    """Les chunks d'un document, avec les métadonnées du contrat (sans chunk_id ni version_index)."""
    ref, titre = document["reference_source"], document["titre"]
    commun = {"reference_source": ref, "version_document": document["version"],
              "droits_acces": document["droits_acces"]}
    if "fiche" in extrait:  # un chunk par champ : la « page » d'un passage de fiche est le nom du champ
        return [{**commun, "page": champ, "ordre": 0, "type_element": "texte",
                 "texte": f"{ref} — {titre} ({document['type_document']})\n{champ} : {valeur}",
                 "metadonnees": {"chemin": [titre, champ]}} for champ, valeur in extrait["fiche"]]

    scanne = document["format"] == "pdf_scanne"
    resultat, section = [], ""
    for numero, markdown in enumerate(extrait["pages"], start=1):
        ordre, tampon = 0, []

        def ajouter(type_element: str, texte: str):
            nonlocal ordre
            chemin = [titre] + ([section] if section else [])
            resultat.append({**commun, "page": str(numero), "ordre": ordre,
                             "type_element": "texte_scanne" if scanne and type_element != "image_schema" else type_element,
                             "texte": f"{ref} — {' > '.join(chemin)}\n{texte}", "metadonnees": {"chemin": chemin}})
            ordre += 1

        def vider():
            if tampon:
                ajouter("texte", "\n".join(tampon))
                tampon.clear()

        liste = blocs(markdown)
        i = 0
        while i < len(liste):
            genre, contenu = liste[i]
            if genre == "titre":
                if numero == 1 and i == 0 and contenu.startswith(ref):
                    i += 1
                    continue  # le titre du document, déjà en tête de chaque chunk
                if contenu.lower().startswith("tableau"):
                    tampon.append(contenu)  # titre d'un tableau : il suit le tableau dans son chunk
                else:
                    vider()
                    section = contenu
            elif genre == "texte":
                if sum(map(len, tampon)) + len(contenu) > taille_max:
                    vider()
                tampon.append(contenu)
            elif genre == "tableau":
                titre_tableau = tampon.pop() if tampon and tampon[-1].lower().startswith("tableau") else ""
                vider()
                entetes, lignes = contenu[0], contenu[1:]
                if scanne:  # un scan reste du texte : lignes « a | b | c », comme les pages retapées
                    rendu = [" | ".join(l) for l in contenu]
                else:       # tableau natif : chaque ligne en « colonne : valeur », en-têtes répétés
                    rendu = [" ; ".join(f"{e} : {v}" for e, v in zip(entetes, l)) for l in lignes]
                morceau = [titre_tableau] if titre_tableau else []
                for ligne in rendu:
                    if sum(map(len, morceau)) + len(ligne) > taille_max and len(morceau) > 1:
                        ajouter("tableau", "\n".join(morceau))
                        morceau = [titre_tableau] if titre_tableau else []
                    morceau.append(ligne)
                ajouter("tableau", "\n".join(morceau))
            elif genre == "image":  # la légende « Figure n … » est juste avant ou juste après l'image
                suivant = liste[i + 1] if i + 1 < len(liste) else None
                if tampon and tampon[-1].lower().startswith("figure"):
                    legende = tampon.pop()
                    vider()
                    ajouter("image_schema", legende)
                elif suivant and suivant[0] == "texte" and suivant[1].lower().startswith("figure"):
                    vider()
                    ajouter("image_schema", suivant[1])
                    i += 1
            i += 1
        vider()
    return resultat
