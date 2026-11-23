"""Séparation stricte : le service d'évaluation n'importe rien d'un RAG.

Il ne parle à un RAG que par ses endpoints d'évaluation, à une adresse web (src/kit/appel_du_rag/), ou par des fichiers.
"""

import ast
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / "src" / "kit"


def modules_importes(dossier: Path) -> set[str]:
    """Rend le premier nom de chaque module importé par les fichiers Python du dossier."""
    noms = set()
    for fichier in dossier.rglob("*.py"):
        for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
            if isinstance(noeud, ast.Import):
                noms.update(a.name.split(".")[0] for a in noeud.names)
            elif isinstance(noeud, ast.ImportFrom) and noeud.module and noeud.level == 0:
                noms.add(noeud.module.split(".")[0])
    return noms


def test_le_kit_n_importe_aucun_rag():
    assert "rag" not in modules_importes(KIT)
