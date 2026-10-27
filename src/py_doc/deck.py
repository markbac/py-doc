"""An HTML deck: the slides of a deck's Markdown as one self-contained web page, for a screen, the web or a PDF.

The same Markdown as ``py-doc slides`` writes to PowerPoint, split into slides the same way: at each heading up
to ``split_level`` and at each page break, a heading above that level making a section slide, and the front
matter's title a title slide. Each slide is drawn by the poster engine, so poster blocks are HTML in the
deck's theme, diagrams are SVG from the tool container and maths is MathML. Speaker notes go to the presenter
view. The page scales each slide to the window and has its own navigation, so it needs no other file.
"""

from __future__ import annotations

import html
import json
import logging
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from py_doc.diagrams.registry import PUPPETEER, TOOLS
from py_doc.directives import Fence
from py_doc.errors import ConversionError
from py_doc.pandoc.pptx_finish import LINES_PER_SLIDE, notes_to_divs
from py_doc.runtime import Mount

logger = logging.getLogger(__name__)

ASPECTS = {"16:9": (1024, 576), "4:3": (1024, 768)}
PDF_TIMEOUT = 300
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*(\{[^{}]*\})?\s*$")
_DIV_OPEN = re.compile(r"^(:{3,})\s*\{?\s*\.?([\w-]+)[^}]*\}?\s*$")
_DIV_CLOSE = re.compile(r"^:{3,}\s*$")


class DeckError(ConversionError):
    """A deck cannot be made: a setting or the Markdown has a mistake."""


@dataclass
class Slide:
    kind: str  # title, part or content
    title: str = ""
    body: list[str] = field(default_factory=list)  # Markdown lines
    notes: list[str] = field(default_factory=list)  # Markdown lines


def split_slides(markdown: str, split_level: int = 2) -> list[Slide]:
    """The slides of ``markdown``: a new one at each heading up to ``split_level`` and at each page break. A
    heading above that level makes a section (part) slide. Speaker notes (``::: notes``) are set aside."""
    slides: list[Slide] = []
    fence = Fence()
    lines = notes_to_divs(markdown).split("\n")
    current: Slide | None = None
    in_notes = False
    depth = 0  # the fenced divs open inside the notes
    skip_close = False
    for line in lines:
        if fence.inside(line):  # code, whatever it holds, stays with the slide or the notes it is in
            if in_notes:
                current.notes.append(line)
            else:
                current = current or _new(slides)
                current.body.append(line)
            continue
        stripped = line.strip()
        if in_notes:
            if _DIV_CLOSE.match(stripped) and depth == 0:
                in_notes = False
            else:
                depth += 1 if _DIV_OPEN.match(stripped) else -1 if _DIV_CLOSE.match(stripped) else 0
                current.notes.append(line)
            continue
        if skip_close:
            skip_close = False
            if _DIV_CLOSE.match(stripped):
                continue
        heading = _HEADING.match(line)
        if heading and len(heading[1]) <= split_level:
            current = Slide("part" if len(heading[1]) < split_level else "content", heading[2].strip())
            slides.append(current)
            continue
        opening = _DIV_OPEN.match(stripped)
        if opening and opening[2] == "pagebreak":
            current = _new(slides)
            skip_close = True
            continue
        if opening and opening[2] == "notes":
            current = current or _new(slides)
            in_notes, depth = True, 0
            continue
        if current is None:
            if not stripped:
                continue
            current = _new(slides)
        current.body.append(line)
    return [slide for slide in slides if slide.kind != "content" or slide.title or _text(slide.body) or slide.notes]


def prepare(text: str) -> str:
    """py-doc's markers, outside code: a ``[[CAPTION:]]`` line is a numbered caption, as on a poster, and the
    page orientation and Word style markers go. Page breaks and fenced divs stay: they make slides and columns."""
    from py_doc.poster import _CAPTION, _STYLE

    out, fence, counts = [], Fence(), {"Figure": 0, "Table": 0}
    for line in text.splitlines():
        if fence.inside(line):
            out.append(line)
        elif m := _CAPTION.match(line):
            kind = m["kind"].title()
            counts[kind] += 1
            out += ["", f"@@CAPTION@@ **{kind} {counts[kind]}:** {m['text']}", ""]
        elif not re.match(r"^\s*\[\[(LANDSCAPE|PORTRAIT)\]\]\s*$", line):
            out.append(_STYLE.sub("", line))
    return "\n".join(out)


