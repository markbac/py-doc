"""``py-doc poster``: one self-contained HTML poster from a Markdown file.

The conventions are in docs/guide/12_posters.md. The settings come in layers (see poster_settings), the
blocks are in poster_blocks and the colours and fonts in poster_themes. Includes, conditions, variables,
captions and callouts are written as in every other py-doc document.
"""

from __future__ import annotations

import base64
import logging
import math
import mimetypes
import re
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

import yaml

from py_doc.diagrams.registry import PUPPETEER, TOOLS
from py_doc.directives import Fence, expand
from py_doc.pandoc.source import split_front_matter
from py_doc.poster_blocks import MD, Ctx, PosterError, block_html, esc, inline, parse_opts, qr_svg
from py_doc.poster_fonts import font_css
from py_doc.poster_settings import SettingsError, layer, merge
from py_doc.poster_themes import apply_overrides, load_theme
from py_doc.runtime import Mount, Runtime

__all__ = ["PosterError", "build", "print_pdf", "write_poster"]

PDF_TIMEOUT = 300

logger = logging.getLogger(__name__)

CSS = """
:root{__VARS__}
*{box-sizing:border-box}
body{margin:0;background:var(--backdrop)}
@page{size:__PAPER__;margin:0}
.poster{width:__W__px;margin:0 auto;background:var(--page);color:var(--text);font-family:var(--font-body);display:flex;flex-direction:column;min-height:__H__px}
header{background:var(--header);padding:34px 40px 28px;text-align:center;border-bottom:10px solid var(--accent);position:relative}
header.logo-left,header.logo-right{padding-left:300px;padding-right:300px}
header.align-left{text-align:left}
header.align-left.logo-right{padding-left:40px}
header.align-left.logo-left{padding-right:40px}
header img{position:absolute;left:40px;top:50%;transform:translateY(-50%);max-height:120px;max-width:230px}
header.logo-right img{left:auto;right:40px}
h1{margin:0;font-size:68px;line-height:1.05;color:var(--header-text);font-weight:700;font-family:var(--font-heading)}
.subtitle{font-size:36px;color:var(--subtitle);line-height:1.15;margin-top:10px}
.byline{font-size:20px;color:var(--byline);margin-top:10px}
main{padding:24px 40px 28px;display:flex;flex-direction:column;gap:20px;flex:1}
.stats{display:flex;background:var(--surface);border:1px solid var(--border);padding:16px 0}
.stat{flex:1;text-align:center;padding:4px 16px}
.stat+.stat{border-left:5px solid var(--accent)}
.stat b{display:block;font-size:50px;line-height:1;color:var(--strong)}
.stat span{display:block;font-size:18px;color:var(--muted);margin-top:8px}
.trend{display:block;font-style:normal;font-weight:700;font-size:17px;margin-top:6px}
.trend.good{color:var(--good)}
.trend.bad{color:var(--bad)}
.abstract{background:var(--secondary);color:var(--on-secondary);padding:18px 28px;font-size:19px;line-height:1.45;text-align:center}
.abstract p{margin:0}
.cols{display:flex;gap:28px;align-items:flex-start}
.col{flex:1;min-width:0;display:flex;flex-direction:column;gap:22px}
section h2{margin:0 0 10px;background:var(--primary);color:var(--on-primary);font-family:var(--font-heading);padding:10px 16px;font-size:25px;line-height:1.2}
section h2 span{color:var(--highlight);font-weight:600}
.body{font-size:16px;line-height:1.45}
.body>*:first-child{margin-top:0}
.body p{margin:0 0 10px}
.body h3{font-size:19px;margin:14px 0 6px;color:var(--strong)}
.body ul,.body ol{margin:0 0 10px;padding-left:24px}
.body img{max-width:100%;display:block;margin:0 auto 10px;background:var(--surface);border:1px solid var(--border);padding:10px}
.body table{border-collapse:collapse;width:100%;font-size:13.5px;line-height:1.35;margin:0 0 10px;background:var(--surface)}
.body th{background:var(--primary);color:var(--on-primary);text-align:left;padding:6px 10px}
.body td{padding:6px 10px;border:1px solid var(--border)}
.body code{font-family:var(--font-mono);font-size:.9em;background:var(--code);padding:1px 4px}
.body pre{background:var(--surface);border:1px solid var(--border);padding:10px 12px;overflow:auto;margin:0 0 10px}
.body pre code{background:none;padding:0;font-size:13.5px}
.body blockquote{margin:0 0 10px;background:var(--callout);border:1px solid var(--callout-border);padding:8px 12px;font-size:14px}
.body blockquote p{margin:0}
.body blockquote.callout{background:color-mix(in srgb,var(--k) 9%,var(--surface));border:1px solid color-mix(in srgb,var(--k) 40%,var(--surface));border-left:5px solid var(--k)}
.callout.note{--k:var(--note)}
.callout.tip{--k:var(--tip)}
.callout.important{--k:var(--important)}
.callout.warning{--k:var(--warning)}
.callout.caution{--k:var(--caution)}
.body blockquote.callout strong:first-child,.callout-title{color:var(--k)}
.body .callout-title{font-size:12px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;margin-bottom:2px}
.timeline{display:flex;margin:0 0 10px;position:relative;padding-top:10px}
.timeline:before{content:"";position:absolute;left:0;right:0;top:16px;border-top:3px solid var(--border)}
.tl-item{flex:1;min-width:0;position:relative;padding:22px 8px 0 0;display:flex;flex-direction:column;font-size:14px;line-height:1.3}
.tl-item i{position:absolute;top:0;left:0;width:15px;height:15px;border-radius:50%;border:3px solid var(--page)}
.tl-item b{color:var(--strong)}
.tl-item small{color:var(--muted);font-size:12.5px}
.timeline.vertical{flex-direction:column;padding:0 0 0 26px;gap:12px}
.timeline.vertical:before{top:0;bottom:0;left:7px;right:auto;border-top:0;border-left:3px solid var(--border)}
.timeline.vertical .tl-item{padding:0}
.timeline.vertical .tl-item i{left:-26px;top:1px}
.chart{display:block;width:100%;height:auto;color:var(--muted);font-family:var(--font-body)}
.qr{display:inline-flex;flex-direction:column;align-items:center;gap:4px;margin:0 0 10px;background:var(--surface);padding:8px;border:1px solid var(--border)}
.qr .cap{font-size:13px;color:var(--muted)}
.body p.caption{font-size:14px;line-height:1.4;color:var(--muted)}
.body p.caption strong{color:var(--text)}
.fig{background:var(--surface);border:1px solid var(--border);padding:14px 16px;display:flex;flex-direction:column;gap:10px;margin:0 0 10px}
.fig-title{font-size:13px;font-weight:700;color:var(--muted)}
.fig-notes{font-size:13.5px;line-height:1.45}
.fig-notes p{margin:0 0 4px}
.fig-notes blockquote{margin:0}
.bar{display:flex;gap:2px;font-size:14px;font-weight:700;color:var(--on-primary);line-height:1.25}
.bar>div{padding:8px 6px 8px 10px;display:flex;flex-direction:column;justify-content:center;min-width:0}
.bar small{font-weight:400;font-size:13.5px}
.flow{display:flex;align-items:center;gap:6px}
.node{padding:10px 14px;font-size:17px;font-weight:700;border-radius:4px;color:var(--on-primary)}
.node.out{flex:1;background:var(--surface);color:var(--text);border:2px solid var(--strong);font-size:14px;font-weight:400;line-height:1.35;padding:8px 10px;border-radius:0}
.arr{flex:1;text-align:center;font-size:12.5px;line-height:1.25;color:var(--accent-text);font-weight:600}
.arr i{display:block;font-style:normal;font-size:22px;line-height:1}
.lanes{display:flex;gap:8px}
.lane{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}
.lane b{font-size:13px;color:var(--strong)}
.cells{display:flex;gap:4px}
.cell{flex:1;font-size:12.5px;line-height:1.25;padding:8px 6px;font-weight:600}
.cell.fill{background:var(--secondary);color:var(--on-secondary)}
.cell.dash{border:2px dashed var(--secondary);color:var(--strong);padding:6px 4px}
.cards{display:grid;gap:10px;margin:0 0 10px}
.card{background:var(--surface);border:1px solid var(--border);padding:10px 12px}
.card .ch{font-size:15px;font-weight:700;color:var(--strong)}
.card .ct{font-size:14px;line-height:1.4;margin-top:3px}
.card.plain .ct{margin-top:0;line-height:1.45}
.card.label .ch{font-size:12.5px;letter-spacing:.6px;text-transform:uppercase;color:var(--accent-text)}
.card.label .ct{font-size:15px;line-height:1.35}
.lcds{display:flex;gap:10px;margin:0 0 10px}
.lcd{flex:1;min-width:0}
.lcd .scr{background:var(--lcd);border:3px solid var(--lcd-border);border-radius:4px;padding:8px 10px;font-family:var(--font-mono);font-size:14.5px;line-height:1.4;color:var(--lcd-text);font-weight:600;white-space:pre}
.lcd .cap{font-size:13px;line-height:1.3;color:var(--muted);margin-top:6px}
.banner{background:var(--secondary);color:var(--on-secondary);padding:14px 28px;font-size:22px;line-height:1.35;text-align:center;font-weight:600}
.blocks{display:flex;gap:20px}
.block{flex:1;border-left:5px solid var(--accent);padding:2px 0 2px 14px}
.block h3{margin:0;font-size:21px;color:var(--strong);font-family:var(--font-heading)}
.block .body{font-size:15.5px;margin-top:4px}
.refs{font-size:13px;line-height:1.4;color:var(--muted)}
.refs b{color:var(--strong);font-size:14px}
.refs ol,.refs ul{margin:4px 0 0;padding-left:22px;columns:2;column-gap:28px}
.refs p{margin:4px 0 0}
footer{display:flex;align-items:center;gap:24px;border-top:2px solid var(--border);padding-top:14px;margin-top:auto}
footer .fl{flex:1;font-size:26px;color:var(--strong)}
footer .fc{flex:1;text-align:center;font-size:15px;color:var(--muted)}
footer .fr{flex:1;text-align:right;font-size:15px;color:var(--muted)}
footer .logos{display:flex;gap:18px;align-items:center}
footer .logos img{max-height:56px;max-width:160px}
.docinfo{display:flex;gap:18px;font-size:12px;color:var(--muted);margin-top:-12px}
footer .fqr{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
@media print{body{background:none}.poster{margin:0}}
"""

