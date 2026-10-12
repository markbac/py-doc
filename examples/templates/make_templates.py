"""Rebuild the example templates, the logo and the sample Word file.

    python templates/make_templates.py

It needs pandoc on the PATH (for its reference documents), python-docx, python-pptx and Pillow.
The files it writes are already in the folder, so you only run this to change them.

What it writes:

- ``sensor.docx``        the Word template: title page, header, footer, fonts, colours and the callout boxes
- ``sensor_Draft.docx``  the same with a red header. A document with ``status: Draft`` uses it automatically
- ``datasheet.docx``     a second Word template, with ``@@Name`` placeholders and a ``<<BODY>>`` marker
- ``report.tex``         a LaTeX template for PDF output with a green brand colour
- ``sensor.pptx``        the PowerPoint template: coloured titles and a version footer
- ``sensor_Draft.pptx``  the same with a red title colour and "DRAFT" in the version shape
- ``doc.css``            the stylesheet for HTML output
- ``logo.png`` (also copied to ``../docs/guide/images/`` and ``../docs/deck/images/``, because pictures are looked up in the folder of the
  Markdown file that uses them) and ``../word/design_review.docx`` (a plain Word file to try ``py-doc import`` on)
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml as parse_word_xml
from docx.oxml.ns import nsdecls as word_ns
from docx.shared import Cm, Pt, RGBColor
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor as PptxColour
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls

from py_doc.pandoc.reference import add_styles

HERE = Path(__file__).resolve().parent
GUIDE_IMAGES = HERE.parent / "docs" / "guide" / "images"
DECK_IMAGES = HERE.parent / "docs" / "deck" / "images"
BLUE = RGBColor(0x0B, 0x4F, 0x8A)
GREY = RGBColor(0x55, 0x55, 0x55)
RED = RGBColor(0xC6, 0x28, 0x28)
COMPANY = "Example Ltd"

VERSION_BOX = (
    f'<p:sp {nsdecls("p", "a")}><p:nvSpPr><p:cNvPr id="90" name="Version"/><p:cNvSpPr txBox="1"/><p:nvPr userDrawn="1"/></p:nvSpPr>'
    '<p:spPr><a:xfrm><a:off x="457200" y="6400800"/><a:ext cx="4572000" cy="304800"/></a:xfrm>'
    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
    '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-GB" sz="1000"/><a:t>Version {{VERSION}}</a:t></a:r></a:p></p:txBody></p:sp>'
)


def pandoc_file(name: str) -> bytes:
    return subprocess.run(["pandoc", "--print-default-data-file", name], capture_output=True, check=True).stdout


def find(styles, name: str):
    """A style by its name as written in the file (python-docx looks up Heading names in lower case)."""
    return next(style for style in styles if style.name == name)


def page_field(paragraph, instruction: str) -> None:
    """Append a Word field such as PAGE or NUMPAGES to a paragraph."""
    for kind, text in (("begin", None), (None, f" {instruction} "), ("separate", None), (None, "1"), ("end", None)):
        run = paragraph.add_run()
        if kind:
            run._r.append(parse_word_xml(f'<w:fldChar {word_ns("w")} w:fldCharType="{kind}"/>'))
        elif text.strip() == "1":
            run.text = text
        else:
            run._r.append(parse_word_xml(f'<w:instrText {word_ns("w")} xml:space="preserve">{text}</w:instrText>'))


def set_styles(document) -> None:
    """Fonts, colours and the styles pandoc and py-doc use."""
    add_styles(document)  # the boxes for callouts and the Table Grid style
    styles = document.styles
    names = {s.name for s in styles}
    find(styles, "Normal").font.name = "Calibri"
    body = find(styles, "Body Text")
    body.font.name, body.font.size = "Calibri", Pt(11)
    body.paragraph_format.space_after = Pt(6)
    for level, size in ((1, 20), (2, 15), (3, 13)):
        style = find(styles, f"Heading {level}")
        style.font.name, style.font.size, style.font.bold, style.font.color.rgb = "Calibri", Pt(size), True, BLUE
        style.paragraph_format.keep_with_next = True
    title = find(styles, "Title")
    title.font.name, title.font.size, title.font.bold, title.font.color.rgb = "Calibri", Pt(32), True, BLUE
    for name in ("Caption", "Image Caption", "Table Caption"):
        if name in names:
            style = find(styles, name)
            style.font.bold, style.font.italic, style.font.color.rgb = False, True, GREY
    if "Source Code" not in names:
        styles.add_style("Source Code", WD_STYLE_TYPE.PARAGRAPH).base_style = find(styles, "Normal")
    code = find(styles, "Source Code")
    code.font.name, code.font.size = "Consolas", Pt(9)
    if "Lead Paragraph" not in names:  # used as [[STYLE:Lead Paragraph]] in the guide
        lead = styles.add_style("Lead Paragraph", WD_STYLE_TYPE.PARAGRAPH)
        lead.base_style = find(styles, "Normal")
        lead.font.size, lead.font.color.rgb = Pt(13), GREY
        lead.paragraph_format.space_after = Pt(10)
    for section in document.sections:
        section.page_width, section.page_height = Cm(21.0), Cm(29.7)
        section.left_margin = section.right_margin = Cm(2.4)
        section.top_margin = section.bottom_margin = Cm(2.4)


def title_page(document) -> None:
    """Logo, title, description and a table of document facts, all filled in from the front matter."""
    for paragraph in list(document.paragraphs):
        paragraph._element.getparent().remove(paragraph._element)  # pandoc's sample text
    styles = document.styles
    logo = document.add_paragraph(style=find(styles, "Normal"))
    logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo.add_run().add_picture(str(HERE / "logo.png"), width=Cm(5))
    document.add_paragraph("", style="Normal")
    title = document.add_paragraph("Replace-with-Title", style=find(styles, "Title"))
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    description = document.add_paragraph("Replace-with-Description", style="Lead Paragraph")
    description.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("", style="Normal")
    facts = (
        ("Document number", "Replace-with-Document-Number"),
        ("Version", "Replace-with-Version"),
        ("Author", "Replace-with-Author"),
        ("Date", "Replace-with-Date"),
        ("Classification", "Replace-with-Classification"),
    )
    table = document.add_table(rows=len(facts), cols=2)
    table.style = "Table Grid"
    for row, (label, placeholder) in enumerate(facts):
        table.cell(row, 0).text, table.cell(row, 1).text = label, placeholder
        table.cell(row, 0).paragraphs[0].runs[0].bold = True
    document.add_page_break()
    document.add_paragraph("[[INSERTCONTENT]]", style="Normal")  # the document body goes here


def header_footer(document, header: str, colour: RGBColor = GREY) -> None:
    section = document.sections[0]
    paragraph = section.header.paragraphs[0]
    paragraph.text = header
    for run in paragraph.runs:
        run.font.size, run.font.color.rgb = Pt(9), colour
    footer = section.footer.paragraphs[0]
    footer.text = "Replace-with-Title, version Replace-with-Version"
    footer.add_run("\tPage ")
    page_field(footer, "PAGE")
    footer.add_run(" of ")
    page_field(footer, "NUMPAGES")
    for run in footer.runs:
        run.font.size, run.font.color.rgb = Pt(9), GREY


def sensor_docx() -> None:
    """A Word template: your fonts and colours, a title page with placeholders, and the marker for the body."""
    document = Document(io.BytesIO(pandoc_file("reference.docx")))
    set_styles(document)
    title_page(document)
    header_footer(document, f"{COMPANY}  |  Replace-with-Classification")
    document.save(HERE / "sensor.docx")
    # The draft template is the same file with a red header. It is chosen when the document says `status: Draft`.
    for paragraph in document.sections[0].header.paragraphs:
        paragraph.text = f"{COMPANY}  |  DRAFT, not for release  |  Replace-with-Classification"
        for run in paragraph.runs:
            run.font.size, run.font.bold, run.font.color.rgb = Pt(9), True, RED
    document.save(HERE / "sensor_Draft.docx")


def datasheet_docx() -> None:
    """A second Word template with its own conventions: ``@@Name`` placeholders and a ``<<BODY>>`` marker.
    ``py-doc.yml`` names them with ``placeholder_prefix`` and ``marker``."""
    document = Document(io.BytesIO(pandoc_file("reference.docx")))
    set_styles(document)
    for paragraph in list(document.paragraphs):
        paragraph._element.getparent().remove(paragraph._element)
    document.add_paragraph("@@Title", style="Title")
    document.add_paragraph("@@Description", style="Lead Paragraph")
    document.add_paragraph("Version @@Version, @@Date", style="Normal")
    document.add_paragraph("<<BODY>>", style="Normal")
    section = document.sections[0]
    section.header.paragraphs[0].text = f"{COMPANY} datasheet"
    section.footer.paragraphs[0].text = "@@Document-Number"
    document.save(HERE / "datasheet.docx")


def report_tex() -> None:
    """A LaTeX template for PDF output: py-doc's own with a green brand colour. Name it with ``template`` under
    ``pdf`` in ``py-doc.yml``. Everything else in the file is the built-in template, so it keeps working."""
    import py_doc.pandoc as pandoc_package

    built_in = (Path(pandoc_package.__file__).parent / "resources" / "latex_template.tex").read_text(encoding="utf-8")
    custom = built_in.replace("003C64", "1B5E20").replace("0072B2", "2E7D32")
    note = "% Report template for the example datasheet. Copied from py-doc's own LaTeX template with the brand colours\n% lgblue and lgaccent changed. Change the colours, fonts and page layout here.\n"
    (HERE / "report.tex").write_text(note + custom, encoding="utf-8", newline="\n")
    # The Draft twin: a grey DRAFT across every page. `status: Draft` chooses it, as for Word and PowerPoint.
    watermark = (
        "\\usepackage{eso-pic}\n"
        "\\AddToShipoutPictureBG{\\AtPageCenter{\\makebox(0,0){\\rotatebox{55}{\\fontsize{110}{110}\\selectfont\\textcolor[gray]{0.88}{DRAFT}}}}}\n"
    )
    draft = custom.replace("\\begin{document}", watermark + "\\begin{document}", 1)
    (HERE / "report_Draft.tex").write_text(note + "% The Draft twin: the same plus a DRAFT watermark.\n" + draft, encoding="utf-8", newline="\n")


def sensor_pptx() -> None:
    """PowerPoint templates: pandoc's layouts with a coloured title and a version shape. ``sensor_Draft.pptx`` is
    chosen when the deck says ``status: Draft``."""
    for name, label, colour in (("sensor.pptx", "Version {{VERSION}}", (0x0B, 0x4F, 0x8A)), ("sensor_Draft.pptx", "DRAFT, version {{VERSION}}", (0xC6, 0x28, 0x28))):
        presentation = Presentation(io.BytesIO(pandoc_file("reference.pptx")))
        for master in presentation.slide_masters:
            for shape in master.shapes:
                if shape.has_text_frame and shape.is_placeholder and shape.placeholder_format.type in (1, 3):  # title
                    for paragraph in shape.text_frame.paragraphs:
                        for run in paragraph.runs:
                            run.font.color.rgb = PptxColour(*colour)
            master.shapes._spTree.append(parse_xml(VERSION_BOX.replace("Version {{VERSION}}", label)))  # a master has no add_textbox
        ids = presentation.slides._sldIdLst  # pandoc's reference deck has sample slides: a template needs none
        for slide_id in list(ids):
            presentation.part.drop_rel(slide_id.rId)
            ids.remove(slide_id)
        presentation.save(HERE / name)


def doc_css() -> None:
    """The HTML stylesheet: the built-in one with the company colours. The file named as the html template replaces it."""
    import py_doc.pandoc as pandoc_package

    built_in = (Path(pandoc_package.__file__).parent / "resources" / "html.css").read_text(encoding="utf-8")
    brand = (
        "\n/* Company look: colours and measure. Everything above is py-doc's own stylesheet, kept so that\n"
        "   callouts, captions and code blocks still work. */\n"
        "body { max-width: 52rem; margin: 2rem auto; padding: 0 1rem; font-family: Calibri, 'Segoe UI', sans-serif; }\n"
        "h1, h2, h3 { color: #0b4f8a; }\n"
        "h1 { border-bottom: 2px solid #0b4f8a; padding-bottom: 0.2em; }\n"
        "table { border-collapse: collapse; }\n"
        "th { background: #0b4f8a; color: white; }\n"
        "th, td { border: 1px solid #c8d4e0; padding: 0.3em 0.6em; }\n"
        "figcaption, caption { color: #555; font-style: italic; }\n"
    )
    (HERE / "doc.css").write_text(built_in.rstrip() + "\n" + brand, encoding="utf-8", newline="\n")
    draft = (
        "\n/* Draft twin: `status: Draft` chooses this file. A red bar and a DRAFT mark on top of the company look. */\n"
        "body::before { content: 'DRAFT'; display: block; background: #c62828; color: white; text-align: center; font-weight: bold; letter-spacing: 0.3em; padding: 0.3em; }\n"
        "h1, h2, h3 { color: #c62828; }\n"
        "h1 { border-bottom-color: #c62828; }\n"
        "th { background: #c62828; }\n"
    )
    (HERE / "doc_Draft.css").write_text(built_in.rstrip() + "\n" + brand + draft, encoding="utf-8", newline="\n")


def logo() -> None:
    image = Image.new("RGB", (240, 80), (11, 79, 138))
    ImageDraw.Draw(image).text((20, 30), COMPANY, fill="white")
    GUIDE_IMAGES.mkdir(parents=True, exist_ok=True)
    image.save(HERE / "logo.png")
    for folder in (GUIDE_IMAGES, DECK_IMAGES):
        folder.mkdir(parents=True, exist_ok=True)
        image.save(folder / "logo.png")


def design_review() -> None:
    """A plain Word file to try ``py-doc import`` on: headings, bold text, lists, a table, a picture and a caption."""
    document = Document()
    document.core_properties.title = "Design review"
    document.core_properties.author = "A. Writer"
    document.add_heading("Design review", level=1)
    document.add_paragraph("We agreed the sampling design. The decision is ").add_run("final").bold = True
    document.add_heading("Actions", level=2)
    for text in ("Confirm the sampling interval", "Write the test plan"):
        document.add_paragraph(text, style="List Bullet")
    document.add_paragraph("Ask the sensor vendor", style="List Number")
    table = document.add_table(rows=3, cols=2)
    table.style = "Table Grid"
    for row, (name, owner) in enumerate((("Action", "Owner"), ("Sampling interval", "Firmware"), ("Test plan", "Test"))):
        table.cell(row, 0).text, table.cell(row, 1).text = name, owner
    data = io.BytesIO()
    Image.new("RGB", (120, 60), (46, 125, 50)).save(data, format="PNG")
    data.seek(0)
    document.add_picture(data)
    document.add_paragraph("Figure 1: The agreed layout", style="Caption")
    (HERE.parent / "word").mkdir(exist_ok=True)
    document.save(HERE.parent / "word" / "design_review.docx")


if __name__ == "__main__":
    logo()
    sensor_docx()
    datasheet_docx()
    report_tex()
    sensor_pptx()
    doc_css()
    design_review()
    print("Wrote sensor.docx, sensor_Draft.docx, datasheet.docx, report.tex, report_Draft.tex, doc_Draft.css, sensor.pptx, sensor_Draft.pptx, doc.css, logo.png, docs/guide/images/logo.png and word/design_review.docx")
