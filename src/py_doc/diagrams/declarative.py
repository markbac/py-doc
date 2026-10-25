"""The written forms of the fences drawn by specialist libraries in the tool image, turned into the JSON their
runner scripts read. Writing a circuit, a chessboard or a molecule never runs code: py-doc reads these lines, and
the runner (``diagrams/tools/*_render.py``) draws what the JSON says.

Each ``translate_*`` function takes the fence body and returns the runner's input, or raises DiagramError.
"""

from __future__ import annotations

import json
import re

from py_doc.errors import ConversionError


class DeclarativeError(ConversionError):
    """A fence of a specialist library has a mistake. Raised as a diagram failure, with its file and line."""


def _lines(text):
    return [
        (n, line.strip())
        for n, line in enumerate(text.splitlines(), 1)
        if line.strip() and not line.strip().startswith("#")
    ]


# ---------------------------------------------------------------------------
# circuit (schemdraw)
# ---------------------------------------------------------------------------

CIRCUIT_ELEMENTS = {  # what a line names: the schemdraw element
    "resistor": "Resistor", "capacitor": "Capacitor", "polarised": "Capacitor2", "inductor": "Inductor2",
    "diode": "Diode", "led": "LED", "zener": "Zener", "schottky": "Schottky", "battery": "Battery",
    "source": "SourceV", "current": "SourceI", "ac": "SourceSin", "switch": "Switch", "button": "Button",
    "ground": "Ground", "vdd": "Vdd", "vss": "Vss", "line": "Line", "dot": "Dot", "lamp": "Lamp", "fuse": "Fuse",
    "crystal": "Crystal", "antenna": "Antenna", "speaker": "Speaker", "motor": "Motor", "meter-v": "MeterV",
    "meter-a": "MeterA", "npn": "BjtNpn", "pnp": "BjtPnp", "nmos": "NFet", "pmos": "PFet", "opamp": "Opamp",
    "gap": "Gap", "and": "And", "or": "Or", "not": "Not", "nand": "Nand", "nor": "Nor", "xor": "Xor",
    "relay": "Relay", "transformer": "Transformer",
}  # fmt: skip
DIRECTIONS = ("right", "left", "up", "down")
ANCHOR = re.compile(r"^([A-Za-z][\w-]*)\.([A-Za-z]\w*)$")


