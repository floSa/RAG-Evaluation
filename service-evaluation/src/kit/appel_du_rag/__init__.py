"""Appel du RAG : le seul endroit du kit qui parle à un RAG.

    appeler.py   appelle les quatre endpoints du RAG à son adresse web (ingérer, montrer l'index, rechercher, répondre),
                 et range ce qu'il rend dans resultats/reponses_du_rag/<version_rag>/

Ces fichiers sont ensuite vérifiés par kit/contrat.py. La règle que chaque RAG doit suivre : documentation/0b_endpoints_du_rag.md.
"""