SCRIPT = """
(function(){
var R=__RATIO__, MIN=__MIN__, PAPER=__PAPER_PX__;
var p=document.querySelector('.poster');
// Share the sections of each balanced group between its columns by their measured heights, keeping their
// order: of every split into one run of sections for each column, the one whose tallest column is shortest
function balance(){
  p.querySelectorAll('.cols[data-balance]').forEach(function(g){
    var cols=g.querySelectorAll(':scope>.col'), k=cols.length, s=[];
    cols.forEach(function(c){s.push.apply(s,c.querySelectorAll(':scope>section'));});
    var n=s.length, gap=parseFloat(getComputedStyle(cols[0]).rowGap)||0, pre=[0], i, j, t;
    if(k<2||n<=k){return;}
    for(i=0;i<n;i++){pre.push(pre[i]+s[i].getBoundingClientRect().height);}
    function run(a,b){return pre[b]-pre[a]+gap*(b-a-1);}
    var best=[[0]], cut=[[0]];
    for(i=1;i<=n;i++){best[0][i]=Infinity;}
    for(j=1;j<=k;j++){best[j]=[Infinity];cut[j]=[0];
      for(i=1;i<=n;i++){best[j][i]=Infinity;
        for(t=j-1;t<i;t++){var m=Math.max(best[j-1][t],run(t,i));if(m<best[j][i]){best[j][i]=m;cut[j][i]=t;}}}}
    var ends=[], e=n;
    for(j=k;j>0;j--){ends.unshift(e);e=cut[j][e];}
    var a=0;
    ends.forEach(function(b,c){for(i=a;i<b;i++){cols[c].appendChild(s[i]);}a=b;});
  });
}
function natural(w){p.style.zoom='1';p.style.width=w+'px';p.style.height='auto';p.style.minHeight='0';balance();return p.scrollHeight;}
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

COLUMNS = {"portrait": 2, "landscape": 3}


# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

FENCE = re.compile(r"(?ms)^```[ \t]*([\w+-]+)([^\n]*)\n(.*?)^```[ \t]*$")
CALLOUTS = ("note", "tip", "important", "warning", "caution")
_CAPTION = re.compile(r"^\s*\[\[CAPTION:\s*(?:Figure|Table)\s*\]\]\s*(?P<text>.*)$", re.I)
_STYLE = re.compile(r"^\s*\[\[STYLE:[^\]]*\]\]\s*")
_DROPPED = re.compile(r"^\s*(\[\[(LANDSCAPE|PORTRAIT)\]\]|::: \{\.pagebreak\}|:::)\s*$")
_ATTRIBUTES = re.compile(r"\s*\{(?P<attrs>[^{}]*)\}\s*$")


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


def prepare(text):
    """py-doc's own markers, outside code: a ``[[CAPTION:]]`` line is a caption, the page and Word markers go."""
    out, fence = [], Fence()
    for line in text.splitlines():
        if fence.inside(line):
            out.append(line)
        elif m := _CAPTION.match(line):
            out += ["", f"@@CAPTION@@ {m['text']}", ""]
        elif not _DROPPED.match(line):
            out.append(_STYLE.sub("", line))
    return "\n".join(out)


