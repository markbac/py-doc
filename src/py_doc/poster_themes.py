"""Poster themes: the colours, fonts, block palette and logo of a poster.

A theme is a built-in name or a YAML file. A file may start from a built-in theme (``extends``) and
changes only what it names. Every colour of the page is a CSS variable, so a theme never edits the CSS.
"""

from __future__ import annotations

import base64
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from py_doc.errors import ConversionError

GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700"
    "&family=IBM+Plex+Mono:wght@500;600&display=swap"
)

# What each colour paints. The names are the keys of a theme file's `colours`.
COLOUR_ROLES = {
    "backdrop": "around the poster in the browser",
    "page": "the poster background",
    "surface": "cards, figures, tables and the stats strip",
    "border": "the edges of those boxes and the footer rule",
    "text": "body text",
    "muted": "captions, labels and the right footer text",
    "header": "the header background",
    "header-text": "the title",
    "subtitle": "the subtitle",
    "byline": "the byline",
    "accent": "the rule under the header, between the stats and beside the summary blocks",
    "accent-text": "arrow labels and card labels",
    "primary": "behind section headings and table headings, and the default block colour",
    "on-primary": "text on primary and on block colours",
    "secondary": "the introduction box, the banner and filled lane cells",
    "on-secondary": "text on secondary",
    "highlight": "the heading text after a colon",
    "strong": "stat values, card and block headings, lane labels and the left footer text",
    "code": "behind inline code",
    "callout": "behind a > quote",
    "callout-border": "the edge of a > quote",
    "lcd": "the display screen",
    "lcd-text": "text on the display screen",
    "lcd-border": "the edge of the display screen",
    "diagram-fill": "Mermaid boxes",
}

DEFAULT_COLOURS = {
    "backdrop": "#e9e9ef", "page": "#f3f3f7", "surface": "#ffffff", "border": "#d5d8e2", "text": "#1d1f27",
    "muted": "#4a4f5c", "header": "#3b3b40", "header-text": "#ffffff", "subtitle": "#7cc0f2", "byline": "#e6e7ec",
    "accent": "#4a7fc1", "accent-text": "#2f5f9f", "primary": "#2a3150", "on-primary": "#ffffff", "strong": "#2a3150", "secondary": "#3f74b8",
    "on-secondary": "#ffffff", "highlight": "#7cc0f2", "code": "#e4e8f1", "callout": "#fbeee0", "callout-border": "#e3b88a",
    "lcd": "#b7c79a", "lcd-text": "#1f2a14", "lcd-border": "#3b3b40", "diagram-fill": "#e8eef8",
}  # fmt: skip

DEFAULT_PALETTE = {
    "navy": "#2a3150", "blue": "#3f74b8", "amber": "#b4540a", "brown": "#8a3d08",
    "red": "#a3322b", "grey": "#4a4f5c", "green": "#2e6b3a",
}  # fmt: skip

DEFAULT_FONTS = {
    "body": "'Source Serif 4', Georgia, serif",
    "heading": "'Source Serif 4', Georgia, serif",
    "mono": "'IBM Plex Mono', Consolas, monospace",
    "stylesheet": GOOGLE_FONTS,
}

# The other built-in themes, as changes to the default.
BUILTIN = {
    "default": {},
    "dark": {
        "colours": {
            "backdrop": "#0b0e14", "page": "#141923", "surface": "#1d2431", "border": "#2e3748", "text": "#e6e9ef",
            "muted": "#a3abba", "header": "#0b0e14", "accent": "#f2a541", "accent-text": "#f2c27a", "primary": "#2b3a55",
            "secondary": "#33507e", "highlight": "#f2c27a", "strong": "#f2f4f8", "subtitle": "#f2c27a", "code": "#2b3446",
            "callout": "#3a2e1c", "callout-border": "#8a6a35", "diagram-fill": "#dfe6f2",
        },
    },
    "print": {  # less ink: a white page and header, light boxes, and fonts every computer has
        "colours": {
            "backdrop": "#ffffff", "page": "#ffffff", "header": "#ffffff", "header-text": "#1d1f27", "subtitle": "#2a3150",
            "byline": "#4a4f5c", "secondary": "#eef1f6", "on-secondary": "#1d1f27", "highlight": "#a8c8ee",
        },
        "fonts": {"body": "Georgia, serif", "heading": "Georgia, serif", "mono": "Consolas, monospace", "stylesheet": None},
    },
}  # fmt: skip

