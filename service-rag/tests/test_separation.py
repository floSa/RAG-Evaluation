"""Séparation stricte : le RAG n'importe rien du service d'évaluation, et seule sa porte parle de l'évaluation."""

import ast
from pathlib import Path

RAG = Path(__file__).resolve().parents[1] / "src" / "rag"


def modules_importes(fichiers) -> set[str]:
    noms = set()
    for fichier in fichiers:
        for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
            if isinstance(noeud, ast.Import):
                noms.update(a.name for a in noeud.names)
            elif isinstance(noeud, ast.ImportFrom) and noeud.module and noeud.level == 0:
                noms.add(noeud.module)
    return noms


def test_le_rag_n_importe_pas_le_kit():
    assert not any(m.split(".")[0] == "kit" for m in modules_importes(RAG.rglob("*.py")))


def test_le_rag_ne_depend_pas_de_sa_porte():
    """Si on supprime porte_evaluation/, le RAG marche toujours en production."""
    hors_porte = [f for f in RAG.rglob("*.py") if "porte_evaluation" not in f.parts]
    assert not any("porte_evaluation" in m for m in modules_importes(hors_porte))
