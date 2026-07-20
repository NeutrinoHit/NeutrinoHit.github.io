local stringify = pandoc.utils.stringify

local function has_class(element, class)
  for _, value in ipairs(element.classes or {}) do
    if value == class then
      return true
    end
  end
  return false
end

local function inlines_to_latex(inlines)
  local doc = pandoc.Pandoc({ pandoc.Plain(inlines) })
  return pandoc.write(doc, "latex"):gsub("%s+$", "")
end

local function is_html_raw(block, pattern)
  return block
    and block.t == "RawBlock"
    and block.format == "html"
    and block.text:match(pattern)
end

local function project_meta(summary)
  local meta = {
    number = "",
    title = "",
    author = "",
  }

  if not summary or not summary.content then
    return meta
  end

  for _, inline in ipairs(summary.content) do
    if inline.t == "Span" and has_class(inline, "baikal-project-number") then
      meta.number = inlines_to_latex(inline.content)
    elseif inline.t == "Span" and has_class(inline, "baikal-project-title") then
      meta.title = inlines_to_latex(inline.content)
    elseif inline.t == "Span" and has_class(inline, "baikal-project-author") then
      meta.author = inlines_to_latex(inline.content)
    end
  end

  return meta
end

local function is_strong_only_para(block)
  return block
    and block.t == "Para"
    and #block.content == 1
    and block.content[1].t == "Strong"
end

function Para(block)
  if FORMAT ~= "latex" or not is_strong_only_para(block) then
    return nil
  end

  local heading = stringify(block.content[1])
  if heading == "" then
    return nil
  end

  return pandoc.RawBlock("latex", "\\pdfsubheading{" .. inlines_to_latex(block.content[1].content) .. "}")
end

function Div(div)
  if FORMAT ~= "latex" or not has_class(div, "baikal-project-accordion") then
    return nil
  end

  local blocks = pandoc.List()
  local i = 1

  while i <= #div.content do
    if is_html_raw(div.content[i], "<details") then
      local summary = div.content[i + 2]
      local content = div.content[i + 4]
      local meta = project_meta(summary)
      local toc_title = meta.number .. ": " .. meta.title

      blocks:insert(pandoc.RawBlock("latex", "\\phantomsection\\addcontentsline{toc}{section}{" .. toc_title .. "}"))
      blocks:insert(pandoc.RawBlock("latex", "\\begin{projectbox}{" .. meta.number .. "}{" .. meta.title .. "}{" .. meta.author .. "}"))

      if content and content.t == "Div" and has_class(content, "baikal-project-content") then
        blocks:extend(content.content)
      end

      blocks:insert(pandoc.RawBlock("latex", "\\end{projectbox}"))
      i = i + 6
    else
      i = i + 1
    end
  end

  return blocks
end
