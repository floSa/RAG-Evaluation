# Les documents de production du RAG

Ici, les documents que le RAG sert en production, et leur liste exportée de la gestion documentaire :
`liste_des_documents.csv` (séparateur `;`, colonnes `reference;titre;type_document;version;format;droits_acces;fichier`).
Puis `uv run rag indexer`.

**Vide dans le banc d'essai.** Le RAG d'exemple n'a pas de documents à lui : il indexe ceux que le service
d'évaluation lui envoie par son endpoint « ingérer », rangés à part, dans `sorties/evaluation/`.