def callouts(out):
    """Both spellings of a py-doc callout, ``> [!WARNING]`` and ``> **Warning:**``, as callout boxes."""
    kinds = "|".join(CALLOUTS)

    def marked(m):
        kind = m.group(1).lower()
        return f'<blockquote class="callout {kind}"><p class="callout-title">{kind.title()}</p><p>'

    out = re.sub(rf"<blockquote>\s*<p>\[!({kinds})\]\s*", marked, out, flags=re.I)
    out = re.sub(rf"<blockquote>(\s*<p><strong>({kinds}):?</strong>)",
                 lambda m: f'<blockquote class="callout {m.group(2).lower()}">{m.group(1)}', out, flags=re.I)
    return out.replace("<p></p>", "")


def render(text, ctx):
    stash = []

    def take(m):
        h = block_html(m.group(1).lower(), parse_opts(m.group(2)), m.group(3).rstrip("\n"), ctx)
        if h is None:
            return m.group(0)
        stash.append(h)
        return f"\n@@BLK{len(stash) - 1}@@\n"

    text = FENCE.sub(take, embed_images(text, ctx.base))
    out = callouts(MD.render(text))
    out = re.sub(r"<p>(<strong>)?Fig\.", lambda m: f'<p class="caption">{m.group(1) or ""}Fig.', out)
    out = out.replace("<p>@@CAPTION@@ ", '<p class="caption">')
    return re.sub(r"<p>@@BLK(\d+)@@</p>", lambda m: stash[int(m.group(1))], out)


