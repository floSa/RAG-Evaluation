# La méthode : les documents de référence

Ces documents décrivent la méthode que le banc met en œuvre. Ils font foi et ne sont jamais modifiés. Quand ils laissent un choix ouvert, la décision prise est écrite dans [DECISIONS.md](../DECISIONS.md).

| Document | Pour qui | Ce qu'il fixe | Mis en œuvre dans |
| --- | --- | --- | --- |
| [RAG_1 — Constituer le corpus d'évaluation](RAG_1_Constituer_le_corpus_d_evaluation.md) | métier et technique | le fichier Excel, ses colonnes, les règles d'annotation, la configuration minimale | [`corpus/`](../corpus/README.md) |
| [Corpus_evaluation_RAG.xlsx](Corpus_evaluation_RAG.xlsx) | métier | le modèle vide du fichier à remplir, avec ses définitions et son tableau de bord | [`corpus/`](../corpus/README.md) |
| [RAG_2 — Construire le pipeline](RAG_2_Construire_le_pipeline.md) | technique | les techniques d'un RAG selon les cas, de l'extraction à la génération ; ce qu'il faut corriger quand un score est mauvais | [`rag/`](../rag/README.md), et les pistes du guide de lecture |
| [RAG_3 — Évaluer le RAG](RAG_3_Evaluer_le_RAG.md) | métier et technique | les quatre niveaux, chaque score, les outils, les seuils, la décision | [`evaluation/`](../evaluation/README.md) |
| [CONTRAT.md](../corpus/contrat/CONTRAT.md) | technique | les fichiers échangés entre le corpus, le RAG et le kit, champ par champ | [`corpus/contrat/`](../corpus/contrat/) |
| [JUGE.md](../evaluation/juge/JUGE.md) | technique | le prompt du LLM juge, sa sortie, sa vérification | [`evaluation/juge/`](../evaluation/juge/) |

Ordre de lecture conseillé : le document 3, sections 1 à 5 (le principe et les niveaux), puis le document 1 (le corpus), puis le contrat. Le document 2 sert quand un score est mauvais.
