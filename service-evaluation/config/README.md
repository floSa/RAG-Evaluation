# Réglages du service

Les réglages du service d'évaluation, à régler une fois pour le projet. Aucune clé ici : les clés sont dans `.env`.

| Élément | À quoi il sert |
| --- | --- |
| [`kit.yaml`](kit.yaml) | le nom du projet ; l'adresse des endpoints du RAG à évaluer ; l'API des modèles et le modèle juge ; les chemins des dossiers du service |

**Le réglage `sans_reflexion` du juge.** Certains modèles raisonnent longuement avant de répondre (Qwen, par exemple). Avec un serveur installé en local, vLLM ou LiteLLM, on peut leur demander de ne pas le faire : le juge répond alors plusieurs fois plus vite. C'est ce que fait `sans_reflexion: true` : le service ajoute à chaque appel du juge un paramètre propre à ces serveurs, `chat_template_kwargs`. Les autres fournisseurs (OpenAI, Mistral…) ne connaissent pas ce paramètre et peuvent refuser l'appel : l'installation échoue alors dès la vérification des modèles. Par défaut, le réglage vaut donc `false`, et l'appel reste standard. Le mettre à `true` seulement avec vLLM ou LiteLLM et un modèle qui raisonne ; c'est le cas de l'exemple.

Il n'y a pas de seuil de mise en production à régler : le service donne les scores, et le métier décide à leur lecture. Ce que mesure chaque score : les guides [1. Évaluation de l'ingestion](../documentation/1_evaluation_ingestion.md) à [4. Évaluation de bout en bout](../documentation/4_evaluation_bout_en_bout.md).

Suite : remplir [`corpus_annote/`](../corpus_annote/).
