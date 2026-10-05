"""py-doc migrate: representative createdocs projects, the report, and the files it writes."""

from __future__ import annotations

import sys

import pytest
import yaml
from py_doc.app import main
from py_doc.config import load_config
from py_doc.migrate import migrate, read_createdocs, render


def write(path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path):
    """Two guides in different folders sharing a template, one guide built from several files,
    a shared chapter used by two documents, and YAML that is not a build file."""
    write(tmp_path / "templates" / "T.docx", "x")
    write(tmp_path / "docs" / "shared" / "intro.md", "# Intro\n")
    write(tmp_path / "docs" / "guidelines" / "GU-1.md", "# One\n")
    write(
        tmp_path / "docs" / "guidelines" / "GU-1.yaml",
        """
meta: {title: One, author: Ann, doc_number: GU-1, version: "1.0.1", status: Proposed}
cli:
  emit-docx: true
  emit-pdf: true
  output: ../../build/guidelines/GU-1.docx
  template: ../../templates/T.docx
  plantuml-jar-path: ../../templates/plantuml.jar
entries:
  - {file: GU-1.md, heading_offset: 0, page_break: false}
  - {file: ../shared/intro.md}
""",
    )
    for name in ("one.md", "two.md", "three.md"):
        write(tmp_path / "docs" / "guides" / "big" / name, f"# {name}\n")
    write(
        tmp_path / "docs" / "guides" / "big" / "big.yaml",
        """
meta: {title: Big, document_number: GD-9, date: 2026-09-20}
cli:
  emit-docx: true
  output: ../../../build/guides/big.docx
  template: ../../../templates/T.docx
entries:
  - {file: one.md}
  - {file: two.md, heading_offset: 1, page_break: true, title: Second}
  - {file: three.md, include: false}
  - {file: ../../shared/intro.md, extra_key: 1}
variables: {product: Widget}
""",
    )
    write(tmp_path / "mkdocs.yml", "site_name: Docs\n")
    write(tmp_path / ".github" / "workflows" / "ci.yml", "on: push\n")
    return tmp_path


def test_each_build_file_becomes_one_document_with_its_own_sources(repo):
    result = migrate([repo / "docs"], repo)
    docs = result.config["documents"]
    assert list(docs) == ["GU-1", "big"]
    assert [s["file"] for s in docs["GU-1"]["sources"]] == ["docs/guidelines/GU-1.md", "docs/shared/intro.md"]
    assert docs["big"]["sources"] == [
        {"file": "docs/guides/big/one.md"},
        {"file": "docs/guides/big/two.md", "heading_offset": 1, "title": "Second", "page_break": True},
        {"file": "docs/guides/big/three.md", "include": False},
        {"file": "docs/shared/intro.md"},
    ]


def test_properties_and_aliases_are_carried_over(repo):
    docs = migrate([repo / "docs"], repo).config["documents"]
    assert docs["GU-1"]["document_number"] == "GU-1"
    assert "doc_number" not in docs["GU-1"]
    assert docs["GU-1"]["version"] == "1.0.1" and docs["GU-1"]["status"] == "Proposed"
    assert str(docs["big"]["date"]) == "2026-09-20"


def test_output_paths_keep_their_place_relative_to_the_new_file(repo):
    docs = migrate([repo / "docs"], repo).config["documents"]
    assert docs["GU-1"]["outputs"]["docx"]["path"] == "build/guidelines/GU-1.docx"
    assert docs["big"]["outputs"]["docx"]["path"] == "build/guides/big.docx"


def test_a_template_every_document_uses_is_set_once(repo):
    result = migrate([repo / "docs"], repo)
    assert result.config["outputs"] == {"docx": {"template": "templates/T.docx"}}
    assert all("template" not in d["outputs"]["docx"] for d in result.config["documents"].values())


def test_different_templates_stay_with_their_documents(repo):
    write(repo / "templates" / "Other.docx", "x")
    path = repo / "docs" / "guides" / "big" / "big.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("T.docx", "Other.docx"), encoding="utf-8")
    result = migrate([repo / "docs"], repo)
    assert "outputs" not in result.config
    assert result.config["documents"]["big"]["outputs"]["docx"]["template"] == "templates/Other.docx"
    assert result.config["documents"]["GU-1"]["outputs"]["docx"]["template"] == "templates/T.docx"


def test_the_same_source_in_two_documents_is_reported_and_kept_in_both(repo):
    result = migrate([repo / "docs"], repo)
    notes = [f.message for f in result.findings if f.file.name == "intro.md"]
    assert notes == ["is a source of several documents: GU-1, big"]


