# Le fil conducteur : évaluer un RAG, du début à la fin

Ce document dit, dans l'ordre, ce qu'on fait pour évaluer un RAG, où c'est expliqué en détail, et ce que ça a donné sur l'exemple. Il s'adresse à la personne qui prend en charge l'évaluation et sait lancer des commandes : c'est elle qui fait tout. Le métier remplit le corpus d'évaluation et fixe avec elle les seuils.

Les trois dossiers du dépôt :

- [`service-evaluation/`](service-evaluation/README.md) : le service d'évaluation, vierge, à prendre pour votre projet ;
- [`service-rag-exemple/`](service-rag-exemple/README.md) : un RAG simple, qui sert d'exemple à évaluer ;
- [`service-evaluation-exemple/`](service-evaluation-exemple/README.md) : le même service, après avoir tourné sur ce RAG. Tout ce qui est cité « dans l'exemple » s'y trouve.

```mermaid
flowchart TD
    E0["<b>0. Installer le service</b><br/>service-evaluation/README.md, étape 0"]
    E0 --> E1["<b>1. Construire le corpus d'évaluation</b><br/>guide 0a : les règles à donner au métier"]
    E1 --> E2["<b>2. Ranger et importer le corpus</b><br/>service-evaluation/README.md, étape 2"]
    E2 -- "erreurs : à corriger par le métier" --> E1
    E2 --> E3["<b>3. Fixer les seuils</b><br/>guide de la marche à suivre, étape 3"]
    E3 --> E4["<b>4. Brancher le RAG</b><br/>guide 0b, endpoints_a_copier/,<br/>service-rag-exemple/README.md"]
    E4 --> E5["<b>5. Lancer un run par configuration</b><br/>kit evaluer"]
    E5 -- "autre configuration :<br/>changer le réglage dans le RAG" --> E5
    E5 --> E6["<b>6. Lire, vérifier le juge, comparer</b><br/>RAPPORT.md, guide 5, guide 3"]
    E6 --> X["<b>service-evaluation-exemple/README.md</b><br/>tout ce parcours, fait pour de vrai"]
```

## 0. Installer le service

Le service d'évaluation tourne sur votre machine. Pour fonctionner, il a besoin de trois choses :
- **Langfuse**, un site web local où l'on suit les évaluations, et où le métier relit les réponses du RAG ;
- **un modèle de langage, le juge**, qui note les réponses du RAG en les comparant aux bonnes réponses du métier. On s'y connecte avec une clé d'accès ;
- **ses bibliothèques Python**.

Depuis `service-evaluation/`, quatre commandes les mettent en place :

1. `cp .env.example .env`, puis écrire dans `.env` la clé d'accès au juge (`KIT_LLM_CLE`) ;
2. `./initialiser.sh` : écrit dans `.env` les mots de passe de Langfuse ;
3. `docker compose up -d` : démarre Langfuse, à http://127.0.0.1:3100 ;
4. `uv run kit verifier-modeles` : installe les bibliothèques Python, puis vérifie que le juge et Langfuse répondent.

L'installation est finie quand cette dernière commande dit que tout répond. Le détail : [README du service, étape 0](service-evaluation/README.md#la-marche-à-suivre).

**Dans l'exemple.** Le juge est le modèle `chat`, différent du modèle qui écrit les réponses du RAG : un modèle tend à favoriser ses propres réponses.

## 1. Construire le corpus d'évaluation

Pour évaluer le RAG, le service a besoin d'un **corpus d'évaluation** : les documents que le RAG doit lire, et un fichier Excel qui donne, pour chaque question, la bonne réponse et le passage exact des documents où elle se trouve. Le RAG ne voit jamais ce fichier : il ne reçoit que les documents.

Qui fait quoi :
- **le métier construit le corpus**, parce que c'est lui qui connaît les documents et les questions des utilisateurs. Il suit le [guide 0a](service-evaluation/documentation/0a_construction_du_corpus.md), écrit pour lui : copier-coller les passages, jamais les résumer ; prévoir des questions sans réponse et des passages pièges ; garder un tiers des questions pour la décision ; donner à chaque question une fréquence et une gravité ;
- **vous** lui transmettez ce guide et le fichier Excel vierge, [`service-evaluation/corpus_annote/Corpus_evaluation_RAG.xlsx`](service-evaluation/corpus_annote/Corpus_evaluation_RAG.xlsx). Pour lui montrer ce qu'on attend : [le fichier rempli de l'exemple](service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx).

