# Lire et interpréter les résultats d'une évaluation

Ce guide dit **où sont les résultats**, **comment les lire**, et **quoi corriger** quand un score est mauvais. Il s'appuie sur une vraie évaluation : celle du RAG de démonstration (k = 5) sur le corpus d'exemple.

## 1. Où sont les résultats

Une évaluation, c'est un corpus évalué avec une version du RAG. Son identifiant est `<version du corpus>_<version du RAG>`, par exemple `2026-11-20.1_rag-demo-k5-80032dcd`. Ses résultats sont à trois endroits.

**Dans un dossier**, `sorties/resultats/<évaluation>/` :

| Fichier | Pour qui | Contenu |
| --- | --- | --- |
| **`rapport.html`** | **le métier** : à ouvrir en premier | une page : la décision, les scores avec leur seuil, les questions à regarder, la cause probable des erreurs |
| `scores.json` | l'équipe technique | chaque score : valeur, marge d'erreur, nombre de questions, ventilation, seuil ; puis la décision |
| `resultats_par_question.csv` | les deux, dans un tableur | une ligne par question et par score, avec le détail (verdict et justification du juge, chunks en cause…) |
| `passages_non_rattaches.jsonl` | l'équipe technique | les passages du métier introuvables dans l'index, avec leur **cause probable** |
| `croisement.jsonl` | les deux | pour chaque question : bon passage retrouvé ou non, réponse juste ou non, et le diagnostic |
| `relecture.jsonl` | le métier | les réponses à relire, et pourquoi |
| `liens_index.jsonl` | l'équipe technique | chaque lien passage du métier ↔ chunk du RAG, avec son mode (exact, approché, image, coupé) |
| `evaluation.json` | archive | ce qui a été évalué : versions du corpus, du kit et du RAG, modèle et prompt du juge, seuils |