def _new(slides: list[Slide]) -> Slide:
    slides.append(Slide("content"))
    return slides[-1]


def _text(lines: list[str]) -> str:
    return "\n".join(lines).strip()


def line_count(slide: Slide) -> int:
    """The lines a slide shows, roughly as PowerPoint counts its paragraphs: its text, items, rows and code. A
    diagram or block is drawn as a picture, so its lines are not shown: it counts as one."""
    from py_doc.diagrams.registry import BY_FENCE
    from py_doc.poster_blocks import BLOCKS

    count, picture = 0, None
    for line in slide.body:
        stripped = line.strip()
        if picture:
            if stripped == picture:
                picture = None
            continue
        opening = re.match(r"^(`{3,}|~{3,})\s*\{?\.?([\w-]+)", stripped)
        if opening and (opening[2] in BY_FENCE or opening[2] in BLOCKS or opening[2] == "plot"):
            picture = opening[1]
            count += 1
            continue
        if (
            not stripped
            or stripped.startswith(("```", ":::", "<div", "</div"))
            or re.match(r"^\|?[\s:|-]+\|?$", stripped)
        ):
            continue
        count += 1
    return count


def _divs(lines: list[str]) -> str:
    """Pandoc's fenced divs (``:::: columns``, ``::: column``, ``::: incremental``) as HTML around Markdown."""
    out, fence, stack = [], Fence(), []
    for line in lines:
        if fence.inside(line):
            out.append(line)
            continue
        stripped = line.strip()
        opening = _DIV_OPEN.match(stripped)
        if opening:
            stack.append(opening[2])
            out += ["", f'<div class="{html.escape(opening[2])}">', ""]
        elif _DIV_CLOSE.match(stripped) and stack:
            stack.pop()
            out += ["", "</div>", ""]
        else:
            out.append(line)
    out += ["", "</div>", ""] * len(stack)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

CSS = """
html,body{margin:0;height:100%;overflow:hidden;background:var(--backdrop)}
.slide{position:absolute;left:50%;top:50%;width:__W__px;height:__H__px;box-sizing:border-box;padding:40px 56px 54px;
  background:var(--page);color:var(--text);font-family:var(--font-body);display:none;flex-direction:column;overflow:hidden;
  transform:translate(-50%,-50%) scale(var(--k,1));transform-origin:center}
.slide.active{display:flex;animation:fade .25s ease}
@keyframes fade{from{opacity:0}to{opacity:1}}
.slide>h2{margin:0 0 18px;font-family:var(--font-heading);color:var(--strong);font-size:34px;line-height:1.15;
  border-bottom:4px solid var(--accent);padding-bottom:10px}
.slide .body{flex:1;min-height:0;font-size:20px;line-height:1.4}
.slide .body h3{font-size:22px}
.slide .body ul,.slide .body ol{padding-left:28px}
.slide .body li{margin:0 0 6px}
.slide .body img{max-height:360px;width:auto}
.slide.title{background:var(--header);justify-content:center;text-align:center;border-bottom:12px solid var(--accent)}
.slide.title h1{margin:0;font-size:52px;color:var(--header-text);font-family:var(--font-heading);line-height:1.1}
.slide.title .subtitle{font-size:28px;color:var(--subtitle);margin-top:14px}
.slide.title .byline{font-size:20px;color:var(--byline);margin-top:22px}
.slide.part{background:var(--primary);justify-content:center}
.slide.part>h2{color:var(--on-primary);font-size:46px;border:0}
.slide.part .body{flex:0;color:var(--on-primary)}
.columns{display:flex;gap:28px}
.column{flex:1;min-width:0}
.slide .notes{display:none}
.slide .foot{position:absolute;left:56px;right:56px;bottom:16px;display:flex;justify-content:space-between;font-size:13px;color:var(--muted)}
.slide.title .foot,.slide.part .foot{color:var(--on-primary);opacity:.8}
.slide.overflow{outline:6px solid var(--bad);outline-offset:-6px}
.deck.overview{position:fixed;inset:0;overflow:auto}
.deck.overview .slide{display:flex;transform:scale(var(--o,.25));transform-origin:0 0;cursor:pointer;animation:none}
.deck.overview .slide.active{outline:8px solid var(--accent)}
.presenter{display:grid;grid-template-columns:3fr 2fr;grid-template-rows:auto 1fr auto;gap:14px;padding:14px;height:100%;box-sizing:border-box;
  background:#1d1f27;color:#e6e9ef;font-family:var(--font-body)}
.presenter .now,.presenter .next{position:relative;background:#000;overflow:hidden}
.presenter .now{grid-row:1/3}
.presenter .next{aspect-ratio:__W__/__H__}
.presenter .now .slide,.presenter .next .slide{display:flex;animation:none}
.presenter .notes-text{overflow:auto;font-size:20px;line-height:1.45;background:#2a2d38;padding:12px 16px}
.presenter .bar{grid-column:1/3;display:flex;justify-content:space-between;font-size:22px}
@media print{
  @page{size:__W__px __H__px;margin:0}
  html,body,.deck{height:auto;overflow:visible;background:none;margin:0;padding:0;display:block}
  .slide{display:flex!important;position:relative;left:auto;top:auto;transform:none;animation:none;margin:0;
    height:__H__px!important;break-inside:avoid;break-after:page;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .slide:last-child{break-after:auto}
  .slide.overflow{outline:0}
}
"""

