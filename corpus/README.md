# Partie 1 — Le corpus annoté, et comment y brancher un RAG

Ce dossier répond à deux questions.

1. **Comment le métier construit-il le corpus d'évaluation, et comment le charge-t-on dans le kit ?**
2. **Que doit faire un RAG pour être évalué ?** Quels fichiers il reçoit, et quels fichiers il doit rendre : c'est le *contrat*.

```
corpus/
├── contrat/
│   ├── CONTRAT.md          le contrat, champ par champ (document de référence)
│   └── schemas/            un schéma JSON par fichier du contrat : sert à kit verifier-contrat
└── exemple/                un corpus complet et fictif, prêt à l'emploi (voir exemple/README.md)
    ├── sources/            les 50 documents PDF
    ├── Corpus_evaluation_RAG.xlsx   le fichier du métier, rempli
    └── fabrication/        les scripts qui ont fabriqué l'exemple
```

## 1. Le corpus : ce que le métier remplit

Le corpus est **un fichier Excel**, sur le modèle [`docs/Corpus_evaluation_RAG.xlsx`](../docs/Corpus_evaluation_RAG.xlsx). Les règles complètes sont dans le [document 1](../docs/RAG_1_Constituer_le_corpus_d_evaluation.md). En résumé :

| Feuille | Une ligne = | L'essentiel |
| --- | --- | --- |
| Documents | un document retenu | sa référence dans la source, sa version, son format, ses **droits d'accès**, s'il est **en vigueur** |
| Questions | une question | écrite avec les mots des utilisateurs ; le **profil** qui la pose ; la **réponse attendue** et ses **points clés** ; si la réponse est dans les documents (oui, non, non accessible à ce profil) ; **fréquence** et **gravité** d'une erreur ; **réservée à la décision** ou non |
| Passages | un endroit où se trouve la réponse | le document, la **page**, le type d'élément (texte, tableau, texte scanné, image), le passage **copié-collé**, s'il répond entièrement, en partie, ou si c'est un **piège** |
| Pages OCR | une page scannée de référence | le texte retapé à la main ; sert à mesurer la qualité de l'OCR du RAG |
| Tableau de bord | — | se calcule tout seul ; doit être « OK » partout avant de transmettre le fichier |

**Pourquoi le passage exact ?** Parce que le kit doit pouvoir dire si le RAG a bien *indexé* ce passage (niveau 1), s'il l'a *retrouvé* (niveau 2), et seulement ensuite si la réponse est juste (niveau 3). Sans passage, on ne sait pas d'où vient une erreur.

**Pourquoi des questions réservées ?** Un tiers des questions ne sert jamais à régler le RAG. Elles servent à décider de la mise en production. L'équipe technique n'en voit que les scores globaux : c'est ce qui évite de régler le RAG « pour le test ».

Le corpus d'exemple (`exemple/`) couvre tous les cas du document 1 : 50 documents dont 5 scannés, 60 questions (10 sans réponse, 7 avec un profil restreint, 6 pièges, 6 questions de suite, 6 variantes, 6 synthèses), 20 pages OCR. Détails : [exemple/README.md](exemple/README.md).

## 2. L'import : du fichier Excel au corpus standard

```bash
uv run kit importer corpus/exemple/Corpus_evaluation_RAG.xlsx
```

L'import fait, dans l'ordre :

1. **Les contrôles** ([CONTRAT.md](contrat/CONTRAT.md), section 2). Il signale une colonne obligatoire vide, une valeur hors liste, un passage dont le document n'existe pas, un identifiant de question en double, une question « oui » sans passage, une question « non accessible » sans document interdit… **Une seule ligne fausse bloque tout l'import.** Le message donne la feuille, la ligne et la correction attendue, par exemple :
   ```
   Import refusé : 1 ligne(s) à corriger dans Corpus_evaluation_RAG.xlsx.
     - feuille Questions, ligne 2 (Q-001) : « Exploit » n'est pas dans la colonne « Profils d'accès » de la feuille Listes (Tous les utilisateurs, Maintenance, Exploitation).
   ```
   Si la configuration minimale du document 1 n'est pas atteinte (moins de 50 questions…), l'import passe avec un avertissement.
2. **La conversion** des libellés du métier en codes : « PDF scanné » devient `pdf_scanne`, « Tous les utilisateurs » devient `tous`.
3. **L'écriture dans la base** (`sorties/base.sqlite`, ou PostgreSQL en changeant l'adresse dans `evaluation/config/kit.yaml`).
4. **L'export** du corpus standard dans `sorties/corpus/<version_corpus>/` : `corpus.json`, `documents.jsonl`, `questions.jsonl`, `passages.jsonl`, `pages_ocr.jsonl`.
5. **Le jeu de questions dans Langfuse** : `corpus-<projet>-<version_corpus>`, un élément par question.

La **version du corpus** (`2026-11-20.1`) change à chaque import d'un fichier modifié. Réimporter le même fichier ne crée rien. Deux évaluations ne se comparent que sur la même version du corpus.