_COLOUR = re.compile(r"^(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|#[0-9a-fA-F]{8}|[a-zA-Z]+|(rgb|hsl)a?\([^;{}]*\))$")


class ThemeError(ConversionError):
    """A theme cannot be found or has a mistake."""


@dataclass
class Theme:
    colours: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COLOURS))
    palette: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PALETTE))
    fonts: dict[str, str | None] = field(default_factory=lambda: dict(DEFAULT_FONTS))
    logo: Path | None = None

    def colour(self, name: str | None, default: str = "primary") -> str:
        """A block colour: a palette name, a theme colour name, or a colour value."""
        name = (name or "").strip()
        if not name:
            return self.colours[default]
        return self.palette.get(name.lower()) or self.colours.get(name.lower()) or _checked(name, "a block colour")

    def css_variables(self) -> str:
        values = {**self.colours, **{f"font-{k}": v for k, v in self.fonts.items() if k != "stylesheet" and v}}
        return ";".join(f"--{name}:{value}" for name, value in values.items())

    def logo_uri(self) -> str | None:
        if self.logo is None:
            return None
        mime = mimetypes.guess_type(self.logo.name)[0] or "application/octet-stream"
        return f"data:{mime};base64,{base64.b64encode(self.logo.read_bytes()).decode()}"


def _checked(value, where: str) -> str:
    value = str(value).strip()
    if not _COLOUR.match(value):
        raise ThemeError(f"{where}: '{value}' is not a colour (use a hex value such as #2a3150, or a CSS colour name)")
    return value


def _apply(theme: Theme, data: dict, where: str, folder: Path | None) -> None:
    unknown = set(data) - {"extends", "colours", "palette", "fonts", "logo", "name", "description"}
    if unknown:
        raise ThemeError(f"{where}: unknown key '{sorted(unknown)[0]}'. Allowed: colours, extends, fonts, logo, palette")
    for name, value in (data.get("colours") or {}).items():
        if name not in COLOUR_ROLES:
            raise ThemeError(f"{where}: unknown colour '{name}'. Colours: {', '.join(COLOUR_ROLES)}")
        theme.colours[name] = _checked(value, f"{where}: colours.{name}")
    for name, value in (data.get("palette") or {}).items():
        theme.palette[str(name).lower()] = _checked(value, f"{where}: palette.{name}")
    for name, value in (data.get("fonts") or {}).items():
        if name not in DEFAULT_FONTS:
            raise ThemeError(f"{where}: unknown font '{name}'. Fonts: {', '.join(DEFAULT_FONTS)}")
        if value is not None and name == "stylesheet":
            if not re.match(r"^https?://[^\s\"'<>]+$", str(value)):
                raise ThemeError(f"{where}: fonts.stylesheet must be an http or https address")
        elif value is not None and re.search(r"[;{}<>]", str(value)):
            raise ThemeError(f"{where}: fonts.{name} has a character a font name cannot have")
        theme.fonts[name] = None if value is None else str(value)
    if data.get("logo"):
        theme.logo = logo_path(data["logo"], folder or Path.cwd(), where)


def logo_path(value, folder: Path, where: str) -> Path:
    path = Path(str(value))
    path = path if path.is_absolute() else folder / path
    if not path.is_file():
        raise ThemeError(f"{where}: logo not found: {path}")
    return path


def load_theme(spec: str | Path | None, folder: Path) -> Theme:
    """The theme ``spec`` names: a built-in name, or a YAML file relative to ``folder``."""
    theme = Theme()
    if spec is None or str(spec).strip() in ("", "default"):
        return theme
    spec = str(spec).strip()
    if spec in BUILTIN:
        _apply(theme, BUILTIN[spec], f"theme {spec}", None)
        return theme
    path = Path(spec)
    path = path if path.is_absolute() else folder / path
    if not path.is_file():
        raise ThemeError(f"theme '{spec}' is not one of {', '.join(BUILTIN)} and no file {path} exists")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ThemeError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ThemeError(f"{path}: a theme file must be a mapping")
    base = str(data.get("extends") or "default")
    if base not in BUILTIN:
        raise ThemeError(f"{path}: extends '{base}' is not one of {', '.join(BUILTIN)}")
    _apply(theme, BUILTIN[base], f"theme {base}", None)
    _apply(theme, data, str(path), path.parent)
    return theme
