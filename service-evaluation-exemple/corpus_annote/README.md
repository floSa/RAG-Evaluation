# Notre corpus annoté

Le corpus de l'exemple : la maintenance électrique d'une entreprise **entièrement fictive**, Valtéra Industries. Aucune donnée réelle.

| Élément | À quoi il sert |
| --- | --- |
| [`corpus_documentaire/`](corpus_documentaire/) | les 50 documents : 17 procédures, 16 notes techniques dont 5 scannées, 17 comptes rendus d'intervention exportés d'une base de données |
| [`Corpus_evaluation_RAG.xlsx`](Corpus_evaluation_RAG.xlsx) | le fichier du métier, rempli : 60 questions avec leur bonne réponse, 97 passages, 20 pages scannées retapées |
| [`questions_pour_relecture.md`](questions_pour_relecture.md) | les 60 questions sur une page, pour les relire |
| [`ontologie/`](ontologie/) | l'ontologie du domaine (sites, équipements, personnes et leurs liens) et ses règles, pour le RAG à graphe |
| [`notes_du_metier_simulees/`](notes_du_metier_simulees/) | banc d'essai seulement : ce que le métier aurait noté, joué par Claude |
| [`fabrication_du_corpus/`](fabrication_du_corpus/) | banc d'essai seulement : de quoi refabriquer les documents fictifs et le fichier Excel |

Ce que couvre ce corpus, et comment il a été annoté : [guide 0a](../../service-evaluation/documentation/0a_construction_du_corpus.md#2-le-corpus-dexemple-prêt-à-lemploi).
