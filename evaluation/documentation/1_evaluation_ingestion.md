# 1. Évaluation de l'ingestion

**La question** : le RAG a-t-il bien lu et découpé les documents ? Les passages annotés par le métier sont-ils dans son index ?

C'est la première évaluation, et elle peut tourner juste après l'ingestion, avant que le RAG ait répondu à une seule question. Un passage absent de l'index ne pourra jamais être retrouvé ([évaluation 2](2_evaluation_recherche.md)), ni donner une bonne réponse ([évaluation 3](3_evaluation_reponse.md)).

```mermaid
flowchart LR
    P["<b>Passage du métier</b><br/>document, page,<br/>texte copié-collé"] --> R{"<b>Rattachement</b><br/>même document,<br/>même page"}
    C["<b>Chunks du RAG</b><br/>chunks.jsonl"] --> R
    R -- "trouvé" --> L["liens_index.jsonl<br/>passage ↔ chunk"]
    R -- "introuvable" --> N["passages_non_rattaches.jsonl<br/>avec la cause probable"]
    O["<b>Pages retapées</b><br/>par le métier"] --> T{"Erreur de lecture<br/>(jiwer)"}
    E["<b>Pages lues par le RAG</b><br/>pages_extraites.jsonl"] --> T
    T --> S["n1_erreur_caracteres<br/>n1_erreur_mots"]
```

| Où | Quoi |
| --- | --- |
| [`reference/methode_evaluation.md`](reference/methode_evaluation.md) | la méthode (document 3), section 6 pour le rattachement |
| [`../src/kit/etape_1_evaluation_ingestion/rattachement.py`](../src/kit/etape_1_evaluation_ingestion/rattachement.py) | le rattachement d'un passage à un chunk, et la cause probable d'un échec |
| [`../src/kit/etape_1_evaluation_ingestion/scores.py`](../src/kit/etape_1_evaluation_ingestion/scores.py) | les scores de l'ingestion |

## La commande

```bash
uv run kit evaluer-ingestion --corpus sorties/corpus/2026-11-20.1 --rag sorties/sorties_rag/rag-demo-k5-80032dcd
```

Il suffit que le RAG ait écrit `rag.json`, `chunks.jsonl` et, s'il y a des scans, `pages_extraites.jsonl` ([branchement, prise ①](0b_branchement_du_rag.md)).

## Comment le kit tranche : le rattachement

Pour chaque passage du métier, le kit cherche un chunk **du même document et de la même page**, puis compare les textes selon le type d'élément :

| Type de passage | Rattaché si |
| --- | --- |
| texte | le passage est contenu dans le chunk, ou lui ressemble à 95 % |
| tableau | 90 % des mots du passage sont dans le chunk, dans n'importe quel ordre |
| texte scanné | le passage ressemble au chunk à 90 % (l'OCR fait des fautes) |
| image | un chunk de type image existe sur la page |

Un passage réparti sur deux chunks consécutifs est rattaché, mais compté comme **coupé**. Tous les liens trouvés sont écrits dans `liens_index.jsonl` : les évaluations 2 et 3 s'en servent pour savoir quel chunk contient quel passage.

## Les scores

Les identifiants (`n1_…`) sont ceux de `scores.json`, du CSV et de Langfuse. La colonne « Exemple » donne la valeur du RAG d'exemple.

| Score | Ce qu'il mesure | Exemple | Si c'est mauvais |
| --- | --- | --- | --- |
| `n1_documents_indexes` | part des documents du corpus présents dans l'index | 100 % | un document manque : format non lu, erreur d'ingestion |
| `n1_metadonnees_completes` | part des chunks qui portent référence, version, page, type d'élément et droits | 100 % | sans elles, ni rattachement, ni filtre des droits, ni citation possible |
| `n1_passages_rattaches` | part des passages du métier retrouvés dans un chunk du même document, à la même page | 100 % | lire `passages_non_rattaches.jsonl` : chaque passage a sa cause probable (ci-dessous) |
| `n1_passages_coupes` | part des passages coupés entre deux chunks | 0 % | découper par section, ajouter du chevauchement |
| `n1_erreur_caracteres` | caractères à corriger pour passer du texte lu par l'OCR au texte retapé, divisé par le nombre de caractères retapés | **15 %** (seuil 2 %) | voir l'exemple ci-dessous |
| `n1_erreur_mots` | la même chose en mots | 20 % | — |

## Les causes probables d'un passage non rattaché

| Cause affichée par le kit | Ce qu'il faut faire |
| --- | --- |
| « aucun chunk sur la page 4 ; le passage est trouvé page 2 : page mal notée ? » | le **métier** corrige la page dans son fichier Excel |
| « aucun chunk sur la page… : page perdue à l'extraction » | l'équipe technique vérifie l'extraction de ce document |
| « tableau mal extrait : 60 % des mots retrouvés » | traitement dédié des tableaux |
| « OCR : ressemblance de 70 % au mieux » | meilleur OCR, ou modèle de vision sur les pages difficiles |
| « aucun chunk de type image sur la page » | décrire les images (modèle de vision) |
| « document absent de l'index » | l'ingestion a sauté ce document |

## Exemple : pourquoi l'OCR du RAG d'exemple est à 15 %

Comparer le texte retapé et le texte extrait d'une page (NT-031, page 2) montre trois causes :

- **Docling écarte l'en-tête et le pied de page** (« VALTÉRA INDUSTRIES — Archives techniques »).
- **Il colle des mots**, par exemple « TGBT-Aest » ou « Disjoncteurouvert ».
- **Il lit mal des chiffres**, par exemple « 1.600 A » au lieu de « 1 600 A ».

Sur une autre page (NT-040, page 3), il **mélange l'ordre des lignes**. Les passages restent retrouvés, car le rattachement tolère 10 % d'écart, mais une valeur mal lue peut fausser une réponse.

## Si c'est mauvais

Extraction, OCR, tableaux, images, découpage : le [document 2](../../rag/documentation/reference/techniques_rag.md), sections 3 et 4.

**Étape suivante** : [2. Évaluation de la recherche](2_evaluation_recherche.md).
