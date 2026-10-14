-- widths.lua (Word)
-- pandoc's Word writer ignores a picture size in %, so {width=50%} becomes that share of the text width
-- in cm. py-doc puts the text width of the template (page width less the margins) in text-width-cm.

local text_width

local function percent(value)
  return value and tonumber(value:match("^%s*([%d.]+)%%%s*$"))
end

return {
  { Meta = function(meta) text_width = tonumber(pandoc.utils.stringify(meta["text-width-cm"] or "")) end },
  {
    Image = function(image)
      local share = percent(image.attributes.width)
      if not (text_width and share) then return nil end
      image.attributes.width = string.format("%.2fcm", share / 100 * text_width)
      if percent(image.attributes.height) then image.attributes.height = nil end  -- keep the proportions
      return image
    end,
  },
}
