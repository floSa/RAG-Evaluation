# Partie 3 — Le kit d'évaluation

Le kit lit le corpus et les fichiers d'un RAG, et rend des scores sur **quatre niveaux**, une **décision** et un **rapport**. Il est le même pour tous les projets : on ne le modifie pas pour évaluer un nouveau RAG.

```
evaluation/
├── config/
│   ├── kit.yaml          point d'accès et modèle du juge, seuils de ressemblance, chemins
│   └── seuils.json       le seuil de chaque score, fixé par le métier (document 3, section 9)
├── juge/
│   └── JUGE.md           le prompt du LLM juge (document de référence)
├── kit/                  le code (une commande : kit)
├── tests/
└── LIRE_LES_RESULTATS.md où sont les résultats, comment les lire, quoi corriger
```

## 1. Configurer

**Le modèle juge** : [`config/kit.yaml`](config/kit.yaml). La clé est dans `.env` (`KIT_LLM_CLE`).

```yaml
modeles:
  adresse: http://127.0.0.1:8080/v1   # n'importe quel point d'accès compatible OpenAI
  variable_cle: KIT_LLM_CLE
  juge:
    modele: chat                      # de préférence un autre modèle que celui du RAG
    temperature: 0
```

Le juge doit être **un autre modèle que celui du RAG** : un modèle tend à favoriser ses propres réponses. Ici, le RAG génère avec `gemma-4-e4b` et le juge est `chat` (qwen3.5-4b). Tester le branchement :

```bash
uv run kit verifier-modeles
```

**Les seuils** : [`config/seuils.json`](config/seuils.json). Pour chaque score, `seuil`, `sens` (`min` : au moins ; `max` : au plus) et `bloquant`. Les valeurs sont les repères du document 3. **Le métier les fixe avant la première évaluation**, et ne les change pas après avoir vu les résultats.

| Score | Seuil | Bloquant |
| --- | --- | --- |
| passages retrouvés dans l'index (`n1_passages_rattaches`) | ≥ 95 % | |
| erreur de l'OCR (`n1_erreur_caracteres`) | ≤ 2 % | |
| bon passage retrouvé (`n2_reussite_k`) | ≥ 90 % | |
| **fuites de droits** (`n2_fuite_droits`) | 0 | **oui** |
| réponses justes (`n3_exactitude`) | ≥ 80 % | |
| abstentions correctes (`n3_abstention_correcte`) | ≥ 80 % | |
| fidélité aux sources (`n3_fidelite`) | ≥ 90 % | |
| **erreurs graves** (`n3_erreurs_graves`, `n4_erreurs_graves`) | 0 | **oui** |
| score pondéré (`n4_score_pondere`) | ≥ 80 % | |
| temps médian, temps à 95 %, coût moyen | 15 s, 30 s, 0,05 € | |

## 2. Évaluer

Le corpus doit être importé ([partie 1](../corpus/README.md)) et le RAG doit avoir produit ses fichiers ([partie 2](../rag/README.md)).

```bash
uv run kit evaluer --corpus sorties/corpus/2026-11-20.1 --rag sorties/sorties_rag/rag-demo-k5-80032dcd
```

Le kit vérifie d'abord le contrat : si un fichier est faux, il s'arrête et dit pourquoi. Puis il enchaîne les quatre niveaux. On peut aussi les lancer **un par un, dans l'ordre**, avec `kit niveau1` à `kit niveau4` (mêmes options). Le niveau 1 peut tourner juste après l'ingestion, avant que le RAG ait répondu aux questions.

| Niveau | La question posée | Comment le kit la tranche | Durée |
| --- | --- | --- | --- |
| 1. Ingestion | les documents sont-ils bien lus ? les passages du métier sont-ils dans l'index ? | il **rattache** chaque passage à un chunk de même document et même page : texte contenu, ou ressemblant à 95 % ; tableau aux mêmes mots à 90 % ; scan ressemblant à 90 % ; image : un chunk image de la page. Taux d'erreur de l'OCR avec jiwer | secondes |
| 2. Recherche | le bon chunk est-il retrouvé, bien classé, sans document interdit ? | il compare les k chunks retrouvés aux chunks rattachés, selon la règle « la réponse est dans » (un passage, un parmi plusieurs, tous à combiner) | secondes |
| 3. Réponse | la réponse est-elle juste, appuyée, bien citée ? le RAG s'abstient-il quand il le faut ? | le **LLM juge** vérifie chaque point clé (présent, absent, contredit) ; **Ragas** mesure la fidélité aux chunks ; un script contrôle l'abstention, les citations, les valeurs chiffrées | quelques minutes |
| 4. Bout en bout | le RAG est-il utile et sûr, à un coût et un temps acceptables ? | score pondéré par fréquence × gravité ; erreurs graves ; temps et coût ; **décision** par rapport aux seuils | secondes |