Le métier vous rend les documents, un fichier par document nommé par sa référence, et le fichier Excel rempli.

**Dans l'exemple.** L'entreprise est fictive : Claude a joué le métier. Il a rendu [50 documents](service-evaluation-exemple/corpus_annote/corpus_documentaire/) et [le fichier rempli](service-evaluation-exemple/corpus_annote/Corpus_evaluation_RAG.xlsx) : 60 questions, 97 passages, 20 pages scannées retapées. Les 60 questions sur une page : [questions_pour_relecture.md](service-evaluation-exemple/corpus_annote/questions_pour_relecture.md).

## 2. Ranger et importer le corpus

Vous mettez les documents dans `corpus_annote/corpus_documentaire/`, le fichier rempli dans `corpus_annote/`, puis :

```bash
uv run kit importer corpus_annote/Corpus_evaluation_RAG.xlsx
```

Le service contrôle tout le corpus avant d'évaluer, car un corpus faux fausserait toute l'évaluation. Si une seule ligne est fausse, rien n'est importé : vous renvoyez au métier la liste des erreurs, feuille par feuille et ligne par ligne, et vous recommencez. Le détail : [README du service, étape 2](service-evaluation/README.md#la-marche-à-suivre).

**Dans l'exemple.** L'import a produit le corpus contrôlé : [`resultats/corpus/2026-11-20.1/`](service-evaluation-exemple/resultats/corpus/).

## 3. Fixer les seuils

Il y a un seuil par score : le niveau minimal qu'il doit atteindre pour que le RAG parte en production. Le RAG part seulement si chaque score atteint son seuil, sur les questions gardées pour la décision, et s'il n'y a aucune erreur grave ni fuite de droits.

