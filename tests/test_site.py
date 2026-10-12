"""py-doc site: pages, navigation and scaffolds for MkDocs and Astro + Starlight."""

from __future__ import annotations

import json
import shutil

import pytest
import yaml
from PIL import Image

from py_doc.app import main
from py_doc.config import load_config
from py_doc.errors import ConversionError
from py_doc.site import engine_for, generate_site
from py_doc.site.engines import MKDOCS_NAV, STARLIGHT_SIDEBAR, NavPage, NavSection
from py_doc.site.pages import MANIFEST, slug

needs_sh = pytest.mark.skipif(shutil.which("sh") is None, reason="the pages are converted by a shell script")


def test_slugs_keep_letters_digits_and_dashes():
    assert slug("01_Overview") == "01-overview"
    assert slug("Über uns!") == "ber-uns"
    assert slug("___") == "page"


# --- engines ----------------------------------------------------------------------------------------


def test_a_new_mkdocs_site_takes_in_the_navigation(tmp_path):
    engine = engine_for("mkdocs", tmp_path / "site")
    written = engine.scaffold("Sensor docs")
    assert {p.name for p in written} == {"mkdocs.yml", "index.md", ".gitignore"}
    config = (tmp_path / "site" / "mkdocs.yml").read_text(encoding="utf-8")
    assert f"INHERIT: {MKDOCS_NAV}" in config and 'site_name: "Sensor docs"' in config
    assert engine.exists() and engine.content == tmp_path / "site" / "docs" and engine.check() == []


def test_a_scaffold_never_replaces_a_file(tmp_path):
    (tmp_path / "mkdocs.yml").write_text("site_name: Mine\nnav:\n  - Home: index.md\n", encoding="utf-8")
    engine = engine_for("mkdocs", tmp_path)
    written = engine.scaffold("Theirs")
    assert (tmp_path / "mkdocs.yml").read_text(encoding="utf-8").startswith("site_name: Mine")
    assert tmp_path / "mkdocs.yml" not in written
    assert "has its own nav" in engine.check()[0]


def test_an_existing_mkdocs_yml_with_python_tags_is_read(tmp_path):
    (tmp_path / "mkdocs.yml").write_text("docs_dir: pages\nmarkdown_extensions:\n  - x: !!python/name:foo.bar\n", encoding="utf-8")
    engine = engine_for("mkdocs", tmp_path)
    assert engine.content == tmp_path / "pages"
    assert "INHERIT" in engine.check()[0]


def test_the_mkdocs_navigation_has_a_section_per_document(tmp_path):
    engine = engine_for("mkdocs", tmp_path)
    engine.scaffold("x")
    nav = engine.write_nav([
        NavSection("Guide", "guide", [NavPage("Overview", "guide/overview.md"), NavPage("Design", "guide/design.md")]),
        NavSection("Notes", "notes", [NavPage("Release notes", "notes/notes.md")]),
    ])
    data = yaml.safe_load(nav.read_text(encoding="utf-8"))
    assert data["nav"] == [
        {"Home": "index.md"},
        {"Guide": [{"Overview": "guide/overview.md"}, {"Design": "guide/design.md"}]},
        {"Release notes": "notes/notes.md"},
    ]


def test_a_new_starlight_site_passes_the_sidebar_to_starlight(tmp_path):
    engine = engine_for("starlight", tmp_path)
    assert not engine.exists()
    engine.scaffold("Sensor docs")
    assert engine.exists() and engine.check() == []
    package = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    assert "@astrojs/starlight" in package["dependencies"] and package["scripts"]["build"] == "astro build"
    assert "import sidebar from './src/py-doc-sidebar.json'" in (tmp_path / "astro.config.mjs").read_text(encoding="utf-8")
    engine.write_nav([NavSection("Guide", "guide", [])])
    assert json.loads((tmp_path / STARLIGHT_SIDEBAR).read_text(encoding="utf-8")) == [{"label": "Guide", "items": [{"autogenerate": {"directory": "guide"}}]}]


def test_a_starlight_site_without_the_sidebar_is_told_how(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"@astrojs/starlight": "1"}}', encoding="utf-8")
    (tmp_path / "astro.config.mjs").write_text("export default {}", encoding="utf-8")
    assert "py-doc-sidebar.json" in engine_for("starlight", tmp_path).check()[0]


class _Box:
    """Records the build commands instead of running them."""

    def __init__(self):
        self.calls = []

    def run(self, argv, **kwargs):
        self.calls.append(([str(a) for a in argv], kwargs))


def test_the_builds_run_in_the_container(tmp_path):
    box = _Box()
    out = engine_for("mkdocs", tmp_path).build(box)
    assert box.calls[0][0][:2] == ["mkdocs", "build"] and out == tmp_path / "site"
    box = _Box()
    engine_for("starlight", tmp_path).build(box)
    assert [c[0][:2] for c in box.calls] == [["npm", "install"], ["npx", "astro"]]
    assert box.calls[0][1]["network"] is True and box.calls[1][1]["env"]["ASTRO_TELEMETRY_DISABLED"] == "1"


# --- pages ------------------------------------------------------------------------------------------


