"""Icons in poster blocks: the packs, their download and checksum, a project's own icons, credits and the report."""

from __future__ import annotations

import hashlib
import io
import json
import re
import tarfile
import textwrap
from pathlib import Path

import pytest

from py_doc import icons
from py_doc.icons import PACKS, IconError, Icons, Pack
from py_doc.icons_cli import run_icons
from py_doc.poster import PosterError, build

REAL = Path(icons.__file__).parent / "runtime" / "definition"

TABLER = {
    "prefix": "tabler", "width": 24, "height": 24,
    "icons": {
        "server": {"body": '<path stroke="currentColor" d="M3 4h18v6H3z"/>'},
        "router": {"body": '<path d="M1 1h2"/>'},
        "gradient": {"body": '<defs><linearGradient id="a"/></defs><path fill="url(#a)" d="M0 0"/><use href="#a"/>'},
    },
    "aliases": {"servers": {"parent": "server"}},
}  # fmt: skip
MDI = {"prefix": "mdi", "width": 24, "height": 24, "icons": {"router": {"body": "<b/>"}, "chip": {"body": "<c/>"}}}
LOGOS = {
    "prefix": "logos",
    "width": 256,
    "height": 256,
    "icons": {"docker": {"body": "<d/>", "width": 256, "height": 185}},
}


def tarball(data: dict) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as archive:
        for name, content in (("icons.json", data), ("info.json", {"license": {"spdx": "MIT"}})):
            raw = json.dumps(content).encode()
            info = tarfile.TarInfo(f"package/{name}")
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    return out.getvalue()


