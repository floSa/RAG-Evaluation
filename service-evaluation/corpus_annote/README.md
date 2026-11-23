# Le corpus annoté

Ce que le service fait lire au RAG, et ce que le métier en attend. C'est l'entrée du service : **à remplir** pour votre projet.

| Élément | À quoi il sert |
| --- | --- |
| [`corpus_documentaire/`](corpus_documentaire/) | ce que le RAG doit lire : documents, fiches, exports d'application… Un fichier par référence, nommé `<référence>.<extension>` |
| [`Corpus_evaluation_RAG.xlsx`](Corpus_evaluation_RAG.xlsx) | le fichier du métier, vierge, avec ses définitions et ses listes : la liste des documents, les questions, leur bonne réponse, les passages qui la contiennent, des pages scannées retapées |
| [`ontologie/`](ontologie/) | facultatif : l'ontologie du domaine, seulement si votre RAG construit un graphe |

Comment le métier remplit le fichier : [0a. Construction du corpus](../documentation/0a_construction_du_corpus.md). Un corpus rempli, pour voir : [`service-evaluation-exemple/corpus_annote/`](../../service-evaluation-exemple/corpus_annote/).

Suite : importer le corpus (`uv run kit importer corpus_annote/Corpus_evaluation_RAG.xlsx`), puis brancher le RAG avec [`endpoints_a_copier/`](../endpoints_a_copier/).
