"""Fonts inside a poster page, so it looks the same offline and in its PDF.

A theme's own font files (``fonts.files``) are always embedded. With ``embed_fonts``, the web fonts of its
stylesheet are downloaded once on this computer, kept in the cache folder, and embedded in place of the
link. A download that fails leaves the link, with a warning: the poster is still written.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from py_doc.diagrams.render import cache_dir

logger = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024  # embedded fonts beyond this make the page slow to send and open
TIMEOUT = 30
# Google Fonts sends WOFF2, the smallest format, only to a browser it recognises
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
FORMATS = {".woff2": ("font/woff2", "woff2"), ".woff": ("font/woff", "woff"), ".ttf": ("font/ttf", "truetype"),
           ".otf": ("font/otf", "opentype")}  # fmt: skip
_URL = re.compile(r"url\(\s*['\"]?(https://[^'\")\s]+)['\"]?\s*\)")


def fonts_folder() -> Path:
    """Where downloaded fonts are kept between builds, beside the diagram cache."""
    return cache_dir().parent / "fonts"


def _fetch(url: str) -> bytes:
    """``url``, from the cache when it was downloaded before. Raises OSError when it cannot be had."""
    folder = fonts_folder()
    cached = folder / hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
    if cached.is_file() and cached.stat().st_size:
        return cached.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 (https only, checked by the caller)
        data = response.read()
    folder.mkdir(parents=True, exist_ok=True)
    partial = cached.with_name(f"{cached.name}.{os.getpid()}.part")
    partial.write_bytes(data)
    os.replace(partial, cached)
    logger.info(f"Downloaded {url} ({len(data) // 1024} KB) into {folder}")
    return data


def _data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def local_faces(files) -> str:
    """@font-face rules for a theme's own font files, embedded."""
    rules = []
    for face in files:
        mime, fmt = FORMATS[face.path.suffix.lower()]
        rules.append(
            f"@font-face{{font-family:'{face.family}';font-weight:{face.weight};font-style:{face.style};"
            f"font-display:swap;src:url({_data_uri(face.path.read_bytes(), mime)}) format('{fmt}')}}"
        )
    return "".join(rules)


def web_faces(stylesheet: str, where: str) -> str | None:
    """The stylesheet's @font-face rules with every font embedded, or None (and a warning) when it cannot be had."""
    try:
        css = _fetch(stylesheet).decode("utf-8")
        if "<" in css or "@import" in css:
            raise ValueError("the stylesheet is not a plain list of @font-face rules")
        fonts = {url: _fetch(url) for url in dict.fromkeys(_URL.findall(css))}
    except (OSError, urllib.error.URLError, UnicodeDecodeError, ValueError) as exc:
        logger.warning(f"{where}: the fonts of {stylesheet} could not be embedded, so the page links them instead: {exc}")
        return None
    if not fonts:
        logger.warning(f"{where}: {stylesheet} names no font files, so there was nothing to embed")
        return None

    def embedded(match: re.Match) -> str:
        url = match.group(1)
        mime = FORMATS.get(Path(url.split("?")[0]).suffix.lower(), ("font/woff2", ""))[0]
        return f"url({_data_uri(fonts[url], mime)})"

    return _URL.sub(embedded, css)


def font_css(theme, embed: bool, where: str) -> tuple[str, bool]:
    """The @font-face rules to put in the page, and whether the page still needs its stylesheet link."""
    css = local_faces(theme.font_files)
    stylesheet = theme.fonts.get("stylesheet")
    link = bool(stylesheet)
    if embed and stylesheet:
        web = web_faces(stylesheet, where)
        if web is not None:
            css += web
            link = False
    size = len(css.encode("utf-8"))
    if size > MAX_BYTES:
        logger.warning(f"{where}: the embedded fonts are {size // (1024 * 1024)} MB, so the page is slow to send and open")
    return css, link
