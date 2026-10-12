-- captions.lua (PDF and HTML)
-- [[CAPTION:Table]] Text   next to a table (before or after it) becomes that table's caption.
-- [[CAPTION:Figure]] Text  in a paragraph with a picture becomes a figure with that caption.
-- Word keeps the marker and numbers it with a SEQ field instead (see docx_post.py).

local function split(para)
  -- The marker is the first inlines of the paragraph, up to the closing ]]
  local text, last = "", nil
  for i, inline in ipairs(para.content) do
    if inline.t == "Str" then
      text = text .. inline.text
    elseif inline.t == "Space" then
      text = text .. " "
    else
      return nil
    end
    if text:find("%]%]") then last = i break end
  end
  if not last or not text:match("^%[%[CAPTION:[%w _%-]+%]%]$") then return nil end
  local rest = pandoc.List()
  for i = last + 1, #para.content do rest:insert(para.content[i]) end
  while #rest > 0 and (rest[1].t == "Space" or rest[1].t == "SoftBreak") do rest:remove(1) end
  return rest
end

local function is_caption(block)
  return block.t == "Para" and split(block) ~= nil
end

function Blocks(blocks)
  local out = pandoc.List()
  local i = 1
  while i <= #blocks do
    local block = blocks[i]
    local rest = block.t == "Para" and split(block) or nil
    if rest then
      local nxt, prev = blocks[i + 1], out[#out]
      local image_at
      for k, inline in ipairs(rest) do
        if inline.t == "Image" then image_at = k break end
      end
      if nxt and nxt.t == "Table" then
        nxt.caption.long = { pandoc.Plain(rest) }
        out:insert(nxt)
        i = i + 2
      elseif prev and prev.t == "Table" and #prev.caption.long == 0 then
        prev.caption.long = { pandoc.Plain(rest) }
        i = i + 1
      elseif image_at then
        local text = pandoc.List()
        for k = 1, image_at - 1 do text:insert(rest[k]) end
        while #text > 0 and (text[#text].t == "SoftBreak" or text[#text].t == "Space") do text:remove() end
        local image = rest[image_at]
        out:insert(pandoc.Figure(pandoc.Plain({ image }), { pandoc.Plain(text) }))
        i = i + 1
      else
        out:insert(pandoc.Para(rest))  -- no table or picture beside it: keep the words, drop the marker
        i = i + 1
      end
    else
      out:insert(block)
      i = i + 1
    end
  end
  return out
end
