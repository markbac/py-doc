"""
Post-processing helpers applied to the composed DOCX after Pandoc.

Responsibilities
----------------
* Placeholder replacement in body, tables, headers and footers.
* Orientation section-break injection from ``[[LANDSCAPE]]`` / ``[[PORTRAIT]]``
  markers left in the document by the Markdown source.
* Explicit style (``[[STYLE:…]]``) and caption (``[[CAPTION:…]]``) marker handling.
* Table formatting: consistent style, header row repeat, no row splits.
* Layout fixes: image height clamping, keep-with-next on headings / captions.
* Body bold normalisation.
* Core property update.
* TOC update flag.
"""
from __future__ import annotations

import copy
import logging
import re
from contextlib import contextmanager

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import nsmap as _DOCX_NSMAP
from docx.oxml.ns import qn
from docx.shared import Cm, RGBColor
from lxml import etree


log = logging.getLogger(__name__)


def snippet(text: str, n: int = 80) -> str:
    """A single-line preview of text for messages."""
    return (text or "").replace("\n", " ").replace("\r", " ")[:n]

# ---------------------------------------------------------------------------
# Orientation markers
# ---------------------------------------------------------------------------

MARKERS_LANDSCAPE = {"[[LANDSCAPE]]", "__LANDSCAPE__", "__LANDSCAPE_START__"}
MARKERS_PORTRAIT  = {"[[PORTRAIT]]",  "__PORTRAIT__",  "__LANDSCAPE_END__"}

# ---------------------------------------------------------------------------
# Style / caption marker patterns
# ---------------------------------------------------------------------------

STYLE_PATTERN   = re.compile(r"\[\[STYLE:(?P<style>[A-Za-z0-9 _-]+)\]\]")
CAPTION_PATTERN = re.compile(r"\[\[CAPTION:(?P<label>[A-Za-z0-9 _-]+)\]\]")

# ---------------------------------------------------------------------------
# Content insertion marker (e.g. for templates with a trailing back page)
# ---------------------------------------------------------------------------

CONTENT_MARKER = "[[INSERTCONTENT]]"


def find_and_remove_marker(doc: Document, marker: str = CONTENT_MARKER) -> int | None:
    """
    Locate the paragraph containing *marker* in *doc*, remove it, and return
    the body index the caller should insert new content at.

    Returns ``None`` if the marker is not present, so callers can fall back
    to appending at the end of the document. Raises ``ValueError`` if the
    marker appears more than once.
    """
    hits = [p for p in doc.paragraphs if (p.text or "").strip() == marker]

    if not hits:
        return None
    if len(hits) > 1:
        raise ValueError(f"Marker {marker!r} found {len(hits)} times — expected exactly one")

    marker_para = hits[0]
    body        = doc._element.body
    index       = body.index(marker_para._p)
    body.remove(marker_para._p)
    return index


# ---------------------------------------------------------------------------
# Internal XML helpers
# ---------------------------------------------------------------------------

def _get_or_add_body_sectPr(doc: Document):
    body   = doc._element.body
    sectPr = body.sectPr
    if sectPr is None:
        sectPr = OxmlElement("w:sectPr")
        body.append(sectPr)
    return sectPr


def _set_pgSz(sectPr, orientation: str) -> None:
    pgSz = sectPr.find(qn("w:pgSz"))
    if pgSz is None:
        pgSz = OxmlElement("w:pgSz")
        sectPr.append(pgSz)
    pgSz.set(qn("w:orient"), orientation)
    if orientation == "landscape":
        pgSz.set(qn("w:w"), "16838")
        pgSz.set(qn("w:h"), "11906")
    else:
        pgSz.set(qn("w:w"), "11906")
        pgSz.set(qn("w:h"), "16838")


def _insert_seq_field(paragraph, label: str) -> None:
    """Insert a ``SEQ <label>`` field so Word recognises it for Table of Figures."""
    paragraph.style = "Caption"
    paragraph.add_run(f"{label} ")
    run = paragraph.add_run()
    fld_begin             = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr                 = OxmlElement("w:instrText")
    instr.text            = f"SEQ {label} \\* ARABIC"
    fld_sep               = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end               = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_begin, instr, fld_sep, fld_end])
    paragraph.add_run(": ")


