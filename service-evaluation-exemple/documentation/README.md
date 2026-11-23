# La documentation du service

Les guides se lisent dans l'ordre. Chacun dit ce qu'il faut faire, et, pour les évaluations, ce que le service vérifie et comment il calcule chaque score.

| Élément | À quoi il sert |
| --- | --- |
| [`integrer_votre_rag.md`](integrer_votre_rag.md) | **par où commencer** pour votre projet : les étapes, du corpus à la décision |
| [`0a_construction_du_corpus.md`](0a_construction_du_corpus.md) | comment le métier annote le corpus, et comment l'importer |
| [`0b_endpoints_du_rag.md`](0b_endpoints_du_rag.md) | les quatre endpoints que votre RAG doit ouvrir |
| [`1_evaluation_ingestion.md`](1_evaluation_ingestion.md) | évaluation 1 : rien ne s'est-il perdu quand le RAG a rangé les documents dans sa base ? |
| [`2_evaluation_recherche.md`](2_evaluation_recherche.md) | évaluation 2 : la recherche ramène-t-elle les morceaux qui contiennent la réponse ? |
| [`3_evaluation_reponse.md`](3_evaluation_reponse.md) | évaluation 3 : la réponse est-elle juste, fondée sur les documents ? |
| [`4_evaluation_bout_en_bout.md`](4_evaluation_bout_en_bout.md) | évaluation 4 : le RAG est-il bon sur ce qui compte, assez rapide, pas trop cher ? Et la décision |
| [`5_resultats_et_comparaison.md`](5_resultats_et_comparaison.md) | lire un rapport, comparer deux configurations |
| [`methode_et_contrat/`](methode_et_contrat/) | la méthode complète, le format des fichiers échangés, et le prompt du juge |
