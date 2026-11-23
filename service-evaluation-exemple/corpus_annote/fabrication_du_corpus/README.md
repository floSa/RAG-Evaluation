# La fabrication du corpus

De quoi refabriquer le corpus fictif. Rarement utile : seulement pour modifier le corpus d'exemple.

| Élément | À quoi il sert |
| --- | --- |
| [`monde.md`](monde.md) | l'entreprise fictive : ses sites, ses équipements, ses personnes |
| [`contenus/`](contenus/) | le contenu de chacun des 50 documents |
| [`format_contenus.md`](format_contenus.md) | le format de ces contenus |
| [`fabriquer_pdf.py`](fabriquer_pdf.py) | dessine les 50 PDF dans `corpus_documentaire/` |
| [`questions.yaml`](questions.yaml) | les 60 questions, leurs réponses et leurs passages |
| [`remplir_excel.py`](remplir_excel.py) | vérifie chaque passage contre son document, et remplit le fichier Excel |
| [`polices/`](polices/) | les polices utilisées dans les PDF |

Les commandes : [0a. Construction du corpus](../../../service-evaluation/documentation/0a_construction_du_corpus.md#2-le-corpus-dexemple-prêt-à-lemploi).