def translate_circuit(text: str) -> str:
    """Lines of ``[name:] element [label] [| direction] [| at name.anchor] [| to name.anchor]``.

    Each element continues from the end of the one before, in its direction (default right). ``at`` starts it
    from an anchor of a named element (``R1.end``, ``R1.start``, ``U1.out``), and ``to`` draws a line to one.
    """
    elements, names = [], set()
    for number, line in _lines(text):
        parts = [part.strip() for part in line.split("|")]
        head = parts[0]
        name = None
        m = re.match(r"^([A-Za-z][\w-]*)\s*:\s*(.*)$", head)
        if m and m[1].lower() not in CIRCUIT_ELEMENTS:
            name, head = m[1], m[2]
        kind, _, label = head.partition(" ")
        kind = kind.lower()
        if kind not in CIRCUIT_ELEMENTS:
            raise DeclarativeError(
                f"line {number}: '{kind}' is not a circuit element. They are: {', '.join(sorted(CIRCUIT_ELEMENTS))}"
            )
        element = {"element": CIRCUIT_ELEMENTS[kind], "label": label.strip(), "line": number}
        if name:
            if name in names:
                raise DeclarativeError(f"line {number}: the name {name} is used twice")
            names.add(name)
            element["name"] = name
        for part in parts[1:]:
            word, _, rest = part.partition(" ")
            word = word.lower()
            if word in DIRECTIONS and not rest:
                element["direction"] = word
            elif word in ("at", "to") and ANCHOR.match(rest.strip()):
                ref = ANCHOR.match(rest.strip())
                if ref[1] not in names:
                    raise DeclarativeError(f"line {number}: {ref[1]} is not the name of an element before it")
                element[word] = [ref[1], ref[2]]
            elif word == "length" and re.fullmatch(r"[\d.]+", rest.strip()):
                element["length"] = float(rest)
            elif word == "flip" and not rest:
                element["flip"] = True
            else:
                raise DeclarativeError(
                    f"line {number}: '{part}' is not a direction (right, left, up, down), 'at name.end', "
                    "'to name.start', 'length 2' or 'flip'"
                )
        elements.append(element)
    if not elements:
        raise DeclarativeError("a circuit needs at least one element")
    return json.dumps({"elements": elements}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# chess (python-chess)
# ---------------------------------------------------------------------------

SQUARE = re.compile(r"^[a-h][1-8]$")
FEN = re.compile(r"^([pnbrqkPNBRQK1-8]+/){7}[pnbrqkPNBRQK1-8]+(\s.*)?$")


def translate_chess(text: str) -> str:
    """``fen: <position>``, ``highlight: e4 f3``, ``arrow: f1 c4 | colour`` and ``flip: yes`` lines. Without a
    fen line, the starting position."""
    spec = {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "highlight": [],
        "arrows": [],
        "flip": False,
    }
    for number, line in _lines(text):
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "fen":
            if not FEN.match(value):
                raise DeclarativeError(f"line {number}: '{value[:40]}' is not a FEN position")
            spec["fen"] = value
        elif key == "highlight":
            squares = value.lower().split()
            bad = [s for s in squares if not SQUARE.match(s)]
            if bad:
                raise DeclarativeError(f"line {number}: {', '.join(bad)} is not a square such as e4")
            spec["highlight"] += squares
        elif key == "arrow":
            move, _, colour = value.partition("|")
            squares = move.lower().split()
            if len(squares) != 2 or not all(SQUARE.match(s) for s in squares):
                raise DeclarativeError(f"line {number}: an arrow is 'arrow: f1 c4', not '{value}'")
            spec["arrows"].append({"from": squares[0], "to": squares[1], "colour": colour.strip() or "#2e6b3a"})
        elif key == "flip":
            spec["flip"] = value.lower() in ("yes", "true")
        else:
            raise DeclarativeError(
                f"line {number}: a chess line starts fen:, highlight:, arrow: or flip:, not '{key}:'"
            )
    return json.dumps(spec)


# ---------------------------------------------------------------------------
# music (abcjs): ABC notation is already a written form; it is checked for a key line
# ---------------------------------------------------------------------------


def translate_music(text: str) -> str:
    """ABC notation, as written. ``X:`` and ``K:`` header lines are added when it has none."""
    lines = text.strip().splitlines()
    if not lines:
        raise DeclarativeError("a music fence needs ABC notation, such as 'K:C' and 'CDEF GABc'")
    if not any(line.startswith("X:") for line in lines):
        lines.insert(0, "X:1")
    if not any(re.match(r"^K:", line) for line in lines):
        # K: ends the header, so it goes after the last header line (X:, T:, M:, L: ...)
        last = max(n for n, line in enumerate(lines) if re.match(r"^[A-Za-z]:", line))
        lines.insert(last + 1, "K:C")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# The science image: fences drawn by matplotlib, RDKit, CoolProp and the like (diagrams/tools/science_render.py)
# ---------------------------------------------------------------------------


def _science(kind: str, spec: dict) -> str:
    return json.dumps({"kind": kind, **spec}, ensure_ascii=False)


def _keyed(text: str, keys: tuple[str, ...], what: str) -> tuple[dict[str, str], list[tuple[int, list[str]]]]:
    """``key: value`` lines for ``keys``, and the other lines as pipe-separated cells."""
    found, rows = {}, []
    for number, line in _lines(text):
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() in keys and "|" not in key:
            found[key.strip().lower()] = value.strip()
        else:
            rows.append((number, [cell.strip() for cell in line.split("|")]))
    return found, rows


def _number(text: str, number: int, what: str) -> float:
    try:
        return float(text.replace(",", ""))
    except ValueError:
        raise DeclarativeError(f"line {number}: {what} '{text}' is not a number") from None


SMILES = re.compile(r"^[A-Za-z0-9@+\-\[\]\(\)=#$:/\\.%*]+$")


def translate_molecule(text: str) -> str:
    """``name | SMILES`` lines, or one SMILES on its own: 2D structures drawn by RDKit, in a grid."""
    molecules = []
    for number, line in _lines(text):
        name, sep, smiles = line.rpartition("|") if "|" in line else ("", "", line)
        smiles = smiles.strip()
        if not SMILES.match(smiles):
            raise DeclarativeError(f"line {number}: '{smiles}' is not a SMILES string, such as CC(=O)O")
        molecules.append({"name": name.strip(), "smiles": smiles, "line": number})
    if not molecules:
        raise DeclarativeError("a molecule fence needs a SMILES string, or 'name | SMILES' lines")
    return _science("molecule", {"molecules": molecules})


def translate_phylogeny(text: str) -> str:
    """A tree in Newick form, such as ``((Human,Chimp),Gorilla);``, drawn as a cladogram."""
    tree = " ".join(line for _, line in _lines(text))
    if not tree.endswith(";") or tree.count("(") != tree.count(")"):
        raise DeclarativeError("a phylogeny is a tree in Newick form, ending in ';', with its brackets matched")
    return _science("phylogeny", {"newick": tree})


def translate_ternary(text: str) -> str:
    """``axes: A | B | C`` and ``label | a | b | c`` lines, the three parts of each point in any unit."""
    keys, rows = _keyed(text, ("axes", "title"), "ternary")
    axes = [a.strip() for a in keys.get("axes", "A | B | C").split("|")]
    if len(axes) != 3:
        raise DeclarativeError("axes: names three parts, such as 'axes: Sand | Silt | Clay'")
    points = []
    for number, cells in rows:
        if len(cells) < 4:
            raise DeclarativeError(f"line {number}: a point is 'label | a | b | c'")
        parts = [_number(c, number, "a part") for c in cells[1:4]]
        if sum(parts) <= 0:
            raise DeclarativeError(f"line {number}: the parts of '{cells[0]}' add up to nothing")
        points.append({"label": cells[0], "parts": parts})
    return _science("ternary", {"axes": axes, "points": points})


def translate_seq_logo(text: str) -> str:
    """Aligned sequences, one a line, all of one length: DNA, RNA or protein. ``type: protein`` for protein."""
    keys, rows = _keyed(text, ("type",), "seq-logo")
    sequences = ["".join(cells).replace(" ", "").upper() for _, cells in rows]
    if len(sequences) < 2:
        raise DeclarativeError("a sequence logo needs at least two aligned sequences")
    if len({len(s) for s in sequences}) != 1:
        raise DeclarativeError("the sequences of a logo must all be the same length (aligned)")
    alphabet = keys.get("type", "dna").lower()
    allowed = {"dna": "ACGT-", "rna": "ACGU-", "protein": "ACDEFGHIKLMNPQRSTVWY-"}.get(alphabet)
    if allowed is None:
        raise DeclarativeError(f"type: is dna, rna or protein, not '{alphabet}'")
    bad = sorted({c for s in sequences for c in s} - set(allowed))
    if bad:
        raise DeclarativeError(f"{', '.join(bad)} is not a letter of {alphabet}")
    return _science("seq-logo", {"sequences": sequences, "alphabet": alphabet})


def translate_upset(text: str) -> str:
    """``Set A, Set B | count`` lines: how many items are in exactly those sets."""
    memberships = []
    for number, line in _lines(text):
        sets, _, count = line.rpartition("|")
        names = [s.strip() for s in sets.split(",") if s.strip()]
        if not names:
            raise DeclarativeError(f"line {number}: an UpSet line is 'Set A, Set B | count'")
        memberships.append({"sets": names, "count": _number(count.strip(), number, "a count")})
    if not memberships:
        raise DeclarativeError("an UpSet plot needs 'Set A, Set B | count' lines")
    return _science("upset", {"memberships": memberships})


IMPEDANCE = re.compile(r"^\s*(-?[\d.]+)\s*([+-])\s*j\s*([\d.]+)\s*$|^\s*(-?[\d.]+)\s*([+-])\s*([\d.]+)\s*j\s*$")


def translate_smith(text: str) -> str:
    """``z0: 50`` and ``label | 50+25j`` lines: impedances in ohms, drawn normalised on a Smith chart."""
    keys, rows = _keyed(text, ("z0", "title"), "smith")
    z0 = _number(keys.get("z0", "50"), 0, "z0")
    points = []
    for number, cells in rows:
        if len(cells) < 2:
            raise DeclarativeError(f"line {number}: a point is 'label | 50+25j'")
        m = IMPEDANCE.match(cells[1].replace(" ", ""))
        if not m:
            raise DeclarativeError(f"line {number}: '{cells[1]}' is not an impedance such as 50+25j")
        real, sign, imag = (m[1], m[2], m[3]) if m[1] is not None else (m[4], m[5], m[6])
        points.append({"label": cells[0], "real": float(real), "imag": float(imag) * (1 if sign == "+" else -1)})
    return _science("smith", {"z0": z0, "points": points})


SPAN = re.compile(r"^\s*(\d+)\s*\.\.\s*(\d+)\s*$")


def _features(rows):
    features = []
    for number, cells in rows:
        if len(cells) < 2:
            raise DeclarativeError(f"line {number}: a feature is 'name | start..end | strand | colour'")
        m = SPAN.match(cells[1])
        if not m:
            raise DeclarativeError(f"line {number}: '{cells[1]}' is not a span such as 100..780")
        strand = cells[2] if len(cells) > 2 and cells[2] else "+"
        if strand not in ("+", "-", "0", "->", "<-"):
            raise DeclarativeError(f"line {number}: a strand is +, - or 0, not '{strand}'")
        features.append({
            "name": cells[0], "start": int(m[1]), "end": int(m[2]),
            "strand": {"+": 1, "->": 1, "-": -1, "<-": -1}.get(strand, 0),
            "colour": cells[3] if len(cells) > 3 and cells[3] else "#3f74b8",
        })  # fmt: skip
    return features


def translate_plasmid(text: str) -> str:
    """``size: 8450`` and ``name | start..end | + or - | colour`` lines: a circular map."""
    keys, rows = _keyed(text, ("size", "title"), "plasmid")
    if "size" not in keys:
        raise DeclarativeError("a plasmid map needs 'size: 8450' (base pairs)")
    return _science("plasmid", {"size": int(_number(keys["size"], 0, "size")), "features": _features(rows)})


def translate_gene_locus(text: str) -> str:
    """``size: 5000`` and ``name | start..end | + or - | colour`` lines: a linear map of a locus."""
    keys, rows = _keyed(text, ("size", "title"), "gene-locus")
    features = _features(rows)
    size = int(_number(keys["size"], 0, "size")) if "size" in keys else max(f["end"] for f in features) + 100
    return _science("gene-locus", {"size": size, "features": features})


GAMUTS = ("sRGB", "Display P3", "Adobe RGB (1998)", "ITU-R BT.2020", "DCI-P3")


def translate_cie(text: str) -> str:
    """``gamut: sRGB`` lines (sRGB, Display P3, Adobe RGB (1998), ITU-R BT.2020, DCI-P3) and ``label | x | y``
    points, on the CIE 1931 chromaticity diagram."""
    gamuts, points = [], []
    for number, line in _lines(text):
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() == "gamut":
            if value.strip() not in GAMUTS:
                raise DeclarativeError(f"line {number}: a gamut is one of {', '.join(GAMUTS)}")
            gamuts.append(value.strip())
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 3:
            raise DeclarativeError(f"line {number}: a point is 'label | x | y'")
        points.append({"label": cells[0], "x": _number(cells[1], number, "x"), "y": _number(cells[2], number, "y")})
    return _science("cie", {"gamuts": gamuts or ["sRGB"], "points": points})


DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def translate_sun_path(text: str) -> str:
    """``lat: 51.5``, ``lon: -0.1``, ``timezone: Europe/London`` and ``day: label | 2026-06-21`` lines: the sun's
    altitude against its azimuth through each day."""
    keys, rows = _keyed(text, ("lat", "lon", "timezone"), "sun-path")
    if "lat" not in keys or "lon" not in keys:
        raise DeclarativeError("a sun path needs 'lat:' and 'lon:'")
    days = []
    for number, cells in rows:
        name = re.sub(r"^day\s*:\s*", "", cells[0])
        day = cells[1] if len(cells) > 1 else name  # 'day: June | 2026-06-21', or the date alone
        if not DATE.match(day):
            raise DeclarativeError(f"line {number}: a day is 'day: label | 2026-06-21'")
        days.append({"label": name if len(cells) > 1 else day, "date": day})
    lat, lon = _number(keys["lat"], 0, "lat"), _number(keys["lon"], 0, "lon")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise DeclarativeError("lat: is from -90 to 90 and lon: from -180 to 180")
    default = [
        {"label": "June solstice", "date": "2026-06-21"},
        {"label": "Equinox", "date": "2026-03-20"},
        {"label": "December solstice", "date": "2026-12-21"},
    ]
    return _science(
        "sun-path", {"lat": lat, "lon": lon, "timezone": keys.get("timezone", "UTC"), "days": days or default}
    )


FLUIDS = ("Water", "R134a", "R32", "R410A", "R744", "Ammonia", "Propane", "Air", "Nitrogen", "CO2")


def translate_thermo_cycle(text: str) -> str:
    """``fluid: Water`` and ``state: label | pressure in kPa | temperature in °C`` lines, joined in order and closed:
    a cycle on the temperature-entropy diagram, with the fluid's saturation dome."""
    keys, rows = _keyed(text, ("fluid", "title"), "thermo-cycle")
    fluid = keys.get("fluid", "Water")
    if fluid not in FLUIDS:
        raise DeclarativeError(f"fluid: is one of {', '.join(FLUIDS)}, not '{fluid}'")
    states = []
    for number, cells in rows:
        name = cells[0].removeprefix("state:").strip()
        if len(cells) < 3:
            raise DeclarativeError(f"line {number}: a state is 'state: label | kPa | °C'")
        states.append(
            {
                "label": name,
                "p_kpa": _number(cells[1], number, "a pressure"),
                "t_c": _number(cells[2], number, "a temperature"),
            }
        )
    if len(states) < 3:
        raise DeclarativeError("a cycle needs at least three states")
    return _science("thermo-cycle", {"fluid": fluid, "states": states})
