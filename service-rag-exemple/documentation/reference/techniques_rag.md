# Construire le pipeline d'un RAG : ce qu'on met en place selon les cas

Un **RAG** est un assistant qui répond à des questions en s'appuyant sur des documents : il les lit, les découpe en morceaux de texte (des **chunks**), retrouve ceux qui servent à une question, puis fait écrire la réponse par un modèle de langage. Ce chemin, des documents jusqu'à la réponse, s'appelle le **pipeline**.

Ce document dit **quelle technique mettre en place à chaque étape du pipeline, dans quel cas, et comment savoir qu'elle marche**. Il s'adresse à l'équipe technique qui construit ou améliore un RAG. Il se suffit à lui-même.

## Le principe en bref

**La règle : une technique ajoutée doit améliorer un score de l'évaluation. Sinon, on la retire.** Chaque technique coûte en temps de réponse, en argent et en maintenance. On ne l'ajoute donc pas « parce que c'est la mode », mais parce que l'évaluation a montré un échec qu'elle corrige.

**On commence simple.** La configuration minimale suffit pour un premier RAG. On y ajoute des techniques quand l'évaluation montre un échec précis.

**Comment on sait que ça marche.** On évalue le RAG sur un corpus de questions dont on connaît les bonnes réponses. L'évaluation donne des scores à quatre niveaux, qu'on lit dans l'ordre : l'**ingestion** (les documents sont-ils bien lus et rangés ?), la **recherche** (le bon chunk est-il retrouvé ?), la **réponse** (est-elle juste et appuyée sur les documents ?) et le **bout en bout** (le RAG est-il utile, rapide, pas trop cher ?). Dans ce document, chaque technique indique le score qui montre son effet.

## Les six étapes du pipeline

| Étape | Son rôle | Ce qui se perd si elle est mal faite |
| --- | --- | --- |
| **1. Extraction** | lire chaque document et en sortir un texte fidèle | ce que l'extraction perd est perdu pour tout le reste |
| **2. Découpage** | couper ce texte en chunks qui se comprennent seuls | un chunk incompréhensible ne sera jamais bien retrouvé |
| **3. Indexation** | ranger les chunks dans une base vectorielle, et dans un graphe si besoin | une base qui ne filtre pas les droits oblige à filtrer trop tard |
| **4. Recherche** | trouver les bons chunks pour une question | le modèle répond à côté, ou dit qu'il ne sait pas |
| **5. Génération** | rédiger la réponse à partir des chunks trouvés | une réponse inventée, ou sans source |
| **6. Exploitation** | garder le RAG à jour et sous contrôle | un document supprimé ou périmé encore cité |

