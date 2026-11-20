# Partie 2 — Le RAG de démonstration

Ce RAG est un **prétexte** : il montre comment un RAG se branche sur le kit. Il est volontairement minimal, et ses défauts sont utiles : ils donnent au kit quelque chose à mesurer. Pour brancher **votre** RAG, partez du [contrat](../corpus/README.md#3-brancher-un-rag--le-contrat) ; ce dossier est un exemple à copier.

```
rag/
├── rag_demo/
│   ├── config.yaml      LE fichier de réglage : point d'accès, modèles, k, chemins
│   ├── extraction.py    lecture des PDF et découpage en chunks
│   ├── rag.py           index, recherche, génération, traces Langfuse
│   ├── connecteur.py    les six méthodes du contrat (pour kit lancer)
│   └── cli.py           la commande rag-demo
└── tests/
```

Il n'importe rien du kit, et le kit n'importe rien de lui : un test le vérifie.

## Ce qu'il fait

| Étape | Comment | Fichier |
| --- | --- | --- |
| Extraction | PDF natifs et scannés : Docling (mise en page, tableaux, OCR) ; fiches de base de données : `pypdf`, qui garde les colonnes « champ : valeur » | `extraction.py` |
| Découpage | un chunk par section, avec le chemin de titres en tête ; un chunk par tableau, lignes écrites « colonne : valeur » ; un chunk par figure (sa légende) ; un chunk par champ de fiche. Chaque chunk porte la référence, la version, la page, le type d'élément et les droits du document | `extraction.py` |
| Index | les vecteurs en mémoire (numpy), sauvegardés sur disque : pas de base vectorielle | `rag.py` |
| Recherche | hybride : sens (embeddings) et mots (BM25), fusionnés par rang ; **filtre des droits avant le classement** | `rag.py` |
| Génération | un seul prompt : citations [n] obligatoires, phrase d'abstention fixe si les extraits ne suffisent pas | `rag.py` |
| Suivi | une trace Langfuse par question (recherche, génération, tokens) | `rag.py` |

## Le régler : un seul fichier

Tout est dans [`rag_demo/config.yaml`](rag_demo/config.yaml) ; seule la clé est dans `.env` (`RAG_LLM_CLE`).

| Réglage | Valeur ici | Pour changer |
| --- | --- | --- |
| `modeles.adresse` | `http://127.0.0.1:8080/v1` (LiteLLM local) | n'importe quel point d'accès compatible OpenAI |
| `modeles.generation.modele` | `gemma-4-e4b` | un autre modèle de génération ; prix au million de tokens pour le coût |
| `modeles.embeddings.modele` | `embed` (bge-m3) | relancer `rag-demo indexer` après un changement |
| `recherche.k` | 5 | ou `--k 3` sur la ligne de commande : une autre version du RAG, comparable |
| `documents`, `catalogue` | le corpus d'exemple | les documents et le `documents.jsonl` de votre corpus |

La **version du RAG** (`rag-demo-k5-80032dcd`) se calcule à partir de k, des modèles, du prompt et de l'index. Changer un réglage donne une nouvelle version, dans un nouveau dossier de `sorties/sorties_rag/`. Deux versions se comparent avec `kit comparer`.

## Le faire tourner

```bash
uv run rag-demo indexer
```

La commande lit le catalogue (`sorties/corpus/<dernière version>/documents.jsonl`), extrait, découpe et vectorise les documents. Il faut 2 minutes la première fois, le temps que Docling lise les 50 PDF. Les fois suivantes sont instantanées : l'extraction est gardée dans `sorties/rag_demo/extraction/`.

```bash
uv run rag-demo exporter
```

La commande écrit `rag.json`, `chunks.jsonl` et `pages_extraites.jsonl` dans `sorties/sorties_rag/<version_rag>/`.

```bash
uv run rag-demo repondre sorties/corpus/2026-11-20.1/questions.jsonl
```

La commande pose les 60 questions, chacune avec son profil, en environ 8 secondes par question. Elle écrit `recherches.jsonl` et `reponses.jsonl`.

On peut aussi faire tout cela en une commande, par le connecteur, avec la commande du kit :

```bash
uv run kit lancer rag_demo.connecteur:Connecteur --corpus sorties/corpus/2026-11-20.1 -p k=3
```

## Ses limites connues, et ce que le kit en dit

Ces limites sont voulues ou acceptées : c'est un prétexte. Elles montrent que le kit les détecte.

| Limite | Ce que le kit mesure |
| --- | --- |
| Pas de modèle de vision : une figure n'est connue que par sa légende ; une valeur écrite seulement dans un schéma est perdue | niveau 3 : la question Q-034 (câbles du TGBT-A, lisibles seulement sur le schéma) reçoit une abstention |
| Docling écarte l'en-tête et le pied de page, colle des mots, et mélange parfois l'ordre des lignes d'un scan | niveau 1 : taux d'erreur de caractères de 15 %, seuil 2 % |
| Toutes les versions des documents sont indexées, même celles qui ne sont plus en vigueur | niveau 2 : « périmé ou piège avant le bon passage » |
| Recherche simple, sans reranker ni décomposition de la question | niveau 2 : les questions qui combinent plusieurs passages échouent plus souvent |
| Un seul prompt, petit modèle (4 milliards de paramètres) | niveau 3 : les synthèses sur l'ensemble des documents sont fausses ; voir le croisement recherche × réponse |