def test_unsupported_settings_are_reported_not_dropped_silently(repo):
    result = migrate([repo / "docs"], repo)
    messages = {(f.file.name, f.message) for f in result.findings if f.level == "warning"}
    assert ("GU-1.yaml", "PDF output is not supported yet and was not carried over") in messages
    assert ("GU-1.yaml", "cli.plantuml-jar-path was left out: PlantUML diagrams are not rendered") in messages
    assert ("GU-1.yaml", "createdocs chose the template from the status. py-doc uses one template per output") in messages
    assert ("big.yaml", "entries[3].extra_key has no equivalent and was left out") in messages
    assert ("big.yaml", "variables are kept in the file but py-doc does not apply them yet") in messages


def test_versioned_file_names_are_flagged_as_a_behaviour_change(repo):
    result = migrate([repo / "docs"], repo)
    assert any("added the version to the output file name" in f.message for f in result.findings)


def test_missing_source_is_a_warning(repo):
    (repo / "docs" / "guides" / "big" / "two.md").unlink()
    result = migrate([repo / "docs"], repo)
    assert any(f.message == "entries[1]: 'two.md' does not exist" for f in result.findings)


def test_other_yaml_is_skipped_and_hidden_folders_are_not_searched(repo):
    result = migrate([repo], repo)
    assert [p.name for p in result.skipped] == ["mkdocs.yml"]
    assert len(result.migrated) == 2


def test_document_ids_stay_unique(repo):
    for folder in ("a", "b"):
        write(repo / folder / "doc.md", "# D\n")
        write(repo / folder / "doc.yaml", "entries: [{file: doc.md}]\n")
    ids = [doc_id for _, doc_id in migrate([repo / "a", repo / "b"], repo).migrated]
    assert ids == ["doc", "b-doc"]


def test_pdf_only_document_still_gets_a_word_output_with_a_warning(tmp_path):
    write(tmp_path / "a.md", "# A\n")
    write(tmp_path / "a.yaml", "cli: {emit-pdf: true, output: out/a.pdf}\nentries: [{file: a.md}]\n")
    result = migrate([tmp_path], tmp_path)
    assert result.config["documents"]["a"]["outputs"]["docx"]["path"] == "out/a.docx"
    assert any("built no Word file" in f.message for f in result.findings)


def test_output_extension_decides_the_format_when_no_emit_flag_is_set(tmp_path):
    write(tmp_path / "a.md", "# A\n")
    write(tmp_path / "a.yaml", "cli: {output: out/a.docx}\nentries: [{file: a.md}]\n")
    result = migrate([tmp_path], tmp_path)
    assert not any(f.level == "warning" for f in result.findings)


def test_no_template_flag_drops_the_template(tmp_path):
    write(tmp_path / "a.md", "# A\n")
    write(tmp_path / "a.yaml", "cli: {emit-docx: true, template: t.docx, no-template: true}\nentries: [{file: a.md}]\n")
    docx = migrate([tmp_path], tmp_path).config["documents"]["a"]["outputs"]["docx"]
    assert "template" not in docx


def test_unknown_meta_key_is_reported(tmp_path):
    write(tmp_path / "a.md", "# A\n")
    write(tmp_path / "a.yaml", "meta: {title: A, flavour: mint}\nentries: [{file: a.md}]\n")
    result = migrate([tmp_path], tmp_path)
    assert any(f.message == "meta.flavour has no equivalent and was left out" for f in result.findings)


def test_generated_file_loads_and_builds_the_same_document(repo):
    from py_doc.build import merge_document

    result = migrate([repo / "docs"], repo)
    (repo / "py-doc.yml").write_text(render(result.config), encoding="utf-8")
    config = load_config(repo / "py-doc.yml")
    merged = merge_document(config.documents["big"])
    assert merged.metadata.title == "Big"
    assert config.output_path(config.documents["big"], "docx") == repo / "build" / "guides" / "big.docx"
    assert config.outputs["docx"].template == repo / "templates" / "T.docx"


def test_read_createdocs_rejects_other_yaml(tmp_path):
    assert read_createdocs(write(tmp_path / "m.yml", "site_name: x\n")) is None
    assert read_createdocs(write(tmp_path / "n.yml", "entries: [1, 2]\n")) is None
    assert read_createdocs(write(tmp_path / "o.yml", "entries: [unclosed\n")) is None


def test_unknown_source_format_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Unknown legacy format"):
        migrate([tmp_path], tmp_path, "mkdocs")


