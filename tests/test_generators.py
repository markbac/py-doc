"""Content generators: the configuration, each built-in type, custom ones and py-doc generate."""

from __future__ import annotations

import shutil
import sys
import textwrap

import pytest
from py_doc.app import main
from py_doc.config import ConfigError, load_config
from py_doc.generators import GeneratorError, run_generators


def project(tmp_path, generators: str, documents: str = "documents:\n  guide: {sources: [intro.md]}\n"):
    (tmp_path / "intro.md").write_text(
        "---\ntitle: Guide\nversion: '2.0'\nstatus: Draft\ndocument_number: GD-7\n---\n\n# Intro\n\n## Scope\n\n"
        "| ID | Text |\n|---|---|\n| FR-001 | Works |\n\nSee FR-001 and FR-002.\n",
        encoding="utf-8",
    )
    (tmp_path / "py-doc.yml").write_text(documents + "content:\n  generators:\n" + textwrap.indent(generators, "    "), encoding="utf-8")
    return load_config(tmp_path / "py-doc.yml")


def generated(tmp_path, generators: str, name: str = "out.md") -> str:
    run_generators(project(tmp_path, generators))
    return (tmp_path / name).read_text(encoding="utf-8")


class TestConfiguration:
    def test_options_are_checked_by_type(self, tmp_path):
        with pytest.raises(ConfigError, match=r"content.generators\[0\] \(openapi\) needs source"):
            project(tmp_path, "- {type: openapi, output: a.md}\n")
        with pytest.raises(ConfigError, match="unknown key 'colour'"):
            project(tmp_path, "- {type: glossary, output: a.md, colour: red}\n")
        with pytest.raises(ConfigError, match="needs an output"):
            project(tmp_path, "- {type: glossary}\n")
        with pytest.raises(ConfigError, match="already writes"):
            project(tmp_path, "- {type: glossary, output: a.md}\n- {type: documents, name: d, output: a.md}\n")

    def test_an_unknown_type_fails_when_it_runs(self, tmp_path):
        config = project(tmp_path, "- {type: nonesuch, output: a.md, anything: 1}\n")
        with pytest.raises(GeneratorError, match="unknown type 'nonesuch'"):
            run_generators(config)

    def test_a_file_is_only_rewritten_when_it_changes(self, tmp_path):
        config = project(tmp_path, "- {type: glossary, output: out.md}\n")
        assert run_generators(config) == [tmp_path.resolve() / "out.md"]
        assert run_generators(config) == []


class TestBuiltins:
    def test_glossary_from_a_file(self, tmp_path):
        (tmp_path / "terms.yml").write_text("Zeta: Last.\nAlpha: First.\n", encoding="utf-8")
        text = generated(tmp_path, "- {type: glossary, source: terms.yml, output: out.md}\n")
        assert text.index("| Alpha | First. |") < text.index("| Zeta | Last. |")

    def test_documents_index_and_toc(self, tmp_path):
        text = generated(tmp_path, "- {type: documents, output: out.md}\n- {type: toc, document: guide, output: toc.md}\n")
        assert "| [Guide](intro.md) | GD-7 | 2.0 | Draft |" in text
        assert (tmp_path / "toc.md").read_text(encoding="utf-8").splitlines()[2:] == ["- [Intro](intro.md#intro)", "  - [Scope](intro.md#scope)"]

    def test_adr_index(self, tmp_path):
        (tmp_path / "adr").mkdir()
        (tmp_path / "adr" / "0001-a.md").write_text("# Use A\n\n## Status\n\nAccepted\n", encoding="utf-8")
        (tmp_path / "adr" / "0002-b.md").write_text("---\nstatus: Superseded\n---\n\n# Use B\n", encoding="utf-8")
        text = generated(tmp_path, "- {type: adr-index, source: adr, output: out.md}\n")
        assert "| 0001 | [Use A](adr/0001-a.md) | Accepted |  |" in text and "| 0002 | [Use B](adr/0002-b.md) | Superseded |  |" in text

    def test_requirements_traceability(self, tmp_path):
        text = generated(tmp_path, "- {type: requirements, sources: ['*.md'], output: out.md}\n")
        assert "| FR-001 | [intro.md:14](intro.md) | [intro.md:16](intro.md) |" in text
        assert "| FR-002 | not defined | [intro.md:16](intro.md) |" in text

    def test_openapi_and_asyncapi(self, tmp_path):
        (tmp_path / "o.yml").write_text(
            "openapi: 3.0.0\ninfo: {title: Pets, version: '1'}\npaths:\n  /pets: {get: {summary: List pets}, post: {operationId: addPet}}\n"
            "components: {schemas: {Pet: {description: A pet}}}\n",
            encoding="utf-8",
        )
        (tmp_path / "a.yml").write_text(
            "asyncapi: 2.6.0\ninfo: {title: Events, version: '1'}\nchannels:\n  pets/added: {subscribe: {summary: New pet, message: {name: PetAdded}}}\n",
            encoding="utf-8",
        )
        text = generated(
            tmp_path, "- {type: openapi, engine: summary, source: o.yml, output: out.md}\n- {type: asyncapi, engine: summary, source: a.yml, output: a.md}\n"
        )
        assert "| `GET` | `/pets` | List pets |" in text and "| `POST` | `/pets` | addPet |" in text and "- `Pet`: A pet" in text
        assert "| `pets/added` | subscribe | PetAdded | New pet |" in (tmp_path / "a.md").read_text(encoding="utf-8")
        with pytest.raises(GeneratorError, match="not an OpenAPI description"):
            generated(tmp_path, "- {type: openapi, engine: summary, source: a.yml, output: out.md}\n")

    def test_python_api_reads_without_importing(self, tmp_path):
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "__init__.py").write_text(
            '"""The package."""\nimport not_installed_anywhere\n\n\ndef run(x: int = 1) -> str:\n    """Run it.\n\n    Details."""\n\n\n'
            'def _hidden():\n    pass\n\n\nclass Tool:\n    """A tool."""\n\n    def use(self) -> None:\n        """Use it."""\n',
            encoding="utf-8",
        )
        text = generated(tmp_path, "- {type: python-api, source: pkg, output: out.md}\n")
        assert "### `run(x: int=1) -> str`\n\nRun it." in text and "_hidden" not in text
        assert "### class `Tool`\n\nA tool.\n\n#### `use(self) -> None`\n\nUse it." in text

    def test_a_diagram_file_becomes_a_fenced_block(self, tmp_path):
        (tmp_path / "flow.puml").write_text("@startuml\nA -> B\n@enduml\n", encoding="utf-8")
        text = generated(tmp_path, "- {type: diagram, source: flow.puml, caption: Flow, output: out.md}\n")
        assert text == "```plantuml\n@startuml\nA -> B\n@enduml\n```\n\n[[CAPTION:Figure]] Flow\n"

    def test_command_output_is_the_markdown(self, tmp_path):
        run = f"[{sys.executable!r}, -c, \"print('# Made')\"]"
        assert generated(tmp_path, f"- {{type: command, run: {run}, output: out.md}}\n") == "# Made\n"
        failing = f"[{sys.executable!r}, -c, 'import sys; sys.exit(3)']"
        with pytest.raises(GeneratorError, match="exited with status 3"):
            generated(tmp_path, f"- {{type: command, run: {failing}, output: out.md}}\n")

    def test_a_python_function_of_your_own(self, tmp_path, monkeypatch):
        (tmp_path / "mygen.py").write_text("def make(spec, project):\n    return f'# {spec.name} from {project.name}'\n", encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))
        text = generated(tmp_path, "- {type: python, callable: 'mygen:make', name: custom, output: out.md}\n", )
        assert text == "# custom from None\n"