**Dans Langfuse** (http://127.0.0.1:3100), on trouve :
- l'expérience du même nom, avec une ligne par question : la réponse, ses scores, et le lien vers la trace du RAG (recherche, génération) ;
- les files de relecture du métier.

**Dans la base** (`sorties/base.sqlite`), on trouve tout, y compris le détail des questions réservées, qui n'apparaît nulle part ailleurs.

## 2. Lire le rapport, dans l'ordre

### 2.1 La décision

C'est l'encadré en haut du rapport. Deux règles le décident.

1. **Les critères bloquants : une fuite de droits ou une erreur grave bloque, quel que soit le reste.** Ils se jugent sur **toutes** les questions.
2. **Les seuils** se jugent sur les **questions réservées à la décision** : celles qui n'ont jamais servi à régler le RAG.

Pour le RAG de démonstration, la décision est **« mise en production non recommandée »** :
- 2 erreurs graves, ce qui déclenche un critère bloquant ;
- l'OCR à 15 %, pour un seuil de 2 % ;
- le bon passage retrouvé dans 69 % des cas sur les questions réservées, pour un seuil de 90 %.

> **Pourquoi deux jeux de questions ?** Si l'on règle le RAG en regardant les questions de la décision, on finit par le régler « pour le test », et le score ne veut plus rien dire. Le rapport et le CSV montrent donc le détail des questions de réglage. Pour les questions réservées, ils ne montrent que les scores globaux. Leur détail reste dans la base.

### 2.2 Les scores, niveau par niveau, et dans l'ordre

**On lit toujours les niveaux dans l'ordre.** Une réponse fausse vient souvent d'un passage perdu à l'ingestion ou mal retrouvé. Changer le prompt n'y changera rien.

Chaque score est donné avec :

| Colonne | Ce qu'elle veut dire |
| --- | --- |
| Valeur | le score, sur les questions non réservées |
| ± (marge) | l'incertitude à 95 % : avec 28 questions, « 86 % ± 13 % » veut dire « quelque part entre 73 % et 99 % ». **Un score sur moins de 10 questions est une tendance, pas une mesure** |
| n | le nombre de questions (ou de passages, de pages, de chunks) sur lequel il est calculé |
| Seuil, état | le seuil du métier, et s'il est atteint |

### 2.3 Les questions à regarder en premier

Le rapport les liste dans cet ordre :
1. les erreurs graves et les fuites ;
2. les réponses fausses ;
3. les réponses données là où il fallait s'abstenir ;
4. les passages perdus à l'ingestion.

Pour chacune, il donne le détail : la justification du juge, les chunks en cause, la cause probable.

### 2.4 Où chercher la cause : le croisement recherche × réponse

Pour chaque question dont la réponse est dans les documents, le kit croise deux faits. Le bon passage a-t-il été retrouvé (niveau 2) ? La réponse est-elle juste (niveau 3) ?

| Bon passage retrouvé ? | Réponse | Diagnostic | Où agir (document 2) |
| --- | --- | --- | --- |
| oui | juste | **ok** | — |
| oui | fausse, partielle ou abstention | **génération** : le RAG avait la bonne information et l'a mal utilisée | prompt, citations obligatoires, modèle, calcul délégué |
| non | fausse ou abstention | **recherche** : la bonne information n'est pas arrivée jusqu'au modèle | recherche hybride, reranker, phrase de contexte, découpage |
| non, et aucun passage rattaché | — | **ingestion** : l'information n'est même pas dans l'index | extraction, OCR, tableaux, images |
| non | juste | juste **sans le bon passage** : le modèle sait de lui-même, ou le corpus a oublié un passage | vérifier l'annotation |

Résultat du RAG de démonstration, sur 32 questions :

| Diagnostic | Questions |
| --- | --- |
| ok | 20 |
| génération : le bon chunk était retrouvé | 6 |
| recherche : le bon chunk n'est pas retrouvé | 4 |
| génération : abstention à tort | 2 |

**Lecture** : la recherche marche plutôt bien, et la moitié des erreurs vient de la génération. On commence donc par le prompt et le modèle de génération, pas par la recherche.

## 3. Chaque score : ce qu'il mesure, comment le lire, quoi faire

Les identifiants (`n1_…`) sont ceux de `scores.json`, du CSV et de Langfuse. Les valeurs entre parenthèses sont celles du RAG de démonstration.

### Niveau 1 — Ingestion : les documents sont-ils bien lus ?

| Score | Ce qu'il mesure | Démo | Si c'est mauvais |
| --- | --- | --- | --- |
| `n1_documents_indexes` | part des documents du corpus présents dans l'index | 100 % | un document manque : format non lu, erreur d'ingestion |
| `n1_metadonnees_completes` | part des chunks qui portent référence, version, page, type d'élément et droits | 100 % | sans elles, ni rattachement, ni filtre des droits, ni citation possible |
| `n1_passages_rattaches` | part des passages du métier retrouvés dans un chunk du même document, à la même page | 100 % | lire `passages_non_rattaches.jsonl` : chaque passage a sa cause probable (voir plus bas) |
| `n1_passages_coupes` | part des passages coupés entre deux chunks | 0 % | découper par section, ajouter du chevauchement |
| `n1_erreur_caracteres` | caractères à corriger pour passer du texte lu par l'OCR au texte retapé, divisé par le nombre de caractères retapés | **15 %** (seuil 2 %) | voir l'exemple ci-dessous |
| `n1_erreur_mots` | la même chose en mots | 20 % | — |

**Les causes probables d'un passage non rattaché**, données par le kit :

| Cause affichée | Ce qu'il faut faire |
| --- | --- |
| « aucun chunk sur la page 4 ; le passage est trouvé page 2 : page mal notée ? » | le **métier** corrige la page dans son fichier Excel |
| « aucun chunk sur la page… : page perdue à l'extraction » | l'équipe technique vérifie l'extraction de ce document |
| « tableau mal extrait : 60 % des mots retrouvés » | traitement dédié des tableaux |
| « OCR : ressemblance de 70 % au mieux » | meilleur OCR, ou modèle de vision sur les pages difficiles |
| « aucun chunk de type image sur la page » | décrire les images (modèle de vision) |
| « document absent de l'index » | l'ingestion a sauté ce document |

**Exemple : pourquoi l'OCR de la démo est à 15 %.** Comparer le texte retapé et le texte extrait d'une page (NT-031, page 2) montre trois causes :
- **Docling écarte l'en-tête et le pied de page** (« VALTÉRA INDUSTRIES — Archives techniques »).
- **Il colle des mots**, par exemple « TGBT-Aest » ou « Disjoncteurouvert ».
- **Il lit mal des chiffres**, par exemple « 1.600 A » au lieu de « 1 600 A ».

Sur une autre page (NT-040, page 3), il **mélange l'ordre des lignes**. Les passages restent retrouvés, car le rattachement tolère 10 % d'écart, mais une valeur mal lue peut fausser une réponse.

### Niveau 2 — Recherche : le bon passage est-il retrouvé ?

| Score | Ce qu'il mesure | Démo | Si c'est mauvais |
| --- | --- | --- | --- |
| `n2_reussite_k` | part des questions dont la recherche ramène le bon passage dans les k premiers chunks. Si la réponse doit **combiner** plusieurs passages, il faut les avoir tous | **86 %** ± 13 % (seuil 90 %) | voir la ventilation par type de document ; recherche hybride, phrase de contexte, filtres de métadonnées |
| `n2_rappel_k` | part des passages attendus retrouvés | 81 % | questions à combiner : décomposer la question |
| `n2_rang_premier` | 1 si le premier bon chunk est 1er, 1/2 s'il est 2e… | 0,68 | bon chunk trouvé mais mal classé : un reranker |
| `n2_reussite_1`, `_3`, `_5` | la réussite pour k = 1, 3, 5 | 54 %, 75 %, 86 % | aide à choisir k : ici, passer de 3 à 5 gagne 11 points |
| **`n2_fuite_droits`** | nombre de questions où un document **interdit au profil** est retrouvé | **0** | **bloquant** : filtrer les droits *pendant* la recherche, pas après |
| `n2_perimes_pieges` | part des questions où une version périmée ou un passage piège est classé avant le bon | 0 % | filtre sur la version en vigueur |

**Lire la ventilation.** Dans `scores.json` (ou section 5 du rapport), `n2_reussite_k` par type de document donne :
- procédures : 100 % ;
- notes techniques : 88 % ;
- comptes rendus d'intervention : 50 %, sur 4 questions seulement.

Ce dernier chiffre est une tendance, pas une mesure, mais il dit où regarder en premier : les fiches d'intervention.

### Niveau 3 — Réponse : la réponse est-elle juste et appuyée ?

| Score | Ce qu'il mesure | Démo | Si c'est mauvais |
| --- | --- | --- | --- |
| `n3_exactitude` | le juge vérifie chaque point clé attendu : présent, absent ou contredit. Juste = 1, partielle = 0,5, fausse = 0. Les abstentions ne sont pas notées ici | **79 %** ± 15 % (seuil 80 %) | lire la justification du juge dans le CSV ; croiser avec la recherche |
| `n3_completude_listes` | pour une question « liste » : part des éléments attendus présents | 100 % | graphe et ontologie pour les listes |
| `n3_valeurs` | les valeurs chiffrées attendues sont-elles dans la réponse, avec la bonne unité et dans la tolérance ? | 91 % | calcul délégué à un outil plutôt qu'au modèle |
| `n3_abstention_correcte` | sur les questions sans réponse ou interdites au profil : part des fois où le RAG dit ne pas savoir | 100 % | consigne d'abstention ; vérifier que le contexte suffit avant de répondre |
| `n3_abstention_a_tort` | part des questions où le RAG ne répond pas alors qu'il avait le bon passage | 6 % | consigne d'abstention trop stricte |
| `n3_fidelite` | (Ragas) part des affirmations de la réponse appuyées par les chunks donnés au modèle | 92 % | citations obligatoires ; LLM juge garde-fou |
| `n3_citations` | au moins une source citée est la bonne, sans piège ni document interdit | 89 % | — |
| **`n3_erreurs_graves`** | réponses fausses, non fidèles (une seule affirmation non appuyée suffit), ou données au lieu de s'abstenir, **sur une question de gravité forte** | **2** | **bloquant** ; chaque cas est relu par le métier |
| `n3_synthese` | (Ragas) note de 1 à 5 sur la grille de JUGE.md, ramenée sur 100 % | 50 % | un RAG vectoriel synthétise mal : graphe |
| `n3_questions_suite` | exactitude des questions de suite | 100 % | — |
| `n3_variantes` | part des groupes de reformulations dont les réponses diffèrent | 0 % | robustesse aux reformulations |

**Lire le verdict du juge.** Dans le CSV, la colonne `detail` de `n3_exactitude` donne le statut de chaque point clé. Par exemple, pour Q-008 :

```
1. present : La valeur de 72 A est explicitement mentionnée dans la réponse.
2. absent : La valeur de 500 ms n'est pas mentionnée dans la réponse.
```

Verdict : **partielle**. La réponse donne le courant de réglage, mais oublie la temporisation.

**Les deux erreurs graves de la démo :**
- **Q-004** n'est pas fidèle (0,5) : une affirmation de la réponse n'est appuyée par aucun extrait.
- **Q-046** est une synthèse fausse.

C'est au métier de les relire, dans la file `relecture-reponses` de Langfuse.

### Niveau 4 — Bout en bout : le RAG est-il utile et sûr ?

| Score | Ce qu'il mesure | Démo |
| --- | --- | --- |
| `n4_score_pondere` | réponses justes, pondérées par **fréquence × gravité** (de 1 à 9). Une question fréquente et grave compte 9 fois plus qu'une question rare et sans gravité. Une abstention compte juste sur une question sans réponse, et fausse sur une question qui en a une | 80 % ± 12 % |
| `n4_erreurs_graves` | repris du niveau 3 | 2 |
| `n4_temps_median`, `n4_temps_p95` | temps de réponse médian, et temps sous lequel répondent 95 % des questions | 7,8 s et 13,3 s |
| `n4_cout_moyen` | coût moyen par question, en euros | 0 € (modèles locaux) |

Le score pondéré dit ce que vivront les utilisateurs. Un RAG à 90 % d'exactitude qui se trompe sur les questions fréquentes et graves sera moins bon ici.

## 4. Les marges d'erreur : ne pas sur-interpréter

La marge est `± 1,96 × √(p × (1 − p) ÷ n)` (document 3). Ce qu'il faut retenir :
- avec 50 questions, un score est précis à ± 11 points environ ; avec 200, à ± 5,5 ;
- une marge de « ± 0 % » sur un score de 100 % ou de 0 % ne veut pas dire « certain » : la formule ne sait pas estimer l'incertitude aux extrêmes ;
- un score sur moins de 10 questions (une case de la ventilation, par exemple) est une tendance.

## 5. Comparer deux versions

`kit comparer A B` répond à la question : « la nouvelle version est-elle meilleure ? »

1. **Même corpus** : sinon la comparaison est refusée.
2. **Écart et marge** : un écart plus petit que la marge **ne prouve rien seul**.
3. **Question par question** : les questions gagnées et perdues sont plus parlantes que les moyennes.
4. **Test de McNemar** : il ne regarde que les questions qui ont changé. Une valeur p au-dessus de 0,05 veut dire que l'écart peut être dû au hasard.
5. **Régression** : une question de gravité forte perdue est signalée, même si la moyenne monte. Elle se regarde avant toute décision.

**Exemple : le RAG de démonstration avec k = 5 (A), puis k = 3 (B).**

```bash
uv run kit comparer sorties/resultats/2026-11-20.1_rag-demo-k5-80032dcd sorties/resultats/2026-11-20.1_rag-demo-k3-80032dcd
```

| Score | k = 5 | k = 3 | Lecture |
| --- | --- | --- | --- |
| bon passage retrouvé (`n2_reussite_k`) | 86 % | 75 % | moins de chunks, moins de chances de ramener le bon : 3 questions perdues |
| passages attendus retrouvés (`n2_rappel_k`) | 81 % | 64 % | le seul écart **plus grand que la marge** : ce n'est pas le hasard |
| réponses justes (`n3_exactitude`) | 79 % (n = 28) | 83 % (n = 23) | semble monter, mais sur 5 questions de moins : le RAG s'abstient davantage, et les abstentions ne sont pas notées ici |
| erreurs graves | 2 | 0 | moins de contexte, moins d'occasions d'affirmer sans appui |
| score pondéré (`n4_score_pondere`) | 80 % | 77 % | ce que vivront les utilisateurs : 4 questions perdues, aucune gagnée |

McNemar donne p = 0,125 sur le score pondéré : avec 40 questions, on ne peut pas exclure le hasard.

**Conclusion** : k = 3 n'est pas meilleur. Il évite les deux erreurs graves, mais en répondant moins. Pour décider, il faudrait plus de questions (la configuration recommandée en prévoit 200), et un correctif ciblé des deux erreurs graves sur k = 5.

C'est tout l'intérêt de lire **plusieurs scores ensemble**. Une exactitude qui monte peut cacher un RAG qui répond moins.

## 6. Le parcours de correction, en résumé

```
Niveau 1 mauvais ?  → extraction, OCR, tableaux, images, découpage      (document 2, sections 3 et 4)
Niveau 2 mauvais ?  → recherche hybride, reranker, filtres, k           (document 2, section 6)
Niveau 3 mauvais ?  → regarder d'abord le croisement :
                       « recherche »  → revenir au niveau 2
                       « génération » → prompt, citations, abstention, modèle (document 2, section 7)
Bloquant ?          → fuite : filtre des droits pendant la recherche ; erreur grave : relecture métier, garde-fou
Puis                → nouvelle version du RAG, kit evaluer, kit comparer avec la précédente
```
