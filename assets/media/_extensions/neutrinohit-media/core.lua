-- Shared films of NeutrinoHit: lookup in the project's media.lock.json.
-- An entry gives the immutable address of a film (/<home>/<id>/<variant>-v<version>.mp4)
-- and, while the film is not yet published, the local file it replaces (fallback).

local M = {}
local lock

local function project_root()
  return quarto.project.directory or pandoc.path.directory(quarto.doc.input_file)
end

function M.load()
  if lock then return lock end
  local path = pandoc.path.join({ project_root(), "media.lock.json" })
  local handle = io.open(path, "r")
  if not handle then error("nh-video: " .. path .. " is missing (neutrinohit-map: nh_media.py lock)") end
  local text = handle:read("a")
  handle:close()
  lock = quarto.json.decode(text)
  return lock
end

function M.entry(id, variant)
  for _, e in ipairs(M.load().media) do
    if e.id == id and e.variant == variant then return e end
  end
  error("nh-video: " .. id .. "/" .. variant .. " is not in media.lock.json (neutrinohit-map: nh_media.py lock)")
end

-- Address written into the page: the shared film once published (or in a preview with
-- NH_MEDIA_PREVIEW=1), else the local file relative to the rendered document.
function M.src(id, variant)
  local e = M.entry(id, variant)
  if e.status == "published" or os.getenv("NH_MEDIA_PREVIEW") == "1" then return e.url end
  if not e.fallback or e.fallback == "" then
    error("nh-video: " .. id .. "/" .. variant .. " is not published yet and has no local fallback")
  end
  local file = pandoc.path.join({ project_root(), e.fallback })
  return pandoc.path.make_relative(file, pandoc.path.directory(quarto.doc.input_file), true)
end

-- "nh:<id>/<variant>" -> address; anything else unchanged
function M.resolve(value)
  local id, variant = tostring(value):match("^nh:([%w%-]+)/([%w%-]+)$")
  if id then return M.src(id, variant) end
  return nil
end

return M
