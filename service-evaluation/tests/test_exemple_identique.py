"""service-evaluation-exemple/ est le même service que service-evaluation/, qui a en plus tourné sur le RAG d'exemple.

Le code, les guides, les tests et les fichiers d'installation doivent donc être identiques dans les deux dossiers.
Seuls diffèrent ce que le service remplit en tournant : config/, corpus_annote/, resultats/, et le README.
"""

from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SERVICE, EXEMPLE = RACINE / "service-evaluation", RACINE / "service-evaluation-exemple"
COMMUNS = ["FIL_CONDUCTEUR.md", "AGENTS.md", "CLAUDE.md", "src", "tests", "documentation", "endpoints_a_copier", ".env.example", ".python-version",
           "docker-compose.yml", "initialiser.sh", "pyproject.toml", "uv.lock"]
IGNORES = {"__pycache__", ".pytest_cache"}


def fichiers(dossier: Path) -> dict[str, bytes]:
    if dossier.is_file():
        return {"": dossier.read_bytes()}
    return {f.relative_to(dossier).as_posix(): f.read_bytes() for f in sorted(dossier.rglob("*"))
            if f.is_file() and not IGNORES & set(f.parts)}


def test_l_exemple_a_le_meme_code_et_les_memes_guides_que_le_service():
    differences = []
    for nom in COMMUNS:
        a, b = fichiers(SERVICE / nom), fichiers(EXEMPLE / nom)
        differences += [f"{nom}/{f}" for f in sorted(set(a) | set(b)) if a.get(f) != b.get(f)]
    assert differences == [], ("Copier ces fichiers de service-evaluation/ vers service-evaluation-exemple/ : "
                               + ", ".join(differences))
