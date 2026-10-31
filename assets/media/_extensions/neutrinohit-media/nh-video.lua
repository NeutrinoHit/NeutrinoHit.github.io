-- {{< nh-video <id> variant="<variant>" [attribute="value" ...] >}}
-- A <video> element for a shared NeutrinoHit film. Other arguments become attributes of
-- the element (class, style, poster, aria-label ...); "true" gives a bare attribute
-- (controls, muted, loop, autoplay, playsinline), "false" leaves it out.

local core = dofile(quarto.utils.resolve_path("core.lua"))

local function escape(text)
  return (text:gsub("&", "&amp;"):gsub('"', "&quot;"):gsub("<", "&lt;"))
end

return {
  ["nh-video"] = function(args, kwargs, meta, raw_args, context)
    local id = pandoc.utils.stringify(args[1] or "")
    local variant = pandoc.utils.stringify(kwargs["variant"] or "")
    if id == "" or variant == "" then error("nh-video: usage {{< nh-video <id> variant=\"<variant>\" >}}") end
    local names = {}
    for name, _ in pairs(kwargs) do
      if name ~= "variant" then table.insert(names, name) end
    end
    table.sort(names)
    local parts = { '<video src="' .. escape(core.src(id, variant)) .. '"' }
    for _, name in ipairs(names) do
      local value = pandoc.utils.stringify(kwargs[name])
      if value == "true" then
        table.insert(parts, name)
      elseif value ~= "false" then
        table.insert(parts, name .. '="' .. escape(value) .. '"')
      end
    end
    local html = table.concat(parts, " ") .. "></video>"
    if context == "block" then return pandoc.RawBlock("html", html) end
    return pandoc.RawInline("html", html)
  end
}
