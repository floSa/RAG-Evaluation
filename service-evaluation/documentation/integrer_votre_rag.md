# Intégrer votre RAG, pas à pas

Ce dépôt sert à deux choses différentes :

| Usage | Pour quoi | Suivre |
| --- | --- | --- |
| **Voir les résultats** | voir à quoi ressemble une évaluation, sans rien installer | [`service-evaluation-exemple/`](../../service-evaluation-exemple/README.md) |
| **Essayer avec l'exemple** | faire tourner le service sur le corpus d'exemple et le RAG d'exemple, sans rien écrire | le [README du service](../README.md#essayer-avec-le-corpus-dexemple) |
| **L'adapter à votre RAG** | évaluer **votre** RAG, sur **vos** documents, avec les questions de **votre** métier | ce guide |

Pour votre projet, vous gardez le service d'évaluation tel quel. Vous fournissez deux choses : **votre corpus annoté**, et **les quatre endpoints de votre RAG**. Le service RAG d'exemple ne sert plus que de modèle.

## Les étapes

| Étape | Qui | Ce qu'on fait | Fini quand |
| --- | --- | --- | --- |
| [1. Installer le service d'évaluation](#1-installer-le-service-dévaluation) | équipe technique | lancer Langfuse, brancher le juge | `kit verifier-modeles` répond |
| [2. Constituer votre corpus](#2-constituer-votre-corpus) | le métier, aidé de l'équipe technique | choisir les documents, écrire les questions, annoter les passages | `kit importer` accepte le fichier |
| [3. Régler le kit pour votre projet](#3-régler-le-kit-pour-votre-projet) | équipe technique et métier | le nom du projet, les documents, l'adresse du RAG, les seuils | `config/` est à jour |
| [4. Ouvrir les quatre endpoints de votre RAG](#4-ouvrir-les-quatre-endpoints-de-votre-rag) | l'équipe du RAG | ajouter à votre RAG un dossier `endpoints_evaluation/` | les quatre adresses répondent |
| [5. Vérifier les endpoints](#5-vérifier-les-endpoints) | l'équipe du RAG | faire appeler les endpoints par le kit | « règle : respectée » |
| [6. Évaluer, lire, corriger](#6-évaluer-lire-corriger) | tous | évaluer, lire le rapport, corriger, comparer | la décision est prise |

## 1. Installer le service d'évaluation

Seul le dossier `service-evaluation/` vous sert. Il faut Docker, [uv](https://docs.astral.sh/uv/), et un point d'accès à des modèles de langage compatible OpenAI pour le juge. Depuis `service-evaluation/` :

```bash
cp .env.example .env
```

Mettre dans `.env` la clé du point d'accès (`KIT_LLM_CLE`), et dans [`config/kit.yaml`](../config/kit.yaml) son adresse et le nom des modèles (`modeles`). Puis :

```bash
./initialiser.sh
```

```bash
docker compose up -d
```

```bash
uv run kit verifier-modeles
```

Le juge doit être, de préférence, **un autre modèle que celui de votre RAG** : un modèle tend à favoriser ses propres réponses.

## 2. Constituer votre corpus

C'est l'étape la plus longue, et la seule qui se fait à la main. Tout le détail : [0a. Construction du corpus](0a_construction_du_corpus.md).

1. **Copier le fichier vierge** [`corpus_annote/Corpus_evaluation_RAG.xlsx`](../corpus_annote/Corpus_evaluation_RAG.xlsx), et le donner au métier.
2. **Le métier le remplit** : les documents retenus, les questions réelles des utilisateurs, la réponse attendue, et le passage exact où elle se trouve, copié-collé. Chaque feuille porte ses définitions. Le [corpus d'exemple](../../service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx) montre un fichier complet.
3. **Ranger les documents** dans un dossier, chacun nommé par sa référence : `<référence dans la source>.<extension>`, par exemple `PR-1101.pdf`. C'est sous cette forme que le kit les envoie à votre RAG.
4. **Importer** :

   ```bash
   uv run kit importer mon_corpus.xlsx
   ```

   Si une ligne est fausse, rien n'est importé, et chaque erreur est listée avec sa feuille, sa ligne et la correction. On corrige, on relance. Le kit signale aussi ce qui manque pour la configuration minimale (10 documents par type, 50 questions, 20 pages OCR).

## 3. Régler le kit pour votre projet

Tout est dans [`config/`](../config/), sans toucher au code.

| Réglage | Fichier | Quoi mettre |
| --- | --- | --- |
| `projet` | `kit.yaml` | le nom de votre projet (il nomme le jeu de questions dans Langfuse) |
| `chemins.corpus_documentaire` | `kit.yaml` | le dossier de votre corpus documentaire (étape 2) ; par défaut `corpus_annote/corpus_documentaire/` |
| `rag.adresse` | `kit.yaml` | l'adresse des endpoints de votre RAG, par exemple `http://127.0.0.1:8100` |
| `graphe.formes` | `kit.yaml` | seulement si votre RAG a un graphe : les règles SHACL de **votre** ontologie |
| les seuils | `seuils.json` | à fixer **avec le métier, avant d'évaluer** : la part de réponses justes exigée, les critères bloquants… ([document 3](methode_et_contrat/methode_evaluation.md), section 9) |

Fixer les seuils avant de voir les scores évite de les choisir pour faire passer le RAG.

## 4. Ouvrir les quatre endpoints de votre RAG

Le service d'évaluation n'entre jamais dans votre RAG : il appelle quatre adresses web. Votre RAG les ouvre, dans un dossier à part, `endpoints_evaluation/`, écrit pour l'évaluation et pour rien d'autre. La règle complète : [0b. Les endpoints du RAG](0b_endpoints_du_rag.md).

### Partir du modèle

[`../endpoints_a_copier/endpoints_evaluation.py`](../endpoints_a_copier/endpoints_evaluation.py) est un modèle complet, à copier dans votre RAG. Tel quel, il marche déjà : c'est un « RAG » jouet, qui fait un chunk par page et cherche par mots communs. Il donne la forme exacte de chaque endpoint. Vous remplacez le contenu des quatre fonctions marquées **À REMPLACER** par l'appel à votre RAG ; les formes d'entrée et de sortie ne changent pas.

Avant de toucher à votre RAG, lancez le modèle tel quel, depuis `service-evaluation/endpoints_a_copier/`, puis faites l'étape 5 : vous verrez le kit appeler les endpoints et noter le RAG jouet de bout en bout. Il obtient un score pondéré d'environ 24 % : c'est un jouet.

```bash
uv run --with fastapi --with uvicorn --with pypdf uvicorn endpoints_evaluation:app --host 127.0.0.1 --port 8100
```

Votre RAG n'est pas en Python ? Il ouvre les mêmes quatre adresses, avec les mêmes champs ([contrat](methode_et_contrat/contrat_des_fichiers.md#les-endpoints-dévaluation)).

### ① Ingérer : la premier endpoint

Le service d'évaluation envoie ses documents. Votre RAG les indexe **comme en production** (même extraction, même découpage, mêmes modèles), mais **dans un espace à part** : un autre dossier, une autre collection, jamais l'index de production.

Ce qu'elle reçoit, pour chaque document : `reference_source`, `titre`, `type_document`, `version`, `format`, `droits_acces`, `fichier` (le nom du fichier) et `contenu` (le fichier, en base64). Ce qu'elle rend : le nombre de documents, de chunks et de pages.

Par exemple, si votre RAG a une fonction qui indexe un dossier (`mon_rag.indexer` est un nom d'exemple, à remplacer par le vôtre) :

```python
import base64
from pathlib import Path

import mon_rag   # votre RAG


@app.post("/ingerer")
def ingerer(demande: Documents) -> dict:
    dossier = Path("espace_evaluation/documents")        # à part de la production
    dossier.mkdir(parents=True, exist_ok=True)
    metadonnees = []
    for d in demande.documents:
        (dossier / Path(d.fichier).name).write_bytes(base64.b64decode(d.contenu))
        metadonnees.append({"reference": d.reference_source, "version": d.version,
                            "droits": d.droits_acces, "fichier": Path(d.fichier).name})
    resultat = mon_rag.indexer(dossier, metadonnees, collection="evaluation")
    return {"documents": len(demande.documents), "chunks": resultat.nb_chunks, "pages": resultat.nb_pages}
```

Le point qui compte : chaque chunk de votre index doit garder **la référence du document reçue (`reference_source`), sa version, sa page et ses droits d'accès**. Sans eux, le kit ne peut pas retrouver les passages du métier, ni vérifier les droits.

### ② Montrer l'index

Votre RAG rend ce qu'il a lu et découpé, et sa version exacte :

| Partie | Ce qu'on y met |
| --- | --- |
| `rag` | le nom du RAG, sa **version** (`version_rag`), son type (`vectoriel`, `graphe`, `hybride`, `agent`), k, les versions de ses briques |
| `chunks` | chaque chunk de l'index : `chunk_id`, `reference_source`, `version_document`, `page`, `type_element`, `droits_acces`, `ordre`, `texte`, `version_index` |
| `pages` | le texte de chaque page lue, avant découpage : il sert à mesurer la lecture des scans |
| `graphe` | le graphe en Turtle, si votre RAG en a un ; sinon `null` |

La version doit **changer dès que l'index, un modèle, le prompt ou k changent** : c'est ce qui permet de comparer deux versions sans ambiguïté.

### ③ Rechercher

Pour une question, votre RAG rend les k chunks retrouvés, dans l'ordre, **avant toute génération** : `chunk_id`, `rang`, `score`. Il applique les droits du `profil` **pendant** la recherche : un chunk interdit ne doit jamais remonter. Pour une question de suite, `historique` contient l'échange précédent.

### ④ Répondre

Pour une question, votre RAG rend sa réponse, telle qu'un utilisateur la recevrait : `reponse`, `abstention` (vrai si votre RAG dit lui-même ne pas savoir), `chunks_cites` (les sources citées), `chunks_contexte` (tous les chunks donnés au modèle), `duree_ms`, `trace_id`, et si possible `cout`, `tokens_entree`, `tokens_sortie`.

### Les erreurs fréquentes

| Erreur | Ce que l'évaluation verra |
| --- | --- |
| une référence de document modifiée (`PR-1101.pdf` au lieu de `PR-1101`) | aucun passage rattaché : l'évaluation 1 s'effondre |
| la page d'un chunk en nombre, ou la page où il finit | des passages introuvables |
| les droits filtrés **après** la recherche, au lieu de pendant | une fuite de droits, critère bloquant |
| des `chunk_id` différents entre ② et ③ | des recherches qui citent des chunks inconnus : le kit refuse |
| une version qui ne change pas quand un réglage change | deux versions confondues, comparaison impossible |
| l'abstention devinée dans le texte, au lieu d'être dite par le RAG | des abstentions mal comptées |
| les documents de l'évaluation indexés avec ceux de la production | une évaluation faussée, et une production polluée |

## 5. Vérifier les endpoints

Lancer votre RAG, endpoints ouverts. Une première vérification à la main :

```bash
curl -s http://127.0.0.1:8100/index
```

Avant toute ingestion, la réponse attendue est une erreur claire : rien n'a encore été ingéré. Puis faire appeler les quatre endpoints par le kit, depuis `service-evaluation/` :

```bash
uv run kit appeler-rag --rag http://127.0.0.1:8100
```

Le kit envoie les documents, pose chaque question, range ce que votre RAG rend, puis le vérifie. Il finit par « règle : respectée », ou il dit **précisément ce qui ne va pas**, porte par endpoint et ligne par ligne :

```
Réponses du RAG rangées dans resultats/reponses_du_rag/mon-rag-k5-d2a069ef ; règle : 3 écart(s).
  - chunks.jsonl, ligne 13 : champ « texte » : ne doit pas être vide.
  - reponses.jsonl, ligne 3 : champ obligatoire « abstention » absent.
  - recherches.jsonl, Q-007 : posée avec le profil « tous » au lieu de « exploitation ».
```

On corrige les endpoints, on relance, jusqu'à « règle : respectée ».

## 6. Évaluer, lire, corriger

```bash
uv run kit evaluer --rag http://127.0.0.1:8100
```

Sans `--rag`, le kit prend l'adresse de `kit.yaml`. La commande appelle les endpoints, enchaîne les quatre évaluations, et finit par le chemin du rapport, `RAPPORT.md`.

| Ensuite | Où |
| --- | --- |
| lire la décision et les scores, dans l'ordre | [5. Résultats et comparaison](5_resultats_et_comparaison.md) |
| comprendre un mauvais score, et quoi changer dans le RAG | la section « Si c'est mauvais » des guides [1](1_evaluation_ingestion.md), [2](2_evaluation_recherche.md), [3](3_evaluation_reponse.md) et [4](4_evaluation_bout_en_bout.md) |
| vérifier le juge, une fois, puis à chaque changement de juge | [3. Évaluation de la réponse](3_evaluation_reponse.md#vérifier-le-juge-avant-de-lui-faire-confiance) : `kit verifier-juge` |
| faire relire au métier les réponses douteuses | Langfuse, file `relecture-reponses` |
| après chaque changement du RAG : évaluer de nouveau, puis comparer | `uv run kit comparer <résultats A> <résultats B>` ([guide 5](5_resultats_et_comparaison.md)) |

## Récapitulatif

- [ ] le service d'évaluation est lancé, `kit verifier-modeles` répond ;
- [ ] le corpus est annoté par le métier, et `kit importer` l'accepte ;
- [ ] `kit.yaml` et `seuils.json` sont réglés, les seuils fixés avec le métier ;
- [ ] votre RAG a son dossier `endpoints_evaluation/`, et indexe les documents de l'évaluation à part ;
- [ ] `kit appeler-rag` finit par « règle : respectée » ;
- [ ] `kit evaluer` produit le rapport, et le juge est vérifié.
