# Résultats de l'évaluation d'exemple

**Ce qu'on a évalué** : le RAG d'exemple ([`service-rag/`](../../service-rag/)), sur le corpus d'exemple : 50 documents fictifs de maintenance électrique, et 60 questions écrites par le métier, avec leur bonne réponse. 40 questions servent à régler le RAG ; 20 sont **réservées à la décision**, jamais montrées pendant les réglages.

On a testé **quatre versions** du RAG. Ce fichier donne leurs résultats et la façon de les lire.

## En bref

| Version du RAG | Ce qui change | Bon passage retrouvé | Réponses justes | Erreurs graves | Score pondéré | Décision |
| --- | --- | --- | --- | --- | --- | --- |
| **Référence** | RAG vectoriel, 5 passages par question (k = 5) | 86 % | 79 % | **1** | 80 % | non recommandée |
| k = 3 | 3 passages au lieu de 5 | 75 % | 83 % | 0 | 77 % | non recommandée |
| Hybride | un graphe ajouté aux passages | 82 % | 90 % | 0 | 82 % | non recommandée |
| Sans réflexion | le modèle répond sans « réfléchir » d'abord | 86 % | 71 % | 0 | 77 % | non recommandée |

Scores sur les 40 questions de réglage. **Score pondéré** : la part de réponses justes, où les questions fréquentes et graves comptent plus. C'est le score le plus proche de ce que vivront les utilisateurs.

**À retenir** : aucune version n'est prête pour la production. Les quatre butent sur les mêmes points : le texte des documents scannés est mal lu, et la recherche ne ramène pas assez souvent le bon passage. Les écarts entre versions sont faibles, souvent plus petits que la marge d'erreur.

## 1. La version de référence : la décision

**Mise en production non recommandée**, pour deux raisons :

1. **Un critère bloquant** : 1 erreur grave (question Q-046, voir la partie 3). Une seule suffit à refuser, quel que soit le score.
2. **Quatre seuils non atteints** sur les 20 questions réservées :

| Score | Ce qu'il mesure | Résultat | Seuil du métier | Atteint ? |
| --- | --- | --- | --- | --- |
| Documents indexés | les documents que le RAG a bien rangés | 100 % | 100 % | oui |
| Passages retrouvés dans l'index | les passages du métier présents dans ce que le RAG a lu | 100 % | 95 % | oui |
| **Erreur de lecture des scans** | caractères mal lus sur les pages scannées | **15 %** | 2 % au plus | **non** |
| **Bon passage retrouvé** | la recherche ramène le passage qui contient la réponse | **69 %** | 90 % | **non** |
| Fuites de droits | un utilisateur voit un document qui lui est interdit | 0 | 0 | oui |
| **Réponses justes** | notées par un modèle juge, contre la bonne réponse du métier | **77 %** | 80 % | **non** |
| Abstentions correctes | le RAG dit « je ne sais pas » quand la réponse n'existe pas | 100 % | 80 % | oui |
| Fidélité aux sources | la réponse dit ce que disent les documents, sans inventer | 98 % | 90 % | oui |
| **Score pondéré** | réponses justes, pondérées par fréquence et gravité | **76 %** | 80 % | **non** |
| Temps de réponse (médian) | | 8,0 s | 15 s au plus | oui |
| Coût par question | | 0 € (modèles locaux) | 0,05 € au plus | oui |

Les seuils ont été fixés par le métier avant l'évaluation, dans [`config/seuils.json`](../config/seuils.json).

## 2. Où le RAG perd des points, étape par étape

On lit les étapes dans l'ordre : une réponse fausse vient souvent d'un passage mal lu ou mal retrouvé avant.

| Étape | Ce qui va | Ce qui ne va pas |
| --- | --- | --- |
| **1. Ingestion** : le RAG lit et range les documents | tous les documents sont rangés ; tous les passages du métier s'y retrouvent | les pages scannées sont mal lues : 15 % de caractères faux |
| **2. Recherche** : il retrouve les bons passages | aucune fuite de droits | le bon passage est retrouvé pour 86 % des questions ; il n'arrive en premier que pour 54 % |
| **3. Réponse** : il répond à partir de ces passages | fidèle aux documents (95 %) ; il s'abstient quand il le faut (100 %) | 79 % de réponses justes ; 1 erreur grave ; les synthèses sont faibles (65 %) |
| **4. Bout en bout** : ce que vit l'utilisateur | 7,4 s par réponse en médiane ; coût nul | score pondéré de 80 %, tout juste au seuil ; les comptes rendus d'intervention sont mal traités (9 %) |

