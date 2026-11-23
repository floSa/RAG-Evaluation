# Sorties du kit

Le kit écrit ici tout ce qu'il produit. Le dossier est **vide dans le dépôt** : il se remplit chez vous, et son contenu n'est pas versionné.

| Dossier | Ce que le kit y écrit | Commande |
| --- | --- | --- |
| `corpus/<version>/` | le corpus importé et contrôlé : questions, passages, documents | `kit importer` |
| `sorties_rag/<version du RAG>/` | ce que le RAG a rendu par ses quatre portes : index, recherches, réponses | `kit appeler-rag` (ou `kit evaluer`) |
| `resultats/<corpus>_<version du RAG>/` | les résultats d'une évaluation, dont `rapport.html` | `kit evaluer` |
| `base.sqlite` | la base : tout, y compris le détail des questions réservées | `kit init-base`, puis chaque commande |

Pour voir des résultats sans rien lancer : [`resultats_exemple/`](../resultats_exemple/).
