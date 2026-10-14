-- Remove the level-1 heading of the book home page where it repeats the title.
--
-- In a combined PDF or EPUB book the title page already shows the book title,
-- so the "# <book title>" heading of index.qmd would print it a second time.
--
-- The title is read from metadata, in this order:
--   hide-book-index-title: "<text>"   explicit override
--   book.title                         Quarto book title
--   title
--
-- Formats where the heading is removed:
--   hide-book-index: combined   PDF/LaTeX and EPUB only (default)
--   hide-book-index: all        every format, including HTML
--   hide-book-index: false      never (the filter does nothing)

local book_title = nil
local mode = "combined"

local function read_meta(meta)
  local explicit = meta["hide-book-index-title"]
  if explicit then
    book_title = pandoc.utils.stringify(explicit)
  elseif meta.book and meta.book.title then
    book_title = pandoc.utils.stringify(meta.book.title)
  elseif meta.title then
    book_title = pandoc.utils.stringify(meta.title)
  end

  local option = meta["hide-book-index"]
  if option ~= nil then
    if type(option) == "boolean" then
      mode = option and "combined" or "none"
    else
      mode = pandoc.utils.stringify(option)
    end
  end
end

local function applies_to_format()
  if mode == "all" then
    return true
  end
  if mode == "combined" then
    return FORMAT:match("latex") ~= nil or FORMAT:match("epub") ~= nil
  end
  return false
end

local function hide_header(header)
  if header.level ~= 1 or not book_title or not applies_to_format() then
    return nil
  end
  if pandoc.utils.stringify(header.content) == book_title then
    return {}
  end
end

return {
  { Meta = read_meta },
  { Header = hide_header },
}
