"""Linear barcodes for posters: Code 128, Code 39, EAN-13, EAN-8, UPC-A and ITF-14, as inline SVG.

``python-barcode`` turns the data into the pattern of bars; py-doc checks the data first, works out or
checks the check digit of the GS1 codes, and draws the bars itself in the theme's colour, with the digits
under them. EAN and UPC have their guard bars drawn longer, and ITF-14 its bearer bars, as printed on
products and cartons.
"""

from __future__ import annotations

import html

import barcode

TYPES = ("code128", "code39", "ean13", "ean8", "upca", "itf14")
ALIASES = {"128": "code128", "39": "code39", "ean": "ean13", "ean-13": "ean13", "ean-8": "ean8", "upc": "upca", "upc-a": "upca", "itf": "itf14", "itf-14": "itf14"}
_GS1 = {"ean13": 13, "ean8": 8, "upca": 12, "itf14": 14}  # digits with the check digit
_CODE39 = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%")
# The clear space each side, in modules. An ITF narrow bar is two modules, and ITF-14 needs ten of them
QUIET = {"code128": 10, "code39": 10, "ean13": 11, "ean8": 7, "upca": 9, "itf14": 20}


class BarcodeError(ValueError):
    """The data does not fit the barcode type. The message says why."""


def kind_of(value: str | None) -> str:
    kind = (value or "code128").lower()
    kind = ALIASES.get(kind, kind)
    if kind not in TYPES:
        raise BarcodeError(f"type must be one of {', '.join(TYPES)}, not '{value}'")
    return kind


def gs1_check_digit(digits: str) -> str:
    """The GS1 check digit (EAN, UPC, ITF-14): weights 3 and 1 from the right."""
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return str((10 - total % 10) % 10)


def checked(kind: str, data: str) -> str:
    """The data as it will be encoded: for the GS1 codes with its check digit, worked out or checked."""
    data = data.strip()
    if not data:
        raise BarcodeError("a barcode block needs the data to encode")
    if kind in _GS1:
        digits = data.replace(" ", "").replace("-", "")
        size = _GS1[kind]
        if not digits.isdigit() or len(digits) not in (size - 1, size):
            raise BarcodeError(f"{kind} takes {size - 1} digits (the check digit is worked out) or {size} with the check digit, not '{data}'")
        if len(digits) == size:
            if gs1_check_digit(digits[:-1]) != digits[-1]:
                raise BarcodeError(f"the check digit of {digits} should be {gs1_check_digit(digits[:-1])}, not {digits[-1]}: is a digit mistyped?")
            return digits
        return digits + gs1_check_digit(digits)
    if kind == "code39":
        upper = data.upper()
        bad = sorted(set(upper) - _CODE39)
        if bad:
            raise BarcodeError(f"code39 has only A to Z, 0 to 9 and - . $ / + % and space, not {' '.join(repr(c) for c in bad)}")
        return upper
    if any(ord(c) > 126 or (ord(c) < 32) for c in data):
        raise BarcodeError("code128 takes printable ASCII only")
    return data


def _code39(data: str, check: bool):
    return barcode.get_barcode_class("code39")(data, add_checksum=check)  # barcode.get() does not pass add_checksum on


def pattern(kind: str, data: str, check: bool = False) -> str:
    """The modules, left to right: 1 a bar, 0 a space, G a bar drawn longer (an EAN or UPC guard)."""
    if kind == "ean13":
        return barcode.get("ean13-guard", data[:-1]).build()[0]
    if kind == "upca":  # a UPC-A is the EAN-13 of the same number with a leading 0
        return barcode.get("ean13-guard", "0" + data[:-1]).build()[0]
    if kind == "ean8":
        return barcode.get("ean8-guard", data[:-1]).build()[0]
    if kind == "itf14":
        return barcode.get("itf", data).build()[0]
    if kind == "code39":
        return _code39(data, check).build()[0]
    return barcode.get("code128", data).build()[0]


def human_text(kind: str, data: str, check: bool = False) -> str:
    """The digits or text printed under the bars, grouped as on products."""
    if kind == "ean13":
        return f"{data[0]} {data[1:7]} {data[7:]}"
    if kind == "upca":
        return f"{data[0]} {data[1:6]} {data[6:11]} {data[11]}"
    if kind == "ean8":
        return f"{data[:4]} {data[4:]}"
    if kind == "itf14":
        return f"{data[0]} {data[1:3]} {data[3:8]} {data[8:13]} {data[13]}"
    if kind == "code39":
        full = _code39(data, check).get_fullcode()
        return f"*{full}*"
    return data


