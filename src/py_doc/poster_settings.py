"""The settings of a poster, from four layers, lowest first: ``poster:`` in py-doc.yml (every poster), the
front matter, the poster's entry under ``posters:``, and the command line.

Every layer takes the same keys. A path is resolved against the file that names it before the layers are
merged, so a logo named in py-doc.yml is from py-doc.yml and one in the front matter is from the Markdown.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

TEXT = ("title", "subtitle", "byline", "orientation", "paper", "version", "document_number")
NUMBERS = ("width", "columns")
MAPPINGS = ("colours", "palette", "fonts", "header", "footer", "variables", "conditions")
KEYS = (*TEXT, *NUMBERS, "split", "theme", "logo", "icons", "pdf", "embed_fonts", *MAPPINGS)
ENTRY_KEYS = ("source", "output")  # only for a poster of py-doc.yml
HEADER_KEYS = ("align", "logo")
FOOTER_KEYS = ("left", "centre", "right", "logos", "qr", "qr-label", "document", "version", "credits")
LEGACY = {"footer-left": "left", "footer-right": "right"}  # the front matter keys of md2poster


class SettingsError(ValueError):
    """A setting has the wrong name or type. The message names its place."""


def _path(value, folder: Path, where: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SettingsError(f"{where} must be a path")
    path = Path(value.strip())
    return path if path.is_absolute() else (folder / path).resolve()


def layer(data: dict, folder: Path, where: str, strict: bool = True) -> dict:
    """One layer, checked, with its paths resolved against ``folder``.

    ``strict`` makes an unknown key an error (py-doc.yml); otherwise it is ignored with a warning (front matter).
    """
    if not isinstance(data, dict):
        raise SettingsError(f"{where} must be a mapping")
    out: dict = {}
    for key, value in data.items():
        key = str(key).lower()
        if key in LEGACY:
            out.setdefault("footer", {})[LEGACY[key]] = "" if value is None else str(value)
            continue
        if key not in KEYS:
            if strict:
                raise SettingsError(f"unknown key '{key}' in {where}. Allowed: {', '.join(sorted(KEYS))}")
            logger.warning(f"{where}: '{key}' is not a poster setting, so it is ignored")
            continue
        if value is None:
            continue
        place = f"{where}.{key}"
        if key in TEXT:
            out[key] = str(value)
        elif key in NUMBERS:
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise SettingsError(f"{place} must be a whole number")
            out[key] = value
        elif key == "split":
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            out[key] = str(value)
        elif key == "theme":
            text = str(value).strip()  # a file name is from this layer's file, a bare word is a built-in theme
            out[key] = _path(text, folder, place) if text.endswith((".yml", ".yaml")) else text
        elif key in ("logo", "icons"):  # icons: a folder of the project's own SVG icons
            out[key] = _path(value, folder, place)
        elif key == "embed_fonts":  # true: every font of the stylesheet; a list: only those subsets, such as latin
            if (
                isinstance(value, list)
                and value
                and all(isinstance(v, str) and re.fullmatch(r"[a-z][a-z0-9-]*", v) for v in value)
            ):
                out[key] = [str(v) for v in value]
            elif isinstance(value, bool):
                out[key] = value
            else:
                raise SettingsError(f"{place} must be true, false or a list of subsets such as [latin, latin-ext]")
        elif key == "pdf":  # true: beside the page; a path: there
            if isinstance(value, bool):
                out[key] = value
            elif isinstance(value, str) and value.strip():
                out[key] = _path(value, folder, place)
            else:
                raise SettingsError(f"{place} must be true, false or a path")
        else:
            if not isinstance(value, dict):
                raise SettingsError(f"{place} must be a mapping")
            out[key] = {**out.get(key, {}), **{str(k).lower(): v for k, v in value.items()}}
    files = out.get("fonts", {}).get("files")
    if isinstance(files, list):  # a font file is from this layer's file, as a logo is
        out["fonts"]["files"] = [
            {**item, "file": str(_path(item["file"], folder, f"{where}.fonts.files"))}
            if isinstance(item, dict) and item.get("file")
            else item
            for item in files
        ]
    if "header" in out:
        _only(out["header"], HEADER_KEYS, f"{where}.header")
    if "footer" in out:
        footer = out["footer"]
        _only(footer, FOOTER_KEYS, f"{where}.footer")
        if "logos" in footer:
            logos = footer["logos"] if isinstance(footer["logos"], list) else [footer["logos"]]
            footer["logos"] = [_path(item, folder, f"{where}.footer.logos") for item in logos]
        if "credits" in footer:  # the sources of the pictures: a line, or a list of them
            credits = footer["credits"] if isinstance(footer["credits"], list) else [footer["credits"]]
            if not all(isinstance(item, str) and item.strip() for item in credits):
                raise SettingsError(f"{where}.footer.credits must be a line of text, or a list of them")
            footer["credits"] = [item.strip() for item in credits]
    return out


def _only(data: dict, allowed, where: str) -> None:
    for key in data:
        if key not in allowed:
            raise SettingsError(f"unknown key '{key}' in {where}. Allowed: {', '.join(allowed)}")


def merge(*layers: dict) -> dict:
    """The layers, each over the ones before it. Mappings such as ``colours`` merge key by key."""
    out: dict = {}
    for item in layers:
        for key, value in (item or {}).items():
            if key in MAPPINGS:
                out[key] = {**out.get(key, {}), **value}
            else:
                out[key] = value
    return out
