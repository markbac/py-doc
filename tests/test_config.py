"""The py-doc.yml model: defaults, overrides and clear errors."""

from __future__ import annotations

from pathlib import Path

import pytest
from py_doc.config import ConfigError, find_config, load_config, parse_config


def write(tmp_path, text: str):
    path = tmp_path / "py-doc.yml"
    path.write_text(text, encoding="utf-8")
    return path


MINIMAL = """
documents:
  guide:
    sources: [a.md]
"""


def test_empty_file_gives_defaults(tmp_path):
    config = load_config(write(tmp_path, ""))
    assert config.documents == {}
    assert config.lint.severities["DOC001"] == "warning"


def test_paths_are_relative_to_the_file_not_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    path = write(tmp_path, "documents:\n  g:\n    sources:\n      - file: docs/a.md\n")
    monkeypatch.chdir(tmp_path / "docs")
    config = load_config(path)
    assert config.documents["g"].sources[0].file == (tmp_path / "docs" / "a.md").resolve()


def test_source_defaults_and_string_shorthand(tmp_path):
    source = load_config(write(tmp_path, MINIMAL)).documents["guide"].sources[0]
    assert (source.heading_offset, source.title, source.page_break, source.include) == (0, None, False, True)


def test_default_output_is_build_folder_named_after_the_document(tmp_path):
    config = load_config(write(tmp_path, MINIMAL))
    doc = config.documents["guide"]
    assert config.output_formats(doc) == ["docx"]
    assert config.output_path(doc, "docx") == tmp_path / "build" / "guide.docx"


def test_output_directory_default_and_document_override(tmp_path):
    config = load_config(
        write(
            tmp_path,
            """
outputs:
  docx: {dir: out}
documents:
  a: {sources: [a.md]}
  b:
    sources: [b.md]
    outputs:
      docx: {path: special/b.docx}
      pptx: {}
""",
        )
    )
    assert config.output_path(config.documents["a"], "docx") == (tmp_path / "out" / "a.docx").resolve()
    assert config.output_path(config.documents["b"], "docx") == (tmp_path / "special" / "b.docx").resolve()
    assert config.output_formats(config.documents["b"]) == ["docx", "pptx"]
    assert config.output_path(config.documents["b"], "pptx") == tmp_path / "build" / "b.pptx"


def test_metadata_is_mapped_to_document_properties(tmp_path):
    config = load_config(
        write(
            tmp_path,
            """
documents:
  g:
    title: Guide
    document_number: GD-1
    keywords: [a, b]
    classification: Internal
    sources: [a.md]
""",
        )
    )
    metadata = config.documents["g"].metadata()
    assert (metadata.title, metadata.document_id, metadata.keywords) == ("Guide", "GD-1", "a, b")
    assert metadata.extra == {"classification": "Internal"}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("bogus: 1", "unknown key 'bogus' in the top level"),
        ("- a", "the configuration must be a mapping"),
        ("documents:\n  g: {}", "documents.g.sources must be a list"),
        ("documents:\n  g: {sources: []}", "documents.g.sources must be a list"),
        ("documents:\n  g: {sources: [{page_brek: true, file: a.md}]}", "unknown key 'page_brek' in documents.g.sources[0]"),
        ("documents:\n  g: {sources: [{title: x}]}", "documents.g.sources[0] needs a 'file'"),
        ("documents:\n  g: {sources: [{file: a.md, heading_offset: x}]}", "heading_offset must be int"),
        ("documents:\n  g: {sources: [{file: a.md, heading_offset: true}]}", "heading_offset must be int"),
        ("documents:\n  g: {sources: [a.md], outputs: {pdf: {}}}", "unknown key 'pdf'"),
        ("documents:\n  g: {sources: [a.md], outputs: {pptx: {split_level: 9}}}", "split_level must be 1 to 6"),
        ("outputs:\n  docx: {path: x.docx}", "takes 'dir', not 'path'"),
        ("lint:\n  rules: {DOC999: error}", "unknown rule 'DOC999'"),
        ("lint:\n  rules: {DOC001: loud}", "lint.rules.DOC001 must be one of error, warning, info or off"),
        ("lint:\n  acronyms: {min_length: 1}", "min_length must be at least 2"),
        ("lint:\n  glossary: {API: api}", "lint.glossary.API must be a list"),
    ],
)
def test_mistakes_are_errors_that_name_the_place(tmp_path, text, message):
    with pytest.raises(ConfigError, match=message.replace("[", r"\[").replace("]", r"\]")):
        load_config(write(tmp_path, text))


def test_error_names_the_file(tmp_path):
    path = write(tmp_path, "bogus: 1")
    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert str(exc.value).startswith(str(path))


def test_invalid_yaml_and_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_config(write(tmp_path, "a: [unclosed"))
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yml")


class TestLint:
    def load(self, tmp_path, body: str):
        return load_config(write(tmp_path, "lint:\n" + body)).lint

    def test_rule_severity_and_off(self, tmp_path):
        lint = self.load(tmp_path, "  rules:\n    DOC001: error\n    DOC002: off\n    DOC003: warning\n")
        assert lint.severities == {"DOC001": "error", "DOC002": "warning", "DOC003": "warning"}
        assert lint.disabled_rules == {"DOC002"}

    def test_glossary_and_phrases_extend_the_defaults(self, tmp_path):
        lint = self.load(tmp_path, "  glossary:\n    Kubernetes: [k8s]\n  phrases:\n    utilise: use\n")
        assert lint.glossary["Kubernetes"] == ["k8s"]
        assert "LwM2M" in lint.glossary
        assert lint.redundant_phrases["utilise"] == "use"
        assert "in order to" in lint.redundant_phrases

    def test_acronym_policy(self, tmp_path):
        lint = self.load(tmp_path, "  acronyms:\n    min_length: 4\n    allowed: [SBOM]\n")
        assert lint.acronym_min_length == 4
        assert "SBOM" in lint.allowed_acronyms and "URL" in lint.allowed_acronyms

    def test_exclude_adds_to_the_default_directories(self, tmp_path):
        lint = self.load(tmp_path, "  exclude: [drafts]\n")
        assert {"drafts", "node_modules"} <= lint.exclude_dirs


def test_reserved_sections_are_kept_with_a_warning(tmp_path, caplog):
    config = load_config(write(tmp_path, "site: {name: x}\n"))
    assert config.reserved == {"site": {"name": "x"}}
    assert "'site' section is accepted but not used yet" in caplog.text


def test_find_config_walks_up(tmp_path):
    path = write(tmp_path, "")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert find_config(deep) == path


def test_parse_config_accepts_a_dict():
    assert parse_config({"project": {"name": "X"}}, Path(".")).name == "X"