def test_build_runs_the_generators_before_the_documents_that_use_them(tmp_path, monkeypatch, pandoc_runtime):
    (tmp_path / "terms.yml").write_text("Broker: Passes messages.\n", encoding="utf-8")
    project(
        tmp_path,
        "- {type: glossary, source: terms.yml, output: gen/glossary.md}\n",
        "documents:\n  guide: {sources: [intro.md, gen/glossary.md], outputs: {html: {}}}\n",
    )
    monkeypatch.chdir(tmp_path)
    assert main(["build"]) == 0
    assert "Passes messages." in (tmp_path / "build" / "guide.html").read_text(encoding="utf-8")
    assert main(["generate", "--list"]) == 0


class TestApiMarkdown:
    def test_html_headings_and_asides_become_markdown(self):
        from py_doc.generators.apidocs import clean_markdown

        raw = (
            '<h1 id="pets-api">Pets API v1</h1>\n\n> Scroll down for code samples, example requests and responses.\n\n'
            '<h2 id="pets-api-default">Default &amp; more</h2>\n\n<aside class="success">\nThis operation does not require authentication\n</aside>\n\n'
            "```yaml\n# not a heading\n```\n\n# Schemas\n\n<a id=\"schemapet\"></a>\n\n* <a href=\"https://x.org/v1\">https://x.org/v1</a>\n"
        )
        assert clean_markdown(raw, heading_offset=1, title="Pets reference", nest=True) == (
            "## Pets reference\n\n#### Default & more\n\n> [!NOTE]\n> This operation does not require authentication\n\n"
            "```yaml\n# not a heading\n```\n\n### Schemas\n\n[]{#schemapet}\n\n* [https://x.org/v1](https://x.org/v1)\n"
        )

    def test_engine_and_options_are_checked(self, tmp_path):
        (tmp_path / "o.yml").write_text("openapi: 3.0.0\ninfo: {title: T, version: '1'}\npaths: {}\n", encoding="utf-8")
        with pytest.raises(GeneratorError, match="engine must be one of tool, summary"):
            generated(tmp_path, "- {type: openapi, engine: magic, source: o.yml, output: out.md}\n")
        with pytest.raises(GeneratorError, match="need engine: tool"):
            generated(tmp_path, "- {type: openapi, engine: summary, html: x.html, source: o.yml, output: out.md}\n")
        with pytest.raises(ConfigError, match="unknown key 'validate'"):
            project(tmp_path, "- {type: asyncapi, validate: false, source: o.yml, output: out.md}\n")


@pytest.mark.skipif(not all(shutil.which(tool) for tool in ("redocly", "widdershins")), reason="Redocly CLI and Widdershins are not installed")
def test_openapi_reference_with_the_real_tools(tmp_path, pandoc_runtime):
    from pathlib import Path

    api = Path(__file__).parent.parent / "examples" / "docs" / "includes" / "apis" / "library-openapi.yaml"
    text = generated(tmp_path, f"- {{type: openapi, source: {api.as_posix()!r}, html: api.html, output: out.md}}\n")
    assert "## Books" in text and "### listBooks" in text and "<h" not in text
    assert (tmp_path / "api.html").stat().st_size > 10000