def heading_html(h):
    if ":" in h:
        a, b = h.split(":", 1)
        return f"{esc(a)}: <span>{esc(b.strip())}</span>"
    return esc(h)


def heading_attributes(heading, where):
    """A section heading and its ``{.wide colour=red}``: whether it spans every column, and its colour."""
    m = _ATTRIBUTES.search(heading)
    if not m:
        return heading.strip(), False, None
    wide, colour = False, None
    for item in parse_opts(m["attrs"]):
        if item == ".wide":
            wide = True
        elif item == "colour" or item == "color":
            colour = parse_opts(m["attrs"])[item]
        else:
            logger.warning(f"{where}: heading '{heading.strip()}' has '{item}', which a poster does not use")
    return heading[: m.start()].strip(), wide, colour


def parse_stats(text):
    """``value | label | change | good or bad`` rows. The change and its verdict are optional."""
    rows = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    rows = [r for r in rows if not re.match(r"^\|[\s:|-]+\|?$", r)][1:]  # drop separator and header row
    out = []
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if len(cells) >= 2:
            out.append((cells[0], cells[1], cells[2] if len(cells) > 2 else "", cells[3].lower() if len(cells) > 3 else ""))
    return out


def trend_html(change, verdict):
    if not change:
        return ""
    up = change.startswith("+") or change.lower().startswith("up")
    down = change.startswith(("-", "−")) or change.lower().startswith("down")
    arrow = "▲" if up else "▼" if down else "▶"
    good = verdict == "good" if verdict in ("good", "bad") else not down
    kind = "good" if good else "bad"
    return f'<em class="trend {kind}">{arrow} {esc(change)}</em>'


