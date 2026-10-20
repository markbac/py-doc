"""``py-doc poster``: one self-contained HTML poster from a Markdown file.

The conventions are in docs/guide/12_posters.md. Diagram fences are drawn by the tool container, like
in every other output, and embedded as PNG pictures.
"""

from __future__ import annotations

import base64
import html
import logging
import mimetypes
import re
import shlex
from collections.abc import Callable
from pathlib import Path

from markdown_it import MarkdownIt

from py_doc.diagrams import BY_FENCE, DiagramError
from py_doc.diagrams.render import draw_cached
from py_doc.errors import ConversionError, ToolFailed
from py_doc.runtime import Runtime

logger = logging.getLogger(__name__)

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#e9e9ef}
@page{size:__PAPER__;margin:0}
.poster{width:__W__px;margin:0 auto;background:#f3f3f7;color:#1d1f27;font-family:'Source Serif 4',Georgia,serif;display:flex;flex-direction:column;min-height:__H__px}
header{background:#3b3b40;padding:34px 40px 28px;text-align:center;border-bottom:10px solid #4a7fc1}
h1{margin:0;font-size:68px;line-height:1.05;color:#fff;font-weight:700}
.subtitle{font-size:36px;color:#7cc0f2;line-height:1.15;margin-top:10px}
.byline{font-size:20px;color:#e6e7ec;margin-top:10px}
main{padding:24px 40px 28px;display:flex;flex-direction:column;gap:20px;flex:1}
.stats{display:flex;background:#fff;border:1px solid #d5d8e2;padding:16px 0}
.stat{flex:1;text-align:center;padding:4px 16px}
.stat+.stat{border-left:5px solid #4a7fc1}
.stat b{display:block;font-size:50px;line-height:1;color:#2a3150}
.stat span{display:block;font-size:18px;color:#4a4f5c;margin-top:8px}
.abstract{background:#3f74b8;color:#fff;padding:18px 28px;font-size:19px;line-height:1.45;text-align:center}
.abstract p{margin:0}
.cols{display:flex;gap:28px;align-items:flex-start}
.col{flex:1;min-width:0;display:flex;flex-direction:column;gap:22px}
section h2{margin:0 0 10px;background:#2a3150;color:#fff;padding:10px 16px;font-size:25px;line-height:1.2}
section h2 span{color:#7cc0f2;font-weight:600}
.body{font-size:16px;line-height:1.45}
.body>*:first-child{margin-top:0}
.body p{margin:0 0 10px}
.body h3{font-size:19px;margin:14px 0 6px;color:#2a3150}
.body ul,.body ol{margin:0 0 10px;padding-left:24px}
.body img{max-width:100%;display:block;margin:0 auto 10px;background:#fff;border:1px solid #d5d8e2;padding:10px}
.body table{border-collapse:collapse;width:100%;font-size:13.5px;line-height:1.35;margin:0 0 10px;background:#fff}
.body th{background:#2a3150;color:#fff;text-align:left;padding:6px 10px}
.body td{padding:6px 10px;border:1px solid #d5d8e2}
.body code{font-family:'IBM Plex Mono',monospace;font-size:.9em;background:#e4e8f1;padding:1px 4px}
.body pre{background:#fff;border:1px solid #d5d8e2;padding:10px 12px;overflow:auto;margin:0 0 10px}
.body pre code{background:none;padding:0;font-size:13.5px}
.body blockquote{margin:0 0 10px;background:#fbeee0;border:1px solid #e3b88a;padding:8px 12px;font-size:14px}
.body blockquote p{margin:0}
.body p.caption{font-size:14px;line-height:1.4;color:#4a4f5c}
.body p.caption strong{color:#1d1f27}
.fig{background:#fff;border:1px solid #d5d8e2;padding:14px 16px;display:flex;flex-direction:column;gap:10px;margin:0 0 10px}
.fig-title{font-size:13px;font-weight:700;color:#4a4f5c}
.fig-notes{font-size:13.5px;line-height:1.45}
.fig-notes p{margin:0 0 4px}
.fig-notes blockquote{margin:0}
.bar{display:flex;gap:2px;font-size:14px;font-weight:700;color:#fff;line-height:1.25}
.bar>div{padding:8px 6px 8px 10px;display:flex;flex-direction:column;justify-content:center;min-width:0}
.bar small{font-weight:400;font-size:13.5px}
.flow{display:flex;align-items:center;gap:6px}
.node{padding:10px 14px;font-size:17px;font-weight:700;border-radius:4px;color:#fff}
.node.out{flex:1;background:#fff;color:#1d1f27;border:2px solid #2a3150;font-size:14px;font-weight:400;line-height:1.35;padding:8px 10px;border-radius:0}
.arr{flex:1;text-align:center;font-size:12.5px;line-height:1.25;color:#2f5f9f;font-weight:600}
.arr i{display:block;font-style:normal;font-size:22px;line-height:1}
.lanes{display:flex;gap:8px}
.lane{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}
.lane b{font-size:13px;color:#2a3150}
.cells{display:flex;gap:4px}
.cell{flex:1;font-size:12.5px;line-height:1.25;padding:8px 6px;font-weight:600}
.cell.fill{background:#3f74b8;color:#fff}
.cell.dash{border:2px dashed #3f74b8;color:#2a3150;padding:6px 4px}
.cards{display:grid;gap:10px;margin:0 0 10px}
.card{background:#fff;border:1px solid #d5d8e2;padding:10px 12px}
.card .ch{font-size:15px;font-weight:700;color:#2a3150}
.card .ct{font-size:14px;line-height:1.4;margin-top:3px}
.card.plain .ct{margin-top:0;line-height:1.45}
.card.label .ch{font-size:12.5px;letter-spacing:.6px;text-transform:uppercase;color:#2f5f9f}
.card.label .ct{font-size:15px;line-height:1.35}
.lcds{display:flex;gap:10px;margin:0 0 10px}
.lcd{flex:1;min-width:0}
.lcd .scr{background:#b7c79a;border:3px solid #3b3b40;border-radius:4px;padding:8px 10px;font-family:'IBM Plex Mono',monospace;font-size:14.5px;line-height:1.4;color:#1f2a14;font-weight:600;white-space:pre}
.lcd .cap{font-size:13px;line-height:1.3;color:#4a4f5c;margin-top:6px}
.banner{background:#3f74b8;color:#fff;padding:14px 28px;font-size:22px;line-height:1.35;text-align:center;font-weight:600}
.blocks{display:flex;gap:20px}
.block{flex:1;border-left:5px solid #4a7fc1;padding:2px 0 2px 14px}
.block h3{margin:0;font-size:21px;color:#2a3150}
.block .body{font-size:15.5px;margin-top:4px}
footer{display:flex;justify-content:space-between;align-items:baseline;border-top:2px solid #d5d8e2;padding-top:14px;margin-top:auto}
footer b{font-size:26px;color:#2a3150}
footer span{font-size:15px;color:#4a4f5c}
@media print{body{background:none}.poster{margin:0}}
"""

FONTS = ("https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700"
         "&family=IBM+Plex+Mono:wght@500;600&display=swap")


SCRIPT = """
(function(){
var R=1.4142, MIN=__MIN__, PAPER=__PAPER_PX__;
var p=document.querySelector('.poster');
function natural(w){p.style.zoom='1';p.style.width=w+'px';p.style.height='auto';p.style.minHeight='0';return p.scrollHeight;}
function scale(){p.style.zoom=document.documentElement.clientWidth/(+p.dataset.w);}
function fit(){
  var lo=MIN,hi=4000;
  if(natural(lo)<=lo*R){hi=lo;}
  else{while(hi-lo>6){var m=(lo+hi)>>1;if(natural(m)<=m*R){hi=m;}else{lo=m;}}}
  p.style.width=hi+'px';p.style.height=(hi*R)+'px';p.style.minHeight='';
  p.dataset.w=hi;scale();
}
window.addEventListener('resize',scale);
window.addEventListener('beforeprint',function(){p.style.zoom=PAPER/(+p.dataset.w);});
window.addEventListener('afterprint',scale);
window.addEventListener('load',fit);
if(document.fonts&&document.fonts.ready){document.fonts.ready.then(fit);}
fit();
})();
"""

PAPER_MM = {"a0": (841, 1189), "a1": (594, 841), "a2": (420, 594), "a3": (297, 420), "a4": (210, 297)}

COLOURS = {"navy": "#2a3150", "blue": "#3f74b8", "amber": "#b4540a", "brown": "#8a3d08",
           "red": "#a3322b", "grey": "#4a4f5c", "green": "#2e6b3a"}

# Mermaid theme that matches the poster palette. Skipped if the diagram has its own init.
MERMAID_INIT = ('%%{init: {"theme":"base","themeVariables":{"fontFamily":"Georgia, serif","fontSize":"16px",'
                '"primaryColor":"#e8eef8","primaryBorderColor":"#2a3150","primaryTextColor":"#1d1f27",'
                '"lineColor":"#2a3150","secondaryColor":"#f3f3f7","tertiaryColor":"#ffffff",'
                '"clusterBkg":"#f3f6fb","clusterBorder":"#3f74b8","edgeLabelBackground":"#ffffff"}}}%%\n')

FENCE = re.compile(r"(?ms)^```[ \t]*([\w+-]+)([^\n]*)\n(.*?)^```[ \t]*$")
TOK = re.compile(r"\[([^\]|]+)(?:\|([^\]]+))?\]|-(?:([^>\[\]]*?)-)?>")


MD = MarkdownIt("commonmark").enable("table")


class PosterError(ConversionError):
    """The Markdown cannot be made into a poster."""


class Ctx:
    """Per-build state shared by all blocks."""

    def __init__(self, base, runtime):
        self.base = base
        self._connect, self._runtime = runtime, None
        self.n = 0
        self.failed = 0

    def runtime(self):
        """The tool container, started on the first diagram, so a poster without one needs no Docker."""
        if self._runtime is None:
            self._runtime = self._connect()
        return self._runtime


def esc(s):
    return html.escape(s, quote=True)


def col(name):
    name = (name or "").strip().lower()
    return COLOURS.get(name, name) if name else COLOURS["navy"]


def inline(s):
    return MD.renderInline(s)


def parse_opts(info):
    try:
        toks = shlex.split(info)
    except ValueError:
        toks = info.split()
    return {k.lower(): v for k, _, v in (t.partition("=") for t in toks)}


# ---------------------------------------------------------------------------
# Diagram fences -> the tool container -> embedded image
# ---------------------------------------------------------------------------

def render_diagram(lang, code, ctx):
    ctx.n += 1
    if lang == "mermaid" and "%%{init" not in code:
        code = MERMAID_INIT + code
    return draw_cached(ctx.runtime(), BY_FENCE[lang], code, "png", False, ctx.base)


def diagram_html(lang, code, opts, ctx):
    try:
        path = render_diagram(lang, code, ctx)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode()
        return f'<img alt="{esc(opts.get("alt", lang + " diagram"))}" src="data:{mime};base64,{data}">'
    except (ToolFailed, DiagramError) as exc:  # a broken diagram must not stop the poster
        ctx.failed += 1
        lines = (getattr(exc, "output", None) or str(exc) or type(exc).__name__).strip().splitlines()
        errs = [line.strip() for line in lines if "error" in line.lower()]
        msg = (errs or lines or [type(exc).__name__])[0 if errs else -1].strip()[:160]
        logger.warning(f"{lang} diagram not rendered: {msg}")
        return (f'<pre><code>{esc(code)}</code></pre>'
                f'<p class="caption">{esc(lang)} diagram could not be rendered: {esc(msg)}</p>')


# ---------------------------------------------------------------------------
# Poster blocks: cards, lcd, and the figure kinds (segments, flow, lanes)
# ---------------------------------------------------------------------------

def cards_html(code, opts):
    rows = [[c.strip() for c in line.split("|")] for line in code.splitlines() if line.strip()]
    style = opts.get("style", "title")
    cols = int(opts.get("cols", min(len(rows), 4) or 1))
    out = ""
    for r in rows:
        head, text, colour = ("", r[0], None) if len(r) == 1 else (r[0], r[1], r[2] if len(r) > 2 else None)
        top = f' style="border-top:4px solid {col(colour or "blue")}"' if style == "top" else ""
        h = f'<div class="ch">{inline(head)}</div>' if head else ""
        out += f'<div class="card {esc(style)}"{top}>{h}<div class="ct">{inline(text)}</div></div>'
    return f'<div class="cards" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{out}</div>'


def lcd_html(code):
    screens = [[]]
    for line in code.splitlines():
        if line.strip():
            screens[-1].append(line)
        elif screens[-1]:
            screens.append([])
    out = ""
    for s in screens:
        if not s:
            continue
        shown = "".join(f"<div>{esc(x)}</div>" for x in s if not x.startswith("--"))
        cap = " ".join(x[2:].strip() for x in s if x.startswith("--"))
        out += (f'<div class="lcd"><div class="scr">{shown}</div>'
                + (f'<div class="cap">{esc(cap)}</div>' if cap else "") + "</div>")
    return f'<div class="lcds">{out}</div>'


def kv_split(code):
    meta, rest = {}, []
    for line in code.splitlines():
        m = re.match(r"^(title|height):\s*(.*)$", line.strip(), re.I)
        if m:
            meta[m.group(1).lower()] = m.group(2)
        else:
            rest.append(line)
    return meta, rest


def segments_part(code):
    meta, lines = kv_split(code)
    rows, notes = [], []
    for line in lines:
        (rows if re.match(r"^\s*\d+(\.\d+)?\s*\|", line) else notes).append(line)
    cells, detailed = "", False
    for r in (c for c in ([x.strip() for x in line.split("|")] for line in rows)):
        label = r[1] if len(r) > 1 else ""
        det = r[2] if len(r) > 2 else ""
        detailed = detailed or bool(det)
        cells += (f'<div style="flex:{r[0]};background:{col(r[3] if len(r) > 3 else "navy")}">{inline(label)}'
                  + (f"<small>{inline(det)}</small>" if det else "") + "</div>")
    h = meta.get("height") or ("64" if detailed else "36")
    return meta.get("title"), f'<div class="bar" style="min-height:{h}px">{cells}</div>', "\n".join(notes).strip()


def flow_part(code):
    meta, lines = kv_split(code)
    rows, notes = "", []
    for line in lines:
        if "->" not in line or "[" not in line:
            notes.append(line)
            continue
        parts = ""
        for m in TOK.finditer(line):
            if m.group(1) is not None:
                if m.group(2):
                    parts += f'<div class="node" style="background:{col(m.group(2))}">{inline(m.group(1))}</div>'
                else:
                    parts += f'<div class="node out">{inline(m.group(1))}</div>'
            else:
                label = (m.group(3) or "").strip()
                parts += f'<div class="arr">{inline(label) + "<br>" if label else ""}<i>→</i></div>'
        rows += f'<div class="flow">{parts}</div>'
    return meta.get("title"), rows, "\n".join(notes).strip()


def lanes_part(code):
    meta, lines = kv_split(code)
    lanes, notes = "", []
    for line in lines:
        if "|" not in line:
            notes.append(line)
            continue
        label, *cells = [c.strip() for c in line.split("|")]
        cells = [c.replace("-", "‑") for c in cells]  # non-breaking hyphen keeps "wake-up" whole
        inner = "".join(
            f'<div class="cell fill">{inline(c[1:].strip())}</div>' if c.startswith("*")
            else f'<div class="cell dash">{inline(c)}</div>' for c in cells)
        lanes += f'<div class="lane"><b>{esc(label)}</b><div class="cells">{inner}</div></div>'
    return meta.get("title"), f'<div class="lanes">{lanes}</div>', "\n".join(notes).strip()


FIG_KINDS = {"segments": segments_part, "flow": flow_part, "lanes": lanes_part}


def figure_html(parts, ctx):
    out = ""
    for title, inner, notes in parts:
        out += f'<div class="fig-title">{esc(title)}</div>' if title else ""
        out += inner
        out += f'<div class="fig-notes">{render(notes, ctx)}</div>' if notes else ""
    return f'<div class="fig">{out}</div>'


def block_html(lang, opts, code, ctx):
    """HTML for a fence we handle, or None to leave it as an ordinary code block."""
    if lang in BY_FENCE:
        return diagram_html(lang, code, opts, ctx)
    if lang == "cards":
        return cards_html(code, opts)
    if lang == "lcd":
        return lcd_html(code)
    if lang in FIG_KINDS:
        return figure_html([FIG_KINDS[lang](code)], ctx)
    if lang == "figure":  # several kinds in one box, split by +++ lines, each starting with @kind
        parts = []
        for sub in re.split(r"(?m)^\+\+\+\s*$", code):
            kind, _, body = sub.strip("\n").partition("\n")
            kind = kind.strip().lstrip("@").lower()
            if kind not in FIG_KINDS:
                logger.warning(f"unknown figure part '{kind}'")
                continue
            parts.append(FIG_KINDS[kind](body))
        return figure_html(parts, ctx)
    return None


# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

def embed_images(text, base):
    def sub(m):
        alt, src = m.group(1), m.group(2)
        if src.startswith(("http:", "https:", "data:")):
            return m.group(0)
        p = base / src
        if not p.is_file():
            logger.warning(f"image not found: {src}")
            return m.group(0)
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return f"![{alt}](data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()})"
    return re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", sub, text)


def render(text, ctx):
    stash = []

    def take(m):
        h = block_html(m.group(1).lower(), parse_opts(m.group(2)), m.group(3).rstrip("\n"), ctx)
        if h is None:
            return m.group(0)
        stash.append(h)
        return f"\n@@BLK{len(stash) - 1}@@\n"

    text = FENCE.sub(take, embed_images(text, ctx.base))
    out = MD.render(text)
    out = re.sub(r"<p>(<strong>)?Fig\.", lambda m: f'<p class="caption">{m.group(1) or ""}Fig.', out)
    return re.sub(r"<p>@@BLK(\d+)@@</p>", lambda m: stash[int(m.group(1))], out)


def parse_front_matter(text):
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith("#"):
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        text = text[m.end():]
    return meta, text


def heading_html(h):
    if ":" in h:
        a, b = h.split(":", 1)
        return f"{esc(a)}: <span>{esc(b.strip())}</span>"
    return esc(h)


def parse_stats(text):
    rows = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s:|-]+\|?$", r)][1:]  # drop separator and header row
    out = []
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if len(cells) >= 2:
            out.append((cells[0], cells[1]))
    return out


def build(md_path, runtime: Callable[[], Runtime]):
    """The poster page for ``md_path`` and the build state (diagrams drawn and failed)."""
    md_path = Path(md_path)
    ctx = Ctx(md_path.parent, runtime)
    meta, body = parse_front_matter(md_path.read_text(encoding="utf-8"))
    h1 = re.search(r"(?m)^# +(.+)$", body)
    title = meta.get("title") or (h1.group(1) if h1 else md_path.stem)

    parts = re.split(r"(?m)^## +(.+)$", body)
    stats, abstract, summary, sections = [], "", None, []
    for heading, content in zip(parts[1::2], parts[2::2]):
        key = heading.strip().lower()
        if key == "stats":
            stats = parse_stats(content)
        elif key == "abstract":
            abstract = render(content.strip(), ctx)
        elif key == "summary":
            summary = content
        else:
            sections.append((heading.strip(), content.strip()))
    if not sections:
        raise PosterError(f"{md_path}: no sections found (expected '## Heading' blocks)")

    if "split" in meta:
        n = int(meta["split"])
    else:
        total, acc, n = sum(len(c) for _, c in sections), 0, 0
        for _, c in sections:
            if acc >= total / 2 and n:
                break
            acc += len(c)
            n += 1
    n = max(1, min(n, len(sections) - 1)) if len(sections) > 1 else 1

    def sec(h, c):
        return f'<section><h2>{heading_html(h)}</h2><div class="body">{render(c, ctx)}</div></section>'

    left = "".join(sec(h, c) for h, c in sections[:n])
    right = "".join(sec(h, c) for h, c in sections[n:])
    stats_html = "".join(f'<div class="stat"><b>{esc(v)}</b><span>{esc(label)}</span></div>' for v, label in stats)

    summary_html = ""
    if summary:
        chunks = re.split(r"(?m)^### +(.+)$", summary)
        banner = " ".join(chunks[0].split())
        blocks = "".join(
            f'<div class="block"><h3>{esc(h.strip())}</h3><div class="body">{render(c.strip(), ctx)}</div></div>'
            for h, c in zip(chunks[1::2], chunks[2::2]))
        summary_html = (f'<div class="banner">{esc(banner)}</div>' if banner else "") + \
                       (f'<div class="blocks">{blocks}</div>' if blocks else "")

    width = int(meta.get("width", 1400))  # minimum layout width, the script widens it until the content fits
    paper = meta.get("paper", "a1").lower()
    if paper not in PAPER_MM:
        raise PosterError(f"{md_path}: paper must be one of {', '.join(PAPER_MM)}")
    css = (CSS.replace("__W__", str(width)).replace("__H__", str(round(width * 1.4142)))
           .replace("__PAPER__", "{}mm {}mm".format(*PAPER_MM[paper])))
    script = SCRIPT.replace("__MIN__", str(width)).replace("__PAPER_PX__", str(PAPER_MM[paper][0] / 25.4 * 96))
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{FONTS}">
<style>{css}</style>
</head>
<body>
<div class="poster">
<header><h1>{esc(title)}</h1>
{f'<div class="subtitle">{esc(meta["subtitle"])}</div>' if meta.get("subtitle") else ""}
{f'<div class="byline">{esc(meta["byline"])}</div>' if meta.get("byline") else ""}</header>
<main>
{f'<div class="stats">{stats_html}</div>' if stats_html else ""}
{f'<div class="abstract">{abstract}</div>' if abstract else ""}
<div class="cols"><div class="col">{left}</div><div class="col">{right}</div></div>
{summary_html}
<footer><b>{esc(meta.get("footer-left", ""))}</b><span>{esc(meta.get("footer-right", ""))}</span></footer>
</main>
</div>
<script>{script}</script>
</body>
</html>
"""
    return page, ctx
