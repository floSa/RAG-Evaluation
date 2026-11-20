# Corpus d'exemple — maintenance électrique de Valtéra Industries (fictif)

Un corpus d'évaluation complet, annoté selon le document 1, sur une entreprise **entièrement fictive** : aucune donnée réelle. Il atteint la configuration minimale du document 1 sur toutes les lignes du tableau de bord.

| Élément | Contenu |
| --- | --- |
| `sources/` | 50 documents PDF : 17 procédures (PDF natifs), 16 notes techniques (11 natives, 5 scannées et bruitées : images seules, sans texte), 17 comptes rendus d'intervention (fiches de la GMAO exportées en « champ : valeur ») |
| `Corpus_evaluation_RAG.xlsx` | le fichier du métier rempli : 50 documents, 60 questions, 97 passages, 20 pages OCR retapées |
| `questions_pour_relecture.md` | les 60 questions, sur une page, pour relecture |
| `fabrication/` | de quoi tout refabriquer : le monde fictif, les contenus JSON, les scripts |
| `ontologie/` | ontologie et règles SHACL (étape 9) |

## Ce que le corpus couvre

| Cas du document 1 | Dans le corpus |
| --- | --- |
| Types de documents | 3 types, au moins 16 documents par type (2 choisis par le métier, les autres « tirés au hasard ») |
| Formats | PDF natif, PDF scanné (5 notes de 4 pages), fiche de base de données |
| Éléments | texte, tableaux, schémas avec figure numérotée (PR-1101, PR-1111, NT-057, NT-058), texte scanné |
| Droits | 4 documents réservés au profil « Maintenance » (PR-1102, NT-051, OT-24109, OT-24114) |
| Versions | PR-1104-B (2021) remplacée par PR-1104-C (2025), avec des valeurs différentes |
| Questions | 60 : 10 sans réponse, 19 à plusieurs passages, 6 synthèses, 7 avec un profil restreint dont 3 « non accessible », 6 questions de suite, 6 variantes, 6 avec passage piège (ancienne version, autre ouvrage), 20 réservées à la décision ; fréquences et gravités variées |
| Pages OCR | les 20 pages des 5 notes scannées, retapées |

## Refabriquer le corpus

```bash
uv run --group fabrication python corpus_exemple/fabrication/fabriquer_pdf.py
```

```bash
uv run python corpus_exemple/fabrication/remplir_excel.py
```

Le premier script dessine les PDF à partir de `fabrication/contenus/*.json` ; le second vérifie chaque passage de `fabrication/questions.yaml` contre sa source (texte copié de la bonne page, ligne de tableau, schéma présent, valeur du champ d'une fiche), remplit le fichier Excel et recalcule le tableau de bord.

## Conventions d'annotation retenues

| Point | Convention |
| --- | --- |
| Fiche de base de données | « Page » = nom du champ (par exemple « Pièces remplacées ») ; « Passage » = la valeur, ou la partie de la valeur qui répond ; type d'élément « Texte » |
| Tableau | ligne d'en-têtes puis ligne qui répond, cellules séparées par « \| » |
| Schéma | une phrase qui dit ce que montre la figure, avec son numéro (« Figure 1 : … ») ; certaines valeurs ne figurent que sur le schéma (NT-057, NT-058) |
| Question non accessible | posée avec le profil « Exploitation » sur un document réservé à « Maintenance » ; la réponse attendue est que le RAG ne donne pas l'information |
| Pages OCR | tout ce qu'on lit sur la page, en-tête et pied de page compris, dans l'ordre de lecture |
