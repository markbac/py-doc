"""The pages of a site: each source file of each document becomes one page, in a folder per document.

The Markdown goes through the same steps as every other output (includes, variables, conditions, generated
C4 chapters, diagrams drawn as SVG) and then through pandoc with ``site.lua``, which writes Markdown the
site's own tool reads: admonitions for MkDocs, asides for Starlight. Pictures are copied beside the pages,
links between source files point at the pages made from them, and nothing py-doc did not write itself is
ever replaced (a manifest in the site folder lists what it wrote).
"""

from __future__ import annotations

import hashlib
import json
import logging
import posixpath
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from py_doc.build import _combine_metadata
from py_doc.c4 import source as c4_source
from py_doc.config import ProjectConfig
from py_doc.diagrams import render_parts
from py_doc.errors import ConversionError
from py_doc.pandoc.engine import INPUT_FORMAT, RESOURCES
from py_doc.pandoc.source import first_heading, join_sources
from py_doc.runtime import Mount, Runtime

from .engines import Engine, NavPage, NavSection, engine_for

logger = logging.getLogger(__name__)

MANIFEST = ".py-doc-site.json"
FILTERS = ("admonitions.lua", "pagebreak.lua", "markers.lua", "site.lua")
OUTPUT_FORMAT = "gfm"  # pipe tables, task lists and raw HTML. site.lua writes the maths
TIMEOUT = 900
_LINK = re.compile(r"(?P<lead>!?\[(?:[^\]\\]|\\.)*\]\()(?P<target><[^>]*>|[^)\s]+)(?P<rest>[^)]*\))")
_HTML_SRC = re.compile(r'(?P<lead><img\b[^>]*?\bsrc=")(?P<target>[^"]+)(?P<rest>")')
# Code first (fenced blocks, then inline code of any number of backticks), else a run of text up to the next backtick
_CODE_OR_TEXT = re.compile(
    r"(?P<code>^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)[ \t]*$|(?P<ticks>`+).+?(?<!`)(?P=ticks)(?!`))|(?P<text>[^`]+|`)",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class Page:
    document: str
    source: Path
    slug: str
    title: str
    order: int
    markdown: str = ""
    pictures: dict[str, Path] = field(default_factory=dict)

    @property
    def path(self) -> str:
        """Below the content folder: guide/overview.md."""
        return f"{self.document}/{self.slug}.md"


def slug(text: str) -> str:
    """A page or folder name both MkDocs and Starlight keep as it is: lower case letters, digits and -."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "page"


def generate_site(
    config: ProjectConfig,
    runtime: Callable[[], Runtime],
    variables: dict | None = None,
    conditions: dict | None = None,
) -> tuple[Engine, list[Path]]:
    """Write the pages and the navigation of ``config.site``. Returns the engine and the files written."""
    site = config.site
    if site is None:
        raise ConversionError("py-doc.yml has no site section. Add one, such as `site: {engine: mkdocs}`")
    engine = engine_for(site.engine, site.dir)
    if not engine.exists():
        raise ConversionError(f"There is no {site.engine} site in {site.dir}. Run `py-doc site init` to make one")
    names = site.documents or list(config.documents)
    pages: list[Page] = []
    sections: list[NavSection] = []
    for name in names:
        title, made = _pages_of(config, name, runtime, variables or {}, conditions or {})
        sections.append(NavSection(title, name, [NavPage(page.title, page.path) for page in made]))
        pages += made
    _convert(pages, site.engine, runtime())
    written = _write(pages, engine)
    written.append(engine.write_nav(sections))
    for advice in engine.check():
        logger.warning(advice)
    return engine, written


def _pages_of(config: ProjectConfig, name: str, runtime, variables: dict, conditions: dict) -> tuple[str, list[Page]]:
    """The title and the pages of one document, with their diagrams drawn.

    The title is the document's own (py-doc.yml, then the first source's front matter, then its first heading).
    A page break or a heading offset means nothing on a site, so both are left out.
    """
    doc = config.documents[name]
    sources = c4_source.expand(list(doc.sources), doc.id, config.root, runtime, config.c4)
    sources = [replace(s, heading_offset=0, page_break=False) for s in sources if s.include]
    joined = join_sources(sources, {**doc.variables, **variables}, {**doc.conditions, **conditions}, doc.id)
    metadata = _combine_metadata(doc, joined.metadata, joined.first_heading, config.root)
    pages: list[Page] = []
    used: set[str] = set()
    for order, (file, text) in enumerate(joined.parts, start=1):
        name_ = slug(file.stem)
        while name_ in used:
            name_ += "-2"
        used.add(name_)
        title = first_heading(text) or (metadata.title if order == 1 else file.stem)
        rendered = render_parts([(file, text)], "html", runtime)
        pages.append(Page(name, file, name_, title, order, rendered.markdown, rendered.pictures))
    return metadata.title or name, pages


def _convert(pages: list[Page], engine: str, runtime: Runtime) -> None:
    """Run pandoc once, in one container, for every page."""
    if not pages:
        return
    with tempfile.TemporaryDirectory(prefix="py-doc-site-") as folder:
        work = Path(folder)
        lines = ["set -e"]
        filters = " ".join(f"--lua-filter '{runtime.container_path(RESOURCES / name)}'" for name in FILTERS)
        for number, page in enumerate(pages):
            (work / f"{number}.md").write_text(page.markdown, encoding="utf-8", newline="\n")
            source, target = runtime.container_path(work / f"{number}.md"), runtime.container_path(work / f"{number}.out")
            lines.append(
                f"pandoc '{source}' --from={INPUT_FORMAT} {filters} -M site-engine={engine} "
                f"--to={OUTPUT_FORMAT} --wrap=none --output '{target}'"
            )
        (work / "pages.sh").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        result = runtime.run(["sh", work / "pages.sh"], mounts=[Mount(RESOURCES), Mount(work, writable=True)], workdir=work, timeout=TIMEOUT)
        for line in result.stderr.splitlines():
            if line.startswith("[WARNING]"):
                logger.warning(f"pandoc: {line.removeprefix('[WARNING]').strip()}")
        for number, page in enumerate(pages):
            page.markdown = (work / f"{number}.out").read_text(encoding="utf-8")


def _write(pages: list[Page], engine: Engine) -> list[Path]:
    """Put the pages, their pictures and their front matter in the content folder, replacing only py-doc's own files."""
    content = engine.content
    manifest = engine.root / MANIFEST
    before = set(json.loads(manifest.read_text(encoding="utf-8")).get("files", [])) if manifest.is_file() else set()
    by_source = {page.source.resolve(): page for page in pages}
    files: dict[Path, bytes] = {}
    for page in pages:
        text = _relink(page, by_source, engine.name, files, content)
        front = {"title": page.title}
        if engine.name == "starlight":
            front["sidebar"] = {"order": page.order}
        header = "---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False) + "---\n\n"
        files[content / page.path] = (header + text.rstrip() + "\n").encode("utf-8")
        files[content / page.document / ".gitignore"] = b"# Written by py-doc site: built from the sources, so not kept in Git\n*\n"

    def relative(path: Path) -> str:
        return path.relative_to(engine.root).as_posix()

    clashes = [path for path in files if path.exists() and relative(path) not in before]
    if clashes:
        raise ConversionError(f"{clashes[0]} is already there and py-doc did not write it, so it is left alone. Move it, or leave the document out of site.documents")
    for old in sorted(before - {relative(p) for p in files}):
        (engine.root / old).unlink(missing_ok=True)  # a page or picture of an earlier run that is gone now
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    manifest.write_text(json.dumps({"files": sorted(relative(p) for p in files)}, indent=1) + "\n", encoding="utf-8")
    logger.info(f"Wrote {len(pages)} page(s) to {content}")
    return sorted(files)