SCRIPT = """
(function(){
var W=__W__, H=__H__, deck=document.querySelector('.deck'), slides=[].slice.call(deck.querySelectorAll(':scope>.slide'));
var at=0, channel=('BroadcastChannel' in window)?new BroadcastChannel('py-doc-deck:'+document.title):null;
function fit(){var k=Math.min(innerWidth/W,innerHeight/H);document.documentElement.style.setProperty('--k',k);
  if(deck.classList.contains('overview')){grid();}}
// The overview: every slide small, four or more to a row, each placed where it goes in the grid
function grid(){var gap=16,cols=Math.max(2,Math.min(6,Math.floor(innerWidth/260))),o=(innerWidth-gap*(cols+1))/cols/W;
  document.documentElement.style.setProperty('--o',o);
  slides.forEach(function(s,i){s.style.left=(gap+(i%cols)*(W*o+gap))+'px';s.style.top=(gap+Math.floor(i/cols)*(H*o+gap))+'px';});}
function overview(on){deck.classList.toggle('overview',on);
  if(on){grid();slides[at].scrollIntoView({block:'center'});}else{slides.forEach(function(s){s.style.left='';s.style.top='';});}}
function show(n,quiet){at=Math.max(0,Math.min(slides.length-1,n));
  slides.forEach(function(s,i){s.classList.toggle('active',i===at);});
  if(location.hash!=='#/'+(at+1)&&!presenting){history.replaceState(null,'','#/'+(at+1));}
  if(channel&&!quiet){channel.postMessage({slide:at});}
  if(presenting){present();}}
function next(){show(at+1);} function prev(){show(at-1);}
function fromHash(){var m=/^#\\/(\\d+)/.exec(location.hash);if(m){show(+m[1]-1,true);}}
// The slides whose content is taller or wider than the slide: marked, and named in the console
var overflow=[];
function check(){overflow=[];slides.forEach(function(s,i){var shown=s.classList.contains('active');s.style.display='flex';
  var b=s.querySelector('.body');var over=b&&(b.scrollHeight>b.clientHeight+2||b.scrollWidth>b.clientWidth+2);
  s.classList.toggle('overflow',!!over);if(over){overflow.push(i+1);}if(!shown){s.style.display='';}});
  window.pyDocOverflow=overflow;
  if(overflow.length){console.warn('py-doc deck: slide(s) '+overflow.join(', ')+' hold more than they can show. Split them, or move detail to the notes.');}}
document.addEventListener('keydown',function(e){if(e.altKey||e.ctrlKey||e.metaKey){return;}
  var k=e.key;
  if(k==='ArrowRight'||k==='ArrowDown'||k==='PageDown'||k===' '||k==='n'){next();}
  else if(k==='ArrowLeft'||k==='ArrowUp'||k==='PageUp'||k==='Backspace'){prev();}
  else if(k==='Home'){show(0);} else if(k==='End'){show(slides.length-1);}
  else if(k==='o'){overview(!deck.classList.contains('overview'));}
  else if(k==='f'){if(document.fullscreenElement){document.exitFullscreen();}else{document.documentElement.requestFullscreen();}}
  else if(k==='p'&&!presenting){window.open(location.pathname+'#presenter/'+(at+1),'py-doc-presenter','width=1200,height=760');}
  else if(k==='Escape'){overview(false);}
  else{return;}
  e.preventDefault();});
deck.addEventListener('click',function(e){if(e.target.closest('a')){return;}
  if(deck.classList.contains('overview')){var s=e.target.closest('.slide');if(s){show(slides.indexOf(s));overview(false);}return;}
  if(!presenting){next();}});
var x0=null;
deck.addEventListener('touchstart',function(e){x0=e.touches[0].clientX;},{passive:true});
deck.addEventListener('touchend',function(e){if(x0===null){return;}var d=e.changedTouches[0].clientX-x0;x0=null;
  if(Math.abs(d)>40){if(d<0){next();}else{prev();}}});
if(channel){channel.onmessage=function(m){if(typeof m.data.slide==='number'&&m.data.slide!==at){show(m.data.slide,true);}};}
// The presenter view: this slide, the next one, the notes and a timer, kept in step with the deck
var presenting=/^#presenter/.test(location.hash), started=Date.now(), view=null;
function present(){
  if(!view){deck.style.display='none';view=document.createElement('div');view.className='presenter';
    view.innerHTML='<div class="now"></div><div class="next"></div><div class="notes-text"></div><div class="bar"><span class="count"></span><span class="clock"></span></div>';
    document.body.appendChild(view);setInterval(tick,1000);}
  function place(box,s){box.innerHTML='';if(!s){return;}var c=s.cloneNode(true);c.classList.add('active');
    var r=box.getBoundingClientRect(),k=Math.min(r.width/W,r.height/H);c.style.setProperty('--k',k);box.appendChild(c);}
  place(view.querySelector('.now'),slides[at]);place(view.querySelector('.next'),slides[at+1]);
  var n=slides[at].querySelector('.notes');
  view.querySelector('.notes-text').innerHTML=n?n.innerHTML:'<em>No notes</em>';
  view.querySelector('.count').textContent='Slide '+(at+1)+' of '+slides.length;tick();}
function tick(){if(!view){return;}var s=Math.floor((Date.now()-started)/1000);
  view.querySelector('.clock').textContent=Math.floor(s/60)+':'+('0'+s%60).slice(-2);}
addEventListener('resize',function(){fit();if(presenting){present();}});
addEventListener('hashchange',fromHash);
fit();
var m=/^#(?:presenter)?\\/(\\d+)/.exec(location.hash);  // the slide the address names, #/12 or #presenter/12
show(m?+m[1]-1:0,true);
function ready(){check();}
if(document.fonts&&document.fonts.ready){document.fonts.ready.then(ready);}else{addEventListener('load',ready);}
})();
"""