## 3. Les questions à regarder en premier

| Question | Ce qui ne va pas |
| --- | --- |
| **Q-046** : « Quelles règles de sécurité retrouve-t-on dans toutes les interventions électriques ? » | **erreur grave** : aucune des règles attendues (habilitation, consignation, vérification d'absence de tension…) n'est citée |
| Q-030 : « Quelles interventions a-t-on faites sur l'armoire AD-A07 ? » | il ne décrit pas ce qui a été fait (séparation en deux circuits), et se trompe sur une autre intervention : « aucune suite » au lieu d'un remplacement du différentiel |
| Q-041 : « Quels problèmes électriques reviennent le plus souvent ? » | il ne cite aucun des cinq problèmes attendus (échauffements, défauts d'isolement, déclenchements de différentiels…) |
| Q-043 : « Quels enseignements tirer des campagnes de thermographie depuis 2023 ? » | une date fausse : 2025 au lieu de 2023 |

Trois de ces quatre questions sont des **synthèses** : il faut rassembler des informations de plusieurs documents. C'est le point faible de ce RAG.

## 4. La faute est-elle dans la recherche ou dans la réponse ?

Pour les 32 questions qui ont une réponse dans les documents :

| Diagnostic | Questions | Que corriger |
| --- | --- | --- |
| tout va bien | 20 | — |
| le bon passage était retrouvé, mais la réponse est fausse | 6 | la génération : le prompt, le modèle |
| le bon passage était retrouvé, mais le RAG s'est abstenu | 2 | la génération |
| le bon passage n'a pas été retrouvé | 4 | la lecture des documents, le découpage, la recherche |

## 5. Les comparaisons : une version est-elle meilleure ?

| Comparaison | Ce qu'on a vu | Conclusion |
| --- | --- | --- |
| **k = 3** au lieu de 5 | il retrouve moins (75 % au lieu de 86 %) ; il n'a plus d'erreur grave, mais seulement parce qu'il se tait sur Q-046 | **pas meilleur** |
| **Hybride** (avec un graphe) | 2 questions gagnées, 1 perdue ; aucun écart plus grand que la marge d'erreur | **rien de mesurable** sur ce corpus : il a peu de questions qui demandent de suivre des liens |
| **Sans réflexion** | 9 fois plus rapide (0,9 s au lieu de 7,4 s), mais les calculs deviennent faux (valeurs justes : 75 % au lieu de 91 %) | **on garde la réflexion** : les 7 s restent sous le seuil de 15 s |

Le détail de chaque comparaison : [guide 5](../documentation/5_resultats_et_comparaison.md#5-comparer-deux-versions).

## Comment ces résultats ont été produits

Chaque version a été évaluée avec une commande, puis comparée à la référence :

```bash
uv run kit evaluer
```

```bash
uv run kit comparer <dossier de la référence> <dossier de l'autre version>
```

Les fichiers produits par le kit sont dans [`donnees/`](donnees/), un dossier par version. Ce rapport en est tiré. Vous n'en avez besoin que pour creuser :

| Fichier | Contenu |
| --- | --- |
| `rapport.html` | ce même rapport, en page web, avec tous les scores (à télécharger et ouvrir dans un navigateur) |
| `resultats_par_question.csv` | une ligne par question et par score, avec la justification du juge : à ouvrir dans un tableur |
| `scores.json` | tous les scores, avec leur marge d'erreur et leur détail |
| les autres `.json` et `.jsonl` | le détail technique : liens entre passages et index, diagnostics, comparaisons |

Le rôle de chaque fichier : [guide 5](../documentation/5_resultats_et_comparaison.md#1-où-sont-les-résultats). Vos propres évaluations s'écrivent dans [`sorties/resultats/`](../sorties/).