Vous posez au métier les questions de la [marche à suivre, étape 3](service-evaluation/documentation/integrer_votre_rag.md#3-fixer-les-seuils-avec-le-métier) (quelle part de réponses justes est acceptable, combien de temps attendre…), et vous écrivez ses réponses dans `config/seuils.json`. Toujours **avant** la première évaluation : sinon, on finit par choisir les seuils pour faire passer le RAG.

**Dans l'exemple.** [`config/seuils.json`](service-evaluation-exemple/config/seuils.json) : par exemple au moins 80 % de réponses justes, aucune erreur grave, une réponse en moins de 15 secondes.

## 4. Brancher le RAG

Le service ne connaît pas le code du RAG. Il lui parle par quatre **endpoints**, quatre adresses web de forme fixe : ① il lui envoie les documents ; ② il lit ce que le RAG en a fait ; ③ il lui demande de rechercher ; ④ il lui demande de répondre.

Vous copiez le code tout prêt, [`service-evaluation/endpoints_a_copier/`](service-evaluation/endpoints_a_copier/), dans votre RAG, et vous y branchez ses fonctions ([guide 0b](service-evaluation/documentation/0b_endpoints_du_rag.md) : ce que chaque endpoint reçoit et rend). Vous lancez le RAG, vous mettez son adresse dans `rag.adresse` de `config/kit.yaml`, puis vous vérifiez :

```bash
uv run kit appeler-rag
```

C'est bon quand il répond « règle : respectée » ; sinon, il dit précisément ce qui ne va pas.

**Dans l'exemple.** Le RAG d'exemple ouvre ses quatre endpoints dans [`src/rag/endpoints_evaluation/`](service-rag-exemple/src/rag/endpoints_evaluation/). On l'a lancé comme le dit [son README](service-rag-exemple/README.md#le-lancer) : `docker compose up -d --build`, depuis `service-rag-exemple/`, à l'adresse http://127.0.0.1:8100.

## 5. Lancer un run par configuration

Une configuration, ce sont les réglages du RAG à un moment donné : le nombre de morceaux que la recherche ramène (k), les modèles, le prompt… Un run évalue une configuration. Les réglages se changent **dans le RAG**, jamais dans le service.

Le RAG allumé avec la configuration à tester, vous lancez :

```bash
uv run kit evaluer
```

Le service appelle lui-même le RAG : il lui envoie les documents, pose toutes les questions, puis calcule les scores des quatre évaluations (l'ingestion, la recherche, la réponse, de bout en bout). Il écrit un `RAPPORT.md` dans `resultats/evaluations/`. Pour une autre configuration : vous changez le réglage dans le RAG, vous le relancez, puis vous relancez `kit evaluer`. Pour le RAG d'exemple : [« Changer de configuration »](service-rag-exemple/README.md#changer-de-configuration).

**Dans l'exemple.** Quatre runs, en relançant à chaque fois le RAG d'exemple avec un réglage différent :

| Configuration | Réglage du RAG | Rapport produit |
| --- | --- | --- |
| Référence | `docker compose up -d` : 5 morceaux ramenés | [RAPPORT.md](service-evaluation-exemple/resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k5-5954e822/RAPPORT.md) |
| k = 3 | `RAG_K=3 docker compose up -d` | [RAPPORT.md](service-evaluation-exemple/resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k3-5954e822/RAPPORT.md) |
| Sans réflexion | `sans_reflexion: true` dans la configuration du RAG | [RAPPORT.md](service-evaluation-exemple/resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k5-94d362c8/RAPPORT.md) |
| Hybride | `RAG_GRAPHE=true docker compose up -d` : un graphe ajouté | [RAPPORT.md](service-evaluation-exemple/resultats/evaluations/2026-11-20.1_graphrag-hybride-k5-57001489/RAPPORT.md) |

## 6. Lire, vérifier le juge, comparer

### 6a. Lire le rapport

Le `RAPPORT.md` de chaque configuration dit si elle peut partir en production, et sinon où est le problème. On le lit dans l'ordre : la décision ; les scores, évaluation par évaluation ; les questions à regarder ; enfin, si la faute vient de la recherche ou de la réponse. Le détail : [guide 5](service-evaluation/documentation/5_resultats_et_comparaison.md#2-lire-le-rapport-dans-lordre).

**Dans l'exemple.** Le [rapport de la référence](service-evaluation-exemple/resultats/evaluations/2026-11-20.1_graphrag-vectoriel-k5-5954e822/RAPPORT.md) dit : « Mise en production non recommandée ». Il y a 1 erreur grave, et quatre seuils ne sont pas atteints : la lecture des pages scannées, le bon passage ramené, les réponses justes, le score pondéré.

### 6b. Vérifier le juge

C'est le juge qui note les réponses : avant de croire ses notes, on vérifie qu'il note comme le métier. `uv run kit verifier-juge --envoyer` envoie 30 réponses dans Langfuse ; le métier les note ; puis `uv run kit verifier-juge` mesure l'accord. Le détail : [guide 3](service-evaluation/documentation/3_evaluation_reponse.md#vérifier-le-juge-avant-de-lui-faire-confiance).

**Dans l'exemple.** Le juge et le métier sont d'accord à 89 %, pour 90 % exigés : le juge est à surveiller.

### 6c. Comparer deux configurations

Pour savoir si un réglage améliore vraiment le RAG, ou si l'écart est dû au hasard :

```bash
uv run kit comparer resultats/evaluations/<configuration A> resultats/evaluations/<configuration B>
```

Le service écrit un `RAPPORT.md` de comparaison dans `resultats/comparaisons_de_configurations/`. Le détail : [guide 5](service-evaluation/documentation/5_resultats_et_comparaison.md#5-comparer-deux-versions).

**Dans l'exemple.** Chaque configuration est comparée à la référence :

| Comparaison | Conclusion | Rapport |
| --- | --- | --- |
| Référence contre k = 3 | pas meilleure : elle retrouve moins souvent le bon passage | [RAPPORT.md](service-evaluation-exemple/resultats/comparaisons_de_configurations/2026-11-20.1_graphrag-vectoriel-k5-5954e822_contre_graphrag-vectoriel-k3-5954e822/RAPPORT.md) |
| Référence contre sans réflexion | on garde la réflexion : sans elle, 9 fois plus rapide, mais les calculs deviennent faux | [RAPPORT.md](service-evaluation-exemple/resultats/comparaisons_de_configurations/2026-11-20.1_graphrag-vectoriel-k5-5954e822_contre_graphrag-vectoriel-k5-94d362c8/RAPPORT.md) |
| Référence contre hybride | rien de mesurable : l'écart peut venir du hasard | [RAPPORT.md](service-evaluation-exemple/resultats/comparaisons_de_configurations/2026-11-20.1_graphrag-vectoriel-k5-5954e822_contre_graphrag-hybride-k5-57001489/RAPPORT.md) |

**Conclusion de l'exemple.** Aucune configuration n'est prête. Les quatre butent sur les mêmes points : les pages scannées sont mal lues, et la recherche ne ramène pas assez souvent le bon passage. C'est donc là qu'il faut corriger le RAG, avant de relancer un run.
