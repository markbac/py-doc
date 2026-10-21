"""py-doc site: pages, navigation and scaffolds for MkDocs and Astro + Starlight."""

from __future__ import annotations

import json
import shutil

import pytest
import yaml
from PIL import Image

from py_doc.app import main
from py_doc.config import ConfigError, load_config
from py_doc.errors import ConversionError
from py_doc.site import engine_for, generate_site
from py_doc.site.engines import MKDOCS_NAV, STARLIGHT_SIDEBAR, NavPage, NavSection
from py_doc.site.pages import MANIFEST, Page, nav_items, slug

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
    (tmp_path / "mkdocs.yml").write_text(
        "docs_dir: pages\nmarkdown_extensions:\n  - x: !!python/name:foo.bar\n", encoding="utf-8"
    )
    engine = engine_for("mkdocs", tmp_path)
    assert engine.content == tmp_path / "pages"
    assert "INHERIT" in engine.check()[0]


def test_the_mkdocs_navigation_has_a_section_per_document(tmp_path):
    engine = engine_for("mkdocs", tmp_path)
    engine.scaffold("x")
    nav = engine.write_nav(
        [
            NavSection(
                "Guide", "guide", [NavPage("Overview", "guide/overview.md"), NavPage("Design", "guide/design.md")]
            ),
            NavSection("Notes", "notes", [NavPage("Release notes", "notes/notes.md")]),
        ]
    )
    data = yaml.safe_load(nav.read_text(encoding="utf-8"))
    assert data["nav"] == [
        {"Home": "index.md"},
        {"Guide": [{"Overview": "guide/overview.md"}, {"Design": "guide/design.md"}]},
        {"Release notes": "notes/notes.md"},
    ]


def test_hand_written_pages_follow_the_documents_in_the_navigation(tmp_path):
    engine = engine_for("mkdocs", tmp_path)
    engine.scaffold("x")
    nav = engine.write_nav(
        [NavSection("Guide", "guide", [NavPage("Overview", "guide/overview.md")])], {"Blog": "blog/index.md"}
    )
    assert yaml.safe_load(nav.read_text(encoding="utf-8"))["nav"][-2:] == [
        {"Overview": "guide/overview.md"},
        {"Blog": "blog/index.md"},
    ]
    sidebar = engine_for("starlight", tmp_path / "astro").write_nav([], {"Blog": "blog/index.md", "About": "about.md"})
    assert json.loads(sidebar.read_text(encoding="utf-8")) == [
        {"label": "Blog", "link": "/blog/"},
        {"label": "About", "link": "/about/"},
    ]


def test_a_target_config_inherits_the_navigation_through_mkdocs_yml(tmp_path):
    engine = engine_for("mkdocs", tmp_path)
    engine.scaffold("x")
    (tmp_path / "mkdocs.tarf.yml").write_text(
        "INHERIT: mkdocs.yml\nsite_url: https://tarf.example/\nsite_dir: build-tarf\n", encoding="utf-8"
    )
    assert engine.check("mkdocs.tarf.yml") == []
    assert engine.site_dir("mkdocs.tarf.yml") == tmp_path / "build-tarf" and engine.site_dir() == tmp_path / "build"
    (tmp_path / "mkdocs.alone.yml").write_text("site_name: alone\n", encoding="utf-8")
    assert "INHERIT: py-doc-nav.yml" in engine.check("mkdocs.alone.yml")[0]
    (tmp_path / "mkdocs.moved.yml").write_text("INHERIT: mkdocs.yml\ndocs_dir: pages\n", encoding="utf-8")
    assert "reads its pages from pages" in engine.check("mkdocs.moved.yml")[0]
    assert "is not there" in engine.check("mkdocs.missing.yml")[0]


