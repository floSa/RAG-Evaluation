"""La porte d'évaluation : la SEULE partie du RAG écrite pour le service d'évaluation.

Le service d'évaluation impose à tout RAG quatre portes, de forme fixe, à une adresse web
(service-evaluation/documentation/0b_porte_du_rag.md). Ce dossier les ouvre pour le RAG d'exemple :

    ingerer.py         ENTRÉE   l'évaluation envoie ses documents ; le RAG les indexe à part de la production
    montrer_index.py   SORTIE   ce que le RAG a lu et découpé, et sa version exacte
    rechercher.py      ENTRÉE une question  → SORTIE les k morceaux retrouvés
    repondre.py        ENTRÉE une question  → SORTIE la réponse, ses sources, l'abstention, la trace
    adresse_web.py     les quatre portes, ouvertes à http://127.0.0.1:8100 (commande « rag ouvrir-porte »)

La règle : ce dossier se sert du RAG (rag.assistant, rag.pipeline), jamais l'inverse.
Si on le supprime, le RAG marche toujours en production.
"""

ESPACE = "evaluation"   # l'index des documents de l'évaluation, à part de la production : sorties/evaluation/
