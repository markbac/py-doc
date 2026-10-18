"""The py-doc.yml model: defaults, overrides and clear errors."""

from __future__ import annotations

from pathlib import Path

import pytest
from py_doc.lint.config import C4_RULES
from py_doc.config import ConfigError, find_config, load_config, parse_config

NEW_RULES = {"DOC005": "warning", "DOC006": "warning", "DOC007": "warning", "DOC008": "info", "DOC009": "info"}


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
        ("documents:\n  g: {sources: [a.md], outputs: {epub: {}}}", "unknown key 'epub'"),
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
        assert lint.severities == {"DOC001": "error", "DOC002": "warning", "DOC003": "warning", "DOC004": "error"} | NEW_RULES | C4_RULES
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
    config = load_config(write(tmp_path, "content: {name: x}\n"))
    assert config.reserved == {"content": {"name": "x"}}
    assert "'content' section is accepted but not used yet" in caplog.text


def test_the_site_section(tmp_path):
    docs = "project: {name: Sensor}\ndocuments:\n  guide: {sources: [a.md]}\n  notes: {sources: [b.md]}\n"
    config = load_config(write(tmp_path, docs + "site: {engine: starlight, documents: [guide]}\n"))
    assert config.site.engine == "starlight" and config.site.dir == tmp_path.resolve() / "site"
    assert config.site.title == "Sensor" and config.site.documents == ["guide"]
    with pytest.raises(ConfigError, match="site.engine must be one of mkdocs, starlight"):
        load_config(write(tmp_path, docs + "site: {engine: hugo}\n"))
    with pytest.raises(ConfigError, match="site.documents names 'other'"):
        load_config(write(tmp_path, docs + "site: {engine: mkdocs, documents: [other]}\n"))
    with pytest.raises(ConfigError, match="unknown key 'theme' in site"):
        load_config(write(tmp_path, docs + "site: {engine: mkdocs, theme: x}\n"))


def test_the_site_downloads_and_targets(tmp_path):
    docs = "documents:\n  guide: {sources: [a.md]}\n"
    config = load_config(write(tmp_path, docs + "site: {engine: mkdocs, downloads: [pdf, docx], targets: {github: mkdocs.yml, tarf: mkdocs.tarf.yml}}\n"))
    assert config.site.downloads == ["pdf", "docx"]
    assert config.site.targets == {"github": "mkdocs.yml", "tarf": "mkdocs.tarf.yml"}
    assert load_config(write(tmp_path, docs + "site: {engine: mkdocs, pages: {Blog: blog/index.md}}\n")).site.pages == {"Blog": "blog/index.md"}
    with pytest.raises(ConfigError, match="site.downloads names 'epub'"):
        load_config(write(tmp_path, docs + "site: {engine: mkdocs, downloads: [epub]}\n"))
    with pytest.raises(ConfigError, match="site.targets needs engine: mkdocs"):
        load_config(write(tmp_path, docs + "site: {engine: starlight, targets: {a: x.yml}}\n"))


def test_find_config_walks_up(tmp_path):
    path = write(tmp_path, "")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert find_config(deep) == path


def test_parse_config_accepts_a_dict():
    assert parse_config({"project": {"name": "X"}}, Path(".")).name == "X"


def test_the_example_in_the_user_guide_loads(tmp_path):
    import re

    readme = Path(__file__).parent.parent / "docs" / "guide" / "02_projects.md"  # the configuration example of the user guide
    block = re.search(r"```yaml\n(project:.*?)```", readme.read_text(encoding="utf-8"), re.S).group(1)
    config = load_config(write(tmp_path, block))
    assert list(config.documents) == ["c4-guide"]
    assert config.lint.severities["DOC001"] == "error"


def test_collections_name_sets_of_files_that_documents_take_in(tmp_path):
    for name in ("b.md", "a.md", "intro.md"):
        (tmp_path / "guide").mkdir(exist_ok=True)
        (tmp_path / "guide" / name).write_text("# x\n", encoding="utf-8")
    text = (
        "collections:\n  chapters: [guide/*.md, guide/intro.md]\n"
        "documents:\n  guide:\n    sources: [README.md, {collection: chapters, heading_offset: 1, page_break: true}]\n"
    )
    config = load_config(write(tmp_path, text))
    root = tmp_path.resolve()
    assert config.collections["chapters"] == [root / "guide" / n for n in ("a.md", "b.md", "intro.md")]
    sources = config.documents["guide"].sources
    assert [s.file.name for s in sources] == ["README.md", "a.md", "b.md", "intro.md"]
    assert [s.page_break for s in sources] == [False, True, False, False]
    assert {s.heading_offset for s in sources[1:]} == {1}
    with pytest.raises(ConfigError, match="names 'other', which is not under collections"):
        load_config(write(tmp_path, "documents:\n  guide: {sources: [{collection: other}]}\n"))


def test_bundles_combine_documents_and_build_beside_them(tmp_path):
    text = (
        "documents:\n  guide: {sources: [a.md, b.md], variables: {x: 1}}\n  api: {sources: [c.md], outputs: {pdf: {}}}\n"
        "bundles:\n  handbook: {title: Handbook, documents: [guide, api], outputs: {pdf: {}, docx: {}}, variables: {y: 2}}\n"
    )
    config = load_config(write(tmp_path, text))
    handbook = config.documents["handbook"]
    assert list(config.documents) == ["guide", "api", "handbook"] and config.own_documents == ["guide", "api"]
    assert handbook.bundle == ["guide", "api"] and handbook.meta["title"] == "Handbook"
    assert [(s.file.name, s.page_break) for s in handbook.sources] == [("a.md", False), ("b.md", False), ("c.md", True)]
    assert handbook.variables == {"x": 1, "y": 2}
    assert config.output_formats(handbook) == ["docx", "pdf"] and config.output_formats(config.documents["api"]) == ["pdf"]
    assert set(config.lint.documents) == {"guide", "api"}
    with pytest.raises(ConfigError, match="names 'gone', which is not under documents"):
        load_config(write(tmp_path, "documents:\n  guide: {sources: [a.md]}\nbundles:\n  b: {documents: [gone]}\n"))
    with pytest.raises(ConfigError, match="has the name of a document"):
        load_config(write(tmp_path, "documents:\n  guide: {sources: [a.md]}\nbundles:\n  guide: {documents: [guide]}\n"))


def test_site_groups(tmp_path):
    docs = "documents:\n  a: {sources: [a.md]}\n  b: {sources: [b.md]}\n  c: {sources: [c.md]}\n"
    config = load_config(write(tmp_path, docs + "site: {engine: mkdocs, groups: {Reference: [b, c]}}\n"))
    assert config.site.groups == {"Reference": ["b", "c"]}
    with pytest.raises(ConfigError, match="more than one group"):
        load_config(write(tmp_path, docs + "site: {engine: mkdocs, groups: {X: [a], Y: [a]}}\n"))
    with pytest.raises(ConfigError, match="not a document of the site"):
        load_config(write(tmp_path, docs + "site: {engine: mkdocs, documents: [a], groups: {X: [b]}}\n"))