def test_a_new_starlight_site_passes_the_sidebar_to_starlight(tmp_path):
    engine = engine_for("starlight", tmp_path)
    assert not engine.exists()
    engine.scaffold("Sensor docs")
    assert engine.exists() and engine.check() == []
    package = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))
    assert "@astrojs/starlight" in package["dependencies"] and package["scripts"]["build"] == "astro build"
    assert "import sidebar from './src/py-doc-sidebar.json'" in (tmp_path / "astro.config.mjs").read_text(
        encoding="utf-8"
    )
    engine.write_nav([NavSection("Guide", "guide", [])])
    assert json.loads((tmp_path / STARLIGHT_SIDEBAR).read_text(encoding="utf-8")) == [
        {"label": "Guide", "items": [{"autogenerate": {"directory": "guide"}}]}
    ]


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


def test_a_target_builds_with_its_own_config_file(tmp_path):
    engine = engine_for("mkdocs", tmp_path)
    engine.scaffold("x")
    (tmp_path / "mkdocs.tarf.yml").write_text("INHERIT: mkdocs.yml\nsite_dir: build-tarf\n", encoding="utf-8")
    box = _Box()
    assert engine.build(box, "mkdocs.tarf.yml") == tmp_path / "build-tarf"
    assert box.calls[0][0][-1].endswith("mkdocs.tarf.yml")
    with pytest.raises(ConversionError, match="site.targets names it"):
        engine.build(box, "mkdocs.missing.yml")


# --- pages ------------------------------------------------------------------------------------------


@pytest.fixture
def project(tmp_path):
    docs = tmp_path / "docs"
    (docs / "images").mkdir(parents=True)
    Image.new("RGB", (4, 4), "red").save(docs / "images" / "board.png")
    (docs / "01_overview.md").write_text(
        "---\ntitle: Sensor guide\n---\n\n# Overview\n\nVersion {{version}}. See [the design](02_design.md#flow).\n\n"
        "Write `[text](02_design.md)` or `![](images/none.png)` to link.\n\n"
        "Energy $E = mc^2$ and\n\n$$t = C/I$$\n\n> [!NOTE]\n> Read this first.\n\n![The board](images/board.png)\n\n[[CAPTION:Table]] Pins\n\n| Pin | Use |\n|---|---|\n| 1 | Power |\n",
        encoding="utf-8",
    )
    (docs / "02_design.md").write_text(
        "# Design\n\n## Flow\n\nBack to the [overview](01_overview.md).\n\n::: {.pagebreak}\n:::\n\nDone.\n",
        encoding="utf-8",
    )
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
    assert "`[text](02_design.md)` or `![](images/none.png)`" in overview, "code is shown as written"
    assert "!!! note\n\n    Read this first." in overview
    assert "Energy $E = mc^2$ and" in overview and "$$t = C/I$$" in overview
    assert "*Pins*" in overview
    (picture,) = (docs / "media").iterdir()
    assert picture.name.endswith("-board.png") and f"](media/{picture.name})" in overview
    design = (docs / "02-design.md").read_text(encoding="utf-8")
    assert "# Design" in design and "[overview](01-overview.md)" in design and "pagebreak" not in design
    nav = yaml.safe_load((project / "site" / MKDOCS_NAV).read_text(encoding="utf-8"))["nav"]
    assert nav[-1] == {"Sensor guide": [{"Overview": "guide/01-overview.md"}, {"Design": "guide/02-design.md"}]}
    assert set(json.loads((project / "site" / MANIFEST).read_text(encoding="utf-8"))["files"]) == {
        "docs/guide/01-overview.md",
        "docs/guide/02-design.md",
        f"docs/guide/media/{picture.name}",
        "docs/guide/.gitignore",
    }


@needs_sh
def test_the_first_page_links_the_built_downloads(project, pandoc_runtime, caplog):
    text = (
        (project / "py-doc.yml")
        .read_text(encoding="utf-8")
        .replace("site: {engine: ENGINE}", "site: {engine: ENGINE, downloads: [pdf, docx]}")
    )
    text = text.replace(
        "    variables: {version: '1.0'}\n", "    variables: {version: '1.0'}\n    outputs: {docx: {}, pdf: {}}\n"
    )
    (project / "py-doc.yml").write_text(text, encoding="utf-8")
    (project / "build").mkdir()
    (project / "build" / "guide.pdf").write_bytes(b"%PDF-1.7 test")
    config, runtime = _site(project, "mkdocs", pandoc_runtime)
    generate_site(config, runtime)
    docs = project / "site" / "docs" / "guide"
    overview = (docs / "01-overview.md").read_text(encoding="utf-8")
    assert "# Overview\n\nDownload: [PDF](downloads/guide.pdf)\n" in overview
    assert (docs / "downloads" / "guide.pdf").read_bytes() == b"%PDF-1.7 test"
    assert "Download" not in (docs / "02-design.md").read_text(encoding="utf-8"), "only the first page links them"
    assert "guide.docx is not there" in caplog.text and "py-doc build guide" in caplog.text
    assert (
        "docs/guide/downloads/guide.pdf"
        in json.loads((project / "site" / MANIFEST).read_text(encoding="utf-8"))["files"]
    )


