-- site.lua (Markdown pages for MkDocs or Astro + Starlight)
-- Runs after admonitions.lua, pagebreak.lua and markers.lua. The metadata value `site-engine` is mkdocs or starlight.
--   A callout box becomes an admonition (MkDocs: !!! note) or an aside (Starlight: :::note).
--   The centring div around a diagram is taken away: the site's stylesheet places pictures.
--   Starlight prints the page title itself, so the first level 1 heading is dropped there.

local engine = "mkdocs"
local ASIDES = { note = "note", tip = "tip", important = "note", warning = "caution", caution = "danger" }

local function markdown_of(blocks)
  return pandoc.write(pandoc.Pandoc(blocks), FORMAT)
end

local function callout(div)
  local kind
  for _, class in ipairs(div.classes) do
    if class ~= "admonition" then kind = class end
  end
  local blocks = pandoc.List(div.content)
  if #blocks > 0 and blocks[1].t == "Para" and #blocks[1].content == 1 and blocks[1].content[1].t == "Strong" then
    blocks:remove(1)  -- the NOTE label admonitions.lua puts first: the site draws its own
  end
  local body = markdown_of(blocks):gsub("%s+$", "")
  if engine == "starlight" then
    return pandoc.RawBlock("markdown", ":::" .. ASIDES[kind] .. "\n" .. body .. "\n:::")
  end
  local indented = body:gsub("\n", "\n    "):gsub("\n    \n", "\n\n")
  return pandoc.RawBlock("markdown", "!!! " .. kind .. "\n\n    " .. indented)
end

function Meta(meta)
  if meta["site-engine"] then engine = pandoc.utils.stringify(meta["site-engine"]) end
end

function Div(div)
  if div.classes:includes("admonition") then return callout(div) end
  if div.attributes.style == "text-align:center;" then return div.content end
  return nil
end

-- A figure becomes the picture and, when one was written, its caption in italics under it. Raw <figure> HTML
-- would hide the picture from MkDocs and Astro, which find pictures in Markdown and copy them with the page.
-- A picture alone in a paragraph is a figure captioned with its alt text: that is no caption.
function Figure(figure)
  local images = {}
  figure:walk({ Image = function(image) table.insert(images, image) end })
  if #images ~= 1 then return nil end
  local caption = pandoc.utils.stringify(figure.caption.long)
  local out = { pandoc.Para({ images[1] }) }
  if caption ~= "" and caption ~= pandoc.utils.stringify(images[1].caption) then
    table.insert(out, pandoc.Para({ pandoc.Emph(pandoc.utils.blocks_to_inlines(figure.caption.long)) }))
  end
  return out
end

-- Markdown tables have no caption, so it follows the table in italics.
function Table(table)
  local caption = pandoc.utils.stringify(table.caption.long)
  if caption == "" then return nil end
  local inlines = pandoc.utils.blocks_to_inlines(table.caption.long)
  table.caption.long = {}
  return { table, pandoc.Para({ pandoc.Emph(inlines) }) }
end

-- Maths in the dollar form both sites read (MkDocs arithmatex, Starlight remark-math), written here so the
-- page needs no maths extension of the Markdown writer, which older pandoc versions do not have.
function Math(math)
  local mark = math.mathtype == "DisplayMath" and "$$" or "$"
  return pandoc.RawInline("markdown", mark .. math.text .. mark)
end

function Pandoc(doc)
  if engine == "starlight" and #doc.blocks > 0 and doc.blocks[1].t == "Header" and doc.blocks[1].level == 1 then
    doc.blocks:remove(1)
  end
  return doc
end

return { { Meta = Meta }, { Div = Div, Figure = Figure, Table = Table, Math = Math }, { Pandoc = Pandoc } }