# ---------------------------------------------------------------------------
# Section break injection
# ---------------------------------------------------------------------------

def insert_section_break_at(paragraph, orientation: str, doc: Document) -> None:
    """
    Inject a ``nextPage`` section break at *paragraph* and set the page size
    for the section that follows to *orientation*.

    OOXML semantics:
    - Clone the body ``sectPr`` onto the marker paragraph (ends the
      *current* section at that point).
    - Update the body ``sectPr`` to the new orientation (starts the *next*
      section).
    """
    body_sectPr = _get_or_add_body_sectPr(doc)

    pPr        = paragraph._p.get_or_add_pPr()
    para_sectPr = copy.deepcopy(body_sectPr)

    type_elem = para_sectPr.find(qn("w:type"))
    if type_elem is None:
        type_elem = OxmlElement("w:type")
        para_sectPr.insert(0, type_elem)
    type_elem.set(qn("w:val"), "nextPage")

    pPr.append(para_sectPr)
    _set_pgSz(body_sectPr, orientation)

    # body_sectPr may still carry titlePg (and therefore a reference to the
    # template's decorative first-page header/background image) inherited
    # from the cover page — correct for the section that genuinely IS the
    # cover, but wrong for every ongoing section this function creates.
    # Left in place, each orientation break re-copies it via para_sectPr
    # above AND leaves it on body_sectPr for the *next* break to copy
    # again — meaning the cover's background image resurfaces at the start
    # of every landscape/portrait section, not just the actual cover.
    # Stripping it here means only the section that was truly the
    # document's opening cover page keeps titlePg; every section created
    # by an orientation marker behaves as an ordinary continuing section.
    titlePg = body_sectPr.find(qn("w:titlePg"))
    if titlePg is not None:
        body_sectPr.remove(titlePg)

    log.debug("Section break → next section orientation=%s", orientation)


# ---------------------------------------------------------------------------
# Orientation marker pass
# ---------------------------------------------------------------------------

def apply_orientation_markers(doc: Document) -> None:
    """
    Find orientation marker paragraphs and replace each with a Word section
    break that switches the page orientation.
    """
    log.debug("apply_orientation_markers: scanning %d paragraphs", len(doc.paragraphs))

    paragraphs = list(doc.paragraphs)
    landscape_hits = [i for i, p in enumerate(paragraphs) if (p.text or "").strip() in MARKERS_LANDSCAPE]
    portrait_hits  = [i for i, p in enumerate(paragraphs) if (p.text or "").strip() in MARKERS_PORTRAIT]

    log.debug("Landscape markers at: %s", landscape_hits)
    log.debug("Portrait markers at:  %s", portrait_hits)

    if not landscape_hits and not portrait_hits:
        log.debug("No orientation markers found")
        return

    for p in paragraphs:
        marker = (p.text or "").strip()
        if marker in MARKERS_LANDSCAPE:
            insert_section_break_at(p, "landscape", doc)
            p.text = ""
            log.debug("Applied LANDSCAPE break")
        elif marker in MARKERS_PORTRAIT:
            insert_section_break_at(p, "portrait", doc)
            p.text = ""
            log.debug("Applied PORTRAIT break")

    remaining = [
        i for i, p in enumerate(doc.paragraphs)
        if (p.text or "").strip() in (MARKERS_LANDSCAPE | MARKERS_PORTRAIT)
    ]
    if remaining:
        log.warning("Orientation markers still present after processing at: %s", remaining)
    else:
        log.debug("All orientation markers processed")


# ---------------------------------------------------------------------------
# Landscape image rescaling
# ---------------------------------------------------------------------------

