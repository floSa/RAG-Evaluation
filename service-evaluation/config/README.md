# Réglages du service

Les réglages du service d'évaluation, à régler une fois pour le projet. Aucune clé ici : les clés sont dans `.env`.

| Élément | À quoi il sert |
| --- | --- |
| [`kit.yaml`](kit.yaml) | le nom du projet ; l'adresse des endpoints du RAG à évaluer ; l'API des modèles et le modèle juge ; les chemins des dossiers du service |
| [`seuils.json`](seuils.json) | les seuils que le métier fixe **avant** l'évaluation, un par score, et les critères bloquants (fuite de droits, erreur grave). La décision se prend contre ces seuils |

Les seuils proposés ici sont un point de départ : ils se discutent et se fixent avec le métier. Ce que mesure chaque score : les guides [1](../documentation/1_evaluation_ingestion.md) à [4](../documentation/4_evaluation_bout_en_bout.md).

Suite : remplir [`corpus_annote/`](../corpus_annote/).
