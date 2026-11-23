# 0c. Les configurations du RAG : choisir les réglages, puis lancer l'évaluation

Ce guide détaille l'étape 3 du [fil conducteur](../../FIL_CONDUCTEUR.md#3-évaluer-une-configuration-du-rag) : choisir les configurations du RAG à évaluer, fixer leurs réglages dans le RAG, puis lancer l'évaluation.

## 1. Ce qu'est une configuration

Une configuration est un ensemble de réglages du RAG. On en évalue plusieurs, qui ne diffèrent que par un réglage, pour savoir lequel améliore le RAG. Les configurations à tester forment une grille : une ligne par configuration, une colonne par réglage qu'on fait varier.

## 2. Les réglages que tout RAG possède

Ce sont ceux à tester en premier.

| Réglage | Ce que c'est, et ce qu'il change |
| --- | --- |
| Nombre de morceaux ramenés (k) | le nombre de morceaux de texte que la recherche renvoie pour une question, et que le modèle lit pour répondre. Plus il y en a, plus le bon morceau a de chances d'y être, mais plus la réponse est lente et noyée dans des morceaux inutiles |
| Seuil de pertinence | la ressemblance minimale avec la question qu'un morceau doit avoir pour être ramené, même s'il fait partie des k premiers. Trop bas, le modèle lit des morceaux hors sujet ; trop haut, il ne lit plus rien et répond « je ne sais pas » |
| Taille des morceaux | la longueur des morceaux découpés dans les documents, en caractères ou en tokens (un token vaut environ 4 caractères), et leur chevauchement. Trop petits, ils coupent une réponse en deux ; trop grands, ils la noient dans le reste du texte |
| Modèle qui écrit la réponse | le modèle de langage qui rédige la réponse à partir des morceaux. Un modèle plus gros répond plus juste, mais plus lentement et plus cher |
| Consigne du modèle (prompt) | le texte qui dit au modèle comment répondre : s'en tenir aux morceaux, citer ses sources, dire « je ne sais pas ». Elle joue sur les inventions et sur les abstentions |

## 3. Les réglages pour aller plus loin

Seulement si le RAG les possède. Un RAG qui n'en a aucun n'a rien de plus à faire.

| Réglage | Ce que c'est, et ce qu'il change |
| --- | --- |
| Modèle de vectorisation (embedding) | le modèle qui transforme chaque morceau et chaque question en vecteur, pour que la recherche trouve les morceaux de même sens. Un modèle adapté à la langue et au vocabulaire du métier retrouve plus de bons passages. Le changer oblige à refaire l'ingestion |
| Recherche par mots-clés | une recherche classique, par les mots, ajoutée à la recherche par vecteurs. Elle retrouve les références et les codes, que les vecteurs saisissent mal |
| Reclassement (reranker) | l'ajout ou non d'un second modèle, et lequel, qui relit les morceaux ramenés et les reclasse, pour mettre le meilleur en tête. Plus juste, mais plus lent |
| Réflexion du modèle | le modèle raisonne avant de répondre. Des réponses plus justes, surtout pour les calculs, mais plus lentes |
| Graphe (GraphRAG) | l'ajout ou non d'une carte des liens entre les éléments des documents (équipements, sites, personnes), et le modèle qui l'extrait des documents. La recherche la consulte en plus des morceaux ; elle aide pour les questions qui croisent plusieurs documents |

## 4. Ce qui ne change pas d'une configuration à l'autre

Les réglages qu'on ne fait pas varier restent les mêmes. Le rapport les note quand même, pour qu'on sache toujours exactement ce qui a été évalué.

Le juge non plus ne change pas. Le juge, le modèle de langage qui note les réponses (en anglais, *LLM as a judge*), n'est pas un réglage du RAG : il appartient au service d'évaluation et se règle dans son [`config/kit.yaml`](../config/kit.yaml). S'il changeait, les scores des configurations ne se compareraient plus.

## 5. Où se remplissent les réglages

Dans le RAG, pas dans le service d'évaluation. Chaque RAG a sa façon de les fixer : un fichier de réglages, souvent au format YAML ou `.env`, des options données au lancement, ou les deux. C'est l'équipe qui a construit le RAG qui sait où ils sont.

Pour chaque configuration de la grille : fixer ses réglages dans le RAG, puis relancer le RAG pour qu'il les prenne en compte. Le RAG déclare ensuite sa configuration au service, par son endpoint ② ([guide 0b](0b_endpoints_du_rag.md)).

Dans le RAG d'exemple, les réglages sont dans son fichier [`config/config.yaml`](../../service-rag-exemple/config/config.yaml), et deux d'entre eux se changent aussi au lancement : [changer de configuration](../../service-rag-exemple/README.md#changer-de-configuration).

## 6. Lancer l'évaluation

Le service d'évaluation s'utilise dans un terminal, avec la commande `kit` installée à l'étape 0. Le RAG doit tourner, avec la configuration à évaluer. Ouvrir un terminal dans le dossier `service-evaluation/`, puis taper :

```bash
uv run kit evaluer
```

Cette seule commande fait tout le déroulé décrit dans le fil conducteur, à [« Comment ils se parlent »](../../FIL_CONDUCTEUR.md#comment-fonctionne-lévaluation) :
1. elle envoie les documents au RAG, qui les ingère ;
2. elle lit ses morceaux de texte et sa configuration ;
3. elle lui pose chaque question du fichier Excel ;
4. elle calcule les scores, et écrit le rapport, `RAPPORT.md`, dans un dossier à son nom sous `resultats/evaluations/`.

À la fin, elle affiche les scores clés et le chemin du rapport. Pour la configuration suivante : changer le réglage dans le RAG, le relancer, puis relancer la même commande. Le nouveau rapport s'écrit à côté du précédent.

Comment lire le rapport : [guide 5](5_resultats_et_comparaison.md).

Retour au [fil conducteur](../../FIL_CONDUCTEUR.md#3-évaluer-une-configuration-du-rag), étape 3.

**Étape suivante** : [1. Évaluation de l'ingestion](1_evaluation_ingestion.md).