@dataclass
class DeckSettings:
    split_level: int = 2
    aspect: str = "16:9"
    theme: str | Path | None = None
    embed_fonts: bool | list = False
    footer: str | None = None
    pdf: bool = False

    @classmethod
    def from_options(cls, options: dict) -> DeckSettings:
        aspect = str(options.get("aspect", "16:9"))
        if aspect not in ASPECTS:
            raise DeckError(f"aspect must be {' or '.join(ASPECTS)}, not '{aspect}'")
        return cls(
            int(options.get("split_level", 2)), aspect, options.get("theme"), options.get("embed_fonts", False),
            options.get("footer"), bool(options.get("pdf", False)),
        )  # fmt: skip


def build_deck(markdown: str, metadata, base: Path, settings: DeckSettings, runtime, mermaid=None, where=""):
    """The page of the deck of ``markdown``, and the poster context it was drawn with (diagrams drawn, failed)."""
    from py_doc import poster
    from py_doc.pandoc.pptx_finish import _footer_text
    from py_doc.poster_blocks import MD, Ctx
    from py_doc.poster_fonts import font_css
    from py_doc.poster_themes import load_theme

    where = where or str(base)
    theme = load_theme(settings.theme, base)
    ctx = Ctx(base, runtime, theme, poster.render, where)
    ctx.mermaid = mermaid
    slides = split_slides(prepare(markdown), settings.split_level)
    title = metadata.title or ""
    if title:  # as pandoc's PowerPoint writer: the title slide, then a section slide for a # heading
        slides.insert(0, Slide("title", title))
    footer = html.escape(_footer_text(settings.footer, metadata)) if settings.footer else ""
    width, height = ASPECTS[settings.aspect]
    parts = []
    for n, slide in enumerate(slides, 1):
        if slide.kind == "content" and line_count(slide) > LINES_PER_SLIDE:
            logger.warning(
                f"{where}: slide {n}{f' ({slide.title})' if slide.title else ''} has {line_count(slide)} lines, more "
                f"than the {LINES_PER_SLIDE} a slide can show well. Split it, or move detail to the notes"
            )
        if slide.kind == "title":
            inner = f"<h1>{html.escape(title)}</h1>"
            if metadata.subtitle:
                inner += f'<div class="subtitle">{html.escape(metadata.subtitle)}</div>'
            byline = " · ".join(str(v) for v in (metadata.author, metadata.date) if v)
            inner += f'<div class="byline">{html.escape(byline)}</div>' if byline else ""
        else:
            heading = f"<h2>{poster.inline(slide.title)}</h2>" if slide.title else ""
            body = poster.render(_divs(slide.body), ctx) if _text(slide.body) else ""
            inner = heading + f'<div class="body">{body}</div>'
        notes = f'<div class="notes">{MD.render(_text(slide.notes))}</div>' if _text(slide.notes) else ""
        foot = (
            f'<div class="foot"><span>{footer}</span><span>{n}</span></div>' if slide.kind != "title" or footer else ""
        )
        parts.append(f'<div class="slide {slide.kind}" data-n="{n}">{inner}{notes}{foot}</div>')
    css = poster.CSS.replace("__VARS__", theme.css_variables()).replace("__PAPER__", "auto")
    css = css.replace("__W__", str(width)).replace("__H__", str(height))
    deck_css = CSS.replace("__W__", str(width)).replace("__H__", str(height))
    script = SCRIPT.replace("__W__", str(width)).replace("__H__", str(height))
    faces, link = font_css(theme, settings.embed_fonts, where)
    fonts = theme.fonts.get("stylesheet") if link else None
    ctx.stylesheet = fonts
    page = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title or 'Deck')}</title>\n"
        + (f'<link rel="stylesheet" href="{html.escape(fonts)}">\n' if fonts else "")
        + f"<style>{faces}{css}{deck_css}</style>\n</head>\n<body>\n"
        + f'<main class="deck" data-slides="{len(parts)}">\n'
        + "\n".join(parts)
        + f"\n</main>\n<script>{script}</script>\n</body>\n</html>\n"
    )
    return page, ctx, len(parts)