class TestCommand:
    def run(self, monkeypatch, capsys, *args):
        code = main(["migrate", *args])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    def test_check_reports_and_writes_nothing(self, repo, monkeypatch, capsys):
        monkeypatch.chdir(repo)
        code, out, _ = self.run(monkeypatch, capsys, "docs", "--check")
        assert code == 0
        assert "migrated  docs/guidelines/GU-1.yaml -> documents.GU-1" in out
        assert "2 files: PDF output" not in out and "Check only: nothing was written" in out
        assert not (repo / "py-doc.yml").exists()

    def test_repeated_findings_are_grouped(self, repo, monkeypatch, capsys):
        for index in range(4):
            write(repo / "docs" / f"x{index}" / "x.md", "# X\n")
            write(repo / "docs" / f"x{index}" / "x.yaml", "cli: {emit-pdf: true, output: x.pdf}\nentries: [{file: x.md}]\n")
        monkeypatch.chdir(repo)
        _, out, _ = self.run(monkeypatch, capsys, "docs", "--check")
        assert "5 files: PDF output is not supported yet" in out
        assert out.count("PDF output is not supported yet") == 1

    def test_writes_a_config_that_loads(self, repo, monkeypatch, capsys):
        monkeypatch.chdir(repo)
        code, out, _ = self.run(monkeypatch, capsys, "docs")
        assert code == 0 and "written   py-doc.yml" in out
        assert set(load_config(repo / "py-doc.yml").documents) == {"big", "GU-1"}
        assert (repo / "docs" / "guidelines" / "GU-1.yaml").exists()  # originals are untouched

    def test_existing_output_is_not_overwritten_without_a_choice(self, repo, monkeypatch, capsys):
        monkeypatch.chdir(repo)
        (repo / "py-doc.yml").write_text("# mine\n", encoding="utf-8")
        code, _, err = self.run(monkeypatch, capsys, "docs")
        assert code == 1 and "already exists" in err
        assert (repo / "py-doc.yml").read_text(encoding="utf-8") == "# mine\n"

    def test_backup_keeps_the_old_output_and_the_legacy_files(self, repo, monkeypatch, capsys):
        monkeypatch.chdir(repo)
        (repo / "py-doc.yml").write_text("# mine\n", encoding="utf-8")
        code, _, _ = self.run(monkeypatch, capsys, "docs", "--backup")
        assert code == 0
        assert (repo / "py-doc.yml.bak").read_text(encoding="utf-8") == "# mine\n"
        assert (repo / "docs" / "guidelines" / "GU-1.yaml.bak").exists()
        self.run(monkeypatch, capsys, "docs", "--backup")
        assert (repo / "py-doc.yml.bak2").exists()

    def test_force_replaces_the_output(self, repo, monkeypatch, capsys):
        monkeypatch.chdir(repo)
        (repo / "py-doc.yml").write_text("# mine\n", encoding="utf-8")
        assert self.run(monkeypatch, capsys, "docs", "--force")[0] == 0
        assert yaml.safe_load((repo / "py-doc.yml").read_text(encoding="utf-8"))["documents"]

    def test_nothing_to_migrate_is_an_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        code, _, err = self.run(monkeypatch, capsys, ".")
        assert code == 1 and "No createdocs build files found" in err

    def test_missing_path_is_an_error(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        code, _, err = self.run(monkeypatch, capsys, "nope")
        assert code == 1 and "Path not found: nope" in err

    def test_output_in_another_folder_gets_paths_relative_to_it(self, repo, monkeypatch, capsys):
        monkeypatch.chdir(repo)
        code, _, _ = self.run(monkeypatch, capsys, "docs", "-o", "conf/py-doc.yml")
        assert code == 0
        config = yaml.safe_load((repo / "conf" / "py-doc.yml").read_text(encoding="utf-8"))
        assert config["documents"]["big"]["sources"][0]["file"] == "../docs/guides/big/one.md"
        assert load_config(repo / "conf" / "py-doc.yml").documents["big"].sources[0].file.is_file()


def test_python_dash_m_runs_the_unified_command():
    import subprocess

    result = subprocess.run([sys.executable, "-m", "py_doc", "--version"], capture_output=True, text=True, check=False)
    assert result.returncode == 0 and result.stdout.startswith("py-doc ")


def test_a_single_document_keeps_its_template(tmp_path):
    write(tmp_path / "a.md", "# A\n")
    write(tmp_path / "a.yaml", "cli: {emit-docx: true, template: t.docx}\nentries: [{file: a.md}]\n")
    result = migrate([tmp_path], tmp_path)
    assert "outputs" not in result.config
    assert result.config["documents"]["a"]["outputs"]["docx"]["template"] == "t.docx"