Les résultats sont écrits dans `sorties/resultats/<évaluation>/`, dans la base et dans Langfuse. **Pour les lire : [LIRE_LES_RESULTATS.md](LIRE_LES_RESULTATS.md).**

Une évaluation est identifiée par `<version du corpus>_<version du RAG>`. Relancer un niveau remplace ses résultats. Évaluer une autre version du RAG crée une autre évaluation.

## 3. Ce qui va dans Langfuse

Langfuse (http://127.0.0.1:3100) est l'interface partagée avec le métier.

| Objet Langfuse | Contenu | Créé par |
| --- | --- | --- |
| Jeu de données `corpus-<projet>-<version>` | une entrée par question : la question, le profil, l'historique, la réponse attendue, les points clés | `kit importer` |
| Traces du RAG | une par question : recherche, génération, tokens, durée | le RAG lui-même |
| Expérience `<évaluation>` | une ligne par question, reliée au jeu de données, avec la réponse du RAG et sa trace (`trace_rag`) | le kit, au premier niveau publié |
| Scores | sur chaque question de l'expérience (hors questions réservées), et les scores globaux de l'évaluation | chaque niveau |
| File `relecture-reponses` | les réponses que le métier doit relire : fausses ou partielles, toutes celles de gravité forte, 10 au hasard, les désaccords du juge | `kit niveau3` |
| File `verification-juge` | 30 réponses à noter par le métier pour vérifier le juge | `kit verifier-juge --envoyer` |

Le métier note dans une file avec le score **`verdict_metier`** (juste, partielle, fausse).

## 4. Vérifier le juge, avant de lui faire confiance

Le juge est un modèle de langage : il peut se tromper. Avant de s'en servir pour décider, on vérifie qu'il note comme le métier (document 3, section 8 ; [JUGE.md](juge/JUGE.md)).

1. Tirer 30 réponses au hasard (hors questions réservées) et les envoyer au métier :
   ```bash
   uv run kit verifier-juge --corpus sorties/corpus/2026-11-20.1 --rag sorties/sorties_rag/rag-demo-k5-80032dcd --envoyer
   ```
2. Dans Langfuse, **Annotation Queues → `verification-juge`** : le métier ouvre chaque réponse, la lit avec la question, et choisit `verdict_metier` = juste, partielle ou fausse, **sans regarder la note du juge**.
3. Calculer l'accord :
   ```bash
   uv run kit verifier-juge --corpus sorties/corpus/2026-11-20.1 --rag sorties/sorties_rag/rag-demo-k5-80032dcd
   ```
   Exemple de sortie (valeurs d'illustration : le métier n'a pas encore noté l'échantillon de la démonstration) :
   ```
   Notes du métier : 30 sur 30.
   Accord juge / métier : 93 % (seuil 90 %) ; kappa de Cohen : 0.85. Juge VALIDÉ.
     - Q-030 : juge « fausse », métier « partielle »
   ```

**Accord d'au moins 90 %** : le juge est validé. Sinon, on lit les désaccords, on précise le prompt de `JUGE.md`, on change sa version (`version_prompt` dans `kit.yaml`) et on recommence. On refait la vérification à chaque changement de modèle juge ou de prompt.

Le **kappa de Cohen** est l'accord corrigé du hasard. Il révèle un juge qui dit presque toujours « juste » : un tel juge peut atteindre 90 % d'accord brut sans rien distinguer. Repère : au-dessus de 0,8, l'accord est très bon ; sous 0,6, il faut se méfier, même si le taux d'accord passe.

## 5. Comparer deux versions du RAG

Après un changement (k, prompt, modèle, découpage), on évalue la nouvelle version, puis :

```bash
uv run kit comparer sorties/resultats/2026-11-20.1_rag-demo-k5-80032dcd sorties/resultats/2026-11-20.1_rag-demo-k3-…
```

Le kit refuse de comparer deux corpus différents. Il affiche pour chaque score l'écart, et s'il dépasse la marge d'erreur. Il donne aussi, question par question, les **questions gagnées et perdues**, avec le **test de McNemar** : une valeur p au-dessus de 0,05 veut dire que l'écart peut être dû au hasard. Une question de gravité forte perdue est signalée comme **régression**, même si la moyenne monte. Explications : [LIRE_LES_RESULTATS.md](LIRE_LES_RESULTATS.md#comparer-deux-versions).
