# Évaluer votre RAG : la marche à suivre

Ce guide s'adresse à la personne qui prend en charge l'évaluation : data scientist, chef de projet technique, quelqu'un qui sait lire un dépôt et lancer des commandes. C'est elle qui fait toutes les étapes. Le métier n'intervient qu'à l'étape 1 et à l'étape 3 : il fournit le corpus annoté, selon les règles que vous lui transmettez, et il fixe avec vous les seuils.

Un exemple complet, où toutes ces étapes ont été faites : [`service-evaluation-exemple/`](../../service-evaluation-exemple/README.md#ce-quon-a-fait-dans-lordre).

| Étape | Ce que vous faites | Fini quand |
| --- | --- | --- |
| [0. Installer le service](#0-installer-le-service) | copier `service-evaluation/`, démarrer Langfuse, brancher le modèle juge | `kit verifier-modeles` répond |
| [1. Demander le corpus au métier](#1-demander-le-corpus-au-métier) | lui donner le fichier Excel vierge et les règles pour le remplir | le métier vous rend les documents et le fichier rempli |
| [2. Ranger et importer le corpus](#2-ranger-et-importer-le-corpus) | mettre les documents et le fichier à leur place, puis `kit importer` | l'import ne signale plus d'erreur |
| [3. Fixer les seuils avec le métier](#3-fixer-les-seuils-avec-le-métier) | écrire dans `config/seuils.json` ce que le RAG doit atteindre | les seuils sont fixés **avant** toute évaluation |
| [4. Brancher votre RAG](#4-brancher-votre-rag) | ouvrir dans votre RAG les quatre endpoints, à partir de `endpoints_a_copier/` | `kit appeler-rag` finit par « règle : respectée » |
| [5. Lancer l'évaluation](#5-lancer-lévaluation) | `kit evaluer` | un `RAPPORT.md` est écrit |
| [6. Lire, corriger, comparer](#6-lire-corriger-comparer) | lire le rapport ; changer un réglage du RAG, réévaluer, comparer | la décision est prise |

## 0. Installer le service

Copiez le dossier `service-evaluation/` dans votre projet : c'est le service, vierge. Il faut Docker, [uv](https://docs.astral.sh/uv/), et un accès à des modèles de langage par une API compatible OpenAI, pour le modèle juge. Depuis `service-evaluation/` :

```bash
cp .env.example .env
```

Mettez dans `.env` la clé de l'API (`KIT_LLM_CLE`), et dans [`config/kit.yaml`](../config/kit.yaml) son adresse, le nom des modèles (`modeles`) et le nom de votre projet (`projet`). Puis :

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

## 1. Demander le corpus au métier

Le corpus annoté est ce qui permet de juger le RAG : des questions réelles, leur bonne réponse, et l'endroit exact des documents où elle se trouve. Le RAG ne le voit jamais ; il ne reçoit que les documents.

Donnez au métier deux choses :

1. **Le fichier Excel vierge**, [`corpus_annote/Corpus_evaluation_RAG.xlsx`](../corpus_annote/Corpus_evaluation_RAG.xlsx). Chaque feuille porte ses définitions et ses listes de valeurs.
2. **Les règles pour le remplir** : le [guide 0a](0a_construction_du_corpus.md), section 1. Elles disent quels documents choisir, combien de questions écrire et de quels types, comment copier-coller le passage qui contient la réponse, comment noter la fréquence et la gravité de chaque question, et quelles questions garder de côté pour la décision.

Il vous rend :

- **les documents**, un fichier par document, nommé par sa référence : `<référence>.<extension>`, par exemple `PR-1101.pdf` ;
- **le fichier Excel rempli** : la liste des documents, les questions, leur bonne réponse, les passages qui la contiennent, et quelques pages scannées retapées à la main.

Un fichier rempli, pour montrer au métier ce qu'on attend : [celui de l'exemple](../../service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx).

## 2. Ranger et importer le corpus

| Ce que le métier a rendu | Où vous le mettez |
| --- | --- |
| les documents | `corpus_annote/corpus_documentaire/` |
| le fichier Excel rempli | `corpus_annote/Corpus_evaluation_RAG.xlsx`, à la place du fichier vierge |

Puis importez :

```bash
uv run kit importer corpus_annote/Corpus_evaluation_RAG.xlsx
```

Le service contrôle tout le fichier. Si une seule ligne est fausse, rien n'est importé, et chaque erreur est listée avec sa feuille, sa ligne et la correction attendue : c'est la liste à renvoyer au métier. On corrige, on relance. Le service signale aussi ce qui manque pour atteindre la taille minimale (10 documents par type, 50 questions, 20 pages scannées retapées).

## 3. Fixer les seuils avec le métier

Il y a **un seuil par score** : le niveau minimal que ce score doit atteindre, par exemple « au moins 80 % de réponses justes ». Il n'y a pas de seuil unique, parce que chaque score mesure une chose différente : une moyenne de tous les scores laisserait un bon score cacher un mauvais, par exemple d'excellentes réponses qui cachent une fuite de droits. Le RAG part en production seulement si **chaque** score atteint son seuil, sur les 20 questions réservées à la décision, et s'il n'y a aucune erreur grave ni aucune fuite de droits.

Une partie des seuils dépend de ce que les utilisateurs peuvent accepter. Ce n'est pas à vous d'en décider : c'est au métier. Avant toute évaluation, vous lui posez donc ces questions, et vous écrivez ses réponses dans [`config/seuils.json`](../config/seuils.json) :

| Question à poser au métier | Valeur proposée par défaut | Ligne de `seuils.json` |
| --- | --- | --- |
| Quelle part de réponses justes est acceptable ? | au moins 80 % | `n3_exactitude` |
| Et en comptant davantage les questions fréquentes et graves ? | au moins 80 % | `n4_score_pondere` |
| Une réponse fausse à une question grave est-elle tolérable ? | non : aucune | `n3_erreurs_graves`, `n4_erreurs_graves` (bloquants) |
| Montrer un document réservé à quelqu'un qui n'y a pas droit est-il tolérable ? | non : jamais | `n2_fuite_droits` (bloquant) |
| Quand la réponse n'est pas dans les documents, le RAG doit-il le dire ? | oui, dans au moins 80 % des cas | `n3_abstention_correcte` |
| Combien de temps un utilisateur peut-il attendre une réponse ? | 15 s en général, 30 s au pire | `n4_temps_median`, `n4_temps_p95` |
| Combien peut coûter une réponse ? | 0,05 € au plus | `n4_cout_moyen` |

Un critère **bloquant** refuse la mise en production à lui seul, quels que soient les autres scores.

Les autres seuils sont techniques : la lecture des documents, la recherche du bon passage, la fidélité aux documents. Vous les gardez tels qu'ils sont proposés, sauf raison particulière. Ce que mesure chaque score : les guides [1](1_evaluation_ingestion.md) à [4](4_evaluation_bout_en_bout.md) ; les seuils proposés et leur raison : [document 3](methode_et_contrat/methode_evaluation.md), section 9.

Les seuils se fixent **avant** de voir le moindre score : sinon, on finit par les choisir pour faire passer le RAG.

## 4. Brancher votre RAG

Le service n'entre jamais dans votre RAG : il appelle **quatre endpoints**, quatre adresses web de forme fixe que votre RAG ouvre. Vous les ajoutez dans un dossier à part, écrit pour l'évaluation et pour rien d'autre. La règle complète : [guide 0b](0b_endpoints_du_rag.md).

| Endpoint | Ce que le service envoie | Ce que votre RAG rend |
| --- | --- | --- |
| ① `POST /ingerer` | les documents du corpus | combien de documents, de morceaux et de pages il a rangés |
| ② `GET /index` | rien | sa version exacte, tous ses morceaux de texte, les pages qu'il a lues |
| ③ `POST /rechercher` | une question, et le profil de la personne qui la pose | les k morceaux retrouvés, dans l'ordre |
| ④ `POST /repondre` | la même chose | sa réponse, ses sources, et s'il s'abstient |

### Partir du modèle

[`endpoints_a_copier/endpoints_evaluation.py`](../endpoints_a_copier/endpoints_evaluation.py) est un modèle complet, à copier dans votre RAG. Tel quel, il marche déjà : c'est un « RAG » jouet, qui fait un morceau par page et cherche par mots communs. Vous remplacez le contenu des quatre fonctions marquées **À REMPLACER** par l'appel à votre RAG ; les formes d'entrée et de sortie ne changent pas.

Avant de toucher à votre RAG, lancez le modèle tel quel, depuis `endpoints_a_copier/`, puis faites les étapes 5 et 6 : vous verrez le service évaluer le RAG jouet de bout en bout (score pondéré d'environ 24 % : c'est un jouet).

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
| les droits filtrés **après** la recherche, au lieu de pendant | une fuite de droits, critère bloquant |
| des `chunk_id` différents entre ② et ③ | des recherches qui citent des morceaux inconnus : le service refuse |
| une version qui ne change pas quand un réglage change | deux configurations confondues, comparaison impossible |
| l'abstention devinée dans le texte, au lieu d'être dite par le RAG | des abstentions mal comptées |
| les documents de l'évaluation indexés avec ceux de la production | une évaluation faussée, et une production polluée |

## 5. Lancer l'évaluation

C'est vous qui lancez l'évaluation ; votre RAG n'a qu'à rester allumé. Une évaluation porte sur **une configuration** de votre RAG, c'est-à-dire tous ses réglages tels qu'ils sont au moment du lancement.

```bash
uv run kit evaluer
```

Le service appelle les quatre endpoints, puis enchaîne les quatre évaluations : l'ingestion, la recherche, la réponse, et de bout en bout. Il affiche à la fin la décision et le chemin du rapport.

## 6. Lire, corriger, comparer

Le rapport est dans `resultats/evaluations/<version du corpus>_<version du RAG>/RAPPORT.md`. Il donne la décision, puis chaque score avec son seuil, les questions à regarder en premier, et si la faute vient de la recherche ou de la réponse. Comment le lire : [guide 5](5_resultats_et_comparaison.md).

| Ensuite | Comment |
| --- | --- |
| comprendre un mauvais score, et quoi changer dans le RAG | la section « Si c'est mauvais » des guides [1](1_evaluation_ingestion.md), [2](2_evaluation_recherche.md), [3](3_evaluation_reponse.md) et [4](4_evaluation_bout_en_bout.md) |
| vérifier le juge, une fois, puis à chaque changement de juge | `kit verifier-juge --envoyer` ; le métier note 30 réponses dans Langfuse ; puis `kit verifier-juge` ([guide 3](3_evaluation_reponse.md#vérifier-le-juge-avant-de-lui-faire-confiance)) |
| faire relire au métier les réponses douteuses | dans Langfuse, la file `relecture-reponses` |
| tester un autre réglage | relancer votre RAG avec ce réglage, `kit evaluer`, puis `kit comparer resultats/evaluations/<A> resultats/evaluations/<B>` ([guide 5](5_resultats_et_comparaison.md#5-comparer-deux-versions)) |

## Récapitulatif

- [ ] le service est installé, `kit verifier-modeles` répond ;
- [ ] le métier a rendu les documents et le fichier rempli, et `kit importer` l'accepte ;
- [ ] les seuils sont fixés avec le métier, avant toute évaluation ;
- [ ] votre RAG ouvre ses quatre endpoints, et range les documents de l'évaluation à part ;
- [ ] `kit appeler-rag` finit par « règle : respectée » ;
- [ ] `kit evaluer` a écrit le `RAPPORT.md`, et le juge est vérifié.