def rescale_landscape_images(doc: Document) -> None:
    """
    Expand images inside landscape sections to full landscape text width.
    Only images whose containing paragraph falls within a landscape section
    are affected; portrait-section images are left untouched.
    """
    # Build a set of <w:p> elements that live in landscape sections.
    # We walk paragraphs in document order, advancing the section index
    # each time we pass a paragraph that carries a sectPr (i.e. a section
    # boundary), which is exactly what _text_width_for_shape does internally.
    sections = list(doc.sections)
    if not any(s.orientation == WD_ORIENT.LANDSCAPE for s in sections):
        return  # nothing to do

    # Map each <w:p> element → section index (same walk as _text_width_for_shape)
    para_to_sec: dict = {}
    sec_idx = 0
    for para in doc.paragraphs:
        para_to_sec[id(para._p)] = sec_idx
        pPr = para._p.find(qn("w:pPr"))
        if pPr is not None and pPr.find(qn("w:sectPr")) is not None:
            sec_idx = min(sec_idx + 1, len(sections) - 1)

    rescaled = 0
    for shape in doc.inline_shapes:
        # Walk up from the inline element to find the containing <w:p>
        el = shape._inline
        containing_p = None
        for _ in range(6):
            el = el.getparent()
            if el is None:
                break
            if el.tag == qn("w:p"):
                containing_p = el
                break

        if containing_p is None:
            continue

        sec_idx = para_to_sec.get(id(containing_p), 0)
        section = sections[min(sec_idx, len(sections) - 1)]

        if section.orientation != WD_ORIENT.LANDSCAPE:
            continue  # portrait section — leave this image alone

        usable_width = (
            section.page_width - section.left_margin - section.right_margin
        )
        if shape.width < usable_width:
            ratio = usable_width / float(shape.width)
            shape.height = int(shape.height * ratio)
            shape.width  = usable_width

        # Centre the paragraph
        para_obj = next(
            (p for p in doc.paragraphs if p._p is containing_p), None
        )
        if para_obj is not None:
            para_obj.alignment = WD_ALIGN_PARAGRAPH.CENTER

        rescaled += 1

    if rescaled:
        log.info("rescale_landscape_images: %d image(s) expanded to landscape width",
                 rescaled)


# ---------------------------------------------------------------------------
# Placeholder replacement
# ---------------------------------------------------------------------------

def replace_placeholders(doc: Document, replacements: dict[str, str]) -> None:
    """
    Replace template placeholder strings throughout the document.

    Strategy
    --------
    *Body / body tables* — paragraph-level: concatenate all run texts,
    perform replacements, write back to the first run and blank the rest.
    Preserves run formatting (``<w:rPr>``).

    *Headers / footers* — raw XML walk over ``<w:t>`` nodes inside every
    ``<w:p>`` descendant.  This reaches paragraphs inside header/footer
    tables that python-docx may not surface through its object model.
    """
    log.info("replace_placeholders: %d keys", len(replacements))

    # --- body helpers ---------------------------------------------------

    def _replace_para(para):
        runs = para.runs
        if not runs:
            return
        full = "".join(r.text for r in runs)
        if not any(k in full for k in replacements):
            return
        replaced = full
        for k, v in replacements.items():
            replaced = replaced.replace(k, v)
        runs[0].text = replaced
        for r in runs[1:]:
            r.text = ""

    def _replace_table(table):
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_para(p)
                for t in cell.tables:
                    _replace_table(t)

    for p in doc.paragraphs:
        _replace_para(p)
    for t in doc.tables:
        _replace_table(t)

    # --- header / footer XML walk ---------------------------------------

    _W_P        = qn("w:p")
    _W_R        = qn("w:r")
    _W_T        = qn("w:t")
    _XML_SPACE  = "{http://www.w3.org/XML/1998/namespace}space"

    def _replace_hf(hf_element):
        # Break-like elements split a paragraph into independent visual
        # segments (e.g. tab-stop columns for a left/right header split).
        # Merging text across one of these would collapse a multi-column
        # header/footer into a single run, losing the split entirely — so
        # each segment (a maximal run of consecutive <w:t> nodes) is
        # replaced on its own. Word can still split ONE placeholder across
        # several runs within a segment (e.g. spell-check), which is why
        # each segment is still concatenated before replacing, rather than
        # replacing node-by-node.
        _BREAK_TAGS = {qn("w:tab"), qn("w:br"), qn("w:cr"), qn("w:drawing"),
                       qn("w:object"), qn("w:pict"), qn("w:noBreakHyphen")}

        def _replace_segment(segment):
            if not segment:
                return
            full = "".join(t.text or "" for t in segment)
            if not any(k in full for k in replacements):
                return
            replaced = full
            for k, v in replacements.items():
                replaced = replaced.replace(k, v)
            segment[0].text = replaced
            if replaced != replaced.strip():
                segment[0].set(_XML_SPACE, "preserve")
            for t in segment[1:]:
                t.text = ""

        for para_el in hf_element.iter(_W_P):
            segment = []
            for r_el in para_el.iter(_W_R):
                for child in r_el:
                    if child.tag == _W_T:
                        segment.append(child)
                    elif child.tag in _BREAK_TAGS:
                        _replace_segment(segment)
                        segment = []
            _replace_segment(segment)

    for section in doc.sections:
        for hf in (section.header, section.footer):
            try:
                _replace_hf(hf._element)
            except Exception as exc:
                log.warning("Header/footer replacement failed: %s", exc)


