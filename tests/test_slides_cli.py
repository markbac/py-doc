"""Integration tests for the py-doc2slides command line."""

from __future__ import annotations

import subprocess
import sys

import pytest
from pptx import Presentation
from pptx_helpers import titles
from py_doc.slides_cli import main


def run_cli(monkeypatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["py-doc2slides", *args])
    main()


@pytest.fixture
def deck_md(tmp_path):
    path = tmp_path / "deck.md"
    path.write_text("# Deck\n\n## One\n\n- a\n\n## Two\n\n- b\n", encoding="utf-8")
    return path


def test_converts_next_to_the_input_by_default(deck_md, tmp_path, monkeypatch):
    run_cli(monkeypatch, str(deck_md))
    assert titles(tmp_path / "deck.pptx") == ["Deck", "One", "Two"]


def test_output_naming_a_directory_gets_the_file_inside(deck_md, tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    run_cli(monkeypatch, str(deck_md), "-o", str(out))
    assert (out / "deck.pptx").exists()


def test_split_level_option_is_applied(deck_md, tmp_path, monkeypatch):
    run_cli(monkeypatch, str(deck_md), "--split-level", "1")
    assert titles(tmp_path / "deck.pptx") == ["Deck"]


def test_split_level_out_of_range_is_a_usage_error(deck_md, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, str(deck_md), "--split-level", "9")
    assert exc.value.code == 2


@pytest.mark.parametrize("flag", ["-t", "--template", "-r", "--reference"])
def test_template_and_its_old_names(flag, deck_md, tmp_path, monkeypatch):
    template = tmp_path / "t.pptx"
    prs = Presentation()
    prs.core_properties.title = "kept"
    prs.save(str(template))
    run_cli(monkeypatch, str(deck_md), flag, str(template), "-o", str(tmp_path / "x.pptx"))
    assert Presentation(str(tmp_path / "x.pptx")).core_properties.title == "kept"


def test_missing_template_exits_1_on_stderr(deck_md, tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, str(deck_md), "-t", str(tmp_path / "gone.pptx"))
    assert exc.value.code == 1
    assert "template not found" in capsys.readouterr().err.lower()
    assert not (tmp_path / "deck.pptx").exists()


def test_allow_missing_template_falls_back(deck_md, tmp_path, monkeypatch):
    run_cli(monkeypatch, str(deck_md), "-t", str(tmp_path / "gone.pptx"), "--allow-missing-template")
    assert (tmp_path / "deck.pptx").exists()


def test_unknown_layout_name_fails_that_file_with_status_1(deck_md, tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, str(deck_md), "--content-layout", "Nope")
    assert exc.value.code == 1
    assert "no layout named 'Nope'" in capsys.readouterr().err


def test_batch_continues_after_a_bad_file(tmp_path, monkeypatch, capsys):
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.md").write_text("# A\n", encoding="utf-8")
    (root / "b.md").write_bytes(b"caf\xe9\n")
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, str(root), "-o", str(tmp_path / "dist"))
    assert exc.value.code == 1
    assert "1 of 2 file(s) converted to PowerPoint, 1 failed" in capsys.readouterr().err
    assert (tmp_path / "dist" / "a.pptx").exists()


def test_version(monkeypatch, capsys):
    import py_doc

    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, "--version")
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"py-doc2slides {py_doc.__version__}"


def test_module_entry_point_prints_help():
    result = subprocess.run(
        [sys.executable, "-m", "py_doc.slides_cli", "--help"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "PowerPoint" in result.stdout
