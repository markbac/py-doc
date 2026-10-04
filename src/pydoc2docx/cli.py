import argparse
import os
import sys
from pathlib import Path
from .converter import DocxConverter

def main():
    parser = argparse.ArgumentParser(
        prog="py-doc2docx",
        description="Convert Markdown technical documentation to Word (.docx) documents"
    )
    parser.add_argument("input", type=str, help="Input Markdown (.md) file or directory")
    parser.add_argument("-o", "--output", type=str, help="Output Word (.docx) file path or directory")
    parser.add_argument("-t", "--template", type=str, help="Optional reference Word (.docx) template")

    parser.add_argument(
        "--allow-missing-template",
        action="store_true",
        help="Use a default blank document with a warning if the template file is not found (default: fail)",
    )

    args = parser.parse_args()

    if args.template and not args.allow_missing_template and not Path(args.template).is_file():
        print(f"Error: Word template not found: {args.template}")
        sys.exit(1)

    converter = DocxConverter(
        template_path=Path(args.template) if args.template else None,
        allow_missing_template=args.allow_missing_template,
    )
    input_path = Path(args.input).resolve()

    if input_path.is_file():
        out_path = Path(args.output) if args.output else input_path.with_suffix(".docx")
        converter.convert_file(input_path, out_path)
    elif input_path.is_dir():
        out_dir = Path(args.output) if args.output else input_path
        for root, _, files in os.walk(input_path):
            for f in files:
                if f.endswith(".md"):
                    src = Path(root) / f
                    dst = out_dir / src.relative_to(input_path).with_suffix(".docx")
                    converter.convert_file(src, dst)
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