def _relink(page: Page, by_source: dict[Path, Page], engine: str, files: dict[Path, bytes], content: Path) -> str:
    """Point links at the pages made from their source files, and copy the pictures the page shows."""
    folder = content / page.document

    def picture(target: str) -> str | None:
        if target in page.pictures:  # a diagram, drawn under diagrams/
            files[folder / target] = page.pictures[target].read_bytes()
            return target
        found = (page.source.parent / target).resolve()
        if not found.is_file():
            logger.warning(f"{page.source}: the picture {target} was not found")
            return None
        digest = hashlib.sha256(found.read_bytes()).hexdigest()[:8]
        name = f"media/{digest}-{found.name}"
        files[folder / name] = found.read_bytes()
        return name

    def page_link(target: str) -> str | None:
        path, _, anchor = target.partition("#")
        if not path.lower().endswith((".md", ".markdown")):
            return None
        other = by_source.get((page.source.parent / path).resolve())
        if other is None:
            return None
        if engine == "starlight":
            url = f"/{other.document}/{other.slug}/"
        else:
            url = posixpath.relpath(other.path, page.document)
        return url + (f"#{anchor}" if anchor else "")

    def swap(match: re.Match) -> str:
        target = match["target"].strip("<>")
        if re.match(r"^([a-z][a-z0-9+.-]*:|#|/)", target, re.IGNORECASE):
            return match.group(0)  # a web address, an anchor on this page, or a path from the site root
        if match["lead"].startswith("!") or match["lead"].startswith("<img"):
            new = picture(target)
        else:
            new = page_link(target)
        return f"{match['lead']}{new}{match['rest']}" if new else match.group(0)

    def outside_code(match: re.Match) -> str:
        if match["code"]:
            return match["code"]  # a fenced block or inline code shows the text as it is
        text = match["text"]
        return _HTML_SRC.sub(swap, _LINK.sub(swap, text))

    return _CODE_OR_TEXT.sub(outside_code, page.markdown)
