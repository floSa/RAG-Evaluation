# La documentation du service

Les guides se lisent dans l'ordre. Chacun dit ce qu'il faut faire, et, pour les évaluations, ce que le service vérifie et comment il calcule chaque score.

| Élément | À quoi il sert |
| --- | --- |
| [`../FIL_CONDUCTEUR.md`](../FIL_CONDUCTEUR.md) | **par où commencer** : le fil conducteur, qui explique ce qu'on fait et renvoie, dans l'ordre, vers chacun de ces guides |
| [`0a_construction_du_corpus.md`](0a_construction_du_corpus.md) | comment le métier annote le corpus, et comment l'importer |
| [`0b_endpoints_du_rag.md`](0b_endpoints_du_rag.md) | les quatre endpoints que votre RAG doit ouvrir |
| [`0c_configurations_du_rag.md`](0c_configurations_du_rag.md) | où fixer les réglages du RAG, et comment lancer l'évaluation |
| [`1_evaluation_ingestion.md`](1_evaluation_ingestion.md) | évaluation 1 : rien ne s'est-il perdu quand le RAG a rangé les documents dans sa base ? |
| [`2_evaluation_recherche.md`](2_evaluation_recherche.md) | évaluation 2 : la recherche ramène-t-elle les morceaux qui contiennent la réponse ? |
| [`3_evaluation_reponse.md`](3_evaluation_reponse.md) | évaluation 3 : la réponse est-elle juste, fondée sur les documents ? |
| [`4_evaluation_bout_en_bout.md`](4_evaluation_bout_en_bout.md) | évaluation 4 : le RAG est-il bon sur ce qui compte, assez rapide, pas trop cher ? Et les scores clés, que le métier lit pour décider |
| [`5_resultats_et_comparaison.md`](5_resultats_et_comparaison.md) | lire un rapport, comparer deux configurations |
| [`6_aide_a_la_decision.md`](6_aide_a_la_decision.md) | des repères pour lire chaque score, lire l'intervalle de confiance, et présenter les scores à ceux qui décident |
| [`cas_particuliers.md`](cas_particuliers.md) | pour aller plus loin : un RAG avec un graphe de connaissances, un RAG qui se repose des questions, des réponses qui se calculent sur des données |
| [`methode_et_contrat/`](methode_et_contrat/) | la méthode complète, le format des fichiers échangés, et le prompt du juge |
