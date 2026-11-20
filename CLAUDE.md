# Consignes pour Claude Code : bac à sable d'évaluation de RAG

## Ta mission

Construire, étape par étape, un dépôt qui met en œuvre la méthode d'évaluation de RAG décrite dans `docs/`. Le dépôt contient deux parties strictement séparées :

| Partie | Dossier | Rôle |
| --- | --- | --- |
| Le kit d'évaluation | `kit/` | standard, réutilisable par tout projet : il lit le corpus et les sorties d'un RAG, et rend les scores des quatre niveaux |
| Le RAG de démonstration | `rag_demo/` | très simple ; il ne sert qu'à montrer comment un RAG se branche sur le kit |

Et un corpus d'exemple, annoté selon les règles du document 1, dans `corpus_exemple/`.

On s'arrête à la **configuration minimale** des documents 1 et 3. Le code doit permettre d'ajouter ensuite la configuration recommandée sans tout reprendre.

## Les documents de référence (ils font foi)

| Fichier | Ce qu'il fixe |
| --- | --- |
| `docs/RAG_1_Constituer_le_corpus_d_evaluation.md` | le corpus : fichier Excel, colonnes, règles d'annotation, rattachement |
| `docs/RAG_2_Construire_le_pipeline.md` | les techniques de RAG ; utile pour le RAG de démonstration |
| `docs/RAG_3_Evaluer_le_RAG.md` | l'évaluation : les quatre niveaux, chaque score, les outils, les seuils |
| `specs/CONTRAT.md` | les fichiers échangés, champ par champ, et les identifiants des scores |
| `specs/JUGE.md` | le prompt du LLM juge, sa sortie, sa vérification |
| `docs/Corpus_evaluation_RAG.xlsx` | le modèle de fichier Excel du métier |

Avant chaque étape, relis les sections qui la concernent. **Tu ne modifies jamais ces documents.** Si une règle est ambiguë, contradictoire ou impossible à coder, tu t'arrêtes et tu poses la question, avec ta proposition.

## Règles de travail

1. **Une étape à la fois.** Au début d'une étape : annonce en quelques lignes ce que tu vas faire. À la fin : résume ce qui est fait, donne les commandes pour le vérifier, et **attends la validation** avant de passer à la suivante.
2. **Séparation stricte.** `rag_demo/` n'importe rien de `kit/`, et `kit/` n'importe rien de `rag_demo/`. Ils ne se parlent que par les fichiers du contrat ou par le connecteur (méthodes nommées dans `specs/CONTRAT.md`).
3. **Le contrat d'abord.** Les noms de fichiers, de champs, de codes et de scores sont ceux de `specs/CONTRAT.md`, sans exception.
4. **Tests.** Chaque module a ses tests (`pytest`), dont au moins un cas réel tiré du corpus d'exemple.
5. **Simplicité.** Pas d'abstraction inutile ; du code lisible, commenté en français ; une commande par action.
6. **Secrets.** Aucune clé dans le code : un fichier `.env` (non versionné) et un `.env.example`.
7. **Modèles de langage.** Le juge, la génération et les embeddings passent par une configuration unique (`config/kit.yaml` pour le kit, `rag_demo/config.yaml` pour le RAG) : point d'accès compatible OpenAI, nom du modèle. On doit pouvoir changer de fournisseur sans toucher au code.
8. **Licences.** Uniquement des bibliothèques sous licence permissive (MIT, Apache 2.0, BSD). Pas de bibliothèque sous AGPL ou GPL : par exemple, `pypdf` ou `pdfplumber` plutôt que PyMuPDF.

## Choix techniques

| Sujet | Choix |
| --- | --- |
| Langage | Python 3.12 au minimum (3.13 conseillé) ; gestion des dépendances avec `uv` |
| Interface | une ligne de commande par partie : `kit …` et `rag-demo …` |
| Base relationnelle | SQLite pour le bac à sable, via SQLAlchemy (passage à PostgreSQL sans changer le code) ; tables du document 1, section 5 |
| Suivi | Langfuse auto-hébergé, lancé par `docker compose` (`infra/`) |
| Scores de réponse | Ragas (`Faithfulness`, `RubricsScore`) ; juge du kit selon `specs/JUGE.md` |
| Rattachement | `rapidfuzz` |
| OCR | `jiwer` pour le taux d'erreur ; `pytesseract` (Tesseract) dans le RAG de démonstration |
| Graphe | `rdflib`, `pyshacl` |
| Excel | `openpyxl` |

