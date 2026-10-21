-- pagebreak.lua
-- ::: {.pagebreak}
-- :::
-- becomes a page break in Word, LaTeX and print styles of HTML, and a new slide in PowerPoint.

function Div(el)
  if not el.classes:includes("pagebreak") then return nil end
  if FORMAT:match("latex") then
    return pandoc.RawBlock("latex", "\\newpage")
  elseif FORMAT:match("html") then
    return pandoc.RawBlock("html", '<div class="pagebreak" style="break-after: page"></div>')
  elseif FORMAT:match("docx") then
    return pandoc.RawBlock("openxml", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
  elseif FORMAT:match("pptx") then
    return pandoc.HorizontalRule()
  end
  return {}
end