## 3. Brancher un RAG : le contrat

Le kit ne connaît pas le RAG. Pour être évalué, un RAG doit seulement **lire des fichiers et en écrire d'autres**, au format du contrat. Le détail champ par champ est dans [contrat/CONTRAT.md](contrat/CONTRAT.md).

### Ce que le RAG reçoit

| Fichier | Ce que le RAG en fait |
| --- | --- |
| les documents (`corpus/exemple/sources/` ici ; vos sources réelles ailleurs) | il les indexe comme en production |
| `sorties/corpus/<version>/documents.jsonl` | le catalogue : pour chaque document, sa référence, sa version, ses droits d'accès, son format. Le RAG doit garder ces métadonnées sur chaque chunk |
| `sorties/corpus/<version>/questions.jsonl` | les questions à poser. Le RAG ne lit que `question_id`, `question`, `profil` et, pour une question de suite, la question précédente et sa réponse attendue (l'historique). **Il ne lit jamais les réponses attendues, les points clés ni les passages** |

### Ce que le RAG doit rendre

Le RAG écrit un dossier par version, `sorties/sorties_rag/<version_rag>/` :

| Fichier | Une ligne = | Sert au niveau | Obligatoire |
| --- | --- | --- | --- |
| `rag.json` | la version évaluée : nom, type, k, versions de l'index, du modèle, du prompt… | tous | oui |
| `chunks.jsonl` | un chunk de l'index, **avec la référence, la version, la page, le type d'élément et les droits du document** | 1 | oui |
| `pages_extraites.jsonl` | une page telle que lue par l'extraction, avant découpage | 1 (OCR) | si des documents sont scannés |
| `graphe.ttl` | le graphe, en RDF | 1 | si le RAG utilise un graphe |
| `recherches.jsonl` | une question : les k chunks retrouvés, dans l'ordre | 2 | oui |
| `reponses.jsonl` | une question : la réponse, **si le RAG s'abstient**, les chunks cités, les chunks donnés au modèle, la durée, le coût, l'identifiant de trace | 3 et 4 | oui |

### Les règles d'appel

| Règle | Pourquoi |
| --- | --- |
| chaque question est posée **avec son profil**, et la recherche applique les droits de ce profil | tester les droits d'accès : un document interdit ne doit jamais remonter |
| une question de suite reçoit en historique la question précédente **et sa réponse attendue** | évaluer la question de suite seule, sans hériter d'une erreur |
| **le même k** pour toutes les questions | comparer les questions entre elles |
| **toutes** les questions sont posées, y compris les réservées | seul l'affichage des résultats diffère |
| le RAG dit lui-même s'il s'abstient (champ `abstention`) | mesurer l'abstention sans deviner à partir du texte |

### Deux façons de produire ces fichiers

| Façon | Comment | Pour qui |
| --- | --- | --- |
| **Par fichiers** | le RAG lit `questions.jsonl` et écrit lui-même les fichiers ci-dessus | tout RAG, quel que soit son langage |
| **Par connecteur** | le RAG fournit un objet Python avec six méthodes ; le kit les appelle et écrit les fichiers | un RAG en Python |

Le connecteur, à copier (exemple complet : [`rag/rag_demo/connecteur.py`](../rag/rag_demo/connecteur.py)) :

```python
class Connecteur:
    def decrire(self) -> dict: ...                      # le contenu de rag.json
    def exporter_index(self): ...                       # itérable des chunks (chunks.jsonl)
    def exporter_pages(self): ...                       # itérable des pages extraites, ou None
    def exporter_graphe(self, chemin): ...              # écrit graphe.ttl, ou ne fait rien
    def rechercher(self, question, profil, historique): ...  # [{"chunk_id", "rang", "score"}, …]
    def repondre(self, question, profil, historique): ...    # un objet de reponses.jsonl, sans question_id
```

```bash
uv run kit lancer mon_rag.connecteur:Connecteur --corpus sorties/corpus/2026-11-20.1
```

Le connecteur ne doit rien importer du kit : le kit l'appelle par le nom de ses méthodes.

### Vérifier le branchement

Avant toute évaluation, le kit vérifie les fichiers du RAG contre les schémas de `contrat/schemas/`. Il dit **précisément ce qui manque**, fichier par fichier et ligne par ligne :

```bash
uv run kit verifier-contrat sorties/sorties_rag/rag-demo-k5-80032dcd --corpus sorties/corpus/2026-11-20.1
```

```
sorties/sorties_rag/mon-rag : 3 problème(s).
  - reponses.jsonl, ligne 3 : champ obligatoire « abstention » absent.
  - rag.json : champ(s) inconnu(s) du contrat : 'temperature'.
  - recherches.jsonl, Q-007 : posée avec le profil « tous » au lieu de « exploitation ».
```

Quand la commande répond « conforme au contrat », le RAG est branché : on passe à [l'évaluation](../evaluation/README.md).
