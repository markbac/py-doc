"""Turn a Word document into Markdown that py-doc builds again: ``py-doc import``.

Headings, lists, tables, code, quotes, callouts, captions, links, emphasis and pictures are kept.
Pictures go to ``<name>/media`` as PNG files, in the order the document uses them. What cannot be
carried over (text boxes, footnotes) is counted in one warning each, never dropped quietly.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree

from .errors import ConversionError, EnvironmentProblem, ToolFailed
from .runtime import Mount, Runtime, connect

logger = logging.getLogger(__name__)

MAX_LIST_NESTING = 6
MONOSPACE = {
    "consolas",
    "courier new",
    "courier",
    "lucida console",
    "menlo",
    "monaco",
    "source code pro",
    "cascadia code",
}
CALLOUTS = {"note", "tip", "important", "warning", "caution"}
QUOTE_STYLES = {"quote", "block text", "intense quote"}
BITMAP_TYPES = {"image/jpeg", "image/jpg", "image/gif", "image/bmp", "image/tiff", "image/webp", "image/x-ms-bmp"}
VECTOR_TYPES = {"image/x-emf", "image/emf", "image/x-wmf", "image/wmf", "image/svg+xml"}
# What python-docx and python-pptx write into a new file's comments: not a description anyone wrote
LIBRARY_DEFAULTS = re.compile(r"^\s*generated (by|using) python-(docx|pptx)\s*$", re.IGNORECASE)
CUSTOM_KEYS = {
    "version": "version", "document_number": "document_id", "document_id": "document_id", "classification": "classification",
    "status": "status", "company": "company", "description": "description",
}  # fmt: skip

W_BODY = qn("w:body")
W_P, W_TBL, W_SDT, W_INS, W_DEL = qn("w:p"), qn("w:tbl"), qn("w:sdt"), qn("w:ins"), qn("w:del")
W_R, W_HYPERLINK, W_SMARTTAG = qn("w:r"), qn("w:hyperlink"), qn("w:smartTag")
W_T, W_TAB, W_BR, W_CR, W_NBH = qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:cr"), qn("w:noBreakHyphen")
W_TYPE, W_VAL = qn("w:type"), qn("w:val")
R_ID, R_EMBED = qn("r:id"), qn("r:embed")
A_BLIP = qn("a:blip")
WP_ANCHOR, WP_INLINE, WP_DOCPR = qn("wp:anchor"), qn("wp:inline"), qn("wp:docPr")
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
V_IMAGEDATA = "{urn:schemas-microsoft-com:vml}imagedata"


class InvalidDocx(ConversionError):
    """The input is missing or is not a Word document."""


@dataclass
class ImportResult:
    markdown: Path
    media: Path
    images: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Piece:
    text: str
    bold: bool = False
    italic: bool = False
    strike: bool = False
    code: bool = False

    def style(self) -> tuple[bool, bool, bool, bool]:
        return (self.bold, self.italic, self.strike, self.code)


@dataclass(frozen=True)
class _Break:
    pass


@dataclass(frozen=True)
class _Image:
    rid: str
    alt: str


@dataclass(frozen=True)
class _Link:
    target: str
    inner: tuple


@dataclass
class _Block:
    kind: str
    lines: list[str]
    label: str = ""


def snake_case_name(path: Path) -> str:
    name = re.sub(r"[^\w\s-]", "", path.stem.lower())
    return re.sub(r"[\s-]+", "_", name).strip("_") or "document"


def _flag(element, name: str) -> bool:
    node = element.find(qn(name)) if element is not None else None
    if node is None:
        return False
    return node.get(W_VAL, "true").lower() not in ("0", "false", "off")


def _escape(text: str) -> str:
    text = re.sub(r"([\\`*\[\]<>])", r"\\\1", text)
    return re.sub(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])", r"\\_", text)


def _line_start(text: str) -> str:
    """Stop a paragraph that starts like Markdown syntax from turning into it."""
    text = re.sub(r"^(\d+)([.)])(\s)", r"\1\\\2\3", text)
    return re.sub(r"^([-+]\s|#{1,6}\s)", lambda m: "\\" + m.group(1), text)


class _Importer:
    def __init__(self, document, name: str, defloat: bool, runtime: Callable[[], Runtime] | None) -> None:
        self.doc = document
        self.name = name
        self.defloat = defloat
        self._runtime = runtime
        self._connected: Runtime | None = None
        self.blocks: list[_Block] = []
        self.media: dict[str, bytes] = {}  # file name -> PNG bytes
        self._by_rid: dict[str, str | None] = {}
        self._by_hash: dict[str, str] = {}
        self.counts = {"text boxes": 0, "footnotes": 0, "floating images": 0, "images not imported": 0}
        self.problems: list[str] = []
        self.heading_offset: int | None = None
        self.title = self.subtitle = self.author = self.date = None
        self._list_stack: list[str] = []
        self._numbering = None
        try:
            self._numbering = document.part.numbering_part.element
        except (NotImplementedError, KeyError, AttributeError):
            pass

    # -- the document ---------------------------------------------------------------------------

    def run(self) -> None:
        body = self.doc.element.body
        if self.defloat:
            for anchor in body.iter(WP_ANCHOR):
                anchor.tag = WP_INLINE  # floating pictures become inline ones, in place
        self._blocks(body)

    def _blocks(self, parent) -> None:
        children = list(parent)
        for index, child in enumerate(children):
            if child.tag == W_P:
                self._paragraph(child, children[index + 1] if index + 1 < len(children) else None)
            elif child.tag == W_TBL:
                self._table(child)
            elif child.tag == W_SDT:
                gallery = child.find(f"{qn('w:sdtPr')}/{qn('w:docPartObj')}/{qn('w:docPartGallery')}")
                content = child.find(qn("w:sdtContent"))
                if content is not None and not (
                    gallery is not None and "table of contents" in gallery.get(W_VAL, "").lower()
                ):
                    self._blocks(content)
            elif child.tag == W_INS:
                self._blocks(child)

    def _add(self, kind: str, lines: list[str], label: str = "") -> None:
        self.blocks.append(_Block(kind, lines, label))

    # -- paragraphs -----------------------------------------------------------------------------

    def _style_name(self, p) -> str:
        try:
            return (Paragraph(p, self.doc._body).style.name or "").strip()
        except Exception:
            return ""

    def _paragraph(self, p, following) -> None:
        style = self._style_name(p)
        lower = style.lower()
        tokens = self._tokens(p)
        text = self._plain(tokens).strip()
        if self._is_toc(p, lower):
            return
        only_images = tokens and all(
            isinstance(t, _Image) or (isinstance(t, _Piece) and not t.text.strip()) for t in tokens
        )
        if lower in ("title", "subtitle", "author", "date") and text:
            setattr(self, lower, text)
            return
        match = re.fullmatch(r"heading\s*([1-6])", lower)
        if match:
            if text:
                level = int(match.group(1))
                if self.heading_offset is None:
                    self.heading_offset = level - 1
                self._close_list()
                self._add("heading", ["#" * max(1, level - self.heading_offset) + " " + self._render(tokens)])
            return
        if lower == "caption":
            self._caption(text, following)
            return
        callout = lower.removeprefix("div.")
        if callout in CALLOUTS and text:
            self._grouped("callout", callout, self._render(tokens))
            return
        if lower in QUOTE_STYLES and text:
            self._grouped("quote", "", self._render(tokens))
            return
        if tokens and (("code" in lower and "char" not in lower) or self._monospace(tokens)) and text:
            self._close_list()
            raw = self._raw(tokens)
            if self.blocks and self.blocks[-1].kind == "code":
                self.blocks[-1].lines.append(raw)
            else:
                self._add("code", [raw])
            return
        info = self._list_info(p, lower)
        if info is not None and text:
            self._list_item(*info, self._render(tokens))
            return
        self._close_list()
        if only_images:
            self._add("image", [self._render(tokens).strip()])
        elif text:
            self._add("paragraph", [_line_start(self._render(tokens))])

    def _is_toc(self, p, style: str) -> bool:
        if style.startswith("toc"):
            return True
        links = p.findall(W_HYPERLINK)
        return bool(links) and all(link.get(qn("w:anchor"), "").startswith("_Toc") for link in links)

    def _grouped(self, kind: str, label: str, text: str) -> None:
        self._close_list()
        last = self.blocks[-1] if self.blocks else None
        if last is not None and last.kind == kind and last.label == label:
            last.lines.append(text)
        else:
            self._add(kind, [text], label)

    def _caption(self, text: str, following) -> None:
        self._close_list()
        match = re.match(r"(?i)^(figure|table)\s+\d+\s*[:.\-–—]?\s*", text)
        label = match.group(1).capitalize() if match else ""
        text = text[match.end() :] if match else text
        previous = self.blocks[-1].kind if self.blocks else ""
        if not label:
            label = "Table" if (following is not None and following.tag == W_TBL) or previous == "table" else "Figure"
        block = _Block("caption", [f"[[CAPTION:{label}]] {_escape(text).strip()}".rstrip()])
        if (previous == "image" and label == "Figure") or (previous == "table" and label == "Table"):
            self.blocks.insert(len(self.blocks) - 1, block)  # py-doc wants the caption before what it names
        else:
            self.blocks.append(block)

    # -- lists ----------------------------------------------------------------------------------

    def _close_list(self) -> None:
        self._list_stack = []

    def _list_info(self, p, style: str) -> tuple[int, str] | None:
        ppr = p.find(qn("w:pPr"))
        num = ppr.find(qn("w:numPr")) if ppr is not None else None
        if num is None:
            try:
                element = Paragraph(p, self.doc._body).style
                for _ in range(5):
                    if element is None:
                        break
                    sppr = element.element.pPr
                    if sppr is not None and sppr.numPr is not None:
                        num = sppr.numPr
                        break
                    element = element.base_style
            except Exception:
                num = None
        if num is not None:
            num_id = num.find(qn("w:numId"))
            level = num.find(qn("w:ilvl"))
            number = num_id.get(W_VAL) if num_id is not None else None
            if number == "0":
                return None
            named = re.search(r"(\d)$", style)
            if level is not None and level.get(W_VAL, "").isdigit():
                depth = int(level.get(W_VAL))
            else:
                depth = int(named.group(1)) - 1 if named and style.startswith("list") else 0
            named_kind = re.match(r"list (bullet|number)", style)
            if named_kind:  # the style says what it is, whatever its numbering definition claims
                return depth, "-" if named_kind.group(1) == "bullet" else "1."
            if number is not None:
                return depth, "-" if self._number_format(number, depth) == "bullet" else "1."
        match = re.match(r"list (bullet|number)(?:\s+(\d))?$", style)
        if match:
            return (int(match.group(2) or 1) - 1), "-" if match.group(1) == "bullet" else "1."
        return None

    def _number_format(self, num_id: str, depth: int) -> str:
        if self._numbering is None:
            return "decimal"
        abstract = self._numbering.xpath(f"w:num[@w:numId='{num_id}']/w:abstractNumId/@w:val")
        if not abstract:
            return "decimal"
        fmt = self._numbering.xpath(
            f"w:abstractNum[@w:abstractNumId='{abstract[0]}']/w:lvl[@w:ilvl='{depth}']/w:numFmt/@w:val"
        )
        return fmt[0] if fmt else "decimal"

    def _list_item(self, depth: int, marker: str, text: str) -> None:
        depth = min(depth, len(self._list_stack), MAX_LIST_NESTING)  # no deeper than one below the item above
        same_list = (
            bool(self.blocks)
            and self.blocks[-1].kind == "list"
            and not (depth == 0 and self._list_stack[:1] not in ([], [marker]))
        )
        del self._list_stack[depth:]
        indent = "".join(" " * (len(m) + 1) for m in self._list_stack)
        self._list_stack.append(marker)
        line = f"{indent}{marker} {text}"
        if same_list:
            self.blocks[-1].lines.append(line)
        else:
            self._add("list", [line])

    # -- tables ---------------------------------------------------------------------------------

    def _table(self, tbl) -> None:
        self._close_list()
        rows: list[list[str]] = []
        for tr in tbl.findall(qn("w:tr")):
            cells: list[str] = []
            for tc in tr.findall(qn("w:tc")):
                props = tc.find(qn("w:tcPr"))
                span = props.find(qn("w:gridSpan")) if props is not None else None
                merge = props.find(qn("w:vMerge")) if props is not None else None
                width = int(span.get(W_VAL)) if span is not None and span.get(W_VAL, "").isdigit() else 1
                if merge is not None and merge.get(W_VAL, "continue") == "continue":
                    text = ""
                else:
                    paragraphs = [self._render(self._tokens(p)).strip() for p in tc.iter(W_P)]
                    text = " ".join(x for x in paragraphs if x).replace("|", "\\|")
                    text = re.sub(r"\s*\\\n\s*", " ", text)
                cells.extend([text] + [""] * (width - 1))
            rows.append(cells)
        rows = [r for r in rows if r]
        if not rows:
            return
        columns = max(len(r) for r in rows)
        rows = [r + [""] * (columns - len(r)) for r in rows]

        def line(cells: list[str]) -> str:
            return "|" + "|".join(f" {c} " if c else " " for c in cells) + "|"

        self._add("table", [line(rows[0]), line(["---"] * columns), *(line(r) for r in rows[1:])])

    # -- inline content -------------------------------------------------------------------------

    def _tokens(self, parent) -> list:
        out: list = []
        for child in parent:
            if child.tag == W_R:
                out.extend(self._run(child))
            elif child.tag == W_HYPERLINK:
                out.append(_Link(self._target(child), tuple(self._tokens(child))))
            elif child.tag in (W_INS, W_SMARTTAG):
                out.extend(self._tokens(child))
            elif child.tag == W_SDT:
                content = child.find(qn("w:sdtContent"))
                if content is not None:
                    out.extend(self._tokens(content))
            # w:del, bookmarks, proofing marks and the rest carry no text to keep
        return out

    def _target(self, link) -> str:
        rid = link.get(R_ID)
        if rid:
            relation = self.doc.part.rels.get(rid)
            return relation.target_ref if relation is not None else ""
        anchor = link.get(qn("w:anchor"))
        return f"#{anchor}" if anchor else ""

    def _format(self, run) -> dict:
        props = run.find(qn("w:rPr"))
        if props is None:
            return {}
        rstyle = props.find(qn("w:rStyle"))
        named = rstyle.get(W_VAL, "").lower() if rstyle is not None else ""
        fonts = props.find(qn("w:rFonts"))
        font = (fonts.get(qn("w:ascii"), "") if fonts is not None else "").lower()
        return {
            "bold": _flag(props, "w:b") or named == "strong",
            "italic": _flag(props, "w:i") or named in ("emphasis", "intenseemphasis"),
            "strike": _flag(props, "w:strike"),
            "code": font in MONOSPACE or "code" in named or "verbatim" in named,
        }

    def _run(self, run) -> list:
        props = run.find(qn("w:rPr"))
        if _flag(props, "w:vanish"):
            return []
        return self._run_content(run, self._format(run))

    def _run_content(self, container, fmt: dict) -> list:
        out: list = []
        for c in container:
            if c.tag == W_T:
                out.append(_Piece(c.text or "", **fmt))
            elif c.tag == W_TAB:
                out.append(_Piece(" ", **fmt))
            elif c.tag == W_NBH:
                out.append(_Piece("-", **fmt))
            elif c.tag in (W_BR, W_CR):
                if c.get(W_TYPE) in (None, "textWrapping"):
                    out.append(_Break())
            elif c.tag == qn("w:drawing"):
                out.extend(self._drawing(c))
            elif c.tag in (qn("w:pict"), qn("w:object")):
                data = next(c.iter(V_IMAGEDATA), None)
                rid = data.get(R_ID) if data is not None else None
                if rid:
                    out.append(_Image(rid, ""))
            elif c.tag in (qn("w:footnoteReference"), qn("w:endnoteReference")):
                self.counts["footnotes"] += 1
            elif c.tag == f"{{{MC}}}AlternateContent":
                choice = c.find(f"{{{MC}}}Choice")
                if choice is not None:
                    out.extend(self._run_content(choice, fmt))
        return out

    def _drawing(self, drawing) -> list:
        if next(drawing.iter(qn("w:txbxContent")), None) is not None:
            self.counts["text boxes"] += 1
            return []
        if drawing.find(WP_ANCHOR) is not None:  # only left alone with --no-defloat-images
            self.counts["floating images"] += 1
            return []
        blip = next(drawing.iter(A_BLIP), None)
        rid = blip.get(R_EMBED) if blip is not None else None
        if not rid:
            return []
        docpr = next(drawing.iter(WP_DOCPR), None)
        alt = ((docpr.get("descr") or "") if docpr is not None else "").strip()
        return [_Image(rid, alt)]

    # -- turning tokens into text ---------------------------------------------------------------

    def _plain(self, tokens) -> str:
        out = []
        for t in tokens:
            if isinstance(t, _Piece):
                out.append(t.text)
            elif isinstance(t, _Link):
                out.append(self._plain(t.inner))
            elif isinstance(t, _Image):
                out.append("￼")
        return "".join(out)

    def _raw(self, tokens) -> str:
        return "".join(
            "\n" if isinstance(t, _Break) else t.text if isinstance(t, _Piece) else "" for t in tokens
        ).rstrip()

    def _monospace(self, tokens) -> bool:
        pieces = [t for t in tokens if isinstance(t, _Piece) and t.text.strip()]
        return bool(pieces) and all(t.code for t in pieces) and all(isinstance(t, (_Piece, _Break)) for t in tokens)

    def _render(self, tokens) -> str:
        merged: list = []
        for t in tokens:
            if isinstance(t, _Piece) and merged and isinstance(merged[-1], _Piece) and merged[-1].style() == t.style():
                merged[-1] = _Piece(merged[-1].text + t.text, *t.style())
            else:
                merged.append(t)
        out = []
        for t in merged:
            if isinstance(t, _Piece):
                out.append(self._piece(t))
            elif isinstance(t, _Break):
                out.append("\\\n")
            elif isinstance(t, _Image):
                out.append(self._image(t))
            elif isinstance(t, _Link):
                label = self._render(t.inner).strip()
                out.append(f"[{label}]({t.target})" if t.target and label else label)
        text = "".join(out)
        text = re.sub(r" +\\\n", "\\\n", text)
        return re.sub(r"(\\\n)+$", "", text.strip())

    def _piece(self, piece: _Piece) -> str:
        text = re.sub(r"\s+", " ", piece.text)
        core = text.strip()
        if not core:
            return text
        lead, trail = text[: len(text) - len(text.lstrip())], text[len(text.rstrip()) :]
        if piece.code:
            ticks = "``" if "`" in core else "`"
            pad = " " if "`" in core else ""
            core = f"{ticks}{pad}{core}{pad}{ticks}"
        else:
            core = _escape(core)
            if piece.bold and piece.italic:
                core = f"***{core}***"
            elif piece.bold:
                core = f"**{core}**"
            elif piece.italic:
                core = f"*{core}*"
        if piece.strike:
            core = f"~~{core}~~"
        return f"{lead}{core}{trail}"

    # -- pictures -------------------------------------------------------------------------------

    def _image(self, image: _Image) -> str:
        if image.rid not in self._by_rid:
            self._by_rid[image.rid] = self._convert_image(image.rid)
        file = self._by_rid[image.rid]
        if file is None:
            return "(image not imported)"
        alt = re.sub(r"([\[\]])", r"\\\1", image.alt.replace("\n", " "))
        return f"![{alt}]({self.name}/media/{file})"

    def _convert_image(self, rid: str) -> str | None:
        part = self.doc.part.related_parts.get(rid)
        if part is None:
            self._fail(f"picture {rid} is missing from the document")
            return None
        digest = hashlib.sha256(part.blob).hexdigest()
        if digest in self._by_hash:
            return self._by_hash[digest]
        kind = (getattr(part, "content_type", "") or "").lower()
        label = Path(str(getattr(part, "partname", rid))).name
        try:
            if kind == "image/png":
                data = part.blob
            elif kind in BITMAP_TYPES:
                data = self._pillow_png(part.blob)
            elif kind in VECTOR_TYPES:
                data = self._inkscape_png(part.blob, kind)
            else:
                raise ConversionError(f"the type {kind or 'unknown'} is not supported")
        except EnvironmentProblem:
            raise
        except (ConversionError, OSError, ValueError) as exc:
            first = str(exc).strip().splitlines()[0] if str(exc).strip() else "it could not be converted"
            self._fail(f"{label} ({kind or 'unknown type'}): {first}")
            return None
        file = f"image_{len(self.media) + 1:03d}.png"
        self.media[file] = data
        self._by_hash[digest] = file
        return file

    def _fail(self, message: str) -> None:
        self.counts["images not imported"] += 1
        self.problems.append(f"Picture not imported, {message}")
        logger.warning("Picture not imported, %s", message)

    def _pillow_png(self, blob: bytes) -> bytes:
        return pillow_png(blob)

    def _inkscape_png(self, blob: bytes, kind: str) -> bytes:
        if self._connected is None:
            self._connected = self._runtime() if self._runtime is not None else connect()
        return inkscape_png(self._connected, blob, kind)


# --- pictures -------------------------------------------------------------------------------------


def pillow_png(blob: bytes) -> bytes:
    """A bitmap of any kind Pillow reads, as PNG."""
    from PIL import Image

    try:
        with Image.open(io.BytesIO(blob)) as image:
            image.load()
            if image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                image = image.convert("RGBA")
            out = io.BytesIO()
            image.save(out, format="PNG")
    except Exception as exc:  # Pillow raises many kinds
        raise ConversionError(f"Pillow could not read it: {exc}") from exc
    return out.getvalue()


def inkscape_png(runtime: Runtime, blob: bytes, kind: str) -> bytes:
    """An EMF, WMF or SVG picture, drawn as PNG by Inkscape in the tool container."""
    import tempfile

    suffix = {"image/svg+xml": ".svg", "image/x-wmf": ".wmf", "image/wmf": ".wmf"}.get(kind, ".emf")
    with tempfile.TemporaryDirectory(prefix="py-doc-import-") as tmp:
        source, target = Path(tmp, f"source{suffix}"), Path(tmp, "image.png")
        source.write_bytes(blob)
        try:
            runtime.run(
                ["inkscape", source, "--export-type=png", f"--export-filename={target}", "--export-dpi=192"],
                mounts=[Mount(tmp, writable=True)],
            )
        except ToolFailed as exc:
            raise ConversionError(f"Inkscape failed: {exc.output or exc}") from exc
        if not target.exists():
            raise ConversionError("Inkscape wrote no picture")
        return target.read_bytes()


# --- front matter ---------------------------------------------------------------------------------


def _custom_properties(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "docProps/custom.xml" in names:
                root = etree.fromstring(archive.read("docProps/custom.xml"))
                for prop in root:
                    value = "".join(prop.itertext()).strip()
                    key = re.sub(r"[\s-]+", "_", (prop.get("name") or "").strip().lower())
                    if value and key in CUSTOM_KEYS:
                        found[CUSTOM_KEYS[key]] = value
            if "docProps/app.xml" in names:
                root = etree.fromstring(archive.read("docProps/app.xml"))
                company = next((e.text for e in root if e.tag.endswith("}Company") and e.text), "")
                if company.strip():
                    found.setdefault("company", company.strip())
    except (zipfile.BadZipFile, etree.XMLSyntaxError, KeyError):
        pass
    return found


def _front_matter(importer: _Importer, path: Path) -> list[str]:
    core = importer.doc.core_properties
    data: dict[str, str] = {}

    def put(key: str, value) -> None:
        text = str(value).strip() if value is not None else ""
        if text:
            data[key] = text

    put("title", importer.title or core.title)
    put("subtitle", importer.subtitle)
    put("author", core.author or importer.author)
    put("date", core.created.date().isoformat() if core.created else importer.date)
    put("subject", core.subject)
    put("keywords", core.keywords)
    put("category", core.category)
    put("description", None if LIBRARY_DEFAULTS.match(core.comments or "") else core.comments)
    put("version", core.version)
    put("status", core.content_status)
    for key, value in _custom_properties(path).items():
        data[key] = value
    if not data:
        return []
    dumped = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1000)
    return ["---", dumped.rstrip(), "---", ""]


# --- output ---------------------------------------------------------------------------------------


def _render_blocks(blocks: list[_Block]) -> str:
    chunks: list[str] = []
    for block in blocks:
        if block.kind == "code":
            text = "\n".join(block.lines)
            fence = "````" if "```" in text else "```"
            chunks.append(f"{fence}\n{text}\n{fence}")
        elif block.kind in ("quote", "callout"):
            lines = [f"> [!{block.label.upper()}]"] if block.kind == "callout" else []
            for number, paragraph in enumerate(block.lines):
                if number:
                    lines.append(">")
                lines.extend("> " + part if part else ">" for part in paragraph.split("\n"))
            chunks.append("\n".join(lines))
        else:
            chunks.append("\n".join(block.lines))
    return "\n\n".join(chunks)


def import_docx(
    source: Path,
    out_dir: Path | None = None,
    *,
    defloat_images: bool = True,
    force: bool = False,
    runtime: Callable[[], Runtime] | None = None,
) -> ImportResult:
    """Write ``<out_dir>/<name>.md`` and ``<out_dir>/<name>/media/*.png`` for the Word file ``source``.

    Raises :class:`InvalidDocx` if the file is missing or is not a Word document, and
    :class:`ConversionError` if the Markdown file exists and ``force`` is not set.
    """
    source = Path(source)
    if not source.is_file():
        raise InvalidDocx(f"Input file not found: {source}")
    try:
        document = Document(str(source))
    except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise InvalidDocx(f"'{source}' is not a Word document (.docx)") from exc

    name = snake_case_name(source)
    out_dir = Path(out_dir) if out_dir else source.resolve().parent
    markdown = out_dir / f"{name}.md"
    media = out_dir / name / "media"
    if markdown.exists() and not force:
        raise ConversionError(f"Output file already exists: {markdown} (use --force to replace it)")

    importer = _Importer(document, name, defloat_images, runtime)
    importer.run()

    front = _front_matter(importer, source)
    text = ("\n".join(front) + "\n" if front else "") + _render_blocks(importer.blocks)
    for what, count in importer.counts.items():
        if count and what != "images not imported":
            message = f"{count} {what} not imported"
            importer.problems.append(message)
            logger.warning("%s: %s", source.name, message)

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        if importer.media:
            media.mkdir(parents=True, exist_ok=True)
            for file, data in importer.media.items():
                (media / file).write_bytes(data)
        markdown.write_text(text.rstrip() + "\n", encoding="utf-8")
    except OSError as exc:
        raise ConversionError(f"Cannot write '{markdown}': {exc.strerror or exc}") from exc
    logger.info("Imported %s to %s (%d picture(s))", source.name, markdown, len(importer.media))
    return ImportResult(markdown, media, len(importer.media), importer.problems)
