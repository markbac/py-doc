-- slides-preview.lua
-- The HTML twin of a deck (py-doc slides --watch): each slide's content goes in a <div class="slide">,
-- starting at each heading up to the slide level and at each page break, as pandoc's PowerPoint writer
-- splits them. A heading above the slide level makes a part divider ("part": pandoc keeps no class named "section"). Runs after pagebreak.lua.

local function is_pagebreak(block)
  return block.t == "RawBlock" and block.format == "html" and block.text:find('class="pagebreak"', 1, true) ~= nil
end

function Pandoc(doc)
  local level = tonumber(pandoc.utils.stringify(doc.meta["preview-slide-level"] or "2")) or 2
  local out = pandoc.Blocks({})
  local current, kind = nil, nil

  local function flush()
    if current ~= nil and #current > 0 then
      out:insert(pandoc.Div(current, pandoc.Attr("", { "slide", kind })))
    end
    current, kind = nil, nil
  end

  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" and block.level <= level then
      flush()
      current, kind = pandoc.Blocks({ block }), (block.level < level) and "part" or "content"
    elseif is_pagebreak(block) then
      flush()
      current, kind = pandoc.Blocks({}), "content"
    else
      if current == nil then
        current, kind = pandoc.Blocks({}), "content"
      end
      current:insert(block)
    end
  end
  flush()
  doc.blocks = out
  return doc
end
