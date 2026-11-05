-- [[LISTTABLE]] tables, which py-doc writes as a grid table in a Div of class "listtable".
--
-- A cell paragraph §N becomes the blocks of the Nth key in the Div's "blocks" attribute: a [[BLOCK:]]
-- that py-doc wrote as a Div of class "listtable-block" elsewhere in the document, and which is taken out
-- of the place it was written. A picture or diagram in a cell is not a figure: it has no caption or number
-- of its own. The table then leaves its Div. In Word a hidden bookmark goes before it,
-- so the Word finishing knows a rich table (its rows may break across pages) from an ordinary one.

local blocks = {}

local function collect(div)
  if div.classes:includes("listtable-block") then
    blocks[div.attributes.key] = div.content
    return {}
  end
end

local function place(div)
  if not div.classes:includes("listtable") then
    return nil
  end
  local keys = {}
  for key in (div.attributes.blocks or ""):gmatch("%S+") do
    keys[#keys + 1] = key
  end
  local filled = div:walk({
    Blocks = function(list)
      local out = pandoc.List()
      for _, block in ipairs(list) do
        local slot = (block.t == "Plain" or block.t == "Para") and #block.content == 1
          and block.content[1].t == "Str" and block.content[1].text:match("^§(%d+)$")
        local found = slot and blocks[keys[tonumber(slot)]]
        if found then
          out:extend(pandoc.Blocks(found):walk({ Figure = function(figure) return figure.content end }))
        else
          out:insert(block)
        end
      end
      return out
    end,
  })
  local out = pandoc.List()
  if FORMAT == "docx" then
    out:insert(pandoc.RawBlock("openxml", '<w:bookmarkStart w:id="0" w:name="_PyDocRichTable"/><w:bookmarkEnd w:id="0"/>'))
  end
  out:extend(filled.content)
  return out
end

return { { Div = collect }, { Div = place } }
