# 0c. Les configurations du RAG : fixer les réglages, puis lancer l'évaluation

Ce guide donne le côté pratique de l'étape 3 du [fil conducteur](../FIL_CONDUCTEUR.md#3-évaluer-une-configuration-du-rag) : où fixer les réglages du RAG, et comment lancer l'évaluation. Ce qu'est une configuration, et quels réglages évaluer, sont expliqués dans le fil conducteur.

## 1. Où se remplissent les réglages

Dans le RAG, pas dans le service d'évaluation. Chaque RAG a sa façon de les fixer : un fichier de réglages, souvent au format YAML ou `.env`, des options données au lancement, ou les deux. C'est l'équipe qui a construit le RAG qui sait où ils sont.

Pour chaque configuration de la grille : fixer ses réglages dans le RAG, puis relancer le RAG pour qu'il les prenne en compte. Le RAG déclare ensuite sa configuration au service, par son endpoint ② ([0b. Les endpoints du RAG : ce que chaque RAG doit fournir](0b_endpoints_du_rag.md)).

Dans le RAG d'exemple, les réglages sont dans son fichier [`config/config.yaml`](../../service-rag-exemple/config/config.yaml), et deux d'entre eux se changent aussi au lancement : [changer de configuration](../../service-rag-exemple/README.md#changer-de-configuration).

## 2. Lancer l'évaluation

Le service d'évaluation s'utilise dans un terminal, avec la commande `kit` installée à l'étape 0. Le RAG doit tourner, avec la configuration à évaluer. Ouvrir un terminal dans le dossier `service-evaluation/`, puis taper :

```bash
uv run kit evaluer
```

Cette seule commande fait tout le déroulé décrit dans le fil conducteur, à [« Comment ils se parlent »](../FIL_CONDUCTEUR.md#comment-fonctionne-lévaluation) :
1. elle envoie les documents au RAG, qui les ingère ;
2. elle lit ses morceaux de texte et sa configuration ;
3. elle lui pose chaque question du fichier Excel ;
4. elle calcule les scores, et écrit le rapport, `RAPPORT.md`, dans un dossier à son nom sous `resultats/evaluations/`.

À la fin, elle affiche les scores clés et le chemin du rapport. Pour la configuration suivante : changer le réglage dans le RAG, le relancer, puis relancer la même commande. Le nouveau rapport s'écrit à côté du précédent.

Comment lire le rapport : [5. Résultats et comparaison](5_resultats_et_comparaison.md).

Retour au [fil conducteur](../FIL_CONDUCTEUR.md#3-évaluer-une-configuration-du-rag), étape 3.

**Étape suivante** : [1. Évaluation de l'ingestion](1_evaluation_ingestion.md).