# ---------------------------------------------------------------------------
# Explicit style / caption markers
# ---------------------------------------------------------------------------

def apply_explicit_styles(doc: Document) -> None:
    """
    Process ``[[STYLE:StyleName]]`` and ``[[CAPTION:Label]]`` markers left
    in paragraph text.

    * ``[[STYLE:…]]`` — strips the marker and applies the named Word style.
    * ``[[CAPTION:…]]`` — strips the marker, applies Caption style, and
      inserts a ``SEQ`` field so Word tracks figure / table numbers.
    """
    log.debug("apply_explicit_styles: scanning")
    for p in doc.paragraphs:
        raw = p.text or ""

        cap_m = CAPTION_PATTERN.search(raw)
        if cap_m:
            label   = cap_m.group("style").strip() if False else cap_m.group("label").strip()
            cleaned = CAPTION_PATTERN.sub("", raw).strip()
            p.text  = ""
            _insert_seq_field(p, label)
            if cleaned:
                p.add_run(cleaned)
            log.debug("Caption SEQ %s applied", label)
            continue

        sty_m = STYLE_PATTERN.search(raw)
        if sty_m:
            style_name = sty_m.group("style").strip()
            p.text     = STYLE_PATTERN.sub("", raw).strip()
            try:
                p.style = style_name
                log.debug("Style '%s' applied", style_name)
            except Exception as exc:
                log.error("Failed to apply style '%s': %s", style_name, exc)

    log.debug("apply_explicit_styles: done")


# ---------------------------------------------------------------------------
# Table formatting
# ---------------------------------------------------------------------------

