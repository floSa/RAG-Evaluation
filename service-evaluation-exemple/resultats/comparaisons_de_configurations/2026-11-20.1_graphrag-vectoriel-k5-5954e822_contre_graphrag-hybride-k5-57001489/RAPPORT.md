# Comparaison de deux configurations

Ce rapport compare deux configurations du RAG, évaluées sur le même corpus, avec les mêmes questions. Il répond à une question : **la configuration B fait-elle mieux que la configuration A ?** Il ne dit pas si l'une ou l'autre peut partir en production : c'est le rapport d'évaluation de chacune qui le dit.

|  | A | B |
| --- | --- | --- |
| Configuration | `graphrag-vectoriel-k5-5954e822` | `graphrag-hybride-k5-57001489` |
| Réglages | RAG vectoriel, k = 5, découpage sections-1, embeddings embed, génération gemma-4-e4b, prompt 1.0, reranker aucun, réflexion du modèle oui, recherche par mots-clés oui, graphe non, candidats avant fusion 30 | RAG hybride, k = 5, découpage sections-1, embeddings embed, génération gemma-4-e4b, prompt 1.0, reranker aucun, réflexion du modèle oui, recherche par mots-clés oui, graphe oui, candidats avant fusion 30 |

**Ce qui change de A à B** : type : vectoriel → hybride; graphe : non → oui.

## 1. Les scores

Sur les questions de réglage. Un écart plus petit que la marge d'erreur ne prouve rien à lui seul.

| Score | A | B | Écart de A à B | L'écart est-il réel ? |
| --- | --- | --- | --- | --- |
| Passages du métier retrouvés | 100 % | 100 % | aucun | — |
| Erreur de lecture des scans (caractères) | 15 % | 15 % | aucun | — |
| Bon passage ramené | 86 % | 82 % | −4 points | non prouvé : dans la marge |
| Passages nécessaires ramenés | 81 % | 81 % | aucun | — |
| Fuites de droits | 0 | 0 | aucun | — |
| Réponses justes | 79 % | 90 % | +11 points | non prouvé : dans la marge |
| Chiffres exacts | 91 % | 91 % | aucun | — |
| Fidélité aux documents | 95 % | 95 % | −1 points | non prouvé : dans la marge |
| Sait dire « je ne sais pas » | 100 % | 100 % | aucun | — |
| Erreurs graves | 1 | 0 | −1 | — |
| Synthèses | 65 % | 73 % | +8 points | — |
| Score pondéré | 80 % | 82 % | +2 points | non prouvé : dans la marge |
| Temps de réponse médian | 7,4 s | 7,4 s | −0,0 s | — |
| Coût par question | 0,00 € | 0,00 € | aucun | — |

## 2. Question par question

Une moyenne peut cacher des mouvements : on regarde les questions que B gagne et celles qu'il perd par rapport à A. Le test de McNemar dit si ces mouvements peuvent venir du hasard : au-dessus de 0,05, on ne peut pas l'exclure.

| Score | Questions gagnées par B | Questions perdues par B | Sur | Peut venir du hasard ? |
| --- | --- | --- | --- | --- |
| Bon passage ramené | aucune | Q-031 | 28 | oui (p = 1,00) |
| Réponses justes | Q-012, Q-043 | aucune | 25 | oui (p = 0,50) |
| Score pondéré | Q-012, Q-043 | Q-031 | 40 | oui (p = 1,00) |

## 3. En résumé

Sur le score pondéré, B gagne 2 point(s) par rapport à A : 2 question(s) gagnée(s), 1 perdue(s). Cet écart peut venir du hasard : aucune des deux configurations n'est démontrée meilleure.

Le détail de tous les scores est dans `fichiers_techniques/comparaison.json`.
