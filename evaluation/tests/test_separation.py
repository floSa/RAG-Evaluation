"""Séparation stricte : le kit n'importe rien du RAG, et le RAG n'importe rien du kit.

Ils ne se parlent que par les fichiers du contrat, ou par le connecteur que le kit charge par son nom
(rag/branchement_evaluation.py).
"""

import ast
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def modules_importes(dossier: str) -> set[str]:
    """Rend le premier nom de chaque module importé par les fichiers Python du dossier."""
    noms = set()
    for fichier in (RACINE / dossier).rglob("*.py"):
        for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
            if isinstance(noeud, ast.Import):
                noms.update(a.name.split(".")[0] for a in noeud.names)
            elif isinstance(noeud, ast.ImportFrom) and noeud.module and noeud.level == 0:
                noms.add(noeud.module.split(".")[0])
    return noms


def test_le_kit_n_importe_pas_le_rag():
    assert "rag" not in modules_importes("evaluation/kit")


def test_le_rag_n_importe_pas_le_kit():
    assert "kit" not in modules_importes("rag")