def write_deck(joined, metadata, output: Path, base: Path, options: dict, runtime, mermaid=None, name="") -> Path:
    """Write the HTML deck of ``joined`` to ``output``, and its PDF beside it when ``options`` ask for one."""
    from py_doc.poster import with_web_fonts

    settings = DeckSettings.from_options(options)
    page, ctx, count = build_deck(joined.markdown, metadata, base, settings, runtime, mermaid, name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    logger.info(
        f"{name or output.name}: {count} slides" + (f", {ctx.failed} diagram(s) not drawn" if ctx.failed else "")
    )
    if settings.pdf:
        pdf = output.with_suffix(".pdf")
        overflow = print_pdf(ctx.runtime(), with_web_fonts(page, ctx), pdf)
        if overflow:
            logger.warning(
                f"{name or output.name}: slide(s) {', '.join(map(str, overflow))} hold more than they can show. "
                "Split them, or move detail to the notes"
            )
        logger.info(f"Wrote {pdf}")
    return output


def print_pdf(runtime, page: str, pdf: Path) -> list[int]:
    """Print the deck ``page`` to ``pdf``, one slide a page, with the tool container's Chromium. Returns the
    numbers of the slides whose content overflows them, as the page found them."""
    with tempfile.TemporaryDirectory(prefix="py-doc-deck-") as folder:
        work = Path(folder)
        source, output = work / "deck.html", work / "deck.pdf"
        source.write_text(page, encoding="utf-8")
        result = runtime.run(
            ["node", TOOLS / "deck_pdf.js", source, output, PUPPETEER],
            mounts=[Mount(work, writable=True), Mount(TOOLS)], workdir=work,
            env={"NODE_PATH": "/opt/node/node_modules"}, timeout=PDF_TIMEOUT,
        )  # fmt: skip
        if not output.is_file() or not output.read_bytes().startswith(b"%PDF"):
            raise DeckError(f"Chromium wrote no PDF for {pdf}")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output, pdf)
    found = re.search(r"^PYDOC-OVERFLOW (\[.*\])$", getattr(result, "stdout", "") or "", re.M)
    return json.loads(found[1]) if found else []