@needs_sh
def test_starlight_pages_have_asides_an_order_and_no_repeated_title(project, pandoc_runtime):
    config, runtime = _site(project, "starlight", pandoc_runtime)
    generate_site(config, runtime)
    overview = (project / "site" / "src" / "content" / "docs" / "guide" / "01-overview.md").read_text(encoding="utf-8")
    assert overview.startswith(
        "---\ntitle: Overview\nsidebar:\n  order: 1\n---\n\nVersion 1.0. See [the design](/guide/02-design/#flow)."
    )
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
    text = (
        (project / "py-doc.yml")
        .read_text(encoding="utf-8")
        .replace(", {file: docs/02_design.md, heading_offset: 1, page_break: true}", "")
    )
    (project / "py-doc.yml").write_text(text, encoding="utf-8")
    generate_site(load_config(project / "py-doc.yml"), runtime)
    assert not (project / "site" / "docs" / "guide" / "02-design.md").exists()
    assert (project / "site" / "docs" / "index.md").is_file(), "a page py-doc did not write stays"


def _with_posters(project, engine_name):
    (project / "posters").mkdir()
    (project / "posters" / "launch.md").write_text("---\ntitle: Launch & go\n---\n## A\n\nText.\n", encoding="utf-8")
    (project / "posters" / "plain.md").write_text("## B\n\nText.\n", encoding="utf-8")
    text = (
        (project / "py-doc.yml")
        .read_text(encoding="utf-8")
        .replace("site: {engine: ENGINE}", "site: {engine: ENGINE, posters: [launch, plain]}")
    )
    text += "posters:\n  launch: {source: posters/launch.md}\n  plain: {source: posters/plain.md}\n  other: {source: posters/plain.md}\n"
    (project / "py-doc.yml").write_text(text.replace("ENGINE", engine_name), encoding="utf-8")
    (project / "build").mkdir()
    (project / "build" / "launch.pdf").write_bytes(b"%PDF-1.7 poster")


@needs_sh
def test_mkdocs_has_the_posters_of_site_posters_and_a_page_that_links_them(project, pandoc_runtime):
    _with_posters(project, "mkdocs")
    config, runtime = _site(project, "mkdocs", pandoc_runtime)
    generate_site(config, runtime)
    folder = project / "site" / "docs" / "posters"
    assert "<title>Launch &amp; go</title>" in (folder / "launch.html").read_text(encoding="utf-8")
    assert (folder / "launch.pdf").read_bytes() == b"%PDF-1.7 poster"
    assert not (folder / "other.html").exists(), "only the posters site.posters names"
    assert (folder / "index.md").read_text(encoding="utf-8") == (
        "---\ntitle: Posters\n---\n\n# Posters\n\n- [Launch & go](launch.html) · [PDF](launch.pdf)\n- [plain](plain.html)\n"
    )
    nav = yaml.safe_load((project / "site" / MKDOCS_NAV).read_text(encoding="utf-8"))["nav"]
    assert nav[-1] == {"Posters": "posters/index.md"}
    files = json.loads((project / "site" / MANIFEST).read_text(encoding="utf-8"))["files"]
    assert "docs/posters/launch.html" in files and "docs/posters/index.md" in files
    text = (project / "py-doc.yml").read_text(encoding="utf-8").replace("posters: [launch, plain]", "posters: [plain]")
    (project / "py-doc.yml").write_text(text, encoding="utf-8")
    generate_site(load_config(project / "py-doc.yml"), runtime)
    assert not (folder / "launch.html").exists(), "a poster no longer listed is removed"


