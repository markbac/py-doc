"""Icons for poster blocks: the Iconify packs of the tool image, and a project's own SVG files.

``icon=tabler:server`` on a card, step, highlight, stat or flow box draws that icon in the text's colour. The
packs are the ones Mermaid's ``architecture`` diagrams draw (package.json of the image), so an icon looks the
same in a diagram and in a block. A pack is downloaded once, checked against its SHA-256 below, and kept in the
cache; ``py-doc icons fetch`` does it ahead of time, as for a machine that will be offline.

A bare name, such as ``icon=server``, is a project icon (an SVG file in the ``icons:`` folder) if there is
one, else Tabler's, then Material Design's.
"""

from __future__ import annotations

import hashlib
import io
import itertools
import json
import logging
import os
import re
import sys
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

from py_doc.errors import ConversionError

logger = logging.getLogger(__name__)

TIMEOUT = 60


@dataclass(frozen=True)
class Pack:
    prefix: str
    version: str  # the same as package.json of the tool image
    sha256: str  # of the npm package
    licence: str  # SPDX
    title: str  # what the docs and the build report call it
    credit: bool = False  # a poster that uses one names it in its credits

    @property
    def url(self) -> str:
        return f"https://registry.npmjs.org/@iconify-json/{self.prefix}/-/{self.prefix}-{self.version}.tgz"


PACKS: dict[str, Pack] = {
    pack.prefix: pack
    for pack in (
        Pack("tabler", "1.2.42", "a34593ca89b860c561f3127b53e1734e72e800bd89d15951bad016f5eda33dfe", "MIT", "Tabler Icons"),
        Pack("logos", "1.2.16", "11963481a86d1c4c9d0e672b221e3be8e306c805a3905e0897e1c6f32af0aad6", "CC0-1.0", "logos"),
        Pack("mdi", "1.2.3", "ddd817a7213f91de51147943915c0cda8c8b818a53c92b5c068cfa9883c6d7ac", "Apache-2.0",
             "Material Design Icons"),
        Pack("wi", "1.2.1", "970218cb228d136a6203596f3aa287470fb771d62ed1a0dcd71b704658e056f6", "OFL-1.1", "Weather Icons"),
    )
}  # fmt: skip
BARE = ("tabler", "mdi")  # where a name without a prefix is looked up, after the project's own icons
_NAME = re.compile(r"^(?:(?P<prefix>[a-z0-9-]+):)?(?P<name>[a-z0-9][a-z0-9_-]*)$")
_ID = re.compile(r'\sid="([^"]+)"')
_uses = itertools.count(1)


class IconError(ConversionError):
    """An icon cannot be found, or its pack cannot be downloaded."""


@dataclass(frozen=True)
class Icon:
    """One icon: its full name, its SVG body and view box, and where it comes from for the credits."""

    name: str  # tabler:server, or the file's stem for a project icon
    body: str
    width: float
    height: float
    source: str  # the pack's title, or "project"
    licence: str  # SPDX, or what the project's icons.yml says
    credit: str = ""  # the line the poster's credits show, when the licence needs one


def cache_dir() -> Path:
    """The folder the packs are kept in: beside the diagram cache (``PY_DOC_CACHE`` overrides both)."""
    override = os.environ.get("PY_DOC_CACHE")
    if override:
        return Path(override) / "icons"
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "py-doc" / "icons"


def pack_dir(pack: Pack) -> Path:
    return cache_dir() / f"{pack.prefix}-{pack.version}"


def fetch(prefix: str) -> Path:
    """Download the pack ``prefix`` into the cache, unless it is there. Returns its ``icons.json``."""
    pack = PACKS[prefix]
    target = pack_dir(pack) / "icons.json"
    if target.is_file():
        return target
    logger.info(f"Downloading the icon pack {pack.prefix} {pack.version} ({pack.title}), once")
    try:
        with urllib.request.urlopen(pack.url, timeout=TIMEOUT) as response:  # noqa: S310 - a fixed https address
            data = response.read()
    except OSError as exc:
        raise IconError(
            f"the {pack.title} icons could not be downloaded from {pack.url}: {exc}. On a machine without network, "
            f"run py-doc icons fetch on one with it and copy {cache_dir()} across"
        ) from None
    found = hashlib.sha256(data).hexdigest()
    if found != pack.sha256:
        raise IconError(f"the {pack.title} icons from {pack.url} have SHA-256 {found}, not {pack.sha256}: not used")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in ("icons.json", "info.json"):  # info.json has the licence, kept with the icons
            extracted = archive.extractfile(f"package/{member}")
            if extracted is None:
                raise IconError(f"the {pack.title} package has no {member}")
            partial = target.parent / f"{member}.{os.getpid()}.part"
            partial.write_bytes(extracted.read())
            os.replace(partial, target.parent / member)
    return target


_loaded: dict[str, dict] = {}


def _pack_data(prefix: str) -> dict:
    if prefix not in _loaded:
        _loaded[prefix] = json.loads(fetch(prefix).read_text(encoding="utf-8"))
    return _loaded[prefix]


