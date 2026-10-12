-- markers.lua (PDF, HTML and PowerPoint)
-- Word handles these markers itself (see docx_post.py). In the other formats they would print as text, so:
--   [[CAPTION:Table]] Text   next to a table (before or after it) becomes that table's caption.
--   [[CAPTION:Figure]] Text  becomes the caption of the picture or code block that follows, or of the one before.
--                            A picture on the same paragraph gets it too.
--   [[STYLE:Name]] Text      keeps the text. A Word style means nothing here.
--   [[LANDSCAPE]], [[PORTRAIT]]  are dropped. Picture widths were already chosen from them.

-- The marker at the start of a paragraph: returns the label and the inlines after it, or nil.
local function leading(para, pattern)
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
  if not last then return nil end
  local label = text:match(pattern)
  if not label then return nil end
  local rest = pandoc.List()
  for i = last + 1, #para.content do rest:insert(para.content[i]) end
  while #rest > 0 and (rest[1].t == "Space" or rest[1].t == "SoftBreak") do rest:remove(1) end
  return label, rest
end

local CAPTION = "^%[%[CAPTION:([%w _%-]+)%]%]$"
local STYLE = "^%[%[STYLE:([^%]]+)%]%]$"
local ORIENTATION = "^%[%[(%u+)%]%]$"

local function caption_of(inlines)
  return { pandoc.Plain(inlines) }
end

function Blocks(blocks)
  local out = pandoc.List()
  local captioned = 0  -- the position in `out` of the block a marker captioned last
  local i = 1
  while i <= #blocks do
    local block = blocks[i]
    local handled = false
    if block.t == "Para" then
      local orientation = leading(block, ORIENTATION)
      local label, rest = leading(block, CAPTION)
      local style, styled = leading(block, STYLE)
      if (orientation == "LANDSCAPE" or orientation == "PORTRAIT") and #block.content == 1 then
        handled = true  -- dropped
        i = i + 1
      elseif label then
        handled = true
        local nxt, prev = blocks[i + 1], out[#out]
        local image_at
        for k, inline in ipairs(rest) do
          if inline.t == "Image" then image_at = k break end
        end
        -- a diagram is a picture inside a centred Div
        local inner = nxt and nxt.t == "Div" and #nxt.content == 1 and nxt.content[1] or nil
        if inner and (inner.t == "Table" or inner.t == "Figure") then
          inner.caption.long = caption_of(rest)
          nxt.content[1] = inner
          out:insert(nxt)
          captioned = #out
          i = i + 2
        elseif nxt and (nxt.t == "Table" or nxt.t == "Figure") then
          nxt.caption.long = caption_of(rest)
          out:insert(nxt)
          captioned = #out
          i = i + 2
        elseif nxt and nxt.t == "CodeBlock" then
          out:insert(pandoc.Figure(nxt, { caption_of(rest)[1] }))
          captioned = #out
          i = i + 2
        elseif prev and (prev.t == "Table" or prev.t == "Figure") and not image_at and captioned ~= #out then
          prev.caption.long = caption_of(rest)
          captioned = #out
          i = i + 1
        elseif image_at then
          local text = pandoc.List()
          for k = 1, image_at - 1 do text:insert(rest[k]) end
          while #text > 0 and (text[#text].t == "SoftBreak" or text[#text].t == "Space") do text:remove() end
          out:insert(pandoc.Figure(pandoc.Plain({ rest[image_at] }), caption_of(text)))
          captioned = #out
          i = i + 1
        else
          out:insert(pandoc.Para(rest))  -- nothing beside it to caption: keep the words, drop the marker
          i = i + 1
        end
      elseif style then
        handled = true
        out:insert(pandoc.Para(styled))
        i = i + 1
      end
    end
    if not handled then
      out:insert(block)
      i = i + 1
    end
  end
  return out
end
