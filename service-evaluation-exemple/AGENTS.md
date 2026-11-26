# Consignes pour un agent de code : évaluer un RAG avec ce service

Ce fichier s'adresse à un agent de code (Claude Code, Codex, Cursor…) à qui l'on demande d'évaluer un RAG avec ce dossier. Il dit quoi faire, dans l'ordre, et ce qu'il ne faut jamais faire. Le sens de chaque étape est dans [FIL_CONDUCTEUR.md](FIL_CONDUCTEUR.md) ; chaque commande a son aide : `uv run kit <commande> --help`.

Toutes les commandes se lancent depuis ce dossier, avec `uv run`.

## Ce que l'utilisateur doit vous donner

| Quoi | Où le mettre |
| --- | --- |
| les documents que le RAG doit savoir lire | `corpus_annote/corpus_documentaire/`, un fichier par document, nommé `<référence>.<extension>` (`PR-1101.pdf`) |
| les questions, leurs bonnes réponses et les passages qui les contiennent | `corpus_annote/Corpus_evaluation_RAG.xlsx`, rempli par le métier, **ou** un fichier JSON de même contenu (`corpus_annote/corpus.json`) |
| l'accès aux modèles du juge : une API compatible OpenAI | adresse et noms des modèles dans `config/kit.yaml` (`modeles`) ; clé dans `.env` (`KIT_LLM_CLE`) |
| le RAG à évaluer | voir « Brancher le RAG » ci-dessous |

S'il manque l'un d'eux, le demander : ne pas l'inventer.

## Les étapes

1. **Installer**, une seule fois :
   ```bash
   cp .env.example .env
   ```
   Remplir `.env` et `config/kit.yaml` avec ce que l'utilisateur a donné, puis vérifier que le juge et les embeddings répondent :
   ```bash
   uv run kit verifier-modeles
   ```
   Langfuse est facultatif : sans lui, ajouter `--sans-langfuse` aux commandes `importer` et `evaluer`.

2. **Importer le corpus** :
   ```bash
   uv run kit importer corpus_annote/Corpus_evaluation_RAG.xlsx
   ```
   ou `uv run kit importer corpus_annote/corpus.json`. Un refus donne chaque ligne fautive et la correction attendue : corriger le fichier (ou le faire corriger par le métier), puis relancer. Le format JSON : [documentation/0a_construction_du_corpus.md](documentation/0a_construction_du_corpus.md#sans-excel--un-fichier-json).

3. **Brancher le RAG**, d'une de ces trois façons :

   | Le RAG… | Ce qu'il faut | Ce qui est évalué |
   | --- | --- | --- |
   | peut ouvrir une adresse web | ses quatre endpoints, à partir de `endpoints_a_copier/endpoints_evaluation.py` ; leur adresse dans `config/kit.yaml` (`rag.adresse`) | tout : ingestion, recherche, réponse, bout en bout |
   | ne peut pas ouvrir d'adresse | qu'il écrive lui-même `rag.json`, `chunks.jsonl`, `recherches.jsonl`, `reponses.jsonl` dans un dossier | tout |
   | n'a qu'une API compatible OpenAI (un portail, un assistant tout fait) | la section `boite_noire` de `config/kit.yaml` ; sa clé dans `.env` (`BOITE_NOIRE_CLE`) | la réponse et le bout en bout seulement |

   Le détail : [documentation/0b_endpoints_du_rag.md](documentation/0b_endpoints_du_rag.md).

4. **Évaluer**, selon le branchement :
   ```bash
   uv run kit evaluer
   ```
   ```bash
   uv run kit evaluer --rag <dossier du RAG>
   ```
   ```bash
   uv run kit evaluer --boite-noire
   ```
   Avant de lancer, vérifier un dossier rendu par le RAG : `uv run kit verifier-contrat <dossier>`.

5. **Lire le résultat** : `resultats/evaluations/<version du corpus>_<version du RAG>/RAPPORT.md`. Donner à l'utilisateur les scores clés du rapport, chacun avec sa phrase et sa fourchette, l'état du juge, et les questions à regarder en premier. Ne pas conclure à sa place : c'est le métier qui décide.

6. **Comparer** deux configurations, ou deux RAG, évalués sur le même corpus :
   ```bash
   uv run kit comparer resultats/evaluations/<A> resultats/evaluations/<B>
   ```

Ajouter des données plus tard : mettre les nouveaux documents dans `corpus_annote/corpus_documentaire/`, ajouter les questions au fichier Excel ou JSON, réimporter (étape 2) : l'import crée une nouvelle version du corpus. Deux évaluations ne se comparent que sur la même version.

## Ce qu'il ne faut jamais faire

- **Montrer au RAG les annotations du métier** : bonnes réponses, points clés, passages. Le RAG ne reçoit que les documents et les questions ; le service s'en charge. Un RAG qui les verrait aurait des scores faux.
- **Modifier une bonne réponse, un point clé ou un passage pour faire monter un score.** Si une annotation paraît fausse, le signaler à l'utilisateur : c'est au métier de la corriger.
- **Régler le RAG sur les questions réservées** (`reservee_decision`) : elles servent aux scores clés, justement parce qu'on ne règle rien sur elles.
- **Modifier le code du service** (`src/`) ou le prompt du juge pour contourner une erreur : lire le message, il dit quoi corriger.
- **Versionner `.env`, les documents ou les résultats** : le fichier `.gitignore` les exclut ; ne pas le contourner.

## Vérifier le service lui-même

```bash
uv run pytest
```
