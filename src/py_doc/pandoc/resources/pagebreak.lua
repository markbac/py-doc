-- pagebreak.lua
-- ::: {.pagebreak}
-- :::
-- becomes a page break in Word, LaTeX and print styles of HTML. Slides have no use for it.

function Div(el)
  if not el.classes:includes("pagebreak") then return nil end
  if FORMAT:match("latex") then
    return pandoc.RawBlock("latex", "\\newpage")
  elseif FORMAT:match("html") then
    return pandoc.RawBlock("html", '<div style="break-after: page"></div>')
  elseif FORMAT:match("docx") then
    return pandoc.RawBlock("openxml", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
  end
  return {}
end
