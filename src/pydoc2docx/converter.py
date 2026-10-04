import re
from pathlib import Path
from typing import Optional

from docx import Document
from docx.shared import Inches, Pt, RGBColor

from .pylogkit import setup_logging

logger = setup_logging(name="Doc2Docx", to_console=True, to_file=False)

# CommonMark ATX heading: one to six '#' followed by whitespace or end of line.
HEADING_RE = re.compile(r"^(#{1,6})(?:\s+(.*))?$")

class DocxConverter:
    """
    Converts Markdown technical documentation into Word (.docx) documents based on createdocs specification.
    """

    def __init__(self, template_path: Optional[Path] = None):
        self.template_path = Path(template_path) if template_path else None

    @staticmethod
    def _add_code_block(doc, code_lines):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.4)
        run = p.add_run("\n".join(code_lines))
        run.font.name = "Consolas"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(30, 41, 59)

    def convert_file(self, md_path: Path, output_path: Path) -> Path:
        md_path = Path(md_path).resolve()
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")

        logger.info(f"Converting Markdown '{md_path.name}' -> Word '{output_path.name}'...")

        if self.template_path and self.template_path.exists():
            doc = Document(str(self.template_path))
            logger.info(f"Loaded reference Word template: {self.template_path.name}")
        else:
            doc = Document()

        content = md_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        in_code_block = False
        code_lines = []

        for line in lines:
            stripped = line.strip()

            # Handle Code Blocks
            if stripped.startswith("```"):
                if in_code_block:
                    # End of code block
                    self._add_code_block(doc, code_lines)
                    code_lines = []
                    in_code_block = False
                else:
                    in_code_block = True
                    code_lines = []
                continue

            if in_code_block:
                code_lines.append(line)
                continue

            # Headings
            if stripped.startswith("#"):
                match = HEADING_RE.match(stripped)
                if match:
                    text = (match.group(2) or "").strip()
                    if text:
                        doc.add_heading(text, level=min(len(match.group(1)), 4))
                    continue

            # Bullet points
            if stripped.startswith("- ") or stripped.startswith("* "):
                doc.add_paragraph(stripped[2:], style='List Bullet')
                continue

            # Numbered list
            num_match = re.match(r"^\d+\.\s*(.*)", stripped)
            if num_match:
                doc.add_paragraph(num_match.group(1), style='List Number')
                continue

            # Paragraph
            if stripped:
                doc.add_paragraph(stripped)

        if in_code_block:
            logger.warning(
                f"Unclosed code fence in '{md_path.name}': keeping the remaining lines as a code block"
            )
            self._add_code_block(doc, code_lines)

        doc.save(str(output_path))
        logger.info(f"Successfully generated Word document: {output_path}")
        return output_path
