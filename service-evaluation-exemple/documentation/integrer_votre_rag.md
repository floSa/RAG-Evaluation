# Évaluer votre RAG : la marche à suivre

Ce guide s'adresse à la personne qui prend en charge l'évaluation : data scientist, chef de projet technique, quelqu'un qui sait lire un dépôt et lancer des commandes. C'est elle qui fait toutes les étapes. Le métier n'intervient qu'aux étapes 1 et 4 : il fournit le corpus annoté, selon les règles que vous lui transmettez, puis il décide, à la lecture des scores, si le RAG peut partir en production.

Un exemple complet, où toutes ces étapes ont été faites : [`service-evaluation-exemple/`](../../service-evaluation-exemple/README.md#ce-quon-a-fait-dans-lordre).

| Étape | Ce que vous faites | Fini quand |
| --- | --- | --- |
| [0. Installer le service](#0-installer-le-service) | copier `service-evaluation/`, démarrer Langfuse, brancher le modèle juge | `kit verifier-modeles` répond |
| [1. Construire et importer le corpus d'évaluation](#1-construire-et-importer-le-corpus-dévaluation) | c'est le métier qui le construit : lui donner le fichier Excel vierge et les règles pour le remplir ; ranger ce qu'il rend, puis `kit importer` | l'import ne signale plus d'erreur |
| [2. Ouvrir les quatre endpoints du RAG au service](#2-ouvrir-les-quatre-endpoints-du-rag-au-service) | ouvrir dans votre RAG les quatre endpoints, à partir de `endpoints_a_copier/` | `kit appeler-rag` finit par « règle : respectée » |
| [3. Évaluer une configuration du RAG](#3-évaluer-une-configuration-du-rag) | `kit evaluer` | un `RAPPORT.md` est écrit |
| [4. Lire le rapport, comparer, faire décider le métier](#4-lire-le-rapport-comparer-faire-décider-le-métier) | lire le rapport ; changer un réglage du RAG, réévaluer, comparer ; présenter les scores clés au métier | le métier a décidé |

## 0. Installer le service

Copiez le dossier `service-evaluation/` dans votre projet : c'est le service, vierge. Ce que l'installation met en place, et à quoi sert chaque chose (la commande `kit`, Langfuse et ses bases de données, l'accès au modèle juge) : [README du service, étape 0](../../service-evaluation/README.md#la-marche-à-suivre). Il faut Docker, [uv](https://docs.astral.sh/uv/), et un accès à des modèles de langage par une API compatible OpenAI, pour le modèle juge. Depuis `service-evaluation/` :

```bash
cp .env.example .env
```

Mettez dans `.env` la clé de l'API (`KIT_LLM_CLE`). Le service en a besoin parce qu'il utilise un modèle de langage, le **juge**, qui compare chaque réponse du RAG à la bonne réponse du métier. N'importe quel fournisseur compatible OpenAI convient (OpenAI, Mistral, ou un serveur local). Mettez ensuite dans [`config/kit.yaml`](../config/kit.yaml) son adresse, le nom des modèles (`modeles`) et le nom de votre projet (`projet`). Puis :

```bash
./initialiser.sh
```

```bash
docker compose up -d
```

```bash
uv run kit verifier-modeles
```

Choisissez de préférence pour juge **un autre modèle que celui de votre RAG** : un modèle tend à favoriser ses propres réponses.

## 1. Construire et importer le corpus d'évaluation

Le corpus annoté est ce qui permet de juger le RAG : des questions réelles, leur bonne réponse, et l'endroit exact des documents où elle se trouve. Le RAG ne le voit jamais ; il ne reçoit que les documents.

Donnez au métier deux choses :

1. **Le fichier Excel vierge**, [`corpus_annote/Corpus_evaluation_RAG.xlsx`](../corpus_annote/Corpus_evaluation_RAG.xlsx). Chaque feuille porte ses définitions et ses listes de valeurs.
2. **Les règles pour le remplir** : le [guide 0a](0a_construction_du_corpus.md), section 1. Elles disent quels documents choisir, combien de questions écrire et de quels types, comment copier-coller le passage qui contient la réponse, comment noter la fréquence et la gravité de chaque question, et quelles questions garder de côté, pour qu'elles ne servent jamais à régler le RAG.

Il vous rend :

- **les documents**, un fichier par document, nommé par sa référence : `<référence>.<extension>`, par exemple `PR-1101.pdf`. Les fiches d'une GED (tickets, comptes rendus) n'ont pas besoin de fichier : le métier les repère par leur numéro et le nom du champ, et le RAG les lit lui-même dans la GED ([guide 0a](0a_construction_du_corpus.md#les-sources--fichiers-et-fiches-de-ged)) ;
- **le fichier Excel rempli** : la liste des documents, les questions, leur bonne réponse, les passages qui la contiennent, et quelques pages scannées retapées à la main.

Un fichier rempli, pour montrer au métier ce qu'on attend : [celui de l'exemple](../../service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx).

### Ranger et importer le corpus

| Ce que le métier a rendu | Où vous le mettez |
| --- | --- |
| les documents | `corpus_annote/corpus_documentaire/` |
| le fichier Excel rempli | `corpus_annote/Corpus_evaluation_RAG.xlsx`, à la place du fichier vierge |

Puis importez :

```bash
uv run kit importer corpus_annote/Corpus_evaluation_RAG.xlsx
```

Le service contrôle tout le fichier. Si une seule ligne est fausse, rien n'est importé, et chaque erreur est listée avec sa feuille, sa ligne et la correction attendue : c'est la liste à renvoyer au métier. On corrige, on relance. Le service signale aussi ce qui manque pour atteindre la taille minimale (10 documents par type, 50 questions, 20 pages scannées retapées).

## 2. Ouvrir les quatre endpoints du RAG au service

Le service n'entre jamais dans votre RAG : il appelle **quatre endpoints**, quatre adresses web de forme fixe que votre RAG ouvre. Vous les ajoutez dans un dossier à part, écrit pour l'évaluation et pour rien d'autre. La règle complète : [guide 0b](0b_endpoints_du_rag.md).

| Endpoint | Ce que le service envoie | Ce que votre RAG rend |
| --- | --- | --- |
| ① `POST /ingerer` | les documents du corpus | combien de documents, de morceaux et de pages il a rangés |
| ② `GET /index` | rien | sa version exacte, tous ses morceaux de texte, les pages qu'il a lues |
| ③ `POST /rechercher` | une question, et le profil de la personne qui la pose | les k morceaux retrouvés, dans l'ordre |
| ④ `POST /repondre` | la même chose | sa réponse, ses sources, et s'il s'abstient |

### Partir du modèle

[`endpoints_a_copier/endpoints_evaluation.py`](../endpoints_a_copier/endpoints_evaluation.py) est un modèle complet, à copier dans votre RAG. Tel quel, il marche déjà : c'est un « RAG » jouet, qui fait un morceau par page et cherche par mots communs. Vous remplacez le contenu des quatre fonctions marquées **À REMPLACER** par l'appel à votre RAG ; les formes d'entrée et de sortie ne changent pas.

Avant de toucher à votre RAG, lancez le modèle tel quel, depuis `endpoints_a_copier/`, puis faites les étapes 4 et 5 : vous verrez le service évaluer le RAG jouet de bout en bout (score pondéré d'environ 24 % : c'est un jouet).

```bash
uv run --with fastapi --with uvicorn --with pypdf uvicorn endpoints_evaluation:app --host 127.0.0.1 --port 8100
```

Votre RAG n'est pas en Python ? Il ouvre les mêmes quatre adresses, avec les mêmes champs ([contrat](methode_et_contrat/contrat_des_fichiers.md#les-endpoints-dévaluation)).

### ① Ingérer

Le service envoie ses documents. Votre RAG les range **comme en production** (même lecture, même découpage, mêmes modèles), mais **à part** : un autre dossier, une autre collection, jamais l'index de production.

Pour chaque document, il reçoit `reference_source`, `titre`, `type_document`, `version`, `format`, `droits_acces`, `fichier` (le nom du fichier) et `contenu` (le fichier, en base64). Par exemple, si votre RAG a une fonction qui indexe un dossier (`mon_rag.indexer` est un nom d'exemple) :

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

Le point qui compte : chaque morceau de votre index doit garder **la référence du document reçue (`reference_source`), sa version, sa page et ses droits d'accès**. Sans eux, le service ne peut pas retrouver les passages du métier, ni vérifier les droits.

### ② Montrer l'index

| Partie | Ce qu'on y met |
| --- | --- |
| `rag` | le nom du RAG, sa **version** (`version_rag`), son type (`vectoriel`, `graphe`, `hybride`, `agent`), k, les versions de ses briques |
| `chunks` | chaque morceau de l'index : `chunk_id`, `reference_source`, `version_document`, `page`, `type_element`, `droits_acces`, `ordre`, `texte`, `version_index` |
| `pages` | le texte de chaque page lue, avant découpage : il sert à mesurer la lecture des scans |
| `graphe` | le graphe en Turtle, si votre RAG en a un ; sinon `null` |

La version doit **changer dès que l'index, un modèle, le prompt ou k changent** : c'est ce qui permet de comparer deux configurations sans ambiguïté.

### ③ Rechercher

Pour une question, votre RAG rend les k morceaux retrouvés, dans l'ordre, **avant toute génération** : `chunk_id`, `rang`, `score`. Il applique les droits du `profil` **pendant** la recherche : un morceau interdit ne doit jamais remonter. Pour une question de suite, `historique` contient l'échange précédent.

### ④ Répondre

Pour une question, votre RAG rend sa réponse, telle qu'un utilisateur la recevrait : `reponse`, `abstention` (vrai si votre RAG dit lui-même ne pas savoir), `chunks_cites` (les sources citées), `chunks_contexte` (tous les morceaux donnés au modèle), `duree_ms`, `trace_id`, et si possible `cout`, `tokens_entree`, `tokens_sortie`.

### Vérifier les endpoints

Lancez votre RAG, endpoints ouverts, mettez son adresse dans `rag.adresse` de [`config/kit.yaml`](../config/kit.yaml), puis :

```bash
uv run kit appeler-rag
```

Le service envoie les documents, pose chaque question, range ce que votre RAG rend dans `resultats/reponses_du_rag/`, puis le vérifie. Il finit par « règle : respectée », ou il dit **précisément ce qui ne va pas**, endpoint par endpoint et ligne par ligne :

```
Réponses du RAG rangées dans resultats/reponses_du_rag/mon-rag-k5-d2a069ef ; règle : 3 écart(s).
  - chunks.jsonl, ligne 13 : champ « texte » : ne doit pas être vide.
  - reponses.jsonl, ligne 3 : champ obligatoire « abstention » absent.
  - recherches.jsonl, Q-007 : posée avec le profil « tous » au lieu de « exploitation ».
```

On corrige les endpoints, on relance, jusqu'à « règle : respectée ».

| Erreur fréquente | Ce que l'évaluation verra |
| --- | --- |
| une référence de document modifiée (`PR-1101.pdf` au lieu de `PR-1101`) | aucun passage retrouvé : l'évaluation 1 s'effondre |
| la page d'un morceau en nombre, ou la page où il finit | des passages introuvables |
| les droits filtrés **après** la recherche, au lieu de pendant | une fuite de droits : un document montré à qui n'y a pas droit |
| des `chunk_id` différents entre ② et ③ | des recherches qui citent des morceaux inconnus : le service refuse |
| une version qui ne change pas quand un réglage change | deux configurations confondues, comparaison impossible |
| l'abstention devinée dans le texte, au lieu d'être dite par le RAG | des abstentions mal comptées |
| les documents de l'évaluation indexés avec ceux de la production | une évaluation faussée, et une production polluée |

## 3. Évaluer une configuration du RAG

C'est vous qui lancez l'évaluation ; votre RAG n'a qu'à rester allumé.

**Les configurations.** Une configuration, ce sont les réglages de votre RAG à un moment donné : k, modèles, prompt, découpage… Ils sont propres à chaque RAG et **se changent dans le RAG, jamais dans le service**. Le service les lit dans ce que le RAG déclare (endpoint ②), et nomme l'évaluation d'après eux. Pour tester une autre configuration : vous changez le réglage dans le RAG, vous le relancez, puis vous relancez `kit evaluer`. Un run = une configuration.

```bash
uv run kit evaluer
```

Le service appelle les quatre endpoints, puis enchaîne les quatre évaluations : l'ingestion, la recherche, la réponse, et de bout en bout. Il affiche à la fin les scores clés, chacun en une phrase, et le chemin du rapport.

## 4. Lire le rapport, comparer, faire décider le métier

Le rapport est dans `resultats/evaluations/<version du corpus>_<version du RAG>/RAPPORT.md`. Il donne d'abord les scores clés, ceux à présenter au métier, puis tous les scores, chacun en une phrase, les questions à regarder en premier, et si la faute vient de la recherche ou de la réponse. Il ne décide pas : c'est le métier qui tranche. Comment le lire : [guide 5](5_resultats_et_comparaison.md).

| Ensuite | Comment |
| --- | --- |
| comprendre un mauvais score, et quoi changer dans le RAG | la section « Si c'est mauvais » des guides [1](1_evaluation_ingestion.md), [2](2_evaluation_recherche.md), [3](3_evaluation_reponse.md) et [4](4_evaluation_bout_en_bout.md) |
| vérifier le juge, une fois, puis à chaque changement de juge | `kit verifier-juge --envoyer` ; le métier note 30 réponses dans Langfuse ; puis `kit verifier-juge` ([guide 3](3_evaluation_reponse.md#vérifier-le-juge-avant-de-lui-faire-confiance)) |
| faire relire au métier les réponses douteuses | dans Langfuse, la file `relecture-reponses` |
| tester un autre réglage | relancer votre RAG avec ce réglage, `kit evaluer`, puis `kit comparer resultats/evaluations/<A> resultats/evaluations/<B>` ([guide 5](5_resultats_et_comparaison.md#5-comparer-deux-versions)) |
| faire décider le métier | lui présenter les scores clés et les questions ratées de la meilleure configuration : il dit si elle peut partir en production, ou ce qu'il faut corriger d'abord |

## Récapitulatif

- [ ] le service est installé, `kit verifier-modeles` répond ;
- [ ] le métier a rendu les documents et le fichier rempli, et `kit importer` l'accepte ;
- [ ] votre RAG ouvre ses quatre endpoints, et range les documents de l'évaluation à part ;
- [ ] `kit appeler-rag` finit par « règle : respectée » ;
- [ ] `kit evaluer` a écrit le `RAPPORT.md`, et le juge est vérifié ;
- [ ] le métier a lu les scores clés et a décidé.
