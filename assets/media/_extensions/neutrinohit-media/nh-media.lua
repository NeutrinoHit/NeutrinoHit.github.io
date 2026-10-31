-- Filter (add "neutrinohit-media" to filters): "nh:<id>/<variant>" in a slide background
-- ({background-video="nh:star-in-jet/film-en"}) or an image/link target becomes the
-- address of the shared film.

local core = dofile(quarto.utils.resolve_path("core.lua"))
local KEYS = { "background-video", "data-background-video", "src", "data-src" }

local function attributes(el)
  local changed = false
  for _, key in ipairs(KEYS) do
    local value = el.attributes[key]
    local resolved = value and core.resolve(value)
    if resolved then
      el.attributes[key] = resolved
      changed = true
    end
  end
  if changed then return el end
end

return {
  { Header = attributes, Div = attributes,
    Image = function(el) local r = core.resolve(el.src); if r then el.src = r; return el end end,
    Link = function(el) local r = core.resolve(el.target); if r then el.target = r; return el end end }
}
