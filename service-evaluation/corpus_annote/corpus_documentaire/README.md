# Le corpus documentaire

Mettre ici ce que le RAG doit lire : documents, fiches, exports d'application… **Un fichier par référence**, nommé `<référence>.<extension>` (par exemple `PR-1101.pdf`), la référence étant celle de la feuille « Documents » du fichier Excel.

Le service envoie ces fichiers au RAG par son endpoint ① « ingérer ». Leur contenu n'est pas versionné : il peut être confidentiel.

Un corpus documentaire rempli, pour voir : [`service-evaluation-exemple/corpus_annote/corpus_documentaire/`](../../../service-evaluation-exemple/corpus_annote/corpus_documentaire/).