def number(meta, key, default, md_path, least=1):
    try:
        value = int(meta.get(key, default))
    except ValueError:
        raise PosterError(f"{md_path}: {key} must be a whole number, not '{meta[key]}'") from None
    if value < least:
        raise PosterError(f"{md_path}: {key} must be at least {least}")
    return value


def columns_of(sections, count, split, md_path):
    """The sections of each column: ``split`` gives how many go in each but the last, else they are balanced by length."""
    count = min(count, len(sections))
    if split:
        try:
            sizes = [int(x) for x in split.split(",")]
        except ValueError:
            raise PosterError(f"{md_path}: split must be a number, or numbers separated by commas") from None
        if len(sizes) != count - 1 or min(sizes) < 1 or sum(sizes) >= len(sections):
            raise PosterError(f"{md_path}: split needs {count - 1} number(s) of sections, leaving at least one for the last column")
        cuts = [sum(sizes[: i + 1]) for i in range(len(sizes))]
        return [sections[a:b] for a, b in zip([0, *cuts], [*cuts, len(sections)])]
    total, acc, columns = sum(len(c) for _, c, _ in sections), 0, [[]]
    for i, section in enumerate(sections):
        left, open_columns = len(sections) - i, count - len(columns)
        if columns[-1] and open_columns and (acc >= total * len(columns) / count or left <= open_columns):
            columns.append([])
        columns[-1].append(section)
        acc += len(section[1])
    return columns


def _choice(meta, key, choices, md_path):
    value = str(meta.get(key, choices[0])).lower()
    if value == "center":
        value = "centre"
    if value not in choices:
        raise PosterError(f"{md_path}: {key} must be {' or '.join(choices)}, not '{value}'")
    return value


def read_settings(md_path, settings=None, defaults=None):
    """The poster's settings and its Markdown body: the project defaults, the front matter, then ``settings``."""
    text = md_path.read_text(encoding="utf-8-sig")
    front, body = split_front_matter(text)
    body = "\n" * text[: len(text) - len(body)].count("\n") + body  # so a directive's line number is the file's
    try:
        data = yaml.safe_load(front) if front else {}
    except yaml.YAMLError as exc:
        raise PosterError(f"{md_path}: the front matter is not valid YAML: {exc}") from None
    try:
        front_layer = layer(data or {}, md_path.parent, f"{md_path} front matter", strict=False)
    except SettingsError as exc:
        raise PosterError(str(exc)) from None
    meta = merge(defaults, front_layer, settings)
    variables = meta.get("variables") or {}
    for key in ("title", "subtitle", "byline"):
        if key in meta:
            meta[key] = fill(meta[key], variables)
    footer = meta.setdefault("footer", {})  # the document's own number and version, unless the footer names others
    for key, source in (("document", "document_number"), ("version", "version")):
        if footer.get(key) in (None, "") and meta.get(source):
            footer[key] = meta[source]
    meta["footer"] = {k: fill(v, variables) if isinstance(v, str) else v for k, v in footer.items()}
    return meta, body


def fill(text, variables):
    """``{{name}}`` in a setting's text, from the variables. An unknown name is left as written."""
    return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(variables.get(m[1], m[0])), text)