@pytest.fixture
def project(tmp_path):
    docs = tmp_path / "docs"
    (docs / "images").mkdir(parents=True)
    Image.new("RGB", (4, 4), "red").save(docs / "images" / "board.png")
    (docs / "01_overview.md").write_text(
        "---\ntitle: Sensor guide\n---\n\n# Overview\n\nVersion {{version}}. See [the design](02_design.md#flow).\n\n"
        "> [!NOTE]\n> Read this first.\n\n![The board](images/board.png)\n\n[[CAPTION:Table]] Pins\n\n| Pin | Use |\n|---|---|\n| 1 | Power |\n",
        encoding="utf-8",
    )
    (docs / "02_design.md").write_text("# Design\n\n## Flow\n\nBack to the [overview](01_overview.md).\n\n::: {.pagebreak}\n:::\n\nDone.\n", encoding="utf-8")
    (tmp_path / "py-doc.yml").write_text(
        "project: {name: Sensor}\ndocuments:\n  guide:\n    sources: [docs/01_overview.md, {file: docs/02_design.md, heading_offset: 1, page_break: true}]\n"
        "    variables: {version: '1.0'}\nsite: {engine: ENGINE}\n",
        encoding="utf-8",
    )
    return tmp_path


def _site(project, engine_name, pandoc_runtime):
    text = (project / "py-doc.yml").read_text(encoding="utf-8").replace("ENGINE", engine_name)
    (project / "py-doc.yml").write_text(text, encoding="utf-8")
    config = load_config(project / "py-doc.yml")
    engine_for(engine_name, config.site.dir).scaffold("Sensor")
    return config, lambda: pandoc_runtime


@needs_sh
def test_mkdocs_pages_have_admonitions_links_pictures_and_captions(project, pandoc_runtime):
    config, runtime = _site(project, "mkdocs", pandoc_runtime)
    engine, written = generate_site(config, runtime)
    docs = project / "site" / "docs" / "guide"
    overview = (docs / "01-overview.md").read_text(encoding="utf-8")
    assert overview.startswith("---\ntitle: Overview\n---\n\n# Overview")
    assert "Version 1.0. See [the design](02-design.md#flow)." in overview
    assert "!!! note\n\n    Read this first." in overview
    assert "*Pins*" in overview
    (picture,) = (docs / "media").iterdir()
    assert picture.name.endswith("-board.png") and f"](media/{picture.name})" in overview
    design = (docs / "02-design.md").read_text(encoding="utf-8")
    assert "# Design" in design and "[overview](01-overview.md)" in design and "pagebreak" not in design
    nav = yaml.safe_load((project / "site" / MKDOCS_NAV).read_text(encoding="utf-8"))["nav"]
    assert nav[-1] == {"Sensor guide": [{"Overview": "guide/01-overview.md"}, {"Design": "guide/02-design.md"}]}
    assert set(json.loads((project / "site" / MANIFEST).read_text(encoding="utf-8"))["files"]) == {
        "docs/guide/01-overview.md", "docs/guide/02-design.md", f"docs/guide/media/{picture.name}", "docs/guide/.gitignore",
    }


@needs_sh
def test_starlight_pages_have_asides_an_order_and_no_repeated_title(project, pandoc_runtime):
    config, runtime = _site(project, "starlight", pandoc_runtime)
    generate_site(config, runtime)
    overview = (project / "site" / "src" / "content" / "docs" / "guide" / "01-overview.md").read_text(encoding="utf-8")
    assert overview.startswith("---\ntitle: Overview\nsidebar:\n  order: 1\n---\n\nVersion 1.0. See [the design](/guide/02-design/#flow).")
    assert ":::note\nRead this first.\n:::" in overview


@needs_sh
def test_a_page_py_doc_did_not_write_is_left_alone(project, pandoc_runtime):
    config, runtime = _site(project, "mkdocs", pandoc_runtime)
    mine = project / "site" / "docs" / "guide" / "01-overview.md"
    mine.parent.mkdir(parents=True)
    mine.write_text("my own page\n", encoding="utf-8")
    with pytest.raises(ConversionError, match="py-doc did not write it"):
        generate_site(config, runtime)
    assert mine.read_text(encoding="utf-8") == "my own page\n"


@needs_sh
def test_a_page_whose_source_is_gone_is_removed(project, pandoc_runtime):
    config, runtime = _site(project, "mkdocs", pandoc_runtime)
    generate_site(config, runtime)
    text = (project / "py-doc.yml").read_text(encoding="utf-8").replace(", {file: docs/02_design.md, heading_offset: 1, page_break: true}", "")
    (project / "py-doc.yml").write_text(text, encoding="utf-8")
    generate_site(load_config(project / "py-doc.yml"), runtime)
    assert not (project / "site" / "docs" / "guide" / "02-design.md").exists()
    assert (project / "site" / "docs" / "index.md").is_file(), "a page py-doc did not write stays"


def test_a_site_must_be_made_first(project):
    (project / "py-doc.yml").write_text((project / "py-doc.yml").read_text(encoding="utf-8").replace("ENGINE", "mkdocs"), encoding="utf-8")
    with pytest.raises(ConversionError, match="py-doc site init"):
        generate_site(load_config(project / "py-doc.yml"), lambda: None)


# --- command ----------------------------------------------------------------------------------------


def test_site_init_makes_the_site_named_in_py_doc_yml(project, monkeypatch, capsys):
    (project / "py-doc.yml").write_text((project / "py-doc.yml").read_text(encoding="utf-8").replace("ENGINE", "starlight"), encoding="utf-8")
    monkeypatch.chdir(project)
    assert main(["site", "init"]) == 0
    assert (project / "site" / "astro.config.mjs").is_file() and "Next: py-doc site build" in capsys.readouterr().out
    assert main(["site", "init"]) == 0
    assert "already there" in capsys.readouterr().out
    assert main(["site", "init", "--engine", "mkdocs"]) == 1


def test_site_init_without_a_site_section_says_what_to_add(tmp_path, monkeypatch, capsys):
    (tmp_path / "py-doc.yml").write_text("documents:\n  a: {sources: [a.md]}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["site", "init"]) == 1
    assert main(["site", "init", "--engine", "mkdocs"]) == 0
    assert "site:\n  engine: mkdocs\n  dir: site" in capsys.readouterr().out