**Une exigence sur toute la chaîne, de l'extraction à l'indexation :** chaque chunk garde **la référence du document dans sa source, sa version, sa page (ou le nom du champ, pour une fiche d'une base documentaire), son type d'élément (texte, tableau, texte scanné, image ou schéma) et ses droits d'accès**. Sans ces informations, on ne peut ni relier un passage à un chunk lors de l'évaluation, ni citer une source, ni filtrer les droits.

**La configuration minimale, puis la recommandée.**

| Étape | Configuration minimale | Configuration recommandée |
| --- | --- | --- |
| Extraction | outil d'analyse de mise en page ; OCR sur les scans | traitement dédié des tableaux, des images et des fiches de base de données |
| Découpage | par section, avec le chemin de titres ; les cinq informations ci-dessus | phrase de contexte devant chaque chunk |
| Indexation | une base vectorielle qui sait filtrer par métadonnées | graphe et ontologie si l'évaluation montre des échecs sur les questions relationnelles |
| Recherche | recherche hybride (mots-clés et sens), filtre des droits | reranker ; réécriture des questions de conversation |
| Génération | réponse citée ; abstention si le contexte ne suffit pas | juge garde-fou avant l'envoi |
| Exploitation | mise à jour des sources ; rattachement et évaluation relancés | cache ; suivi des signaux de production |

## Étape 1. Extraction

Lire chaque document et en sortir un texte fidèle. **Ce que l'extraction perd est perdu pour tout le reste** : aucune étape suivante ne le rattrape.

| Si… | On met en place | Ce que ça apporte, et comment on le vérifie |
| --- | --- | --- |
| **PDF avec du texte** | lecture du texte natif et analyse de mise en page (Docling, Marker) | garde l'ordre de lecture, les titres, les colonnes et les tableaux. On le vérifie à la part de passages perdus au rattachement |
| **PDF scanné** | OCR rapide sur toutes les pages, modèle de vision seulement sur les pages difficiles | rend le texte lisible sans payer le modèle partout. On le vérifie au taux d'erreur de lecture des scans |
| **Tableau dans un document** | un chunk par tableau ou par groupe de lignes, avec titre et en-têtes répétés ; lignes écrites « colonne : valeur » | un chiffre reste lié à sa ligne et à sa colonne. On le vérifie à la recherche, sur les passages de type tableau |
| **Tableur ou export de données** | chargement dans une base et réponse en SQL, pas d'index | un calcul exact au lieu d'une recherche approximative. On le vérifie aux questions de type calcul |
| **Image ou schéma** | description par un modèle de vision ; chunk de type « image ou schéma » avec sa page | l'image devient cherchable. On le vérifie à la recherche, sur les passages de type image |
| **Fiche d'une base documentaire** (GED, tickets) | export de la fiche en « champ : valeur », un chunk par fiche | chaque champ garde son nom. On le vérifie à la recherche, sur ce type de document |
| **Texte invisible dans un document** | suppression du texte blanc sur blanc ou minuscule | empêche des consignes cachées d'atteindre le modèle |

> **À savoir.** Aucun OCR testé ne suffit seul, et ses erreurs se propagent jusqu'à la réponse (OHRBench, 2024).

## Étape 2. Découpage et enrichissement

Couper le texte en chunks qui se comprennent seuls, et leur garder leurs informations d'origine.

| Si… | On met en place | Ce que ça apporte |
| --- | --- | --- |
| **Document structuré** (titres, sections) | un chunk par section ; une section trop longue est recoupée | chaque chunk porte une idée complète |
| **Structure douteuse** | un chunk par page | le meilleur choix par défaut sur des PDF d'entreprise |
| **Coupure à taille fixe** | chevauchement de 10 à 20 % entre chunks voisins | évite de séparer une règle de son exception |
| **Chunk incompréhensible seul** (« le délai est de 14 jours ») | chemin de titres dans le texte du chunk, et une phrase de contexte écrite par un modèle de langage | le chunk dit de quel document et de quelle section il parle |
| **Réponse précise dans un contexte large** | chercher sur de petits chunks, donner au modèle la section entière | précision de la recherche, et contexte pour la réponse |
| **Toujours** | les cinq informations : référence, version, page, type d'élément, droits d'accès (et la date) | permet le rattachement au corpus, le filtrage et la citation |

On vérifie le découpage à la recherche : le bon chunk est-il retrouvé ?

> **À savoir.** Une page par chunk fait mieux que les tailles fixes sur des PDF d'entreprise (NVIDIA, 2025, éditeur). Le découpage « sémantique » ne fait pas mieux que la taille fixe (Qu et al., 2024). La phrase de contexte fait passer l'échec de recherche de 5,7 % à 3,7 % (Anthropic, 2024, éditeur).

## Étape 3. Indexation : base vectorielle, graphe, ou les deux

**La base vectorielle** se choisit sur les fonctions dont on a besoin, pas sur un classement de vitesse.

| Besoin | Bases qui le font nativement |
| --- | --- |
| Combiner mots-clés et sens | Elasticsearch / OpenSearch, Qdrant, Weaviate, Milvus (avec pgvector, à assembler soi-même) |
| Filtrer pendant la recherche (droits, document, date) | Qdrant, Weaviate (pgvector filtre après coup) |
| Vecteurs et données métier dans la même base | pgvector (PostgreSQL) |
| Très gros volume | Milvus distribué, index sur disque |

**Le graphe** s'ajoute quand l'évaluation montre des échecs que la recherche de passages ne peut pas corriger.

| Si les questions demandent… | On met en place | Ce que ça apporte, et comment on le vérifie |
| --- | --- | --- |
| **Une liste complète** (« tous les équipements alimentés par… ») | un graphe métier, structuré par une ontologie, alimenté depuis les bases et les documents | rend la liste entière, pas seulement les passages les plus proches. Se vérifie sur les questions de type liste |
| **Une chaîne de liens** (« quel site dépend de quel fournisseur ») | le même graphe, interrogé par requêtes SPARQL générées et contrôlées par l'ontologie | suit les liens au lieu de les deviner. Se vérifie sur les questions difficiles à plusieurs passages |
| **Une synthèse de tout le corpus** (« quels thèmes reviennent dans les retours d'expérience ») | GraphRAG : regroupement des entités en communautés et résumés | répond sur l'ensemble, pas sur quelques passages. Se vérifie sur les questions de synthèse |
| **Des faits simples** | rien de plus : la recherche hybride suffit | — |

Chaque élément du graphe garde la même provenance qu'un chunk (référence, version, page) : le rattachement à l'évaluation s'applique de la même façon.

> **À savoir.** Sur une base métier, un modèle de langage répond juste à 16,7 % en SQL généré, 54,2 % en SPARQL avec ontologie, 72,55 % avec contrôle et correction par l'ontologie (Sequeda et al., 2023 ; Allemang et Sequeda, 2024). GraphRAG gagne 72 à 79 % des comparaisons sur la synthèse globale, mais recule sur les faits simples et coûte cher à indexer (Edge et al., 2024).

## Étape 4. Recherche

Trouver, pour une question, les chunks qui contiennent la réponse.

| Si… | On met en place | Ce que ça apporte, et comment on le vérifie |
| --- | --- | --- |
| **Toujours** | recherche hybride : embedding (le sens) et BM25 (les mots-clés, où un mot rare pèse plus) | trouve les reformulations et les codes exacts. Se vérifie au rappel de la recherche |
| **Des utilisateurs aux droits différents** | filtre des droits **pendant** la recherche, à partir de l'identité de l'utilisateur | aucun chunk non autorisé, et des résultats même pour un utilisateur aux droits restreints. Se vérifie à l'absence de fuite de droits |
| **Le bon chunk est trouvé, mais mal classé** | reranker : un modèle relit la question et chaque chunk ensemble, puis reclasse | met le bon chunk en tête. Se vérifie au rang du premier bon chunk |
| **Questions de suite** (« et pour le site B ? ») | réécriture en question autonome avant la recherche | la recherche sait de quoi on parle |
| **Questions avec une date, une version, un service** | filtres extraits de la question (« procédure en vigueur », « site B ») | cherche dans le bon sous-ensemble |
| **Questions qui demandent plusieurs recherches successives** | décomposition de la question, ou agent dont le nombre d'appels est plafonné | enchaîne les recherches nécessaires. Se vérifie sur les questions à plusieurs passages |

> **À savoir.** Sur le jeu LIMIT, le meilleur embedding seul retrouve 18,9 % des bons documents, BM25 93,6 % (Weller et al., 2025). Reclasser avec un reranker fait passer le MRR@10 de 16,7 à 36,5 sur MS MARCO (Nogueira et Cho, 2019).

## Étape 5. Génération

Rédiger la réponse à partir des chunks trouvés, sans rien inventer.

| Si… | On met en place | Ce que ça apporte, et comment on le vérifie |
| --- | --- | --- |
| **Toujours** | citations obligatoires : chaque phrase renvoie à son chunk | l'utilisateur vérifie, et l'évaluation mesure la fidélité (la part des affirmations de la réponse qui se trouvent dans les chunks donnés au modèle) |
| **Le contexte ne contient pas la réponse** | consigne d'abstention, et vérification que le contexte suffit avant de répondre | le RAG dit qu'il ne sait pas au lieu d'inventer. Se vérifie aux questions dont la réponse n'est pas dans les documents |
| **Risque d'invention sur des sujets à forte gravité** | juge garde-fou : vérifie avant l'envoi que chaque affirmation est appuyée par un chunk | bloque une réponse non appuyée. Se vérifie à la fidélité et au taux de rejet en production |
| **Calculs, dates, totaux** | calcul délégué au code ou au SQL | évite les erreurs d'arithmétique du modèle. Se vérifie aux questions de type calcul |
| **Plusieurs versions d'un document** | réponse à partir de la version en vigueur (métadonnée de version) | évite de citer une version périmée |

> **À savoir.** Sans consigne d'abstention, un modèle passe de 10,2 % à 66,1 % de réponses fausses quand le contexte est insuffisant (Sufficient Context, 2025).

## Étape 6. Exploitation

Garder le RAG à jour et sous contrôle.

| Si… | On met en place | Ce que ça apporte |
| --- | --- | --- |
| **Les sources changent** | synchronisation des changements, plus une passe complète régulière ; suppression des chunks des documents supprimés ; puis rattachement et évaluation relancés | le RAG ne cite pas un document supprimé ou périmé |
| **Les mêmes questions reviennent souvent** | cache des réponses avec un seuil de similarité strict | répond sans tout recalculer |
| **On change de modèle, de prompt ou de découpage** | un numéro de version pour chacun ; évaluation relancée avant la bascule | on sait si le changement améliore ou dégrade |
| **En production** | traces par question (chunks retrouvés, chunks cités, abstention, versions, durée, coût) envoyées à Langfuse, un outil de suivi | alimente les signaux de production (retours négatifs, abstentions, rejets du juge garde-fou) |

## Brancher le RAG sur l'évaluation

Pour qu'un service d'évaluation puisse tester votre RAG, quel que soit son langage, **le RAG ouvre quatre adresses web** (des « endpoints ») :

| Endpoint | Ce qu'il fait |
| --- | --- |
| ① **ingérer** | reçoit les documents du corpus d'évaluation et les range dans un espace séparé de la production |
| ② **montrer l'index** | rend la version exacte du RAG, ses chunks avec leurs métadonnées, et le texte de chaque page lue |
| ③ **rechercher** | pour une question et un profil, rend les chunks retrouvés, classés |
| ④ **répondre** | pour une question et un profil, rend la réponse, l'abstention éventuelle, les chunks cités et la durée |

Le service les appelle dans cet ordre et ne voit jamais le code du RAG. Seule cette partie s'écrit pour l'évaluation : le reste du RAG ne change pas. Un RAG qui ne peut pas ouvrir d'adresse peut écrire lui-même les fichiers que ces endpoints auraient rendus.

## Un exemple : le RAG simple du dépôt

Le RAG d'exemple du dépôt met en œuvre la configuration minimale, et rien de plus :

| Étape | Ce qu'il fait |
| --- | --- |
| **Extraction** | Docling (en conteneur) pour les PDF natifs et, avec OCR forcé, pour les PDF scannés ; une lecture « champ : valeur » pour les fiches d'une base documentaire. Pas de modèle de vision : une figure n'est connue que par sa légende |
| **Découpage** | un chunk par section, avec le chemin de titres, recoupé au-delà de 1 500 caractères ; les cinq informations sur chaque chunk |
| **Recherche** | deux recherches, par le sens et par les mots, fusionnées par rang ; filtre des droits pendant la recherche ; k = 5. Pas de reranker, pas de décomposition de la question |
| **Génération** | réponse citée, abstention si le contexte ne suffit pas |

Ce que l'évaluation en montre : des erreurs de lecture sur les scans (15 caractères sur 100 mal lus), les figures connues par leur seule légende, et les questions qui combinent plusieurs passages qui échouent plus souvent, faute de reranker et de décomposition. Des techniques de la configuration recommandée (traitement des images, reranker, décomposition de la question) viseraient précisément ces échecs.

## Ce qu'on ne fait pas

- **Le découpage « sémantique » par défaut** : il ne fait pas mieux que la taille fixe, pour un coût plus élevé.
- **Un agent pour une question simple** : plus lent, plus cher, plus de points d'échec.
- **GraphRAG pour des faits simples** : il recule sur ces questions et coûte cher à indexer.
- **Un réentraînement de modèle avant d'avoir le corpus d'évaluation** : on ne saura pas s'il a servi.
- **Laisser le modèle calculer** : il se trompe sur les additions et les dates.
- **Vérifier les droits seulement à l'indexation** : un droit retiré resterait actif jusqu'à la prochaine indexation.

## Petit glossaire

| Mot | Ce que ça veut dire |
| --- | --- |
| **RAG** | assistant qui répond à des questions en s'appuyant sur des documents |
| **Chunk** | un morceau de texte du RAG, avec sa référence, sa page, son type d'élément, ses droits |
| **Embedding** | la représentation d'un texte par des nombres, qui permet de comparer le sens de deux textes |
| **BM25** | une recherche par mots-clés, où un mot rare pèse plus qu'un mot courant |
| **Recherche hybride** | l'embedding et BM25 combinés |
| **Reranker** | un modèle qui reclasse les chunks retrouvés, du plus au moins utile |
| **OCR** | la lecture d'un document scanné par reconnaissance de caractères, qui fait des fautes |
| **Ontologie** | la description des types d'objets et de relations d'un métier, qui structure un graphe |
| **Fidélité** | part des affirmations d'une réponse qui se trouvent dans les chunks donnés au modèle |
| **Abstention** | quand le RAG répond qu'il ne sait pas |
| **Juge garde-fou** | un modèle qui vérifie une réponse avant son envoi |

## Sources

- OHRBench, 2024 : [arxiv.org/abs/2412.02592](https://arxiv.org/abs/2412.02592)
- Anthropic, Contextual Retrieval, 2024 : [anthropic.com/news/contextual-retrieval](https://www.anthropic.com/news/contextual-retrieval)
- Qu et al., Is Semantic Chunking Worth the Computational Cost?, 2024 : [arxiv.org/abs/2410.13070](https://arxiv.org/abs/2410.13070)
- Weller et al., LIMIT, 2025 : [arxiv.org/abs/2508.21038](https://arxiv.org/abs/2508.21038)
- Nogueira et Cho, Passage Re-ranking with BERT, 2019 : [arxiv.org/abs/1901.04085](https://arxiv.org/abs/1901.04085)
- Sequeda et al., 2023 : [arxiv.org/abs/2311.07509](https://arxiv.org/abs/2311.07509) ; Allemang et Sequeda, 2024 : [arxiv.org/abs/2405.11706](https://arxiv.org/abs/2405.11706)
- Edge et al., GraphRAG, 2024 : [arxiv.org/abs/2404.16130](https://arxiv.org/abs/2404.16130)
- Sufficient Context, 2025 : [arxiv.org/abs/2411.06037](https://arxiv.org/abs/2411.06037)
