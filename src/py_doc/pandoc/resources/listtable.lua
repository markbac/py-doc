-- [[LISTTABLE]] tables, which py-doc writes as a grid table in a Div of class "listtable".
--
-- A cell paragraph §N becomes the blocks of the Nth key in the Div's "blocks" attribute: a [[BLOCK:]]
-- that py-doc wrote as a Div of class "listtable-block" elsewhere in the document, and which is taken out
-- of the place it was written. A picture or diagram in a cell is not a figure: it has no caption or number
-- of its own. A block may hold another [[LISTTABLE]], which is placed the same way.
--
-- The Div's "cells" attribute gives the colour and vertical alignment of some cells, as
-- "row.index:bg=RRGGBB,valign=middle", where index counts the cells pandoc has in that row. HTML gets
-- them as a style, PDF the colour as \cellcolor, and Word a hidden bookmark in the cell that py-doc's Word
-- finishing turns into the cell's shading and alignment. The table then leaves its Div. In Word a hidden
-- bookmark before it also tells the finishing that it is a rich table (its rows may break across pages).
-- In PDF a table inside a cell is written as a tabular, as LaTeX cannot nest the longtables pandoc writes.

local blocks = {}
local VALIGN = { top = "top", middle = "center", bottom = "bottom" }

local function collect(div)
  if div.classes:includes("listtable-block") then
    blocks[div.attributes.key] = div.content
    return {}
  end
end

local function bookmark(name)
  return pandoc.RawBlock("openxml", '<w:bookmarkStart w:id="0" w:name="' .. name .. '"/><w:bookmarkEnd w:id="0"/>')
end

local function style_cell(cell, spec)
  local bg = spec:match("bg=(%x+)")
  local valign = spec:match("valign=(%a+)")
  if FORMAT:match("html") or FORMAT == "gfm" or FORMAT == "markdown" then
    local css = {}
    if bg then css[#css + 1] = "background-color: #" .. bg end
    if valign then css[#css + 1] = "vertical-align: " .. valign end
    cell.attributes.style = table.concat(css, "; ")
  elseif FORMAT == "docx" then
    cell.contents:insert(1, bookmark("_PyDocCell_" .. (bg or "none") .. "_" .. (VALIGN[valign] or "none")))
  elseif FORMAT == "latex" and bg then
    local colour = pandoc.RawInline("latex", "\\cellcolor[HTML]{" .. bg .. "}")
    local first = cell.contents[1]
    if first and (first.t == "Plain" or first.t == "Para") then
      first.content:insert(1, colour)
    else
      cell.contents:insert(1, pandoc.Plain({ colour }))
    end
  end
end

local function rows_of(tbl)
  local rows = pandoc.List()
  rows:extend(tbl.head.rows)
  for _, body in ipairs(tbl.bodies) do
    rows:extend(body.body)
  end
  return rows
end

-- LaTeX cannot put a longtable, which pandoc writes for every table, inside another one. A table in a
-- cell becomes a tabular instead: the same columns and rules, without page breaks.
local function as_tabular(tbl)
  local latex = pandoc.write(pandoc.Pandoc({ tbl }), "latex")
  local head, foot, body = latex:match("^(.*)\\endhead\n(.-)\\endlastfoot\n(.*)$")
  if head then  -- a longtable gives its foot before its body: a tabular wants it last
    local last = body:find("\\end{longtable}", 1, true)
    latex = head .. body:sub(1, last - 1) .. foot .. body:sub(last)
  end
  latex = latex:gsub("\\begin{longtable}%[%]", "\\begin{tabular}"):gsub("\\end{longtable}", "\\end{tabular}")
  return pandoc.RawBlock("latex", latex)
end

local function nested_as_tabular(tbl)
  for _, row in ipairs(rows_of(tbl)) do
    for _, cell in ipairs(row.cells) do
      cell.contents = pandoc.Blocks(cell.contents):walk({ Table = as_tabular })
    end
  end
  return tbl
end

local function style_cells(tbl, specs)
  local wanted = {}
  for row, index, spec in specs:gmatch("(%d+)%.(%d+):(%S+)") do
    wanted[row .. "." .. index] = spec
  end
  for r, row in ipairs(rows_of(tbl)) do
    for i, cell in ipairs(row.cells) do
      local spec = wanted[(r - 1) .. "." .. (i - 1)]
      if spec then style_cell(cell, spec) end
    end
  end
  return tbl
end

local place

local function fill(list, keys)
  local out = pandoc.List()
  for _, block in ipairs(list) do
    local slot = (block.t == "Plain" or block.t == "Para") and #block.content == 1
      and block.content[1].t == "Str" and block.content[1].text:match("^§(%d+)$")
    local found = slot and blocks[keys[tonumber(slot)]]
    if found then
      out:extend(pandoc.Blocks(found):walk({ Div = place, Figure = function(figure) return figure.content end }))
    else
      out:insert(block)
    end
  end
  return out
end

place = function(div)
  if not div.classes:includes("listtable") then
    return nil
  end
  local keys = {}
  for key in (div.attributes.blocks or ""):gmatch("%S+") do
    keys[#keys + 1] = key
  end
  local filled = div:walk({ Blocks = function(list) return fill(list, keys) end })
  if div.attributes.cells then
    filled = filled:walk({ Table = function(tbl) return style_cells(tbl, div.attributes.cells) end })
  end
  if FORMAT == "latex" then
    filled = filled:walk({ Table = nested_as_tabular })
  end
  local out = pandoc.List()
  if FORMAT == "docx" then
    out:insert(bookmark("_PyDocRichTable"))
  end
  out:extend(filled.content)
  return out
end

return { { Div = collect }, { Div = place } }
