# Les documents de méthode, en Word

Les mêmes documents que dans le dépôt, en Word, pour les lire ou les transmettre hors de GitHub. Ce sont des copies : les fichiers Markdown du dépôt font foi.

| Fichier Word | Document |
| --- | --- |
| [`RAG_1_Constituer_le_corpus_d_evaluation.docx`](RAG_1_Constituer_le_corpus_d_evaluation.docx) | [Constituer le corpus d'évaluation d'un RAG](../service-evaluation/documentation/methode_et_contrat/methode_corpus_annote.md) |
| [`RAG_2_Construire_le_pipeline.docx`](RAG_2_Construire_le_pipeline.docx) | [Construire le pipeline d'un RAG : ce qu'on met en place selon les cas](../service-rag-exemple/documentation/reference/techniques_rag.md) |
| [`RAG_3_Evaluer_le_RAG.docx`](RAG_3_Evaluer_le_RAG.docx) | [Évaluer le RAG avec le corpus](../service-evaluation/documentation/methode_et_contrat/methode_evaluation.md) |
| [`CONTRAT.docx`](CONTRAT.docx) | [Contrat entre un RAG et le kit d'évaluation](../service-evaluation/documentation/methode_et_contrat/contrat_des_fichiers.md) |
| [`JUGE.docx`](JUGE.docx) | [Le LLM juge du kit](../service-evaluation/documentation/methode_et_contrat/prompt_du_juge.md) |

Après chaque modification d'un de ces documents, refaire les fichiers Word, depuis la racine du dépôt :

```bash
./documents_word/generer.sh
```

Les schémas en Mermaid ne sont pas dessinés dans Word : ils y restent sous forme de texte. Ces cinq documents n'en ont pas.
