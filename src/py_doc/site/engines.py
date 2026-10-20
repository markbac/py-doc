"""What differs between MkDocs and Astro + Starlight: where pages go, the navigation, the scaffold and the build.

py-doc never edits a site's own configuration. It writes the pages into a folder per document, and the
navigation into a file of its own that the configuration takes in:

- MkDocs: ``py-doc-nav.yml``, which ``mkdocs.yml`` inherits (``INHERIT: py-doc-nav.yml``). A ``nav`` in
  ``mkdocs.yml`` itself still wins, so a hand-made navigation is kept.
- Starlight: ``src/py-doc-sidebar.json``, which ``astro.config.mjs`` passes to Starlight as its sidebar.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from py_doc.errors import ConversionError
from py_doc.runtime import Mount, Runtime

logger = logging.getLogger(__name__)

MKDOCS_NAV = "py-doc-nav.yml"
STARLIGHT_SIDEBAR = "src/py-doc-sidebar.json"
TIMEOUT = 1800  # the first npm install of an Astro site downloads a few hundred packages

# The versions a new Starlight site starts from. npm install takes the newest that match.
STARLIGHT_PACKAGES = {
    "@astrojs/markdown-remark": "^7.3.2",  # Astro 7 runs remark plugins (maths) only with it installed
    "@astrojs/starlight": "^0.42.6",
    "astro": "^7.3.8",
    "katex": "^0.19.0",
    "rehype-katex": "^7.0.1",
    "remark-math": "^6.0.0",
    "sharp": "^0.35.5",
}


@dataclass
class NavPage:
    title: str
    path: str  # below the content folder, with / separators: guide/overview.md


@dataclass
class NavSection:
    """A document, or a folder of its pages. A folder's index page, when there is one, comes first."""

    title: str
    folder: str  # below the content folder: guide, or guide/cloud
    pages: list[NavPage | NavSection]

    @property
    def nested(self) -> bool:
        return any(isinstance(item, NavSection) for item in self.pages)


class Engine:
    """One site generator. ``root`` is the site project folder (``site.dir``)."""

    name = ""
    marker = ""  # the file that shows a site of this kind is there

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def exists(self) -> bool:
        return (self.root / self.marker).is_file()

    @property
    def content(self) -> Path:
        """The folder the pages go in."""
        raise NotImplementedError

    def scaffold(self, title: str) -> list[Path]:
        """Write the files of a new site that are missing. Returns the files written."""
        written = []
        for name, text in self.files(title).items():
            path = self.root / name
            if path.exists():
                logger.info(f"Kept {path}: it is already there")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
        return written

    def files(self, title: str) -> dict[str, str]:
        raise NotImplementedError

    def write_nav(self, sections: list[NavSection], pages: dict[str, str] | None = None) -> Path:
        """Write the navigation: a section per document, then the hand-written ``pages`` (title: path below the content folder)."""
        raise NotImplementedError

    def check(self, config_file: str | None = None) -> list[str]:
        """What the site's own configuration lacks to show the generated pages and navigation."""
        return []

    def build(self, runtime: Runtime, config_file: str | None = None) -> Path:
        """Build the site in the tool container. Returns the folder the site was written to."""
        raise NotImplementedError

    def downloads(self, document: str) -> tuple[Path, str]:
        """Where a document's downloadable files go, and how its pages link to that folder."""
        return self.content / document / "downloads", "downloads"

    def posters(self, folder: str) -> tuple[Path, str]:
        """Where the poster pages go, and how the Posters page (``folder``/index.md) links to them."""
        return self.content / folder, ""


# --- MkDocs ---------------------------------------------------------------------------------------


class _Loose(yaml.SafeLoader):
    """Reads mkdocs.yml, whose !!python/name and !ENV tags mean nothing here."""


_Loose.add_multi_constructor("", lambda loader, suffix, node: None)
_Loose.add_multi_constructor("!", lambda loader, suffix, node: None)


