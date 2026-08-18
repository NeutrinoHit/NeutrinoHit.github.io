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

local function blocks_to_latex(blocks)
  local doc = pandoc.Pandoc(blocks)
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

local function is_static_pdf_link(block)
  if not block or block.t ~= "Para" or #block.content ~= 1 then
    return false
  end

  local inline = block.content[1]
  return inline.t == "Link"
    and inline.target:match("baikal%-school%-2026%-projects%.pdf$") ~= nil
end

local function is_image_only_para(block)
  return block
    and block.t == "Para"
    and #block.content == 1
    and block.content[1].t == "Image"
end

function Para(block)
  if FORMAT ~= "latex" then
    return nil
  end

  if is_static_pdf_link(block) then
    return pandoc.List()
  end

  if is_image_only_para(block) then
    local image = block.content[1]
    local image_latex = inlines_to_latex({ image })
    local caption = inlines_to_latex(image.caption)
    local caption_latex = ""

    if caption ~= "" then
      caption_latex = "\\par\\smallskip{\\small\\color{NHMuted}\\textit{" .. caption .. "}}\\par"
    end

    return pandoc.RawBlock(
      "latex",
      "\\begin{center}\n" .. image_latex .. "\n" .. caption_latex .. "\n\\end{center}"
    )
  end

  if not is_strong_only_para(block) then
    return nil
  end

  local heading = stringify(block.content[1])
  if heading == "" then
    return nil
  end

  return pandoc.RawBlock("latex", "\\pdfsubheading{" .. inlines_to_latex(block.content[1].content) .. "}")
end

function Figure(figure)
  if FORMAT ~= "latex" then
    return nil
  end

  local blocks = pandoc.List()
  blocks:insert(pandoc.RawBlock("latex", "\\begin{center}"))
  blocks:extend(figure.content)

  local caption = blocks_to_latex(figure.caption.long)
  if caption ~= "" then
    blocks:insert(pandoc.RawBlock(
      "latex",
      "\\par\\smallskip{\\small\\color{NHMuted}\\textit{" .. caption .. "}}\\par"
    ))
  end

  blocks:insert(pandoc.RawBlock("latex", "\\end{center}"))
  return blocks
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
