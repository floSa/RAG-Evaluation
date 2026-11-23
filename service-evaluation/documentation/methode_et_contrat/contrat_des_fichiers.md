# Contrat entre un RAG et le kit d'évaluation — version 1.0

Ce document fixe les fichiers échangés entre le corpus, le RAG évalué et le kit d'évaluation. Il complète les documents 1 et 3. Il fait foi pour le code : un champ absent de ce document n'existe pas ; un champ obligatoire manquant est une erreur.

## 1. Conventions

| Règle | Valeur |
| --- | --- |
| Encodage | UTF-8 |
| Format des listes d'objets | JSON Lines (`.jsonl`) : un objet JSON par ligne |
| Noms de champs | minuscules, sans accent, mots séparés par `_` |
| Dates | ISO 8601 (`2026-11-20` ou `2026-11-20T14:05:00+01:00`) |
| Valeurs de listes fermées | les codes indiqués ci-dessous, sans accent ; l'import convertit les libellés du fichier Excel en codes (« Tous les utilisateurs » → `tous`, « PDF scanné » → `pdf_scanne`…) ; les profils sont mis en minuscules, sans accent, mots séparés par `_` |
| Champ facultatif absent | omis, ou `null` |
| Version du contrat | champ `contrat` dans `corpus.json` et `rag.json` ; le kit refuse une version majeure qu'il ne connaît pas |

Arborescence :

| Dossier | Contenu | Écrit par |
| --- | --- | --- |
| `corpus/<version_corpus>/` | corpus.json, documents.jsonl, questions.jsonl, passages.jsonl, pages_ocr.jsonl | le module d'import du kit |
| `reponses_du_rag/<version_rag>/` | rag.json, chunks.jsonl, pages_extraites.jsonl, graphe.ttl, recherches.jsonl, reponses.jsonl | le kit, avec ce que rend les endpoints d'évaluation du RAG ; ou le RAG lui-même, par fichiers |
| `resultats/evaluations/<evaluation_id>/` | RAPPORT.md et verification_juge.xlsx ; dans `fichiers_techniques/` : rapport.html, evaluation.json, scores.json, resultats_par_question.csv, liens_index.jsonl… | le kit |
| `resultats/comparaisons_de_configurations/<A>_contre_<B>/` | RAPPORT.md ; dans `fichiers_techniques/` : comparaison.json | le kit (`kit comparer`) |
| `config/` | kit.yaml | l'équipe du projet |

## 2. Le corpus (écrit par l'import, depuis le fichier Excel du document 1)

### corpus.json

| Champ | Type | Obligatoire | Contenu |
| --- | --- | --- | --- |
| contrat | texte | oui | `1.0` |
| version_corpus | texte | oui | ex. `2026-11-20.1` ; change à chaque import d'un fichier modifié |
| projet | texte | oui | nom du projet |
| date | date | oui | date de l'import |
| fichier_source | texte | oui | nom du fichier Excel et son empreinte SHA-256 |
| colonnes_libres | liste de textes | oui | noms des colonnes ajoutées par le projet (service, site…) |

### documents.jsonl — une ligne par document

