"""The old import names and commands keep working and point at their replacements (#45)."""

from __future__ import annotations

import subprocess
import sys

import py_doc
import pydoc2docx
from pydoc2docx.cli import main as old_main
from pydoc2docx.converter import DocxConverter as OldConverter
from py_doc.cli import main


def test_old_import_names_are_the_same_objects():
    assert pydoc2docx.DocxConverter is py_doc.DocxConverter
    assert pydoc2docx.ConversionError is py_doc.ConversionError
    assert OldConverter is py_doc.DocxConverter
    assert old_main is main
    assert pydoc2docx.__version__ == py_doc.__version__


def test_old_module_entry_point_still_runs():
    result = subprocess.run(
        [sys.executable, "-m", "pydoc2docx.cli", "--help"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "Markdown" in result.stdout


# --- the legacy test suites of py-doc2slides and py-doclint, kept as they were ---------------------


def test_legacy_slides_converter_test(tmp_path):
    from pydoc2slides import SlidesConverter

    md_file = tmp_path / "deck.md"
    md_file.write_text(
        "# Project Architecture\nOverview of the system.\n\n---\n\n## Core Modules\n- Module A\n- Module B\n\n```python\nimport sys\n```"
    )
    res = SlidesConverter().convert_file(md_file, tmp_path / "deck.pptx")
    assert res.exists() and res.stat().st_size > 0


def test_legacy_linter_test(tmp_path):
    from pydoclint import DocLinter

    md_file = tmp_path / "test.md"
    md_file.write_text("We use lwm2m over dtls for communications in order to save power.")
    issues = DocLinter().lint_file(md_file)
    assert len(issues) >= 3
    categories = [i.category for i in issues]
    assert "Glossary" in categories and "Style" in categories


def test_old_import_names_for_slides_and_lint_are_the_new_objects():
    import pydoc2slides
    import pydoc2slides.cli
    import pydoc2slides.converter
    import pydoclint
    import pydoclint.cli
    import pydoclint.linter
    from py_doc.lint.cli import main as lint_main
    from py_doc.slides_cli import main as slides_main

    assert pydoc2slides.SlidesConverter is py_doc.SlidesConverter is pydoc2slides.converter.SlidesConverter
    assert pydoc2slides.cli.main is slides_main
    assert pydoclint.cli.main is lint_main
    assert pydoclint.linter.DocLinter is pydoclint.DocLinter
    assert pydoclint.__version__ == pydoc2slides.__version__ == py_doc.__version__


class TestLegacyLinterInterface:
    def test_issue_has_the_old_shape(self, tmp_path):
        from pathlib import Path

        from pydoclint import DocLinter, LintIssue

        md = tmp_path / "a.md"
        md.write_text("Fine.\n\nWe use dtls here.\n", encoding="utf-8")
        [issue] = DocLinter().lint_file(md)
        assert isinstance(issue, LintIssue)
        assert (issue.file, issue.line_no, issue.category, issue.severity) == (Path(md).resolve(), 3, "Glossary", "warning")
        assert repr(issue).startswith("[WARNING] a.md:3 [Glossary] ")

    def test_missing_file_gives_no_issues_like_before(self, tmp_path):
        from pydoclint import DocLinter

        assert DocLinter().lint_file(tmp_path / "gone.md") == []

    def test_custom_glossary_replaces_the_default(self, tmp_path):
        from pydoclint import DocLinter

        md = tmp_path / "a.md"
        md.write_text("We run k8s and dtls.\n", encoding="utf-8")
        issues = DocLinter({"Kubernetes": ["k8s"]}).lint_file(md)
        assert [i.message for i in issues if i.category == "Glossary"] and all("dtls" not in i.message for i in issues)

    def test_directory_result_maps_paths_to_issues_and_leaves_clean_files_out(self, tmp_path):
        from pydoclint import DocLinter

        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "bad.md").write_text("We use dtls.\n", encoding="utf-8")
        (tmp_path / "good.markdown").write_text("All fine.\n", encoding="utf-8")
        results = DocLinter().lint_directory(tmp_path)
        assert list(results) == [str((tmp_path / "sub" / "bad.md").resolve())]
        assert DocLinter().lint_directory(tmp_path / "nope") == {}


class TestRenameNotice:
    def test_legacy_commands_say_where_they_went(self, tmp_path, capsys):
        from py_doc.cli import run_docx
        from py_doc.lint.cli import run
        from py_doc.slides_cli import run_slides

        md = tmp_path / "a.md"
        md.write_text("# A\n", encoding="utf-8")
        assert run_docx([str(md)], legacy=True) == 0
        assert "py-doc2docx is now part of py-doc. `py-doc docx` does the same" in capsys.readouterr().err
        assert run_slides([str(md)], legacy=True) == 0
        assert "`py-doc slides` does the same" in capsys.readouterr().err
        run([str(md)], legacy=True)
        assert "`py-doc lint` does the same" in capsys.readouterr().err

    def test_new_commands_stay_quiet_about_it(self, tmp_path, capsys):
        from py_doc.app import main

        md = tmp_path / "a.md"
        md.write_text("# A\n", encoding="utf-8")
        for command in ("docx", "slides", "lint"):
            main([command, str(md)])
        assert "is now part of py-doc" not in capsys.readouterr().err

    def test_quiet_hides_the_notice(self, tmp_path, capsys):
        from py_doc.cli import run_docx

        md = tmp_path / "a.md"
        md.write_text("# A\n", encoding="utf-8")
        run_docx([str(md), "-q"], legacy=True)
        assert capsys.readouterr().err == ""

    def test_real_legacy_entry_points_show_the_notice(self, tmp_path):
        md = tmp_path / "a.md"
        md.write_text("# A\n", encoding="utf-8")
        for module in ("pydoc2docx", "pydoc2slides"):
            result = subprocess.run([sys.executable, "-m", module, str(md)], capture_output=True, text=True, check=False)
            assert result.returncode == 0 and "is now part of py-doc" in result.stderr, module