def _from_pack(prefix: str, name: str) -> Icon | None:
    data = _pack_data(prefix)
    icons, aliases = data.get("icons", {}), data.get("aliases", {})
    seen = 0
    while name not in icons and name in aliases and seen < 8:  # an alias names another icon of the pack
        name, seen = aliases[name]["parent"], seen + 1
    found = icons.get(name)
    if found is None:
        return None
    pack = PACKS[prefix]
    width = found.get("width", data.get("width", 16))
    height = found.get("height", data.get("height", 16))
    body = found["body"]
    if found.get("left") or found.get("top"):
        body = f'<g transform="translate({-found.get("left", 0)} {-found.get("top", 0)})">{body}</g>'
    credit = f"{pack.title} ({pack.licence})" if pack.credit else ""
    return Icon(f"{prefix}:{name}", body, width, height, pack.title, pack.licence, credit)


class Icons:
    """The icons of one build: the project's ``icons:`` folder, and the icons used, for the credits and report."""

    def __init__(self, folder: Path | None = None):
        self.folder = folder
        self.used: dict[str, Icon] = {}
        self._project: dict[str, dict] | None = None

    def _own(self) -> dict[str, dict]:
        """The project's icons by name: each SVG file of the folder, with what its ``icons.yml`` says of it."""
        if self._project is None:
            self._project = {}
            if self.folder is not None and self.folder.is_dir():
                notes_file = self.folder / "icons.yml"
                notes = {}
                if notes_file.is_file():
                    try:
                        notes = yaml.safe_load(notes_file.read_text(encoding="utf-8")) or {}
                    except yaml.YAMLError as exc:
                        raise IconError(f"{notes_file} is not valid YAML: {exc}") from None
                    if not isinstance(notes, dict):
                        raise IconError(f"{notes_file} must map icon names to their licence and credit")
                for svg in sorted(self.folder.glob("*.svg")):
                    note = notes.get(svg.stem) or {}
                    self._project[svg.stem.lower()] = {"path": svg, **(note if isinstance(note, dict) else {})}
        return self._project

    def get(self, name: str) -> Icon:
        """The icon ``name``: ``prefix:name``, or a bare name. Raises IconError when there is none."""
        m = _NAME.match(name.strip().lower())
        if not m:
            raise IconError(f"'{name}' is not an icon name such as tabler:server, logos:docker or mdi:router")
        prefix, short = m["prefix"], m["name"]
        if prefix and prefix not in PACKS:
            raise IconError(f"'{name}': there is no icon pack {prefix}. The packs are {', '.join(PACKS)}")
        icon = None
        if prefix:
            icon = _from_pack(prefix, short)
        else:
            own = self._own().get(short)
            icon = _from_file(short, own) if own else None
            for pack in BARE if icon is None else ():
                icon = _from_pack(pack, short)
                if icon:
                    break
        if icon is None:
            where = f"the {PACKS[prefix].title} icons" if prefix else _bare_places(self.folder)
            raise IconError(
                f"there is no icon '{name}' in {where}. Search the pack at https://icon-sets.iconify.design"
            )
        self.used[icon.name] = icon
        return icon

    def svg(self, name: str, size: str = "1.25em") -> str:
        """The icon ``name`` as inline SVG, ``size`` wide and high, its ids its own so two on a page do not clash."""
        icon = self.get(name)
        body, use = icon.body, next(_uses)
        for found in dict.fromkeys(_ID.findall(body)):
            new = f"i{use}-{found}"
            body = body.replace(f' id="{found}"', f' id="{new}"').replace(f"url(#{found})", f"url(#{new})")
            body = body.replace(f'href="#{found}"', f'href="#{new}"')  # href and xlink:href
        return (
            f'<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {icon.width:g} {icon.height:g}" '
            f'width="{size}" height="{size}" aria-hidden="true" focusable="false">{body}</svg>'
        )

    def credits(self) -> list[str]:
        """A credit line for each source of the icons used that asks for one, as a CC BY icon does."""
        return list(dict.fromkeys(icon.credit for icon in self.used.values() if icon.credit))

    def manifest(self) -> list[dict]:
        """Every icon used, with its source and licence: the build report's list."""
        return [
            {"name": icon.name, "source": icon.source, "licence": icon.licence}
            for icon in sorted(self.used.values(), key=lambda icon: icon.name)
        ]


def _bare_places(folder: Path | None) -> str:
    own = f"the project's icons ({folder}), " if folder else ""
    return own + " or ".join(f"the {PACKS[prefix].title} icons" for prefix in BARE)


def _from_file(name: str, own: dict) -> Icon:
    """A project icon: the inside of its SVG file, and its view box."""
    path: Path = own["path"]
    text = path.read_text(encoding="utf-8")
    opening = re.search(r"<svg\b[^>]*>", text)
    closing = text.rfind("</svg>")
    if not opening or closing < opening.end():
        raise IconError(f"{path} is not an SVG picture")
    view = re.search(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"', opening.group(0))
    if view:
        x, y, width, height = (float(v) for v in view.groups())
        body = text[opening.end() : closing]
        if x or y:
            body = f'<g transform="translate({-x:g} {-y:g})">{body}</g>'
    else:
        sizes = dict(re.findall(r'\s(width|height)="([\d.]+)', opening.group(0)))
        if len(sizes) < 2:
            raise IconError(f"{path} has no viewBox, nor a width and height")
        width, height, body = float(sizes["width"]), float(sizes["height"]), text[opening.end() : closing]
    licence = str(own.get("licence") or own.get("license") or "the project's")
    credit = str(own.get("credit") or "")
    if not credit and re.match(r"cc[- ]by(?![- ]?0)", licence, re.I):  # CC BY needs a credit; CC0 does not
        raise IconError(f"the icon {path.name} is {licence}, which needs a credit: give it credit: in icons.yml")
    return Icon(name, body, width, height, "project", licence, credit)
