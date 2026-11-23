# Le corpus documentaire du RAG

Ce que le RAG lit pour répondre à ses utilisateurs, en dehors de toute évaluation.

Ici, c'est un dossier de fichiers : on y met les documents et leur liste, `liste_des_documents.csv`, exportée de la gestion documentaire (séparateur `;`, colonnes `reference;titre;type_document;version;format;droits_acces;fichier`), puis on lance `uv run rag indexer`. Dans un autre projet, le contenu peut venir d'ailleurs : une GED, une base de données, une application. Il suffit alors de changer l'étape de lecture du RAG ([`etape_1_extraction.py`](../src/rag/pipeline/etape_1_extraction.py)).

**Vide dans cet exemple.** Le RAG d'exemple ne sert qu'à être évalué : il ne lit que les documents que le service d'évaluation lui envoie par son endpoint ① « ingérer ». Il les range à part, dans `sorties/evaluation/`, pour ne jamais les mélanger avec ce corpus.