def format_all_tables(
    doc: Document,
    style_name: str       = "Table Grid",
    repeat_header: bool   = True,
    prevent_row_split: bool = True,
    autofit: bool         = True,
) -> None:
    """
    Apply a consistent appearance to every table in *doc*.

    * Applies *style_name* if it exists in the document styles. Note:
      python-docx's own style lookup (``doc.styles[name]``) does not
      resolve Word's "aliases" mechanism, so this must be the style's
      plain name (e.g. "Table Grid") even if Word also shows it under an
      alias like "Table Grid,Eykon" — the alias-qualified string will
      always raise KeyError here regardless of what the docx contains.
    * Centres every table and sets a consistent 100% text-area width, so
      tables don't end up a mix of auto-width/left-aligned and
      full-width/left-aligned depending on how Pandoc happened to emit them.
    * Enables autofit and removes fixed cell widths.
    * Marks the first row as a repeating header.
    * Prevents rows from splitting across pages.
    """
    try:
        _ = doc.styles[style_name]
        style_ok = True
    except KeyError:
        log.warning("Table style '%s' not found in document — skipping", style_name)
        style_ok = False

    for tbl in doc.tables:
        if style_ok:
            tbl.style = style_name

        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblPr = tbl._tbl.tblPr
        tblW  = tblPr.find(qn("w:tblW"))
        if tblW is None:
            tblW = OxmlElement("w:tblW")
            tblPr.append(tblW)
        tblW.set(qn("w:type"), "pct")
        tblW.set(qn("w:w"), "5000")  # 5000 = 100% in Word's fiftieths-of-a-percent units

        if autofit:
            try:
                tbl.autofit = True
            except Exception:
                pass
            for row in tbl.rows:
                for cell in row.cells:
                    tcPr = cell._tc.get_or_add_tcPr()
                    tcW  = tcPr.find(qn("w:tcW"))
                    if tcW is not None:
                        tcPr.remove(tcW)

        if repeat_header and tbl.rows:
            hdr  = tbl.rows[0]
            trPr = hdr._tr.get_or_add_trPr()
            if trPr.find(qn("w:tblHeader")) is None:
                trPr.append(OxmlElement("w:tblHeader"))
            for cell in hdr.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True
                    p.paragraph_format.keep_together  = True
                    # Direct run formatting, not reliance on the table
                    # style's conditional "first row" formatting alone:
                    # whatever paragraph style Pandoc assigned to this cell
                    # (commonly "Compact", which inherits Normal's explicit
                    # navy colour) outranks the table style's white-on-navy
                    # override in Word's precedence, silently making header
                    # text invisible. Direct formatting always wins.
                    for run in p.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        if prevent_row_split:
            for row in tbl.rows:
                trPr = row._tr.get_or_add_trPr()
                if trPr.find(qn("w:cantSplit")) is None:
                    trPr.append(OxmlElement("w:cantSplit"))
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.keep_together = True


# ---------------------------------------------------------------------------
# Layout fixes
# ---------------------------------------------------------------------------

def _text_width_for_shape(shape, doc: Document) -> int:
    """
    Return the text-area width (EMU) of the section containing *shape*.

    Walks up the XML tree from the inline shape to find its containing
    ``<w:p>``, then maps that paragraph to its section via python-docx.
    Falls back to the first section if the paragraph cannot be located.
    """
    # Walk up to the containing <w:p>
    el = shape._inline
    for _ in range(6):
        el = el.getparent()
        if el is None:
            break
        if el.tag == qn("w:p"):
            break

    # Find which section this paragraph belongs to by checking whether any
    # section's range of paragraphs includes this element.
    sections = list(doc.sections)
    if len(sections) == 1:
        s = sections[0]
        return s.page_width - s.left_margin - s.right_margin

    # Multi-section: walk paragraphs in order, tracking section transitions
    sec_idx = 0
    for para in doc.paragraphs:
        if para._p is el:
            break
        pPr = para._p.find(qn("w:pPr"))
        if pPr is not None and pPr.find(qn("w:sectPr")) is not None:
            sec_idx = min(sec_idx + 1, len(sections) - 1)

    s = sections[min(sec_idx, len(sections) - 1)]
    return s.page_width - s.left_margin - s.right_margin


