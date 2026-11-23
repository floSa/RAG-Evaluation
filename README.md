# Évaluer un RAG de bout en bout

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-0.12.17-DE5FE9?logo=uv&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker_Compose-v5.7-2496ED?logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.165-009688?logo=fastapi&logoColor=white)
![Langfuse](https://img.shields.io/badge/Langfuse-4.83-0A0A0A)
![Ragas](https://img.shields.io/badge/Ragas-0.4.4-6E44FF)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.1-D71F00?logo=sqlalchemy&logoColor=white)
![Docling Serve](https://img.shields.io/badge/Docling_Serve-1.38.2-1F6FEB)
![rdflib](https://img.shields.io/badge/rdflib-7.6-4B8BBE)
![pySHACL](https://img.shields.io/badge/pySHACL-0.40-4B8BBE)
![Modèles](https://img.shields.io/badge/mod%C3%A8les-API_compatible_OpenAI-412991?logo=openai&logoColor=white)

Un **RAG** est un assistant qui répond à des questions en s'appuyant sur des documents : il les découpe en morceaux de texte, retrouve les morceaux utiles à une question, puis fait écrire la réponse par un modèle de langage.

Ce dépôt donne un **service qui évalue n'importe quel RAG** à partir d'un **corpus annoté** : des documents, et un fichier Excel où le métier a écrit des questions, leur bonne réponse, et l'endroit exact des documents où elle se trouve. Le service mesure ce que le RAG fait bien et mal, et l'écrit en phrases simples ; c'est le métier qui décide, à leur lecture, si le RAG peut partir en production.

**Commencez ici : [le fil conducteur](service-evaluation/FIL_CONDUCTEUR.md)**, qui dit dans l'ordre ce qu'on fait, pourquoi, et ce que ça a donné sur l'exemple, de l'installation à la lecture des résultats.

Il s'adresse à la personne qui prend en charge l'évaluation : data scientist, chef de projet technique, quelqu'un qui sait lire un dépôt et lancer des commandes. C'est elle qui fait tout. Le métier ne fait que fournir le corpus annoté, selon les règles qu'elle lui transmet, puis décider à la lecture des scores.

## Les trois dossiers

| Dossier | Ce que c'est | Pour qui |
| --- | --- | --- |
| [`service-evaluation/`](service-evaluation/README.md) | **le service d'évaluation, vierge** : à prendre pour votre projet | ceux qui veulent évaluer leur RAG |
| [`service-rag-exemple/`](service-rag-exemple/README.md) | **un RAG simple**, qui sert d'exemple à évaluer : il montre comment un RAG se branche sur le service | ceux qui veulent voir comment brancher un RAG |
| [`service-evaluation-exemple/`](service-evaluation-exemple/README.md) | **le service une fois qu'il a tourné sur ce RAG** : le même dossier que `service-evaluation/`, rempli, avec tous les résultats | ceux qui veulent voir à quoi ressemblent les résultats, sans rien installer |

## Par où commencer

| Je veux… | Aller à |
| --- | --- |
| comprendre comment fonctionne l'évaluation, et ce qu'il faut faire dans l'ordre | [le fil conducteur](service-evaluation/FIL_CONDUCTEUR.md) |
| voir à quoi ressemblent les résultats, sans rien installer | [`service-evaluation-exemple/`](service-evaluation-exemple/README.md) |
| faire tourner le service sur le RAG d'exemple | lancer le [RAG d'exemple](service-rag-exemple/README.md#le-lancer), puis suivre [le service d'évaluation](service-evaluation/README.md#essayer-avec-le-corpus-dexemple) |
| évaluer mon RAG, sur mes documents | [le fil conducteur](service-evaluation/FIL_CONDUCTEUR.md), étape par étape |
| comprendre la méthode | le [document 3](service-evaluation/documentation/methode_et_contrat/methode_evaluation.md), sections 1 à 5, puis le [document 1](service-evaluation/documentation/methode_et_contrat/methode_corpus_annote.md) |
| savoir pourquoi un choix a été fait | [DECISIONS.md](DECISIONS.md) |

Il faut Docker, [uv](https://docs.astral.sh/uv/), et un accès à des modèles de langage par une API compatible OpenAI. Ici, le service LLM-Service, à http://127.0.0.1:8080 ; avec un autre fournisseur, on change l'adresse et les noms des modèles dans [`service-evaluation/config/kit.yaml`](service-evaluation/config/kit.yaml) et [`service-rag-exemple/config/config.yaml`](service-rag-exemple/config/config.yaml), sans toucher au code.
