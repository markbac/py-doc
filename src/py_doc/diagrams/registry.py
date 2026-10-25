"""The diagram renderers: for each fence name, the commands that run in the tool container.

Adding a renderer is adding an entry to ``RENDERERS``. A command is a list of words, in which a ``Path``
is translated for the container. Every tool writes ``diagram.<kind>`` in the work folder.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

TOOLS = Path(__file__).parent / "tools"
PUPPETEER = "/etc/py-doc/puppeteer.json"  # in the image, next to the Chromium it configures
DPI = 192

# The widest a Mermaid diagram is drawn, in CSS pixels. A landscape page can show a wider diagram.
MERMAID_WIDTH = {"portrait": 1200, "landscape": 1800}


@dataclass(frozen=True)
class Job:
    source: Path
    output: Path  # the picture, in the work folder
    kind: str  # "png" or "svg", what the document needs
    landscape: bool = False
    source_dir: Path | None = None  # the folder of the Markdown file, where PlantUML finds its includes


Command = list


# Inkscape draws the picture. It can finish without writing one (a quiet failure in a container), so librsvg,
# which is also in the tool image, draws it instead and says so.
_SVG_TO_PNG = (
    'inkscape "$1" --export-type=png --export-filename="$2" --export-dpi=' + str(DPI) + " --export-background=white"
    " --export-background-opacity=1 --export-area-drawing;"
    ' test -s "$2" || { echo "inkscape wrote no picture, so librsvg draws it" >&2;'
    " rsvg-convert --dpi-x=" + str(DPI) + " --dpi-y=" + str(DPI) + ' --background-color=white -o "$2" "$1"; }'
)


def _svg_to_png(job: Job) -> Command:
    return ["sh", "-c", _SVG_TO_PNG, "svg-to-png", job.output.with_suffix(".svg"), job.output]


@dataclass(frozen=True)
class Renderer:
    name: str
    fences: tuple[str, ...]
    suffix: str  # of the source file
    kinds: tuple[str, ...]  # what the tool writes directly, the first being the default
    steps: Callable[[Job], list[Command]]  # the tool, writing in the first of `kinds` that suits (see commands)
    needs_source_dir: bool = False
    environment: Callable[[str], dict[str, str]] | None = None  # from the container path of the source folder
    cacheable: Callable[[str], bool] = field(default=lambda text: True)

    def commands(self, job: Job) -> list[Command]:
        """The commands for ``job``. An SVG-only tool is followed by Inkscape when the document needs PNG."""
        native = job.kind if job.kind in self.kinds else self.kinds[0]
        commands = self.steps(
            Job(job.source, job.output.with_suffix(f".{native}"), native, job.landscape, job.source_dir)
        )
        if native == "svg" and job.kind == "png":
            commands.append(_svg_to_png(job))
        return commands


def _mermaid(job: Job) -> list[Command]:
    # mermaid-cli 12 replaced --width and --height with --size, the longest side of the picture. mermaid.json
    # turns useMaxWidth off, so a diagram keeps its natural size and only a larger one is shrunk to --size.
    size = MERMAID_WIDTH["landscape" if job.landscape else "portrait"]
    command = ["mmdc", "-i", job.source, "-o", job.output, "-p", PUPPETEER, "-c", TOOLS / "mermaid.json"]
    command += ["--backgroundColor", "white", "--size", str(size)]
    if job.kind == "png":
        command += ["--scale", "2"]
    return [command]


def _plantuml(job: Job) -> list[Command]:
    # PlantUML writes next to its input, under the input's name
    return [["plantuml", "-charset", "UTF-8", f"-t{job.kind}", job.source]]


def _dot(job: Job) -> list[Command]:
    command = ["dot", f"-T{job.kind}", job.source, "-o", job.output]
    return [command + [f"-Gdpi={DPI}"] if job.kind == "png" else command]


def _blockdiag(tool: str) -> Callable[[Job], list[Command]]:
    return lambda job: [[tool, "-T", "png", "-o", job.output, job.source]]


def _vega(tool: str) -> Callable[[Job], list[Command]]:
    return lambda job: [[tool, job.source, job.output]]


RENDERERS: tuple[Renderer, ...] = (
    Renderer("mermaid", ("mermaid",), ".mmd", ("png", "svg"), _mermaid),
    Renderer(
        "plantuml",
        ("plantuml", "puml"),
        ".puml",
        ("png", "svg"),
        _plantuml,
        needs_source_dir=True,
        environment=lambda folder: {"JAVA_TOOL_OPTIONS": f"-Dplantuml.include.path={folder}"},
        cacheable=lambda text: "!include" not in text,  # an included file can change without the diagram changing
    ),  # fmt: skip
    Renderer("dot", ("dot", "graphviz"), ".dot", ("png", "svg"), _dot),
    Renderer("ditaa", ("ditaa",), ".ditaa", ("png",), lambda job: [["ditaa", job.source, job.output]]),
    *(
        Renderer(tool, (tool,), ".diag", ("png",), _blockdiag(tool))
        for tool in ("blockdiag", "seqdiag", "actdiag", "nwdiag", "packetdiag", "rackdiag")
    ),
    Renderer(
        "wavedrom",
        ("wavedrom",),
        ".json",
        ("svg",),
        lambda j: [["wavedrom-cli", "--input", j.source, "--svg", j.output]],
    ),
    Renderer(
        "bytefield-svg",
        ("bytefield-svg",),
        ".edn",
        ("svg",),
        lambda j: [["bytefield-svg", "--source", j.source, "--output", j.output]],
    ),  # fmt: skip
    Renderer(
        "pikchr",
        ("pikchr",),
        ".pikchr",
        ("svg",),
        lambda j: [["python3", TOOLS / "pikchr_render.py", j.source, j.output]],
    ),
    Renderer(
        "railroad",
        ("railroad",),
        ".railroad",
        ("svg",),
        lambda j: [["python3", TOOLS / "railroad_render.py", j.source, j.output]],
    ),  # fmt: skip
    Renderer("wireviz", ("wireviz",), ".yml", ("svg",), lambda j: [["wireviz", "-f", "s", j.source]]),
    Renderer("vega-lite", ("vega-lite",), ".json", ("svg",), _vega("vl2svg")),
    Renderer("vega", ("vega",), ".json", ("svg",), _vega("vg2svg")),
)
BY_FENCE: dict[str, Renderer] = {fence: renderer for renderer in RENDERERS for fence in renderer.fences}