def build(md_path, runtime: Callable[[], Runtime], settings: dict | None = None, defaults: dict | None = None):
    """The poster page for ``md_path`` and the build state (diagrams drawn and failed).

    ``defaults`` (the ``poster:`` section of py-doc.yml) are under the front matter, and ``settings`` (the
    poster's entry under ``posters:``, then the command line) are over it. Both are checked layers from
    :func:`py_doc.poster_settings.layer`.
    """
    md_path = Path(md_path)
    meta, body = read_settings(md_path, settings, defaults)
    theme = load_theme(meta.get("theme"), Path.cwd())
    apply_overrides(theme, meta, str(md_path))
    ctx = Ctx(md_path.parent, runtime, theme, render, str(md_path))
    ctx.settings = meta
    body = prepare(expand(body, md_path, meta.get("variables"), meta.get("conditions")))
    h1 = re.search(r"(?m)^# +(.+)$", body)
    title = meta.get("title") or (h1.group(1) if h1 else md_path.stem)

    parts = re.split(r"(?m)^## +(.+)$", body)
    stats, abstract, summary, references, sections = [], "", None, "", []
    for heading, content in zip(parts[1::2], parts[2::2]):
        heading, wide, colour = heading_attributes(heading, md_path)
        key = heading.lower()
        if key == "stats":
            stats = parse_stats(content)
        elif key == "abstract":
            abstract = render(content.strip(), ctx)
        elif key == "summary":
            summary = content
        elif key == "references":
            references = render(content.strip(), ctx)
        else:
            sections.append((heading, content.strip(), {"wide": wide, "colour": colour}))
    if not sections:
        raise PosterError(f"{md_path}: no sections found (expected '## Heading' blocks)")

    orientation = _choice(meta, "orientation", ("portrait", "landscape"), md_path)
    count = number(meta, "columns", COLUMNS[orientation], md_path)
    if meta.get("split") and any(extra["wide"] for _, _, extra in sections):
        raise PosterError(f"{md_path}: split cannot be used with wide sections; the columns are balanced between them")

    def sec(h, c, extra):
        style = f' style="background:{ctx.theme.colour(extra["colour"])}"' if extra["colour"] else ""
        wide = ' class="wide"' if extra["wide"] else ""
        return f'<section{wide}><h2{style}>{heading_html(h)}</h2><div class="body">{render(c, ctx)}</div></section>'

    groups, run = [], []  # the column groups, and a wide section between two of them
    for section in sections:
        if section[2]["wide"]:
            if run:
                groups.append(run)
            groups.append(section)
            run = []
        else:
            run.append(section)
    if run:
        groups.append(run)
    middle = ""
    for group in groups:
        if isinstance(group, tuple):
            middle += sec(*group)
        else:
            columns = columns_of(group, count, meta.get("split"), md_path)
            cols = "".join(f'<div class="col">{"".join(sec(*s) for s in column)}</div>' for column in columns)
            balanced = "" if meta.get("split") else " data-balance"  # the page script shares them out by height
            middle += f'<div class="cols"{balanced}>{cols}</div>'

    stats_html = "".join(
        f'<div class="stat"><b>{esc(v)}</b><span>{esc(label)}</span>{trend_html(change, verdict)}</div>'
        for v, label, change, verdict in stats
    )

    summary_html = ""
    if summary:
        chunks = re.split(r"(?m)^### +(.+)$", summary)
        banner = " ".join(chunks[0].split())
        blocks = "".join(
            f'<div class="block"><h3>{esc(h.strip())}</h3><div class="body">{render(c.strip(), ctx)}</div></div>'
            for h, c in zip(chunks[1::2], chunks[2::2]))
        summary_html = (f'<div class="banner">{inline(banner)}</div>' if banner else "") + \
                       (f'<div class="blocks">{blocks}</div>' if blocks else "")

    # minimum layout width, the script widens it until the content fits
    width = number(meta, "width", 1400 if orientation == "portrait" else 1800, md_path, least=400)
    paper = str(meta.get("paper", "a1")).lower()
    if paper not in PAPER_MM:
        raise PosterError(f"{md_path}: paper must be one of {', '.join(PAPER_MM)}")
    paper_mm = PAPER_MM[paper] if orientation == "portrait" else PAPER_MM[paper][::-1]
    # The paper's own height to width, rounded down: A paper is not exactly 1.4142, and a poster any
    # taller than its page prints a second, empty page
    ratio = math.floor(paper_mm[1] / paper_mm[0] * 10000) / 10000
    css = (CSS.replace("__VARS__", ctx.theme.css_variables()).replace("__W__", str(width))
           .replace("__H__", str(round(width * ratio))).replace("__PAPER__", "{}mm {}mm".format(*paper_mm)))
    script = (SCRIPT.replace("__RATIO__", f"{ratio:.4f}").replace("__MIN__", str(width))
              .replace("__PAPER_PX__", str(paper_mm[0] / 25.4 * 96)))
    faces, link = font_css(ctx.theme, meta.get("embed_fonts") or False, str(md_path))
    fonts = ctx.theme.fonts.get("stylesheet") if link else None
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{f'<link rel="stylesheet" href="{esc(fonts)}">' if fonts else ""}
<style>{faces}{css}</style>
</head>
<body>
<div class="poster {orientation}">
{header_html(meta, title, ctx, md_path)}
<main>
{f'<div class="stats">{stats_html}</div>' if stats_html else ""}
{f'<div class="abstract">{abstract}</div>' if abstract else ""}
{middle}
{summary_html}
{f'<div class="refs"><b>References</b>{references}</div>' if references else ""}
{footer_html(meta.get("footer") or {}, ctx)}
</main>
</div>
<script>{script}</script>
</body>
</html>
"""
    return page, ctx


def header_html(meta, title, ctx, md_path):
    header = meta.get("header") or {}
    align = _choice(header, "align", ("centre", "left"), md_path)
    side = _choice(header, "logo", ("left", "right", "none"), md_path)
    logo = ctx.theme.logo_uri() if side != "none" else None
    classes = [f"align-{align}"] + ([f"logo-{side}"] if logo else [])
    subtitle = f'<div class="subtitle">{esc(meta["subtitle"])}</div>' if meta.get("subtitle") else ""
    byline = f'<div class="byline">{esc(meta["byline"])}</div>' if meta.get("byline") else ""
    picture = f'<img alt="Logo" src="{logo}">' if logo else ""
    return f'<header class="{" ".join(classes)}">{picture}<h1>{esc(title)}</h1>\n{subtitle}\n{byline}</header>'


def footer_html(footer, ctx):
    def text(key):
        value = footer.get(key)
        return inline(str(value)) if value not in (None, "") else ""

    logos = ""
    for path in footer.get("logos") or []:
        if not path.is_file():
            raise PosterError(f"{ctx.where}: footer logo not found: {path}")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        logos += f'<img alt="Logo" src="data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}">'
    qr = ""
    if footer.get("qr"):
        label = f'<span>{text("qr-label")}</span>' if footer.get("qr-label") else ""
        qr = f'<div class="fqr">{qr_svg(str(footer["qr"]), ctx.theme.colours["strong"], 96)}{label}</div>'
    info = [text("document"), f"Version {text('version')}" if text("version") else ""]
    docinfo = "".join(f"<span>{item}</span>" for item in info if item)
    return (f'<footer><b class="fl">{text("left")}</b><span class="fc">{text("centre")}</span>'
            f'<span class="fr">{text("right")}</span>'
            + (f'<div class="logos">{logos}</div>' if logos else "") + qr + "</footer>"
            + (f'<div class="docinfo">{docinfo}</div>' if docinfo else ""))


def write_poster(source: Path, output: Path, runtime: Callable[[], Runtime], settings: dict | None = None,
                 defaults: dict | None = None, pdf: bool | None = None):
    """Build the poster ``source`` into ``output``, and print its PDF when its settings or ``pdf`` ask.

    ``pdf`` (``--pdf`` or ``--no-pdf``) wins over the ``pdf`` setting. Returns the build state and the files written.
    """
    page, ctx = build(source, runtime, settings, defaults)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    files = [output]
    wanted = ctx.settings.get("pdf") if pdf is None else pdf
    if wanted:
        target = wanted if isinstance(wanted, Path) else output.with_suffix(".pdf")
        print_pdf(ctx.runtime(), page, target)
        files.append(target)
    return ctx, files


def print_pdf(runtime: Runtime, page: str, pdf: Path) -> None:
    """Print a poster page to a one-page PDF at ``pdf``, with the Chromium of the tool container.

    The page sets its own paper size and scales itself to it, so the PDF is what Chrome's print dialogue
    makes with no margins and background graphics on. The container has no network, so web fonts the theme
    names are replaced by their fallbacks.
    """
    with tempfile.TemporaryDirectory(prefix="py-doc-poster-") as folder:
        work = Path(folder)
        source, output = work / "poster.html", work / "poster.pdf"
        source.write_text(page, encoding="utf-8")
        runtime.run(
            ["node", TOOLS / "poster_pdf.js", source, output, PUPPETEER],
            mounts=[Mount(work, writable=True), Mount(TOOLS)], workdir=work,
            env={"NODE_PATH": "/opt/node/node_modules"}, timeout=PDF_TIMEOUT,
        )  # fmt: skip
        if not output.is_file() or not output.read_bytes().startswith(b"%PDF"):
            raise PosterError(f"Chromium wrote no PDF for {pdf}")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output, pdf)

