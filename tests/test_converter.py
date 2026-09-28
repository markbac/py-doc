import pytest
from pathlib import Path
from pydoc2docx import DocxConverter

def test_docx_conversion(tmp_path):
    md_file = tmp_path / "spec.md"
    md_file.write_text("# Technical Specification\n\n- Feature 1\n- Feature 2\n\n```python\nprint('hello')\n```")

    out_file = tmp_path / "spec.docx"
    converter = DocxConverter()
    res = converter.convert_file(md_file, out_file)
    
    assert res.exists()
    assert res.stat().st_size > 0