@pytest.fixture
def packs(tmp_path, monkeypatch):
    """Small packs served by a fake npm registry, into a cache of the test's own. Returns the addresses asked."""
    monkeypatch.setenv("PY_DOC_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(icons, "_loaded", {})
    served, asked = {}, []
    fakes = {}
    for data in (TABLER, MDI, LOGOS):
        raw = tarball(data)
        old = PACKS[data["prefix"]]
        fake = Pack(old.prefix, old.version, hashlib.sha256(raw).hexdigest(), old.licence, old.title, old.credit)
        fakes[fake.prefix] = fake
        served[fake.url] = raw
    monkeypatch.setattr(icons, "PACKS", {**PACKS, **fakes})

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(url, timeout=None):
        asked.append(url)
        if url not in served:
            raise OSError("no network")
        return Response(served[url])

    monkeypatch.setattr(icons.urllib.request, "urlopen", urlopen)
    return asked


# --- the packs ---------------------------------------------------------------------------------------


def test_the_packs_are_the_versions_of_the_tool_image():
    """A poster block and a Mermaid diagram draw the same icon: the host's packs are the image's."""
    package = json.loads((REAL / "package.json").read_text(encoding="utf-8"))["dependencies"]
    for pack in PACKS.values():
        assert package[f"@iconify-json/{pack.prefix}"] == pack.version, pack.prefix
        assert re.fullmatch(r"[0-9a-f]{64}", pack.sha256)
    from py_doc.diagrams.registry import ICON_PACKS

    assert set(ICON_PACKS) == set(PACKS)


def test_a_pack_is_downloaded_once_and_kept(packs, tmp_path):
    first = icons.fetch("tabler")
    assert first == tmp_path / "cache" / "icons" / f"tabler-{PACKS['tabler'].version}" / "icons.json"
    assert (first.parent / "info.json").is_file()  # the licence stays with the icons
    icons.fetch("tabler")
    assert len(packs) == 1


def test_a_pack_with_another_checksum_is_refused(packs, monkeypatch):
    pack = icons.PACKS["tabler"]
    monkeypatch.setitem(icons.PACKS, "tabler", Pack(pack.prefix, pack.version, "0" * 64, pack.licence, pack.title))
    with pytest.raises(IconError, match="SHA-256"):
        icons.fetch("tabler")
    assert not icons.pack_dir(pack).joinpath("icons.json").exists()


def test_no_network_says_how_to_bring_the_packs_in(packs, monkeypatch):
    monkeypatch.setattr(icons.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    with pytest.raises(IconError, match="py-doc icons fetch"):
        icons.fetch("tabler")


# --- names ---------------------------------------------------------------------------------------


def test_a_prefixed_name_comes_from_its_pack(packs):
    found = Icons().get("logos:docker")
    assert (found.name, found.width, found.height, found.licence) == ("logos:docker", 256, 185, "CC0-1.0")


def test_a_bare_name_is_tabler_then_mdi(packs):
    found = Icons()
    assert found.get("router").name == "tabler:router"
    assert found.get("chip").name == "mdi:chip"


def test_an_alias_is_the_icon_it_names(packs):
    assert Icons().get("tabler:servers").name == "tabler:server"


def test_an_unknown_icon_or_pack_says_where_it_looked(packs):
    with pytest.raises(IconError, match="no icon 'tabler:nothing' in the Tabler Icons"):
        Icons().get("tabler:nothing")
    with pytest.raises(IconError, match="no icon pack fontawesome"):
        Icons().get("fontawesome:x")
    with pytest.raises(IconError, match="not an icon name"):
        Icons().get("two words")


def test_each_use_of_an_icon_has_ids_of_its_own(packs):
    """Two copies of an icon with a gradient on one page must not point at each other's gradient."""
    found = Icons()
    one, two = found.svg("tabler:gradient"), found.svg("tabler:gradient")
    ids = re.findall(r' id="([^"]+)"', one + two)
    assert len(ids) == len(set(ids)) == 2
    for svg in (one, two):
        own = re.search(r' id="([^"]+)"', svg)[1]
        assert f"url(#{own})" in svg and f'href="#{own}"' in svg


def test_an_icon_is_drawn_in_the_text_colour_at_the_size_asked(packs):
    svg = Icons().svg("tabler:server", "2em")
    assert 'viewBox="0 0 24 24"' in svg and 'width="2em"' in svg and 'stroke="currentColor"' in svg
    assert 'aria-hidden="true"' in svg


# --- a project's own icons -----------------------------------------------------------------------------


def own_icons(tmp_path, notes: str = "") -> Path:
    folder = tmp_path / "icons"
    folder.mkdir(parents=True)
    (folder / "router.svg").write_text('<svg viewBox="2 2 10 10"><rect width="4" height="4"/></svg>', encoding="utf-8")
    (folder / "valve.svg").write_text('<svg width="20" height="10"><path d="M0 0"/></svg>', encoding="utf-8")
    if notes:
        (folder / "icons.yml").write_text(notes, encoding="utf-8")
    return folder


def test_a_project_icon_comes_before_the_packs(packs, tmp_path):
    found = Icons(own_icons(tmp_path)).get("router")
    assert (found.name, found.source, found.width) == ("router", "project", 10)
    assert "translate(-2 -2)" in found.body  # its view box starts at 0 0 on the poster
    assert Icons(own_icons(tmp_path / "b")).get("valve").height == 10  # no viewBox: its width and height


def test_a_cc_by_project_icon_needs_a_credit_and_gets_one(packs, tmp_path):
    with pytest.raises(IconError, match="needs a credit"):
        Icons(own_icons(tmp_path, "router: {licence: CC-BY-4.0}\n")).get("router")
    found = Icons(own_icons(tmp_path / "b", "router: {licence: CC-BY-4.0, credit: 'Router by A. Artist'}\n"))
    found.get("router")
    assert found.credits() == ["Router by A. Artist"]
    cc0 = Icons(own_icons(tmp_path / "c", "router: {licence: CC0-1.0}\n"))
    cc0.get("router")
    assert cc0.credits() == []


# --- on a poster ---------------------------------------------------------------------------------


POSTER = textwrap.dedent(
    """\
    ---
    title: Icons
    icons: icons
    footer:
      credits: Photos from the NASA image library
    ---

    ## Key figures {.stats}

    | Value | Label |
    |---|---|
    | 3 | Gateways | icon=tabler:router |
    | 12 | Months |

    ## Blocks

    ```cards
    Server | Stores readings | icon=tabler:server
    Plain | No icon
    ```

    ```steps
    Fit it | One a floor | icon=router
    ```

    ```highlight
    0 | Failed | icon=mdi:chip | good
    ```

    ```flow
    [Asleep|navy|icon=tabler:server] -timer-> [Done|icon=logos:docker]
    ```
    """
)


def poster(tmp_path, text=POSTER):
    source = tmp_path / "poster.md"
    source.write_text(text, encoding="utf-8")
    own_icons(tmp_path, "router: {licence: CC-BY-4.0, credit: 'Router icon by A. Artist (CC BY 4.0)'}\n")
    return build(source, lambda: None)


def test_every_block_takes_an_icon(packs, tmp_path):
    page, ctx = poster(tmp_path)
    assert page.count('class="icon"') == 6
    assert re.search(r'<div class="stat"><span class="ico"><svg', page)
    assert re.search(r'<div class="ch"><span class="ico"><svg[^>]*>.*?</svg></span>Server', page)
    # in a flow, the icon is SVG in the picture, white on a filled box, in the text colour on an outlined one
    assert re.search(r'<g transform="translate\([^)]+\)" color="#fff"><svg class="icon"', page)
    assert re.search(r'<g transform="translate\([^)]+\)" color="currentColor"><svg class="icon"', page)
    assert "icon=" not in page  # the cell is taken out, not shown


def test_the_footer_credits_the_pictures_and_the_icons_that_ask(packs, tmp_path):
    page, _ = poster(tmp_path)
    credits = re.search(r'<div class="credits">(.*?)</div>', page)[1]
    assert credits == "Photos from the NASA image library · Router icon by A. Artist (CC BY 4.0)"


def test_the_icons_used_are_listed_with_their_licences(packs, tmp_path):
    _, ctx = poster(tmp_path)
    assert ctx.icons.manifest() == [
        {"name": "logos:docker", "source": "logos", "licence": "CC0-1.0"},
        {"name": "mdi:chip", "source": "Material Design Icons", "licence": "Apache-2.0"},
        {"name": "router", "source": "project", "licence": "CC-BY-4.0"},
        {"name": "tabler:router", "source": "Tabler Icons", "licence": "MIT"},
        {"name": "tabler:server", "source": "Tabler Icons", "licence": "MIT"},
    ]


def test_an_unknown_icon_stops_the_poster_with_its_file(packs, tmp_path):
    with pytest.raises(PosterError, match=r"poster\.md: there is no icon 'tabler:nope'"):
        poster(tmp_path, "## A\n\n```cards\nA | b | icon=tabler:nope\n```\n")


def test_a_poster_without_icons_downloads_nothing(packs, tmp_path):
    poster(tmp_path, "## A\n\n```cards\nA | b\n```\n")
    assert packs == []


def test_the_build_report_lists_a_posters_icons(packs, tmp_path, monkeypatch):
    import jsonschema

    from py_doc.app import main

    (tmp_path / "py-doc.yml").write_text(
        "posters:\n  p:\n    source: poster.md\nreports:\n  path: report.json\n", encoding="utf-8"
    )
    (tmp_path / "poster.md").write_text(POSTER, encoding="utf-8")
    own_icons(tmp_path, "router: {licence: CC-BY-4.0, credit: 'Router by A. Artist'}\n")
    monkeypatch.chdir(tmp_path)
    assert main(["build", "-f", "poster"]) == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    schema = json.loads((Path(icons.__file__).parent / "report.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(report, schema)
    listed = report["documents"][0]["icons"]
    assert {"name": "mdi:chip", "source": "Material Design Icons", "licence": "Apache-2.0"} in listed


# --- py-doc icons ----------------------------------------------------------------------------------


def test_icons_fetch_list_and_search(packs, capsys):
    assert run_icons(["fetch", "tabler", "mdi"]) == 0
    assert run_icons(["list"]) == 0
    listing = capsys.readouterr().out
    assert re.search(r"tabler\s+\S+\s+MIT\s+Tabler Icons \(downloaded\)", listing)
    assert re.search(r"logos .*\(not downloaded yet\)", listing)
    assert run_icons(["search", "serv", "--pack", "tabler"]) == 0
    assert capsys.readouterr().out.split() == ["tabler:server", "tabler:servers"]


def test_icons_fetch_refuses_an_unknown_pack(packs):
    with pytest.raises(SystemExit):
        run_icons(["fetch", "nope"])
