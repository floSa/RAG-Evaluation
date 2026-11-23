# Le code de la commande `kit`

Un dossier par étape, dans l'ordre où elles s'enchaînent.

| Élément | À quoi il sert |
| --- | --- |
| [`commandes.py`](commandes.py) | toutes les commandes `kit …` |
| [`config.py`](config.py) | lit les réglages de `config/` et les clés de `.env` |
| [`contrat.py`](contrat.py) | lit les fichiers échangés avec le RAG, et les vérifie contre le contrat |
| [`base.py`](base.py) | la base de données du service |
| [`etape_0a_corpus/`](etape_0a_corpus/) | importer et contrôler le fichier Excel du métier |
| [`appel_du_rag/`](appel_du_rag/) | appeler les quatre endpoints du RAG : le seul endroit qui parle à un RAG |
| [`etape_1_evaluation_ingestion/`](etape_1_evaluation_ingestion/) | évaluation 1 : retrouver les passages du métier dans la base du RAG ; contrôler son graphe |
| [`etape_2_evaluation_recherche/`](etape_2_evaluation_recherche/) | évaluation 2 : les scores de la recherche |
| [`etape_3_evaluation_reponse/`](etape_3_evaluation_reponse/) | évaluation 3 : le juge, les scores de la réponse, la relecture par le métier |
| [`etape_4_evaluation_bout_en_bout/`](etape_4_evaluation_bout_en_bout/) | évaluation 4 : score pondéré, temps, coût |
| [`etape_5_resultats/`](etape_5_resultats/) | écrire les résultats, les rapports, la décision, et comparer deux configurations |