def _digit_groups(kind: str, data: str) -> list[tuple[str, float, float, str]]:
    """Where the digits of an EAN or UPC go: (digits, first module, last module, anchor). The groups sit
    between the guard bars; the first digit (and for UPC-A the last) sit outside them, in the quiet zone."""
    if kind == "ean13":  # guards at modules 0-2, 45-49 and 92-94
        return [(data[0], -1.5, -1.5, "end"), (data[1:7], 3, 45, "middle"), (data[7:], 50, 92, "middle")]
    if kind == "upca":
        return [(data[0], -1.5, -1.5, "end"), (data[1:6], 10, 45, "middle"), (data[6:11], 50, 85, "middle"), (data[11], 96.5, 96.5, "start")]
    if kind == "ean8":  # guards at modules 0-2, 31-35 and 64-66
        return [(data[:4], 3, 31, "middle"), (data[4:], 36, 64, "middle")]
    return []


def barcode_svg(kind: str, data: str, colour: str, width: int = 240, height: int = 70, text: bool = True, check: bool = False) -> str:
    """An inline SVG ``width`` pixels wide: quiet zones, the bars, and the human-readable text under them."""
    modules = pattern(kind, data, check)
    quiet = QUIET[kind]
    bearer = 8 if kind == "itf14" else 0  # ITF-14's frame: four narrow bars thick, in modules
    total = len(modules) + 2 * quiet + 2 * bearer
    unit = width / total
    bar_h = height
    font = max(10.0, min(24.0, width * 0.05))
    # EAN and UPC guards run down beside the digits, as on products
    guard_h = bar_h + (font * 0.75 if text else 5 * unit) if "G" in modules else bar_h
    text_h = font * 1.3 if text else 0
    full_h = max(guard_h, bar_h + text_h) + (2 * bearer * unit)
    rects = []
    x0 = (quiet + bearer) * unit
    top = bearer * unit
    run_start, run_kind = None, None
    for i, m in enumerate(modules + "0"):
        if m in "1G" and run_kind == m:
            continue
        if run_start is not None:
            h = guard_h if run_kind == "G" else bar_h
            rects.append(f'<rect x="{x0 + run_start * unit:.3f}" y="{top:.3f}" width="{(i - run_start) * unit:.3f}" height="{h:.3f}"/>')
            run_start, run_kind = None, None
        if m in "1G":
            run_start, run_kind = i, m
    if bearer:  # bars all round the symbol, as printed on cartons
        b = bearer * unit
        inner_w, inner_h = width - 2 * b, bar_h + 2 * b
        rects.append(f'<path fill-rule="evenodd" d="M0,0H{width:.3f}V{inner_h:.3f}H0Z M{b:.3f},{b:.3f}V{bar_h + b:.3f}H{inner_w + b:.3f}V{b:.3f}Z"/>')
    label = ""
    if text:
        y = (bar_h + 2 * bearer * unit if bearer else bar_h) + font * 0.95
        style = f'font-family="var(--font-mono), monospace" font-size="{font:.2f}"'
        groups = _digit_groups(kind, data)
        if groups:  # EAN and UPC: each group of digits in its place between the guards, the outer digits outside
            for digits, start, end, anchor in groups:
                if anchor == "middle":
                    span = (end - start) * unit * 0.86
                    label += (f'<text x="{x0 + (start + end) / 2 * unit:.3f}" y="{y:.3f}" text-anchor="middle" {style} '
                              f'textLength="{span:.3f}" lengthAdjust="spacing">{digits}</text>')  # fmt: skip
                else:
                    x = x0 + start * unit
                    label += f'<text x="{x:.3f}" y="{y:.3f}" text-anchor="{anchor}" {style}>{digits}</text>'
        else:
            label = (f'<text x="{width / 2:.3f}" y="{y:.3f}" text-anchor="middle" {style} letter-spacing="{font * 0.08:.3f}">'
                     f"{html.escape(human_text(kind, data, check))}</text>")  # fmt: skip
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{full_h:.3f}" viewBox="0 0 {width} {full_h:.3f}" '
            f'role="img" aria-label="{html.escape(kind)} {html.escape(data)}"><g fill="{colour}">{"".join(rects)}{label}</g></svg>')  # fmt: skip
