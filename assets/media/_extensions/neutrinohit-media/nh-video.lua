-- {{< nh-video <id> variant="<variant>" [attribute="value" ...] >}}
-- A <video> element for a shared NeutrinoHit film. Other arguments become attributes of
-- the element (class, style, poster, aria-label ...); "true" gives a bare attribute
-- (controls, muted, loop, autoplay, playsinline), "false" leaves it out.

local core = dofile(quarto.utils.resolve_path("core.lua"))

local function escape(text)
  return (text:gsub("&", "&amp;"):gsub('"', "&quot;"):gsub("<", "&lt;"))
end

-- Inside a raw HTML block Quarto passes values with their quotes: "film-en" -> film-en
local function value_of(arg)
  local text = pandoc.utils.stringify(arg or "")
  return text:match('^"(.*)"$') or text
end

-- {{< nh-url <id> variant="<variant>" >}}: only the address, for a link (<a href>, a download button)
-- or a data file; works inside raw HTML blocks as well. A published address is absolute
-- (https://neutrinohit.github.io/...): Quarto would rewrite a root-relative link in Markdown.
local function nh_url(args, kwargs, meta, raw_args, context)
  local id = value_of(args[1])
  local variant = value_of(kwargs["variant"])
  if id == "" or variant == "" then error("nh-url: usage {{< nh-url <id> variant=\"<variant>\" >}}") end
  local src = core.src(id, variant)
  if src:sub(1, 1) == "/" and not os.getenv("NH_MEDIA_PREVIEW") then src = "https://neutrinohit.github.io" .. src end
  local address = escape(src)
  if context == "text" then return address end
  return pandoc.RawInline("html", address)
end

return {
  ["nh-url"] = nh_url,
  ["nh-video"] = function(args, kwargs, meta, raw_args, context)
    local id = value_of(args[1])
    local variant = value_of(kwargs["variant"])
    if id == "" or variant == "" then error("nh-video: usage {{< nh-video <id> variant=\"<variant>\" >}}") end
    local names = {}
    for name, _ in pairs(kwargs) do
      if name ~= "variant" then table.insert(names, name) end
    end
    table.sort(names)
    local parts = { '<video src="' .. escape(core.src(id, variant)) .. '"' }
    for _, name in ipairs(names) do
      local value = value_of(kwargs[name])
      if value == "true" then
        table.insert(parts, name)
      elseif value ~= "false" then
        table.insert(parts, name .. '="' .. escape(value) .. '"')
      end
    end
    local html = table.concat(parts, " ") .. "></video>"
    if context == "text" then return html end -- inside a raw HTML block
    if context == "block" then return pandoc.RawBlock("html", html) end
    return pandoc.RawInline("html", html)
  end
}