def apply_layout_fixes(doc: Document, max_image_height_cm: float = 20.0) -> None:
    """
    Post-process the composed DOCX:
    - Scale image width down to its section text-area width if it exceeds it
      (preserving aspect ratio).  This is a safety net for images that Pandoc
      embedded too wide; with correct PNG DPI stamps most images already fit.
    - Clamp image height to *max_image_height_cm* (preserving aspect ratio).
    - Keep headings with next paragraph.
    - Keep images with their captions.
    """
    log.debug("apply_layout_fixes: start")
    max_h   = Cm(max_image_height_cm)
    scaled  = 0
    clamped = 0

    for shape in doc.inline_shapes:
        try:
            w = shape.width
            h = shape.height
            if not w or not h:
                continue

            # 1. Scale width to text area if needed
            text_w = _text_width_for_shape(shape, doc)
            if w > text_w:
                ratio        = text_w / float(w)
                shape.width  = text_w
                shape.height = int(h * ratio)
                w, h         = shape.width, shape.height
                scaled      += 1

            # 2. Clamp height
            if shape.height > max_h:
                ratio        = max_h / float(shape.height)
                shape.width  = int(shape.width * ratio)
                shape.height = int(max_h)
                clamped     += 1

        except Exception as exc:
            log.debug("Image resize skipped: %s", exc)
            continue

    if scaled or clamped:
        log.info("apply_layout_fixes: %d image(s) width-scaled, %d height-clamped",
                 scaled, clamped)

    def _has_drawing(para) -> bool:
        return any(r._element.xpath(".//w:drawing") for r in para.runs)

    for p in doc.paragraphs:
        name = (p.style.name or "").lower()
        if name.startswith("heading"):
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together  = True
        if _has_drawing(p):
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together  = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if name == "caption" or (p.text or "").strip().lower().startswith(("figure ", "fig. ")):
            p.paragraph_format.keep_together = True

    log.debug("apply_layout_fixes: done")


# ---------------------------------------------------------------------------
# Body bold normalisation
# ---------------------------------------------------------------------------

def normalize_body_bold(
    doc: Document,
    body_par_styles: tuple[str, ...] = (
        "Normal", "Body Text", "BodyText", "List Paragraph", "List"
    ),
    max_logs: int = 500,
) -> None:
    """
    Remove direct bold formatting from runs in body paragraph styles.
    Headings and ``Div.*`` paragraphs are protected.
    """
    logs_left = max_logs

    def _log(msg: str):
        nonlocal logs_left
        if logs_left > 0:
            log.debug(msg)
            logs_left -= 1

    def _process(p, where: str):
        name = (p.style.name or "") if p.style else ""
        if name.lower().startswith(("heading", "div.")):
            return
        if name not in body_par_styles:
            return
        changed = 0
        for r in p.runs:
            if r.font.bold is True:
                r.font.bold = False
                changed += 1
        if changed:
            _log(f"[bold-norm][{where}] style='{name}' cleared {changed} runs: "
                 f"'{snippet(p.text)}'")

    for p in doc.paragraphs:
        _process(p, "body")

    for si, section in enumerate(doc.sections):
        for hf_name, hf in (("header", section.header), ("footer", section.footer)):
            for p in hf.paragraphs:
                _process(p, f"s{si}.{hf_name}")

    def _walk_table(tbl, prefix: str):
        for ri, row in enumerate(tbl.rows):
            for ci, cell in enumerate(row.cells):
                for p in cell.paragraphs:
                    _process(p, f"{prefix}.r{ri}.c{ci}")
                for ti, inner in enumerate(cell.tables):
                    _walk_table(inner, f"{prefix}.r{ri}.c{ci}.t{ti}")

    for ti, tbl in enumerate(doc.tables):
        _walk_table(tbl, f"tbl{ti}")

    if logs_left <= 0:
        log.debug("normalize_body_bold: log cap reached (%d)", max_logs)


# ---------------------------------------------------------------------------
# Core properties
# ---------------------------------------------------------------------------

# Correct namespace for docProps/core.xml elements. Some templates carry
# stray <keywords>/<category> elements written under the wrong namespace
# (e.g. the custom-properties namespace instead of core-properties) --
# likely inherited from an external metadata-sync tool. Word tolerates one
# such element per local name, but a correctly-namespaced element alongside
# a mis-namespaced one for the same property name is invalid per the
# CT_CoreProperties schema and Word reports the document as unreadable.
# Correct namespace for docProps/core.xml elements under the "cp:" prefix.
#
# docxcompose (imported by pipeline.py for document composition) overwrites
# the shared docx.oxml.ns.nsmap["cp"] entry AT IMPORT TIME with the
# *custom*-properties namespace, which it needs for its own docProps/
# custom.xml handling. That dict is the same one python-docx uses process-
# wide for every "cp:"-prefixed lookup, so from the moment docxcompose is
# imported, python-docx's own core-properties setters for "cp:"-prefixed
# properties (keywords, category, lastModifiedBy, revision, ...) silently
# write under the wrong namespace too. title/author/subject are unaffected
# (they use the "dc:" prefix); keywords/category are exactly the "cp:"
# properties this module sets, so they're the only ones that end up
# corrupted. Word then reports the file as unreadable, since a correctly-
# namespaced element (already present in the template) sitting alongside a
# same-local-name element under the wrong namespace is invalid per the
# CT_CoreProperties schema.
_CORE_PROPS_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"


