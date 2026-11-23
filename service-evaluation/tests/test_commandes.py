"""Tests de la ligne de commande : sans --corpus ni --rag, le kit prend le dossier le plus récent."""

import os

import pytest
import typer

from kit.commandes import le_plus_recent


def test_le_plus_recent(tmp_path, capsys):
    config = {"chemins": {"resultats": str(tmp_path)}}
    for nom, date in (("2026-11-20.1", 1_000), ("2026-11-21.1", 2_000), ("vide", 3_000)):
        dossier = tmp_path / "corpus" / nom
        dossier.mkdir(parents=True)
        if nom != "vide":                      # un dossier vide n'est pas un corpus
            (dossier / "questions.jsonl").write_text("{}", encoding="utf-8")
            os.utime(dossier / "questions.jsonl", (date, date))
    assert le_plus_recent(config, "corpus").name == "2026-11-21.1"
    assert "--corpus" in capsys.readouterr().out    # le dossier choisi est affiché


def test_rien_a_evaluer(tmp_path):
    with pytest.raises(typer.Exit):
        le_plus_recent({"chemins": {"resultats": str(tmp_path)}}, "reponses_du_rag")