@needs_sh
def test_starlight_serves_the_posters_from_public(project, pandoc_runtime):
    _with_posters(project, "starlight")
    config, runtime = _site(project, "starlight", pandoc_runtime)
    generate_site(config, runtime)
    assert (project / "site" / "public" / "posters" / "plain.html").is_file()
    index = (project / "site" / "src" / "content" / "docs" / "posters" / "index.md").read_text(encoding="utf-8")
    assert (
        index
        == "---\ntitle: Posters\n---\n\n- [Launch & go](/posters/launch.html) · [PDF](/posters/launch.pdf)\n- [plain](/posters/plain.html)\n"
    )
    sidebar = json.loads((project / "site" / STARLIGHT_SIDEBAR).read_text(encoding="utf-8"))
    assert sidebar[-1] == {"label": "Posters", "link": "/posters/"}


def test_site_posters_must_be_posters_of_py_doc_yml(tmp_path):
    (tmp_path / "py-doc.yml").write_text("site: {engine: mkdocs, posters: [nope]}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="site.posters names 'nope', which is not under posters"):
        load_config(tmp_path / "py-doc.yml")
    (tmp_path / "p.md").write_text("## A\n", encoding="utf-8")
    (tmp_path / "py-doc.yml").write_text(
        "documents: {posters: {sources: [p.md]}}\nposters: {a: {source: p.md}}\nsite: {engine: mkdocs, posters: [a]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="a document of the site has that name"):
        load_config(tmp_path / "py-doc.yml")


@pytest.fixture
def nested(tmp_path):
    """A document whose sources are in folders: an index page at the top, a folder with one, a folder without."""
    docs = tmp_path / "content" / "primers"
    (docs / "cloud" / "images").mkdir(parents=True)
    (docs / "architecture").mkdir()
    Image.new("RGB", (4, 4), "blue").save(docs / "cloud" / "images" / "broker.png")
    (docs / "index.md").write_text("# Primers\n\nStart with [Kafka](cloud/kafka.md#topics).\n", encoding="utf-8")
    (docs / "cloud" / "index.md").write_text("# Cloud and messaging\n\nThe cloud primers.\n", encoding="utf-8")
    (docs / "cloud" / "kafka.md").write_text(
        "# Kafka\n\n## Topics\n\n![A broker](images/broker.png)\n\nSee [C4](../architecture/c4.md) and [the primers](../index.md).\n",
        encoding="utf-8",
    )
    (docs / "architecture" / "c4.md").write_text("# C4\n\nBack to [Kafka](../cloud/kafka.md).\n", encoding="utf-8")
    (tmp_path / "py-doc.yml").write_text(
        "project: {name: Notes}\ndocuments:\n  primers:\n    sources:\n      - content/primers/index.md\n"
        "      - content/primers/cloud/kafka.md\n      - {file: content/primers/cloud/index.md, heading_offset: 1}\n"
        "      - content/primers/architecture/c4.md\nsite: {engine: ENGINE}\n",
        encoding="utf-8",
    )
    return tmp_path


def _page(slug_: str, title: str) -> Page:
    return Page("primers", None, slug_, title, 0)


def test_the_navigation_nests_by_folder_with_the_index_page_first():
    items = nav_items(
        [
            _page("index", "Primers"),
            _page("cloud/kafka", "Kafka"),
            _page("cloud/index", "Cloud and messaging"),
            _page("iot-and-embedded/mqtt", "MQTT"),
            _page("cloud/deep/x", "X"),
        ]
    )
    assert items[0] == NavPage("Primers", "primers/index.md")
    cloud, iot = items[1:]
    assert cloud.title == "Cloud and messaging" and cloud.folder == "primers/cloud"
    assert cloud.pages[:2] == [
        NavPage("Cloud and messaging", "primers/cloud/index.md"),
        NavPage("Kafka", "primers/cloud/kafka.md"),
    ]
    assert cloud.pages[2] == NavSection("Deep", "primers/cloud/deep", [NavPage("X", "primers/cloud/deep/x.md")])
    assert iot.title == "Iot and embedded", "a folder without an index page is named after the folder"


def test_nested_navigation_for_mkdocs_and_starlight(tmp_path):
    section = NavSection(
        "Primers",
        "primers",
        nav_items([_page("index", "Primers"), _page("cloud/index", "Cloud"), _page("cloud/kafka", "Kafka")]),
    )
    engine = engine_for("mkdocs", tmp_path)
    nav = yaml.safe_load(engine.write_nav([section]).read_text(encoding="utf-8"))["nav"]
    assert nav == [
        {
            "Primers": [
                {"Primers": "primers/index.md"},
                {"Cloud": [{"Cloud": "primers/cloud/index.md"}, {"Kafka": "primers/cloud/kafka.md"}]},
            ]
        }
    ]
    sidebar = json.loads(engine_for("starlight", tmp_path / "astro").write_nav([section]).read_text(encoding="utf-8"))
    assert sidebar == [
        {
            "label": "Primers",
            "items": [
                {"slug": "primers"},
                {"label": "Cloud", "items": [{"slug": "primers/cloud"}, {"slug": "primers/cloud/kafka"}]},
            ],
        }
    ]


def test_a_site_path_must_stay_below_the_document_folder(tmp_path):
    for bad in ("../x", "/x", "a//b", "."):
        (tmp_path / "py-doc.yml").write_text(
            f"documents:\n  a: {{sources: [{{file: a.md, site_path: '{bad}'}}]}}\n", encoding="utf-8"
        )
        with pytest.raises(ConfigError, match="site_path"):
            load_config(tmp_path / "py-doc.yml")
    (tmp_path / "py-doc.yml").write_text(
        "documents:\n  a: {sources: [{file: a.md, site_path: cloud/Kafka.md}]}\n", encoding="utf-8"
    )
    assert load_config(tmp_path / "py-doc.yml").documents["a"].sources[0].site_path == "cloud/Kafka"


@needs_sh
def test_pages_keep_their_folders_and_the_nav_nests(nested, pandoc_runtime):
    config, runtime = _site(nested, "mkdocs", pandoc_runtime)
    generate_site(config, runtime)
    docs = nested / "site" / "docs" / "primers"
    assert "[Kafka](cloud/kafka.md#topics)" in (docs / "index.md").read_text(encoding="utf-8")
    kafka = (docs / "cloud" / "kafka.md").read_text(encoding="utf-8")
    assert "[C4](../architecture/c4.md)" in kafka and "[the primers](../index.md)" in kafka
    (picture,) = (docs / "cloud" / "media").iterdir()
    assert f"](media/{picture.name})" in kafka, "a picture goes beside its page"
    assert "[Kafka](../cloud/kafka.md)" in (docs / "architecture" / "c4.md").read_text(encoding="utf-8")
    nav = yaml.safe_load((nested / "site" / MKDOCS_NAV).read_text(encoding="utf-8"))["nav"]
    assert nav[-1] == {
        "Primers": [
            {"Primers": "primers/index.md"},
            {
                "Cloud and messaging": [
                    {"Cloud and messaging": "primers/cloud/index.md"},
                    {"Kafka": "primers/cloud/kafka.md"},
                ]
            },
            {"Architecture": [{"C4": "primers/architecture/c4.md"}]},
        ]
    }


@needs_sh
def test_starlight_links_reach_pages_in_folders(nested, pandoc_runtime):
    config, runtime = _site(nested, "starlight", pandoc_runtime)
    generate_site(config, runtime)
    kafka = (nested / "site" / "src" / "content" / "docs" / "primers" / "cloud" / "kafka.md").read_text(
        encoding="utf-8"
    )
    assert "[C4](/primers/architecture/c4/)" in kafka and "[the primers](/primers/)" in kafka


@needs_sh
def test_a_site_path_moves_a_page_and_a_clash_is_reported(nested, pandoc_runtime):
    text = (nested / "py-doc.yml").read_text(encoding="utf-8")
    moved = text.replace(
        "- content/primers/architecture/c4.md", "- {file: content/primers/architecture/c4.md, site_path: cloud/c4}"
    )
    (nested / "py-doc.yml").write_text(moved, encoding="utf-8")
    config, runtime = _site(nested, "mkdocs", pandoc_runtime)
    generate_site(config, runtime)
    docs = nested / "site" / "docs" / "primers"
    assert (docs / "cloud" / "c4.md").is_file() and not (docs / "architecture").exists()
    assert "[C4](c4.md)" in (docs / "cloud" / "kafka.md").read_text(encoding="utf-8")
    clash = (nested / "py-doc.yml").read_text(encoding="utf-8").replace("site_path: cloud/c4", "site_path: cloud/Kafka")
    (nested / "py-doc.yml").write_text(clash, encoding="utf-8")
    with pytest.raises(ConversionError, match=r"would both be the page primers/cloud/kafka\.md"):
        generate_site(load_config(nested / "py-doc.yml"), runtime)


def test_a_site_must_be_made_first(project):
    (project / "py-doc.yml").write_text(
        (project / "py-doc.yml").read_text(encoding="utf-8").replace("ENGINE", "mkdocs"), encoding="utf-8"
    )
    with pytest.raises(ConversionError, match="py-doc site init"):
        generate_site(load_config(project / "py-doc.yml"), lambda: None)


# --- command ----------------------------------------------------------------------------------------


def test_site_init_makes_the_site_named_in_py_doc_yml(project, monkeypatch, capsys):
    (project / "py-doc.yml").write_text(
        (project / "py-doc.yml").read_text(encoding="utf-8").replace("ENGINE", "starlight"), encoding="utf-8"
    )
    monkeypatch.chdir(project)
    assert main(["site", "init"]) == 0
    assert (project / "site" / "astro.config.mjs").is_file() and "Next: py-doc site build" in capsys.readouterr().out
    assert main(["site", "init"]) == 0
    assert "already there" in capsys.readouterr().out
    assert main(["site", "init", "--engine", "mkdocs"]) == 1


def test_site_build_checks_the_targets_before_building(project, monkeypatch, capsys):
    text = (project / "py-doc.yml").read_text(encoding="utf-8")
    monkeypatch.chdir(project)
    (project / "py-doc.yml").write_text(
        text.replace(
            "site: {engine: ENGINE}", "site: {engine: mkdocs, targets: {github: mkdocs.yml, tarf: mkdocs.tarf.yml}}"
        ),
        encoding="utf-8",
    )
    engine_for("mkdocs", project / "site").scaffold("x")
    (project / "site" / "mkdocs.tarf.yml").write_text("INHERIT: mkdocs.yml\n", encoding="utf-8")
    assert main(["site", "build", "--target", "other"]) == 1
    assert "--target other is not in site.targets. Defined: github, tarf" in capsys.readouterr().err
    assert main(["site", "build"]) == 1
    assert "github and tarf both build to" in capsys.readouterr().err


def test_site_init_without_a_site_section_says_what_to_add(tmp_path, monkeypatch, capsys):
    (tmp_path / "py-doc.yml").write_text("documents:\n  a: {sources: [a.md]}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["site", "init"]) == 1
    assert main(["site", "init", "--engine", "mkdocs"]) == 0
    assert "site:\n  engine: mkdocs\n  dir: site" in capsys.readouterr().out


def test_groups_put_documents_under_one_section_where_the_first_would_be():
    from py_doc.site.pages import grouped

    sections = {name: NavSection(name.upper(), name, []) for name in "abcd"}
    result = grouped(list("abcd"), sections, {"Reference": ["c", "b"]})
    assert [s.title for s in result] == ["A", "Reference", "D"]
    assert [s.title for s in result[1].pages] == ["C", "B"] and result[1].nested


def test_a_documents_properties_go_in_the_front_matter_of_its_first_page():
    from py_doc.markdown import Metadata
    from py_doc.site.pages import page_meta

    meta = Metadata(title="Guide", version="1.2", status="Draft", document_id="DOC-7", extra={"description": "How to"})
    assert page_meta(meta) == {"description": "How to", "document_id": "DOC-7", "version": "1.2", "status": "Draft"}
