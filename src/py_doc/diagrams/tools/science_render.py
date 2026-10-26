"""Draw a fence of the science image, from the JSON py-doc wrote from its written form (diagrams/declarative.py).

    python3 science_render.py <spec.json> <picture.svg>

The JSON's "kind" says what to draw: molecule (RDKit), phylogeny (Biopython), ternary (python-ternary), seq-logo
(logomaker), upset (UpSetPlot), smith (scikit-rf), plasmid and gene-locus (DNA Features Viewer), cie
(colour-science), sun-path (pvlib) or thermo-cycle (CoolProp). Each draws with matplotlib, except molecules, which
RDKit draws as SVG itself. A mistake ends with a message on stderr and a non-zero status.
"""

import io
import json
import sys

FONT = "DejaVu Sans"


def plt():
    import matplotlib

    matplotlib.use(
        "agg"
    )  # Agg, not the SVG backend: some libraries ask the canvas for a renderer; savefig still writes SVG
    import matplotlib.pyplot as pyplot

    pyplot.rcParams.update(
        {
            "font.family": FONT,
            "font.size": 11,
            "svg.fonttype": "path",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    return pyplot


def save(fig, output):
    fig.savefig(output, format="svg", bbox_inches="tight", facecolor="white")


def molecule(spec, output):
    from rdkit import Chem
    from rdkit.Chem import Draw

    mols, names = [], []
    for item in spec["molecules"]:
        mol = Chem.MolFromSmiles(item["smiles"])
        if mol is None:
            sys.exit(f"line {item['line']}: RDKit cannot read the SMILES '{item['smiles']}'")
        mols.append(mol)
        names.append(item["name"])
    picture = Draw.MolsToGridImage(
        mols, molsPerRow=min(4, len(mols)), subImgSize=(300, 240), legends=names, useSVG=True
    )
    with open(output, "w", encoding="utf-8") as f:
        f.write(picture if isinstance(picture, str) else picture.data)


def phylogeny(spec, output):
    from Bio import Phylo

    pyplot = plt()
    try:
        tree = Phylo.read(io.StringIO(spec["newick"]), "newick")
    except Exception as exc:  # Bio.Phylo raises its own error for each kind of mistake
        sys.exit(f"the Newick tree cannot be read: {exc}")
    leaves = len(tree.get_terminals())
    fig, ax = pyplot.subplots(figsize=(7, 0.45 * leaves + 1))
    Phylo.draw(tree, axes=ax, do_show=False)
    ax.set_ylabel("")
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    save(fig, output)


def ternary_plot(spec, output):
    import ternary

    pyplot = plt()
    fig, tax = ternary.figure(scale=100)
    fig.set_size_inches(6, 5.4)
    tax.boundary(linewidth=1.5)
    tax.gridlines(multiple=10, color="#c8ccd6", linewidth=0.6)
    a, b, c = spec["axes"]
    tax.bottom_axis_label(a, offset=0.02)
    tax.right_axis_label(b, offset=0.14)
    tax.left_axis_label(c, offset=0.14)
    tax.ticks(axis="lbr", multiple=20, linewidth=1, offset=0.02)
    for point in spec["points"]:
        total = sum(point["parts"])
        where = tuple(100 * p / total for p in point["parts"])
        tax.scatter([where], marker="o", color="#3f74b8", s=40, zorder=3)
        tax.annotate(point["label"], where, fontsize=10, xytext=(6, 4), textcoords="offset points")
    tax.clear_matplotlib_ticks()
    tax.get_axes().axis("off")
    save(fig, output)
    del pyplot


def seq_logo(spec, output):
    import logomaker

    pyplot = plt()
    matrix = logomaker.alignment_to_matrix(spec["sequences"], to_type="information", characters_to_ignore="-")
    fig, ax = pyplot.subplots(figsize=(max(4, 0.5 * len(matrix)), 2.4))
    scheme = "chemistry" if spec["alphabet"] == "protein" else "classic"
    logomaker.Logo(matrix, ax=ax, color_scheme=scheme)
    ax.set_ylabel("bits")
    ax.set_xticks(range(len(matrix)))
    ax.set_xticklabels([str(n + 1) for n in range(len(matrix))])
    save(fig, output)


def upset(spec, output):
    from upsetplot import UpSet, from_memberships

    pyplot = plt()
    data = from_memberships([m["sets"] for m in spec["memberships"]], data=[m["count"] for m in spec["memberships"]])
    fig = pyplot.figure(figsize=(8, 4))
    UpSet(data, show_counts=True, sort_by="cardinality", facecolor="#2a3150").plot(fig=fig)
    save(fig, output)


def smith(spec, output):
    from skrf import plotting

    pyplot = plt()
    fig, ax = pyplot.subplots(figsize=(5.5, 5.5))
    plotting.smith(ax=ax, draw_labels=True)
    z0 = spec["z0"]
    for point in spec["points"]:
        z = complex(point["real"], point["imag"])
        gamma = (z - z0) / (z + z0)
        ax.plot(gamma.real, gamma.imag, "o", color="#a3322b")
        ax.annotate(point["label"], (gamma.real, gamma.imag), xytext=(6, 6), textcoords="offset points")
    save(fig, output)


def _features(spec):
    from dna_features_viewer import GraphicFeature

    return [
        GraphicFeature(start=f["start"], end=f["end"], strand=f["strand"], color=f["colour"], label=f["name"])
        for f in spec["features"]
    ]


def plasmid(spec, output):
    from dna_features_viewer import CircularGraphicRecord

    plt()
    record = CircularGraphicRecord(sequence_length=spec["size"], features=_features(spec))
    ax, _ = record.plot(figure_width=6)
    ax.set_title(f"{spec['size']:,} bp")
    save(ax.figure, output)


def gene_locus(spec, output):
    from dna_features_viewer import GraphicRecord

    plt()
    record = GraphicRecord(sequence_length=spec["size"], features=_features(spec))
    ax, _ = record.plot(figure_width=8)
    save(ax.figure, output)


def cie(spec, output):
    import colour
    from colour.plotting import plot_RGB_colourspaces_in_chromaticity_diagram_CIE1931

    plt()
    known = [name for name in spec["gamuts"] if name in colour.RGB_COLOURSPACES]
    try:
        fig, ax = plot_RGB_colourspaces_in_chromaticity_diagram_CIE1931(known, show=False)
    except TypeError:  # older colour-science names it standalone
        fig, ax = plot_RGB_colourspaces_in_chromaticity_diagram_CIE1931(known, standalone=False)
    for point in spec["points"]:
        ax.plot(point["x"], point["y"], "o", color="black")
        ax.annotate(point["label"], (point["x"], point["y"]), xytext=(6, 4), textcoords="offset points")
    ax.set_title("")
    save(fig, output)


def sun_path(spec, output):
    import pandas as pd
    import pvlib

    pyplot = plt()
    fig, ax = pyplot.subplots(figsize=(8, 4))
    for day in spec["days"]:
        times = pd.date_range(f"{day['date']} 00:00", f"{day['date']} 23:59", freq="10min", tz=spec["timezone"])
        position = pvlib.solarposition.get_solarposition(times, spec["lat"], spec["lon"])
        up = position[position["apparent_elevation"] > 0]
        ax.plot(up["azimuth"], up["apparent_elevation"], linewidth=2.5, label=day["label"])
    ax.set_xlim(0, 360)
    ax.set_xticks([0, 45, 90, 135, 180, 225, 270, 315, 360], ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"])
    ax.set_ylim(0, 90)
    ax.set_ylabel("Altitude (°)")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False)
    ax.set_title(f"Latitude {spec['lat']:g}°, longitude {spec['lon']:g}°", fontsize=11)
    save(fig, output)


def thermo_cycle(spec, output):
    import numpy as np
    from CoolProp.CoolProp import PropsSI

    pyplot = plt()
    fluid = spec["fluid"]
    t_crit, t_low = PropsSI("Tcrit", fluid), PropsSI("Tmin", fluid)
    temperatures = np.linspace(t_low + 0.5, t_crit - 0.05, 120)
    liquid = [PropsSI("S", "T", t, "Q", 0, fluid) / 1000 for t in temperatures]
    vapour = [PropsSI("S", "T", t, "Q", 1, fluid) / 1000 for t in temperatures]
    fig, ax = pyplot.subplots(figsize=(7, 4.5))
    ax.plot(liquid + vapour[::-1], [t - 273.15 for t in list(temperatures) + list(temperatures[::-1])], color="#9aa0ab")
    s, t = [], []
    for state in spec["states"]:
        try:
            s.append(PropsSI("S", "P", state["p_kpa"] * 1000, "T", state["t_c"] + 273.15, fluid) / 1000)
        except ValueError as exc:
            sys.exit(
                f"the state '{state['label']}' ({state['p_kpa']:g} kPa, {state['t_c']:g} °C) is not one CoolProp can find: {str(exc)[:120]}"
            )
        t.append(state["t_c"])
    ax.plot(s + s[:1], t + t[:1], color="#a3322b", linewidth=2.5, marker="o")
    for state, x, y in zip(spec["states"], s, t):
        ax.annotate(state["label"], (x, y), xytext=(6, 6), textcoords="offset points", fontweight="bold")
    ax.set_xlabel("Entropy (kJ/kg·K)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title(fluid, fontsize=11)
    save(fig, output)


DRAW = {
    "molecule": molecule, "phylogeny": phylogeny, "ternary": ternary_plot, "seq-logo": seq_logo, "upset": upset,
    "smith": smith, "plasmid": plasmid, "gene-locus": gene_locus, "cie": cie, "sun-path": sun_path,
    "thermo-cycle": thermo_cycle,
}  # fmt: skip


def main(source, output):
    with open(source, encoding="utf-8") as f:
        spec = json.load(f)
    DRAW[spec["kind"]](spec, output)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
