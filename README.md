# Kit d'évaluation de RAG — méthode et consignes

Méthode d'évaluation de RAG (base vectorielle, graphe ou agent), en configuration minimale et recommandée, et consignes pour la mettre en œuvre dans un bac à sable avec Claude Code.

## Contenu

| Fichier | Pour qui | Contenu |
| --- | --- | --- |
| `docs/RAG_1_Constituer_le_corpus_d_evaluation.md` | métier et technique | construire le corpus d'évaluation : fichier Excel, annotation, rattachement au RAG |
| `docs/Corpus_evaluation_RAG.xlsx` | métier | le fichier à remplir, avec définitions et tableau de bord |
| `docs/RAG_2_Construire_le_pipeline.md` | technique | les techniques à mettre en place selon les cas, de l'extraction à la génération |
| `docs/RAG_3_Evaluer_le_RAG.md` | métier et technique | évaluer le RAG à chaque niveau : contrat, scores, outils, seuils, décision |
| `specs/CONTRAT.md` | technique | les fichiers échangés entre corpus, RAG et kit, champ par champ |
| `specs/JUGE.md` | technique | le prompt du LLM juge et sa vérification |
| `CLAUDE.md` | Claude Code | les consignes d'implémentation, étape par étape |
| `word/` | lecture | les mêmes documents au format Word |

## Démarrer le bac à sable

1. Prérequis sur la machine : Docker, Python 3.12 au minimum (3.13 conseillé), `uv`, Tesseract (OCR), un accès à un modèle de langage compatible OpenAI.
2. Créer un dépôt vide et y copier `CLAUDE.md`, `docs/` et `specs/`.
3. Ouvrir Claude Code dans ce dépôt et écrire : « Lis CLAUDE.md et commence l'étape 0. »
4. Valider chaque étape avant la suivante.
