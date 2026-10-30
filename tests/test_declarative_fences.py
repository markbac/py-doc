"""The fences drawn by specialist libraries: their written forms, read by py-doc (no code of a fence runs), and the
science image they may need."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from py_doc.diagrams import BY_FENCE, render
from py_doc.diagrams import declarative as d
from py_doc.diagrams.registry import SCIENCE_FENCES
from py_doc.runtime import image


def spec(text):
    return json.loads(text)


# --- circuit ---


def test_a_circuit_names_its_elements_directions_and_anchors():
    out = spec(
        d.translate_circuit("V1: source 5 V | up\nR1: resistor 10 kΩ | right\nline | to V1.start\ndot | at R1.end")
    )
    els = out["elements"]
    assert els[0] == {"element": "SourceV", "label": "5 V", "line": 1, "name": "V1", "direction": "up"}
    assert els[2]["to"] == ["V1", "start"] and els[3]["at"] == ["R1", "end"]


@pytest.mark.parametrize(
    "text, message",
    [
        ("capacitorx 1 nF", "is not a circuit element"),
        ("R1: resistor\nR1: resistor", "used twice"),
        ("resistor | at R9.end", "R9 is not the name of an element before it"),
        ("resistor | sideways", "is not a direction"),
        ("", "at least one element"),
    ],
)
def test_circuit_mistakes(text, message):
    with pytest.raises(d.DeclarativeError, match=message):
        d.translate_circuit(text)


# --- chess and music ---


def test_a_chessboard_has_its_position_highlights_and_arrows():
    out = spec(d.translate_chess("fen: 8/8/8/8/4P3/8/8/8 w - - 0 1\nhighlight: e4\narrow: e2 e4 | red\nflip: yes"))
    assert out["fen"].startswith("8/8/8/8/4P3") and out["highlight"] == ["e4"] and out["flip"] is True
    assert out["arrows"] == [{"from": "e2", "to": "e4", "colour": "red"}]
    assert spec(d.translate_chess(""))["fen"].startswith("rnbqkbnr/pppppppp")


@pytest.mark.parametrize(
    "text, message",
    [
        ("fen: nonsense", "not a FEN"),
        ("highlight: z9", "not a square"),
        ("arrow: e2", "an arrow is"),
        ("move: e4", "starts fen:"),
    ],
)
def test_chess_mistakes(text, message):
    with pytest.raises(d.DeclarativeError, match=message):
        d.translate_chess(text)


def test_music_gets_the_header_lines_abc_needs():
    out = d.translate_music("T:Scale\nCDEF GABc")
    assert out.splitlines() == ["X:1", "T:Scale", "K:C", "CDEF GABc"]
    assert d.translate_music("X:2\nK:G\nGABc").splitlines()[:2] == ["X:2", "K:G"]


# --- the science image's fences ---


def test_molecules_are_smiles_with_names():
    out = spec(d.translate_molecule("Caffeine | CN1C=NC2=C1C(=O)N(C(=O)N2C)C\nCCO"))
    assert (
        out["kind"] == "molecule"
        and out["molecules"][0]["name"] == "Caffeine"
        and out["molecules"][1]["smiles"] == "CCO"
    )
    with pytest.raises(d.DeclarativeError, match="not a SMILES"):
        d.translate_molecule("water please")


def test_a_phylogeny_is_a_newick_tree():
    assert spec(d.translate_phylogeny("((Human,Chimp),Gorilla);"))["newick"] == "((Human,Chimp),Gorilla);"
    with pytest.raises(d.DeclarativeError, match="Newick"):
        d.translate_phylogeny("((Human,Chimp),Gorilla")


def test_ternary_points_have_three_parts():
    out = spec(d.translate_ternary("axes: Sand | Silt | Clay\nLoam | 40 | 40 | 20"))
    assert out["axes"] == ["Sand", "Silt", "Clay"] and out["points"][0]["parts"] == [40, 40, 20]
    with pytest.raises(d.DeclarativeError, match="'label \\| a \\| b \\| c'"):
        d.translate_ternary("Loam | 40 | 40")


def test_a_sequence_logo_needs_aligned_sequences_of_its_alphabet():
    assert spec(d.translate_seq_logo("ACGT\nACGA\nTCGT"))["sequences"] == ["ACGT", "ACGA", "TCGT"]
    with pytest.raises(d.DeclarativeError, match="same length"):
        d.translate_seq_logo("ACGT\nACG")
    with pytest.raises(d.DeclarativeError, match="not a letter of dna"):
        d.translate_seq_logo("ACGX\nACGT")


def test_upset_memberships_and_smith_impedances():
    assert spec(d.translate_upset("A, B | 12\nA | 5"))["memberships"][0] == {"sets": ["A", "B"], "count": 12}
    out = spec(d.translate_smith("z0: 75\nLoad | 50-25j\nOpen | 100+0j"))
    assert out["z0"] == 75 and out["points"][0] == {"label": "Load", "real": 50, "imag": -25}
    with pytest.raises(d.DeclarativeError, match="not an impedance"):
        d.translate_smith("Load | fifty ohms")


def test_plasmid_and_gene_features():
    out = spec(d.translate_plasmid("size: 5000\nAmpR | 950..1810 | - | amber\nori | 100..780"))
    assert out["size"] == 5000 and out["features"][0]["strand"] == -1 and out["features"][1]["strand"] == 1
    with pytest.raises(d.DeclarativeError, match="needs 'size: 8450'"):
        d.translate_plasmid("ori | 1..10")
    assert spec(d.translate_gene_locus("Exon 1 | 10..90"))["size"] == 190


def test_cie_sun_path_and_thermo_cycle_forms():
    assert spec(d.translate_cie("gamut: sRGB\ngamut: Display P3\nD65 | 0.3127 | 0.3290"))["gamuts"] == [
        "sRGB",
        "Display P3",
    ]
    with pytest.raises(d.DeclarativeError, match="a gamut is one of"):
        d.translate_cie("gamut: Rainbow")
    sun = spec(d.translate_sun_path("lat: 51.5\nlon: -0.1\nday: Midsummer | 2026-06-21"))
    assert sun["days"] == [{"label": "Midsummer", "date": "2026-06-21"}]
    assert len(spec(d.translate_sun_path("lat: 0\nlon: 0"))["days"]) == 3  # the solstices and an equinox
    cycle = spec(
        d.translate_thermo_cycle("fluid: Water\nstate: 1 | 10 | 40\nstate: 2 | 8000 | 41\nstate: 3 | 8000 | 500")
    )
    assert cycle["fluid"] == "Water" and [s["label"] for s in cycle["states"]] == ["1", "2", "3"]
    with pytest.raises(d.DeclarativeError, match="at least three states"):
        d.translate_thermo_cycle("state: 1 | 10 | 40")


# --- the renderers and the science image ---


@pytest.mark.parametrize("fence", ["circuit", "chess", "music", "abc", *SCIENCE_FENCES])
def test_every_specialist_fence_has_a_renderer_with_a_written_form(fence):
    renderer = BY_FENCE[fence]
    assert renderer.translate is not None and renderer.kinds == ("svg",)
    assert renderer.image == ("science" if fence in SCIENCE_FENCES else "tools")


def test_the_science_image_tag_follows_both_definitions():
    tag = image.science_ref()
    assert tag.startswith("py-doc-science:") and len(tag.split(":")[1]) == 12
    assert image.science_ref() == tag  # the same definition, the same tag


def test_a_science_fence_runs_in_the_science_image(monkeypatch, tmp_path):
    monkeypatch.setenv("PY_DOC_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(image, "ensure_science", lambda runtime: "py-doc-science:abc")
    monkeypatch.setattr(image, "science_ref", lambda: "py-doc-science:abc")
    runs = []

    class Fake:
        image = "py-doc-tools:x"

        def container_path(self, path):
            return str(path)

        def run(self, command, *, mounts, workdir, env, timeout, image=None):
            runs.append(image)
            Path(command[-1]).write_text("<svg/>", encoding="utf-8")

    rendered = render.render_parts([(tmp_path / "doc.md", "```molecule\nCCO\n```\n")], "html", lambda: Fake())
    assert runs == ["py-doc-science:abc"] and len(rendered.pictures) == 1


def test_a_mistake_in_a_written_form_names_its_file_and_line(tmp_path):
    with pytest.raises(render.DiagramError, match=r"doc\.md:3: circuit: line 1: 'blob' is not a circuit element"):
        render.render_parts([(tmp_path / "doc.md", "Text.\n\n```circuit\nblob\n```\n")], "docx", lambda: None)


def test_every_circuit_element_is_one_schemdraw_draws():
    schemdraw = pytest.importorskip("schemdraw")
    import schemdraw.elements as elm
    import schemdraw.logic as logic

    from py_doc.diagrams.declarative import CIRCUIT_ELEMENTS

    assert schemdraw  # the version the tool image pins: src/py_doc/runtime/definition/requirements.txt
    missing = [name for name, cls in CIRCUIT_ELEMENTS.items() if not hasattr(elm, cls) and not hasattr(logic, cls)]
    assert not missing