@contextmanager
def _correct_cp_namespace():
    """
    Temporarily force nsmap["cp"] to the correct core-properties namespace
    for the duration of the block, restoring whatever value was there
    beforehand afterwards -- so we don't disturb docxcompose's own use of
    "cp" for docProps/custom.xml elsewhere in the pipeline.
    """
    previous = _DOCX_NSMAP.get("cp")
    _DOCX_NSMAP["cp"] = _CORE_PROPS_NS
    try:
        yield
    finally:
        if previous is not None:
            _DOCX_NSMAP["cp"] = previous


def _purge_mismatched_core_props(doc: Document, local_names: tuple[str, ...]) -> None:
    """
    Remove any docProps/core.xml child whose local name is in *local_names*
    but whose namespace is not the standard core-properties namespace.

    Self-heals documents already carrying a wrong-namespace duplicate from
    an earlier run made before the nsmap collision above was fixed.
    """
    root = doc.core_properties._element
    for child in list(root):
        qname = etree.QName(child.tag)
        if qname.localname in local_names and qname.namespace != _CORE_PROPS_NS:
            log.warning(
                "Removing malformed <%s> core property (wrong namespace: %s)",
                qname.localname, qname.namespace,
            )
            root.remove(child)


def update_core_properties(
    doc: Document,
    title:           str,
    author:          str,
    description:     str,
    version:         str,
    document_number: str,
    subject:         str = "",
    keywords:        str = "",
    category:        str = "",
) -> None:
    """Update DOCX core (document information) properties."""
    _purge_mismatched_core_props(doc, ("keywords", "category"))

    props = doc.core_properties
    MAX_LEN = 255

    def _set_capped(attr: str, value: str) -> None:
        if not value:
            return
        if len(value) > MAX_LEN:
            value = value[:MAX_LEN - 1] + "…"
        setattr(props, attr, value)

    if title:
        props.title = title
    if author:
        props.author = author
    with _correct_cp_namespace():
        _set_capped("subject",  subject)
        _set_capped("keywords", keywords)
        _set_capped("category", category)

    parts = []
    if document_number:
        parts.append(f"Doc {document_number}")
    if version:
        parts.append(f"Version {version}")
    if description:
        parts.append(description)

    if not parts:
        return

    comments = " ".join(" | ".join(parts).split())
    if len(comments) > MAX_LEN:
        comments = comments[:MAX_LEN - 1] + "…"
    try:
        props.comments = comments
    except ValueError:
        props.comments = comments[:MAX_LEN - 1] + "…"


# ---------------------------------------------------------------------------
# TOC / trailing helpers
# ---------------------------------------------------------------------------

def mark_for_toc_update(doc: Document) -> None:
    """
    Add ``<w:updateFields w:val="true"/>`` to the final section so Word
    refreshes the TOC on next open.
    """
    sectPr = doc.sections[-1]._sectPr
    if sectPr.findall(qn("w:updateFields")):
        return
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    sectPr.append(uf)


def clean_trailing_pagebreak(doc: Document) -> None:
    """Remove the trailing blank paragraph commonly left after the TOC."""
    if len(doc.paragraphs) > 1:
        last_p = doc.paragraphs[-1]
        if not last_p.text.strip():
            parent = last_p._element.getparent()
            if parent is not None:
                parent.remove(last_p._element)