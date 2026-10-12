-- center-div.lua
-- markdown_processing.py wraps diagram images in a fenced Div with a CSS
-- style="text-align:center;" attribute. CSS styles are meaningless to
-- Pandoc's LaTeX (and DOCX) writers -- they are silently dropped, and the
-- image renders left-aligned, not promoted into a centred figure.
--
-- For LaTeX output, this filter detects that style attribute and wraps the
-- Div's content in a real \begin{center}...\end{center} block instead.

function Div(el)
  local style = (el.attributes and el.attributes.style) or ""
  if FORMAT:match('latex') and style:match("text%-align%s*:%s*center") then
    local result = { pandoc.RawBlock('latex', '\\begin{center}') }
    for _, b in ipairs(el.content) do table.insert(result, b) end
    table.insert(result, pandoc.RawBlock('latex', '\\end{center}'))
    return result
  end
end
