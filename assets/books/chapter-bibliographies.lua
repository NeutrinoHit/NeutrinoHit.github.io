-- Run citeproc independently for every published chapter.
--
-- A Quarto PDF or EPUB book is one Pandoc document. With the default citeproc
-- pass, every #refs Div therefore receives the bibliography of the whole book.
-- Splitting the document at each chapter's #refs Div gives every chapter its
-- own numbered citations and its own list of sources. HTML chapters go through
-- the same code, so all output formats follow one rule.

local function append_blocks(target, blocks)
  for _, block in ipairs(blocks) do
    target:insert(block)
  end
end

local crossref_prefixes = {
  "eq-",
  "fig-",
  "lst-",
  "sec-",
  "tbl-",
}

local function is_crossref_id(identifier)
  for _, prefix in ipairs(crossref_prefixes) do
    if identifier:sub(1, #prefix) == prefix then
      return true
    end
  end
  return false
end

-- Quarto resolves @fig-..., @eq-... and related references after user Lua
-- filters. pandoc.utils.citeproc would otherwise treat them as missing
-- bibliography entries. Hide pure cross-reference Cite nodes for the duration
-- of citeproc, then restore the original nodes for Quarto's crossref pass.
local function protect_crossrefs(blocks)
  local protected = {}
  local fragment = pandoc.Pandoc(blocks):walk({
    Cite = function(cite)
      local only_crossrefs = #cite.citations > 0
      for _, citation in ipairs(cite.citations) do
        if not is_crossref_id(citation.id) then
          only_crossrefs = false
          break
        end
      end

      if not only_crossrefs then
        return nil
      end

      protected[#protected + 1] = cite
      return pandoc.Span(
        {},
        pandoc.Attr(
          "",
          {"nh-protected-crossref"},
          {{"data-index", tostring(#protected)}}
        )
      )
    end,
  })
  return fragment.blocks, protected
end

local function restore_crossrefs(blocks, protected)
  local fragment = pandoc.Pandoc(blocks):walk({
    Span = function(span)
      if span.classes:includes("nh-protected-crossref") then
        local index = tonumber(span.attributes["data-index"])
        return protected[index]
      end
      return nil
    end,
  })
  return fragment.blocks
end

local function citation_count(blocks)
  local count = 0
  pandoc.Pandoc(blocks):walk({
    Cite = function()
      count = count + 1
    end,
  })
  return count
end

local function process_segment(blocks, metadata)
  local protected_blocks, protected = protect_crossrefs(blocks)
  if citation_count(protected_blocks) == 0 then
    return restore_crossrefs(protected_blocks, protected)
  end

  local fragment = pandoc.Pandoc(protected_blocks, metadata)
  local cited_blocks = pandoc.utils.citeproc(fragment).blocks
  return restore_crossrefs(cited_blocks, protected)
end

function Pandoc(document)
  local output = pandoc.Blocks({})
  local segment = pandoc.Blocks({})

  for _, block in ipairs(document.blocks) do
    segment:insert(block)
    if block.t == "Div" and block.identifier == "refs" then
      append_blocks(output, process_segment(segment, document.meta))
      segment = pandoc.Blocks({})
    end
  end

  if #segment > 0 then
    append_blocks(output, process_segment(segment, document.meta))
  end

  document.blocks = output
  return document
end