| Champ | Type | Obligatoire | Colonne Excel | Valeurs |
| --- | --- | --- | --- | --- |
| reference_source | texte | oui | Référence dans la source | identifiant unique |
| titre | texte | oui | Titre | |
| type_document | texte | oui | Type de document | valeur de la feuille Listes |
| source | texte | oui | Source | valeur de la feuille Listes |
| version | texte | oui | Version | |
| date | date | non | Date | |
| format | code | oui | Format | `pdf_natif`, `pdf_scanne`, `word`, `excel`, `fiche_base` (libellé « Fiche de GED » ; l'ancien libellé « Fiche de base de données » reste accepté) |
| nb_pages | entier | non | Nombre de pages | |
| criticite | code | oui | Criticité | `C1`, `C2`, `C2_export`, `C3` |
| droits_acces | texte | oui | Droits d'accès | profil de la feuille Listes ; `tous` si aucune restriction |
| en_vigueur | booléen | oui | En vigueur | |
| remplace_par | texte | non | Remplacé par | une reference_source |
| selection | code | oui | Sélection | `hasard`, `choix_metier` |
| colonnes_libres | objet | non | colonnes ajoutées | `{"service": "Maintenance", "site": "Site A"}` |

### questions.jsonl — une ligne par question

| Champ | Type | Obligatoire | Colonne Excel | Valeurs |
| --- | --- | --- | --- | --- |
| question_id | texte | oui | Identifiant | `Q-001` |
| question | texte | oui | Question | |
| profil | texte | oui | Profil de l'utilisateur | `tous` par défaut |
| redigee_par | code | oui | Rédigée par | `metier`, `ia_relue`, `production` |
| type_reponse | code | oui | Type de réponse | `fait`, `liste`, `calcul`, `explication`, `synthese` |
| reponse_dans_documents | code | oui | Réponse dans les documents ? | `oui`, `non`, `non_accessible` |
| reponse_est_dans | code | si `oui` | La réponse est dans | `un_passage`, `plusieurs_a_combiner`, `plusieurs_un_suffit`, `ensemble_documents` |
| reponse_attendue | texte | oui | Réponse attendue | |
| points_cles | liste d'objets | si `oui` | Points clés attendus | voir ci-dessous |
| difficulte | code | oui | Difficulté | `facile`, `moyenne`, `difficile` |
| frequence | code | oui | Fréquence | `frequente`, `occasionnelle`, `rare` |
| gravite | code | oui | Gravité d'une erreur | `faible`, `moyenne`, `forte` |
| reservee_decision | booléen | oui | Réservée à la décision | `true` : jamais utilisée pour régler le RAG ; les scores clés sont calculés dessus |
| question_precedente | texte | non | Question précédente | un question_id |
| variante_de | texte | non | Variante de | un question_id |
| annotateur, date | texte, date | non | Annotateur, Date | |
| colonnes_libres | objet | non | colonnes ajoutées | |

Un point clé :

| Champ | Type | Obligatoire | Contenu |
| --- | --- | --- | --- |
| texte | texte | oui | le point clé tel qu'écrit par le métier |
| valeur | nombre | non | pour un calcul ou une valeur : le nombre (`2`) |
| unite | texte | non | `%`, `jours`, `A`… |
| tolerance | nombre | non | écart admis (`0.1`) ; 0 si absent |

L'import découpe la colonne « Points clés attendus » sur « ; » et reconnaît la forme « nombre unité ± tolérance ».

### passages.jsonl — une ligne par passage

| Champ | Type | Obligatoire | Colonne Excel | Valeurs |
| --- | --- | --- | --- | --- |
| passage_id | entier | oui | numéro de ligne | attribué par l'import, stable d'une version à l'autre tant que la ligne ne change pas |
| question_id | texte | oui | Question | |
| reference_source | texte | oui | Référence du document | existe dans documents.jsonl |
| page | texte | oui | Page | numéro de page, ou nom du champ affiché pour une fiche de GED |
| type_element | code | oui | Type d'élément | `texte`, `tableau`, `texte_scanne`, `image_schema` |
| passage | texte | oui | Passage | |
| repond | code | oui | Répond | `entierement`, `en_partie`, `piege` |

### pages_ocr.jsonl — une ligne par page de référence

| Champ | Type | Obligatoire | Contenu |
| --- | --- | --- | --- |
| reference_source | texte | oui | document scanné |
| page | texte | oui | numéro de page |
| texte_retape | texte | oui | texte exact de la page ; tableaux ligne par ligne, cellules séparées par « \| » |
| retape_par, relu_par, date | texte, texte, date | non | |

### Contrôles de l'import (rejet de la ligne, avec un message clair)

- Colonne obligatoire vide ; valeur hors liste.
- `reference_source` d'un passage absente de documents.
- `question_id` en double ; `question_precedente` ou `variante_de` qui ne renvoie à aucune question.
- Question `oui` sans passage (hors pièges) ; question `non_accessible` dont aucun passage ne vient d'un document interdit au profil.
- Avertissement (sans rejet) : configuration minimale du document 1 non atteinte.

## 3. Ce que le RAG rend

Les endpoints d'évaluation du RAG (fin de cette section) rend ces objets ; le kit les range dans ces fichiers.

### rag.json — la version évaluée

| Champ | Type | Obligatoire | Contenu |
| --- | --- | --- | --- |
| contrat | texte | oui | `1.0` |
| nom | texte | oui | nom du RAG |
| version_rag | texte | oui | identifiant unique de cette version |
| type_rag | code | oui | `vectoriel`, `graphe`, `hybride`, `agent` |
| date | date | oui | |
| k | entier | oui | nombre de chunks donnés au modèle |
| versions | objet | oui | `index`, `decoupage`, `embedding`, `generation`, `prompt`, `reranker` (texte ; `aucun` si absent) |
| filtre_droits | booléen | oui | le RAG filtre-t-il les droits ? |
| reglages | objet | non | les autres réglages du RAG, autant qu'il en a : nom du réglage → valeur (texte, nombre ou booléen). Par exemple `{"réflexion du modèle": false, "seuil de pertinence": 0.3, "recherche par mots-clés": true}` : le nom s'écrit tel qu'on veut le lire dans le rapport. Plus le RAG a de fonctionnalités, plus la liste est longue. Le rapport les affiche tous |

### chunks.jsonl — un chunk ou un élément du graphe

| Champ | Type | Obligatoire | Contenu |
| --- | --- | --- | --- |
| chunk_id | texte | oui | identifiant unique dans l'index ; c'est celui des recherches et des réponses |
| type_objet | code | oui | `chunk`, `noeud`, `relation`, `resume` |
| reference_source | texte | oui sauf `resume` | référence du document d'origine |
| version_document | texte | oui sauf `resume` | |
| page | texte | oui sauf `resume` | page, ou nom du champ affiché pour une fiche de GED |
| type_element | code | oui sauf `resume` | `texte`, `tableau`, `texte_scanne`, `image_schema` |
| droits_acces | texte | oui | profil autorisé, ou `tous` |
| ordre | entier | oui sauf `resume` | rang du chunk dans la page (0, 1, 2…) ; sert à détecter les passages coupés |
| texte | texte | oui | le texte indexé (pour une image : sa description) |
| version_index | texte | oui | |
| metadonnees | objet | non | tout le reste (chemin de titres…) |

Un chunk qui chevauche deux pages porte la page où il commence.

### pages_extraites.jsonl — obligatoire si des documents sont scannés

| Champ | Type | Obligatoire | Contenu |
| --- | --- | --- | --- |
| reference_source, page | texte | oui | |
| texte | texte | oui | le texte de la page tel que sorti de l'extraction, avant découpage |

### graphe.ttl — obligatoire si `type_rag` vaut `graphe` ou `hybride`

Le graphe exporté en RDF (Turtle). Chaque nœud et chaque relation réifiée porte sa provenance avec deux propriétés : `kit:referenceSource` et `kit:page` (espace de noms `kit: <https://kit-eval-rag/ns#>`). Le projet fournit à côté `ontologie_formes.ttl` : les règles SHACL de son ontologie.

### recherches.jsonl — une ligne par question

| Champ | Type | Obligatoire | Contenu |
| --- | --- | --- | --- |
| question_id | texte | oui | |
| profil | texte | oui | le profil avec lequel la recherche a été faite |
| k | entier | oui | |
| resultats | liste | oui | les k chunks, dans l'ordre : `{"chunk_id": "...", "rang": 1, "score": 0.83}` |
| resultats_avant_reranking | liste | non | même forme, avant reclassement |
| duree_ms | entier | oui | |

### reponses.jsonl — une ligne par question

| Champ | Type | Obligatoire | Contenu |
| --- | --- | --- | --- |
| question_id, profil | texte | oui | |
| reponse | texte | oui | la réponse envoyée à l'utilisateur |
| abstention | booléen | oui | vrai si le RAG dit ne pas pouvoir répondre |
| chunks_cites | liste de chunk_id | oui | les sources citées dans la réponse (vide si aucune) |
| chunks_contexte | liste de chunk_id | oui | tous les chunks donnés au modèle |
| duree_ms | entier | oui | de la question à la réponse |
| cout | nombre | non | en euros |
| tokens_entree, tokens_sortie | entier | non | |
| trace_id | texte | oui | identifiant de la trace dans Langfuse |

### Règles d'appel

| Règle | Détail |
| --- | --- |
| Profil | chaque question est posée avec son `profil` ; la recherche applique les droits de ce profil |
| Historique | une question avec `question_precedente` reçoit tous les échanges qui la précèdent, du plus ancien au plus récent : `[{"question": <question>, "reponse": <sa reponse_attendue>}, …]` |
| Même k | pour toutes les questions d'une évaluation |
| Isolement | le RAG ne reçoit jamais reponse_attendue, points_cles ni passages, sauf l'historique ci-dessus |
| Toutes les questions | y compris les réservées ; seul l'affichage des résultats diffère |

### Les endpoints d'évaluation

Chaque RAG ouvre quatre endpoints à une adresse web (par défaut http://127.0.0.1:8100). Le kit les appelle dans l'ordre et écrit lui-même les fichiers ci-dessus. Un RAG qui ne peut pas ouvrir d'adresse écrit ces fichiers lui-même.

| Endpoint | Adresse | Corps de la demande | Réponse |
| --- | --- | --- | --- |
| ① ingérer | `POST /ingerer` | `{"documents": [...]}` : pour chaque document, `reference_source`, `titre`, `type_document`, `version`, `format`, `droits_acces` (codes de documents.jsonl), `fichier` (nom) et `contenu` (le fichier, en base64) ; pour une fiche de GED sans fichier, `fichier` et `contenu` valent `null` et le RAG lit la fiche dans sa GED | `{"documents", "chunks", "pages"}` |
| ② montrer l'index | `GET /index` | — | `{"rag": <rag.json>, "chunks": [<chunks.jsonl>], "pages": [<pages_extraites.jsonl>], "graphe": <graphe.ttl en Turtle, ou null>}` |
| ③ rechercher | `POST /rechercher` | `{"question", "profil", "historique"}` | `{"resultats": [{"chunk_id", "rang", "score"}], "duree_ms"}` ; option `resultats_avant_reranking` (même forme, avant reclassement) |
| ④ répondre | `POST /repondre` | `{"question", "profil", "historique"}` | un objet reponses.jsonl, sans `question_id` ni `profil` |

Le RAG range les documents reçus à part de ceux de la production. Il ne reçoit jamais les annotations (règles d'appel ci-dessus).

## 4. Les sorties du kit

### liens_index.jsonl

| Champ | Contenu |
| --- | --- |
| passage_id, chunk_id, version_index | le lien |
| mode | `exact`, `approche`, `image`, `coupe` |
| similarite | de 0 à 1 |

### evaluation.json

`evaluation_id`, date, `version_corpus`, `version_kit`, contenu de rag.json, configuration du juge (modèle, version du prompt).

### resultats_par_question.csv — une ligne par question et par score

| Colonne | Contenu |
| --- | --- |
| evaluation_id, question_id | |
| niveau | `1`, `2`, `3`, `4` |
| score | identifiant standard (tableau ci-dessous) |
| valeur | nombre, ou texte pour un verdict |
| detail | justification courte (juge), chunks en cause… |

### scores.json

`evaluation_id`, puis trois blocs :

| Bloc | Contenu |
| --- | --- |
| `scores` | tous les scores, sur les questions non réservées. Pour chacun : `score`, `niveau`, `valeur`, `marge` (± à 95 %), `n` (nombre de questions ou de passages), `ventilation` (par type de document, difficulté, type d'élément, type de réponse, profil, colonne libre) |
| `scores_cles` | les scores clés présentés au métier, calculés sur les questions réservées ; les fuites de droits et les erreurs graves, sur toutes les questions ; les scores de documents, de chunks et de pages, sur tout le corpus. Pour chacun : `score`, `valeur`, `marge`, `n` |
| `remarque` | une phrase qui rappelle sur quelles questions sont calculés les scores clés, et que le métier décide à leur lecture |

Il n'y a ni seuil ni décision : c'est le métier qui décide, à la lecture des scores clés.

### Identifiants standard des scores

| Niveau | Identifiant | Configuration |
| --- | --- | --- |
| 1 | `n1_documents_indexes`, `n1_metadonnees_completes`, `n1_passages_rattaches`, `n1_passages_coupes` | minimale |
| 1 | `n1_erreur_caracteres` | minimale si scans |
| 1 | `n1_graphe_violations`, `n1_graphe_justesse` | minimale si graphe |
| 1 | `n1_erreur_mots` | recommandée |
| 2 | `n2_reussite_k`, `n2_rappel_k`, `n2_rang_premier` | minimale |
| 2 | `n2_fuite_droits` | minimale si filtre des droits |
| 2 | `n2_ndcg_k`, `n2_reussite_1`, `n2_reussite_3`, `n2_reussite_5`, `n2_reussite_10`, `n2_reussite_avant_reranking`, `n2_perimes_pieges` | recommandée |
| 3 | `n3_exactitude`, `n3_completude_listes`, `n3_valeurs`, `n3_abstention_correcte`, `n3_abstention_a_tort`, `n3_fidelite`, `n3_citations`, `n3_erreurs_graves` | minimale |
| 3 | `n3_synthese` | minimale si graphe |
| 3 | `n3_second_avis`, `n3_questions_suite`, `n3_variantes` | recommandée |
| 4 | `n4_score_pondere`, `n4_erreurs_graves`, `n4_temps_median`, `n4_temps_p95`, `n4_cout_moyen` | minimale |

### Langfuse

| Objet Langfuse | Contenu |
| --- | --- |
| Jeu de données (dataset) | nom `corpus-<projet>-<version_corpus>` ; un élément par question : entrée = question, profil, historique ; sortie attendue = réponse attendue et points clés ; métadonnées = toutes les autres colonnes |
| Expérience (dataset run) | nom = `evaluation_id` ; chaque élément relié à la trace de la réponse du RAG |
| Scores | sur chaque trace, avec les identifiants standard ci-dessus |
| Files de relecture | `relecture-reponses` (réponses à relire par le métier), `justesse-graphe` (50 relations) |
| Vérification du juge | un fichier Excel, `resultats/evaluations/<evaluation_id>/verification_juge.xlsx`, que le métier remplit (30 à 50 réponses) ; le résultat dans `fichiers_techniques/verification_juge_resultat.json` |
