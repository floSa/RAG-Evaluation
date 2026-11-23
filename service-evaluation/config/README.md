# Réglages du service

Les réglages du service d'évaluation, à régler une fois pour le projet. Aucune clé ici : les clés sont dans `.env`.

| Élément | À quoi il sert |
| --- | --- |
| [`kit.yaml`](kit.yaml) | le nom du projet ; l'adresse des endpoints du RAG à évaluer ; l'API des modèles et le modèle juge ; les chemins des dossiers du service |

Il n'y a pas de seuil de mise en production à régler : le service donne les scores, et le métier décide à leur lecture. Ce que mesure chaque score : les guides [1](../documentation/1_evaluation_ingestion.md) à [4](../documentation/4_evaluation_bout_en_bout.md).

Suite : remplir [`corpus_annote/`](../corpus_annote/).