## L'arborescence attendue

| Dossier | Contenu |
| --- | --- |
| `docs/` | les documents de référence |
| `specs/` | CONTRAT.md, JUGE.md, et les schémas JSON du contrat (créés à l'étape 3) |
| `config/` | `kit.yaml`, `seuils.json` |
| `infra/` | `docker-compose.yml` de Langfuse, `.env.example` |
| `corpus_exemple/` | `sources/` (les documents), `Corpus_evaluation_RAG.xlsx` rempli, `ontologie/` |
| `kit/` | le kit : `import_corpus`, `contrat`, `lanceur`, `niveau1`, `niveau2`, `niveau3`, `niveau4`, `juge`, `publication`, `rapport` |
| `rag_demo/` | le RAG vectoriel simple, puis la variante graphe, et leur connecteur |
| `tests/` | les tests du kit et du RAG |
| `sorties/` | corpus exporté, sorties du RAG, résultats (non versionné) |

## Les étapes

### Étape 0 — Lire et cadrer

- Lis tous les documents de référence.
- Propose l'arborescence détaillée, la liste des commandes, et les questions qui restent ouvertes.
- **Validation attendue** avant d'écrire du code.

### Étape 1 — Socle

- Dépôt, dépendances, `.env.example`, `config/kit.yaml`, `config/seuils.json` (seuils du document 3, section 9).
- `infra/docker-compose.yml` : Langfuse qui démarre en local.
- `kit init-base` : crée les tables de la base relationnelle (document 1, section 5).
- **Fini quand** : Langfuse répond, la base est créée, `pytest` passe.

### Étape 2 — Corpus d'exemple

Fabrique un petit corpus **fictif** (aucune donnée réelle), en français, sur un thème industriel (maintenance électrique d'une entreprise fictive). Il doit couvrir tous les cas du document 1, à échelle réduite :

| Cas à couvrir | Minimum |
| --- | --- |
| Types de documents | 3 (procédure, compte rendu d'intervention, note technique), 4 documents par type |
| Formats | PDF natif, un PDF scanné (pages rendues en image, avec un peu de bruit), une fiche de base de données (JSON exporté en PDF « champ : valeur ») |
| Éléments | du texte, au moins 2 tableaux, au moins 1 schéma avec une figure numérotée |
| Droits | 2 documents réservés au profil « Maintenance » |
| Versions | un document remplacé par une version plus récente |
| Questions | 30 : tous les types de réponse (dont 3 synthèses), 4 sans réponse, 4 à plusieurs passages, 3 avec le profil restreint dont 2 « non accessible », 2 questions de suite, 2 variantes, 2 passages pièges ; des fréquences et gravités variées ; 1 question sur 3 réservée à la décision |
| Pages OCR | 3 pages du PDF scanné, retapées |

- Remplis le fichier Excel du document 1 (`docs/Corpus_evaluation_RAG.xlsx`, copié dans `corpus_exemple/`), en respectant exactement ses règles : passages copiés-collés, schéma décrit, etc.
- **Fini quand** : le tableau de bord du fichier est rempli et chaque cas du tableau ci-dessus est présent. Présente-moi la liste des questions pour relecture.

### Étape 3 — Import et contrat

- `kit importer <fichier.xlsx>` : contrôles de `specs/CONTRAT.md` (section 2), rejets avec messages clairs, écriture dans la base, export de `corpus/<version>/`, création du jeu de questions dans Langfuse.
- Schémas JSON de tous les fichiers du contrat dans `specs/schemas/`.
- `kit verifier-contrat <dossier>` : valide les fichiers d'un RAG contre ces schémas et dit précisément ce qui manque.
- **Fini quand** : le corpus d'exemple s'importe sans erreur ; un fichier volontairement faux est rejeté avec le bon message.

### Étape 4 — RAG de démonstration (vectoriel)

Dans `rag_demo/`, sans rien importer du kit :

- extraction : texte des PDF natifs, OCR des pages scannées, tableaux en « colonne : valeur », description des images par un modèle de vision (ou texte de légende si aucun modèle n'est disponible) ;
- découpage par section, avec le chemin de titres et toutes les métadonnées du contrat (référence, version, page, type d'élément, droits, ordre) ;
- recherche hybride (embeddings et BM25), filtre des droits pendant la recherche, k configurable ;
- génération avec citations obligatoires et abstention si le contexte ne suffit pas ; champ `abstention` renseigné ;
- traces envoyées à Langfuse ;
- `rag-demo exporter` (chunks, pages extraites, rag.json) et `rag-demo repondre <questions.jsonl>` (recherches et réponses) ; plus le connecteur Python.
- **Fini quand** : `kit verifier-contrat` valide les sorties du RAG.

### Étape 5 — Niveau 1 : ingestion

- `kit niveau1` : rattachement selon les règles du document 3 (section 6), `liens_index`, tous les scores minimaux du niveau 1, et la liste des passages non rattachés avec leur cause probable.
- **Fini quand** : les scores sont écrits dans la base, dans `resultats/` et dans Langfuse ; un passage volontairement mal noté (mauvaise page) est bien signalé.

### Étape 6 — Niveau 2 : recherche

- `kit niveau2` : règles de réussite selon « La réponse est dans », tous les scores minimaux du niveau 2, fuite de droits.
- **Fini quand** : chaque score est vérifié à la main sur 3 questions du corpus, et documenté dans un test.

### Étape 7 — Niveau 3 : réponse

- Juge selon `specs/JUGE.md`, Ragas pour la fidélité et la synthèse, script pour l'abstention, les citations et les valeurs.
- File de relecture `relecture-reponses` dans Langfuse ; vérification du juge (`kit verifier-juge`) avec la file `verification-juge`.
- Croisement recherche × réponse (document 3, section 8).
- **Fini quand** : tous les scores minimaux du niveau 3 sont produits ; le taux d'accord du juge est calculé à partir de notes saisies dans Langfuse.

### Étape 8 — Niveau 4, décision et rapport

- `kit niveau4` : score pondéré, erreurs graves, temps, coût, marges d'erreur.
- Décision par rapport à `config/seuils.json`, critères bloquants, questions réservées affichées seulement en scores globaux.
- `kit evaluer` : enchaîne les niveaux 1 à 4.
- `kit comparer <evaluation_a> <evaluation_b>` : écarts de scores et questions gagnées ou perdues.
- `rapport.html` : une page lisible par le métier.
- **Fini quand** : `kit evaluer` produit tout en une commande ; deux évaluations du RAG avec deux réglages différents (par exemple k = 3 et k = 5) se comparent.

### Étape 9 — Variante graphe

- Dans `rag_demo/` : une petite ontologie (`corpus_exemple/ontologie/`, avec ses règles SHACL), un graphe extrait des documents par un LLM contraint par l'ontologie, chaque nœud et relation avec sa provenance, une recherche qui combine le graphe et les chunks ; `type_rag` = `hybride`.
- Dans le kit : scores graphe du niveau 1 (violations SHACL ; file `justesse-graphe`) et score de synthèse du niveau 3.
- **Fini quand** : le même kit évalue les deux RAG sans changement de code, et `kit comparer` les compare.

### Étape 10 — Mode d'emploi

- `README.md` : brancher un nouveau RAG sur le kit en partant de zéro (fichiers à produire, commandes, lecture du rapport), avec le RAG de démonstration comme exemple.
- **Fini quand** : je refais l'évaluation complète en suivant uniquement le README.

## À la fin de chaque étape, ton message contient

1. Ce qui a été fait, en quelques lignes.
2. Les commandes pour le vérifier.
3. Les écarts éventuels avec les documents de référence, et pourquoi.
4. La question : « Je passe à l'étape suivante ? »
