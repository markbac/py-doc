-- admonitions.lua
-- Turns callouts into one styled box per callout. Two spellings are accepted:
--   > [!NOTE]            (GitHub)      kinds: NOTE TIP IMPORTANT WARNING CAUTION
--   > **Note:** text     (bold label)  also **Note**: and any capitalisation
-- A block quote that starts with neither is left as an ordinary quote.
-- Word and HTML get a Div (custom-style "Div.note" and classes "admonition note"), LaTeX gets a
-- tcolorbox environment from latex_template.tex.

local KINDS = { NOTE = true, TIP = true, IMPORTANT = true, WARNING = true, CAUTION = true }

local LATEX_ENV = {
  note = "notebox", tip = "tipbox", important = "importantbox",
  warning = "warningbox", caution = "cautionbox",
}

local function inlines_of(block)
  if block.t == "Para" or block.t == "Plain" then return block.content end
  return nil
end

local function drop_leading_space(inlines, from)
  local out = {}
  local skipping = true
  for i = from, #inlines do
    local inline = inlines[i]
    if skipping and (inline.t == "Space" or inline.t == "SoftBreak") then
      -- the gap after the label
    else
      skipping = false
      table.insert(out, inline)
    end
  end
  return out
end

-- Returns the kind and the remaining inlines when a paragraph starts with a callout label.
local function label_of(inlines)
  local first = inlines[1]
  if not first then return nil end
  -- [!NOTE]: pandoc keeps this as the string "[!NOTE]" possibly followed by text
  if first.t == "Str" then
    local kind = first.text:match("^%[!(%u+)%]$")
    if kind and KINDS[kind] then return kind, drop_leading_space(inlines, 2) end
  end
  -- **Note:** or **Note**:
  if first.t == "Strong" then
    local text = pandoc.utils.stringify(first):gsub(":%s*$", ""):upper()
    if KINDS[text] then
      local colon_inside = pandoc.utils.stringify(first):match(":%s*$") ~= nil
      local from = 2
      if not colon_inside and inlines[2] and inlines[2].t == "Str" and inlines[2].text:match("^:") then
        local rest = inlines[2].text:gsub("^:", "")
        local out = {}
        if rest ~= "" then table.insert(out, pandoc.Str(rest)) end
        for i = 3, #inlines do table.insert(out, inlines[i]) end
        return text, drop_leading_space(out, 1)
      end
      return text, drop_leading_space(inlines, from)
    end
  end
  return nil
end

local function flatten(quote)
  local flat = {}
  for _, block in ipairs(quote.content) do
    if block.t == "BlockQuote" then
      for _, inner in ipairs(flatten(block)) do table.insert(flat, inner) end
    else
      table.insert(flat, block)
    end
  end
  return flat
end

local function make(kind, blocks)
  local lower = kind:lower()
  if FORMAT:match("latex") then
    local result = { pandoc.RawBlock("latex", "\\begin{" .. LATEX_ENV[lower] .. "}") }
    for _, b in ipairs(blocks) do table.insert(result, b) end
    table.insert(result, pandoc.RawBlock("latex", "\\end{" .. LATEX_ENV[lower] .. "}"))
    return result
  end
  local content = { pandoc.Para({ pandoc.Strong({ pandoc.Str(kind) }) }) }
  for _, b in ipairs(blocks) do table.insert(content, b) end
  return pandoc.Div(content, pandoc.Attr("", { "admonition", lower }, { ["custom-style"] = "Div." .. lower }))
end

function BlockQuote(quote)
  local groups, current = {}, nil
  for _, block in ipairs(flatten(quote)) do
    local inlines = inlines_of(block)
    local kind, rest
    if inlines then kind, rest = label_of(inlines) end
    if kind then
      current = { kind = kind, blocks = {} }
      if #rest > 0 then table.insert(current.blocks, pandoc.Para(rest)) end
      table.insert(groups, current)
    elseif current then
      table.insert(current.blocks, block)
    else
      return nil
    end
  end
  if #groups == 0 then return nil end
  local result = {}
  for _, g in ipairs(groups) do
    local made = make(g.kind, g.blocks)
    if made.t then table.insert(result, made) else for _, b in ipairs(made) do table.insert(result, b) end end
  end
  if #result == 1 then return result[1] end
  return result
end

local function is_admonition(block)
  return block.t == "Div" and block.classes:includes("admonition")
end

-- Word merges two boxes with nothing between them, so a zero-width paragraph keeps them apart.
function Pandoc(doc)
  if FORMAT:match("latex") or FORMAT:match("html") or FORMAT:match("markdown") or FORMAT:match("gfm") then return nil end
  local out = {}
  for i, block in ipairs(doc.blocks) do
    table.insert(out, block)
    local following = doc.blocks[i + 1]
    if following and is_admonition(block) and is_admonition(following) then
      table.insert(out, pandoc.Para({ pandoc.Str("\u{200B}") }))
    end
  end
  return pandoc.Pandoc(out, doc.meta)
end