class MkDocs(Engine):
    name = "mkdocs"
    marker = "mkdocs.yml"

    def _config(self, config_file: str | None = None) -> dict:
        """The settings of a config file, with the files it INHERITs merged under it as MkDocs does."""
        return self._read(self.root / (config_file or self.marker), [])

    def _read(self, path: Path, seen: list[Path]) -> dict:
        if not path.is_file() or path.resolve() in seen:
            return {}
        try:
            data = yaml.load(path.read_text(encoding="utf-8"), Loader=_Loose)  # noqa: S506 - a safe loader that ignores tags
        except yaml.YAMLError as exc:
            raise ConversionError(f"{path} is not valid YAML: {exc}") from exc
        data = data if isinstance(data, dict) else {}
        parent = data.get("INHERIT")
        if not isinstance(parent, str):
            return data
        base = self._read(path.parent / parent, [*seen, path.resolve()])
        return {**base, **data, "INHERITS": [parent, *base.get("INHERITS", [])]}

    @property
    def content(self) -> Path:
        return self.root / str(self._config().get("docs_dir") or "docs")

    def files(self, title: str) -> dict[str, str]:
        return {
            "mkdocs.yml": MKDOCS_YML.format(title=json.dumps(title)),
            "docs/index.md": f"# {title}\n\nThe documents are in the navigation. py-doc writes them; this page is yours.\n",
            ".gitignore": "build/\n.py-doc-site.json\n",
        }

    def write_nav(self, sections: list[NavSection], pages: dict[str, str] | None = None) -> Path:
        nav: list = []
        if (self.content / "index.md").is_file():
            nav.append({"Home": "index.md"})
        for section in sections:
            entries = _mkdocs_entries(section.pages)
            nav.append(entries[0] if len(entries) == 1 and not section.nested else {section.title: entries})  # one page: no section
        nav += [{title: path} for title, path in (pages or {}).items()]
        path = self.root / MKDOCS_NAV
        header = "# Written by py-doc site from py-doc.yml. mkdocs.yml takes it in with INHERIT: py-doc-nav.yml\n"
        path.write_text(header + yaml.safe_dump({"nav": nav}, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def check(self, config_file: str | None = None) -> list[str]:
        path = self.root / (config_file or self.marker)
        if config_file and not path.is_file():
            return [f"{path} is not there. site.targets names it"]
        config = self._config(config_file)
        if config_file and self.root / str(config.get("docs_dir") or "docs") != self.content:
            return [f"{path} reads its pages from {config.get('docs_dir')}, but py-doc writes them to {self.content}. Leave docs_dir to {self.marker}"]
        if MKDOCS_NAV in config.get("INHERITS", []):
            return []
        if "nav" in config:
            return [f"{path} has its own nav, so that is the navigation. {MKDOCS_NAV} lists the pages py-doc wrote"]
        return [f"Add `INHERIT: {MKDOCS_NAV}` to {path} (or to a file it inherits) to use the navigation py-doc writes"]

    def site_dir(self, config_file: str | None = None) -> Path:
        """Where a config file builds its site to."""
        return self.root / str(self._config(config_file).get("site_dir") or "site")

    def build(self, runtime: Runtime, config_file: str | None = None) -> Path:
        config = self.root / (config_file or self.marker)
        if config_file and not config.is_file():
            raise ConversionError(f"{config} is not there, so that site cannot be built. site.targets names it")
        runtime.run(["mkdocs", "build", "--config-file", config], mounts=[Mount(self.root, writable=True)], workdir=self.root, timeout=TIMEOUT)
        return self.site_dir(config_file)


def _mkdocs_entries(items: list[NavPage | NavSection]) -> list[dict]:
    """A page as {title: path}, a folder as {title: [its entries]}: with navigation.indexes, its index page leads it."""
    return [{item.title: _mkdocs_entries(item.pages)} if isinstance(item, NavSection) else {item.title: item.path} for item in items]


MKDOCS_YML = """\
# Made by `py-doc site init`. Change anything here: py-doc writes only the pages (a folder per document
# under docs/) and the navigation (py-doc-nav.yml, taken in by INHERIT). A nav: here replaces that one.
INHERIT: py-doc-nav.yml
site_name: {title}
docs_dir: docs
site_dir: build
theme:
  name: material
  features: [navigation.sections, navigation.indexes, content.code.copy]
markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - tables
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tasklist: {{custom_checkbox: true}}
  - pymdownx.arithmatex: {{generic: true}}
extra_javascript:
  - https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js
"""


# --- Astro + Starlight ----------------------------------------------------------------------------


class Starlight(Engine):
    name = "starlight"
    marker = "package.json"

    def exists(self) -> bool:
        path = self.root / self.marker
        return path.is_file() and "@astrojs/starlight" in path.read_text(encoding="utf-8")

    @property
    def content(self) -> Path:
        return self.root / "src" / "content" / "docs"

    def downloads(self, document: str) -> tuple[Path, str]:
        """Starlight serves files from public/, at the site root."""
        return self.root / "public" / document / "downloads", f"/{document}/downloads"

    def posters(self, folder: str) -> tuple[Path, str]:
        return self.root / "public" / folder, f"/{folder}/"

    def files(self, title: str) -> dict[str, str]:
        package = {
            "name": "site",
            "type": "module",
            "private": True,
            "scripts": {"dev": "astro dev", "build": "astro build", "preview": "astro preview"},
            "dependencies": STARLIGHT_PACKAGES,
        }
        return {
            "package.json": json.dumps(package, indent=2) + "\n",
            "astro.config.mjs": ASTRO_CONFIG.replace("{title}", json.dumps(title)),
            "src/content.config.ts": CONTENT_CONFIG,
            "src/content/docs/index.md": f"---\ntitle: {json.dumps(title)}\n---\n\nThe documents are in the sidebar. py-doc writes them; this page is yours.\n",
            STARLIGHT_SIDEBAR: "[]\n",
            "tsconfig.json": '{\n  "extends": "astro/tsconfigs/strict",\n  "include": [".astro/types.d.ts", "**/*"],\n  "exclude": ["dist"]\n}\n',
            ".gitignore": "dist/\nnode_modules/\n.astro/\n.py-doc-site.json\n",
        }

    def write_nav(self, sections: list[NavSection], pages: dict[str, str] | None = None) -> Path:
        sidebar = []
        for section in sections:
            # A flat document lists its folder; one with folders lists its pages, so a group takes its index page's title
            items = _starlight_items(section.pages) if section.nested else [{"autogenerate": {"directory": section.folder}}]
            sidebar.append({"label": section.title, "items": items})
        for title, page in (pages or {}).items():
            link = "/" + page.removesuffix(".md").removesuffix("index").strip("/")
            sidebar.append({"label": title, "link": link.rstrip("/") + "/" if link != "/" else "/"})
        path = self.root / STARLIGHT_SIDEBAR
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sidebar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def check(self, config_file: str | None = None) -> list[str]:
        configs = [p for p in self.root.glob("astro.config.*") if p.is_file()]
        if not configs:
            return [f"{self.root} has no astro.config.mjs. Run `py-doc site init` to make one"]
        if any("py-doc-sidebar" in p.read_text(encoding="utf-8") for p in configs):
            return []
        return [
            f"Pass the sidebar py-doc writes to Starlight in {configs[0]}: "
            "`import sidebar from './src/py-doc-sidebar.json';` and `starlight({ sidebar, ... })`"
        ]

    def build(self, runtime: Runtime, config_file: str | None = None) -> Path:
        mounts = [Mount(self.root, writable=True)]
        env = {"ASTRO_TELEMETRY_DISABLED": "1"}
        # npm install keeps to package-lock.json when it matches package.json, and brings it up to date when not
        runtime.run(["npm", "install", "--no-audit", "--no-fund"], mounts=mounts, workdir=self.root, network=True, env=env, timeout=TIMEOUT)
        runtime.run(["npx", "astro", "build"], mounts=mounts, workdir=self.root, env=env, timeout=TIMEOUT)
        return self.root / "dist"


def _starlight_items(items: list[NavPage | NavSection]) -> list[dict]:
    """A page by its slug (Starlight labels it with its title), a folder as a group of its pages."""
    out: list[dict] = []
    for item in items:
        if isinstance(item, NavSection):
            out.append({"label": item.title, "items": _starlight_items(item.pages)})
        else:
            out.append({"slug": item.path.removesuffix(".md").removesuffix("/index")})
    return out


ASTRO_CONFIG = """\
// Made by `py-doc site init`. Change anything here: py-doc writes only the pages (a folder per document under
// src/content/docs) and the sidebar (src/py-doc-sidebar.json, passed to Starlight below).
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import sidebar from './src/py-doc-sidebar.json';

export default defineConfig({
  markdown: { remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex] },
  integrations: [
    starlight({
      title: {title},
      sidebar,
      customCss: ['katex/dist/katex.min.css'],
    }),
  ],
});
"""

CONTENT_CONFIG = """\
import { defineCollection } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

export const collections = {
  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
};
"""

ENGINES: dict[str, type[Engine]] = {"mkdocs": MkDocs, "starlight": Starlight}


def engine_for(name: str, root: Path) -> Engine:
    return ENGINES[name](root)
