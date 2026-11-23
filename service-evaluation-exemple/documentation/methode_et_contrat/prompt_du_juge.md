# Le LLM juge du kit — version 1.0

Le juge note l'exactitude des réponses (niveau 3). Le prompt ci-dessous est le même pour tous les projets ; toute modification change sa version, et le juge doit être vérifié à nouveau (document 3, section 8).

## Réglages

| Réglage | Valeur |
| --- | --- |
| Modèle | de préférence différent de celui du RAG ; inscrit dans evaluation.json |
| Température | 0 |
| Sortie | JSON strict, validé par le kit ; une sortie invalide est redemandée une fois, puis la question part en relecture |
| Questions notées | celles dont `reponse_dans_documents` vaut `oui`, et dont le RAG ne s'est pas abstenu |

## Prompt d'exactitude

```text
Tu es un évaluateur rigoureux. Tu compares la réponse d'un assistant à une réponse de référence écrite par un expert métier.

Question :
{question}

Réponse de référence :
{reponse_attendue}

Points clés que la réponse doit contenir :
{points_cles_numerotes}

Réponse de l'assistant :
{reponse_rag}

Pour chaque point clé, dis s'il est :
- "present" : la réponse de l'assistant l'exprime, avec les mêmes mots ou d'autres mots de même sens ;
- "absent" : la réponse ne l'exprime pas ;
- "contredit" : la réponse affirme quelque chose d'incompatible avec ce point clé.

Règles :
- Une valeur chiffrée est "present" seulement si elle est égale à la valeur attendue, avec la même unité ou une unité équivalente, dans la tolérance indiquée.
- Une information juste mais en plus des points clés ne change rien.
- Une affirmation qui contredit la réponse de référence, même hors des points clés, se signale dans "contradictions".
- Ne juge pas le style ni la longueur.

Réponds uniquement par ce JSON :
{
  "points_cles": [{"numero": 1, "statut": "present|absent|contredit", "justification": "une phrase"}],
  "contradictions": ["une phrase par contradiction hors points clés"],
  "verdict": "juste|partielle|fausse"
}

Verdict :
- "juste" : tous les points clés sont "present" et il n'y a aucune contradiction ;
- "partielle" : au moins un point clé "present", aucun "contredit", aucune contradiction ;
- "fausse" : sinon.
```

Le kit recalcule le verdict à partir des statuts : en cas d'écart avec le verdict du juge, il garde le sien et envoie la question en relecture.

## Scores tirés du juge

| Score | Calcul |
| --- | --- |
| `n3_exactitude` | juste = 1, partielle = 0,5, fausse = 0 ; moyenne sur les questions notées |
| `n3_completude_listes` | pour les questions de type `liste` : part des points clés « present » |

## Grille de synthèse (Ragas RubricsScore)

Pour les questions de type `synthese`, note de 1 à 5 :

| Note | Description |
| --- | --- |
| 1 | la réponse ne traite pas la question, ou n'est appuyée sur aucune source |
| 2 | moins de la moitié des thèmes attendus, ou une erreur importante |
| 3 | la moitié des thèmes attendus au moins, sans erreur importante |
| 4 | presque tous les thèmes attendus, appuyés par les sources |
| 5 | tous les thèmes attendus, exacts, chacun appuyé par une source citée |

`n3_synthese` = moyenne des notes, ramenée sur 100 %.

## Vérification du juge

| Étape | Détail |
| --- | --- |
| 1 | tirer au hasard 30 réponses (50 en configuration recommandée), hors questions réservées |
| 2 | les écrire dans un fichier Excel, `verification_juge.xlsx`, avec la question, la bonne réponse, ses points clés et la réponse du RAG ; le métier note chacune juste, partielle ou fausse, avec le critère ci-dessus, sans voir la note du juge (s'il préfère, il note dans la file Langfuse `verification-juge`) |
| 3 | le kit calcule l'accord : part des réponses où le métier et le juge donnent le même verdict |
| 4 | accord d'au moins 90 % : juge validé ; sinon, lire les réponses où le juge et le métier ne sont pas d'accord, préciser la consigne du juge (son prompt, dont on change alors la version) ou changer de modèle juge, puis refaire la vérification |
