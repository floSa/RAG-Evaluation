"""Le nom du dossier d'une comparaison reste court : Windows refuse les chemins de plus de 260 caractères."""

import pytest

from kit.etape_5_resultats.comparaison import nom_dossier


def comparaison(va: str, vb: str, corpus: str = "2026-11-20.1") -> dict:
    return {"a": f"{corpus}_{va}", "b": f"{corpus}_{vb}", "rag_a": {"version_rag": va}, "rag_b": {"version_rag": vb}}


@pytest.mark.parametrize("va, vb, attendu", [
    # les deux comparaisons du corpus d'exemple
    ("rag-exemple-vectoriel-k5-5954e822", "rag-exemple-vectoriel-k3-5954e822", "2026-11-20.1_k5-5954e822_contre_k3-5954e822"),
    ("rag-exemple-vectoriel-k5-5954e822", "rag-exemple-vectoriel-k5-94d362c8", "2026-11-20.1_k5-5954e822_contre_k5-94d362c8"),
    # deux RAG sans début commun : les noms restent entiers
    ("rag-a-k5", "autre-b-k5", "2026-11-20.1_rag-a-k5_contre_autre-b-k5"),
])
def test_nom_dossier(va, vb, attendu):
    assert nom_dossier(comparaison(va, vb)) == attendu


def test_chemin_court():
    r = comparaison("rag-exemple-vectoriel-k5-5954e822", "rag-exemple-vectoriel-k3-5954e822")
    chemin = f"service-evaluation-exemple/resultats/comparaisons_de_configurations/{nom_dossier(r)}/fichiers_techniques/comparaison.json"
    assert len(chemin) < 150
