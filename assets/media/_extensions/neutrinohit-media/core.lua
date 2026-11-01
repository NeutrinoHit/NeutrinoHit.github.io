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

-- The same address made absolute (https://neutrinohit.github.io/...) once published: Quarto
-- rewrites a root-relative src or link against the project ("../media-qft/..."), and pandoc
-- cannot fetch it for an EPUB. A preview (NH_MEDIA_PREVIEW=1) and a local fallback stay as they are.
M.SITE = "https://neutrinohit.github.io"

function M.absolute_src(id, variant)
  local src = M.src(id, variant)
  if src:sub(1, 1) == "/" and os.getenv("NH_MEDIA_PREVIEW") ~= "1" then return M.SITE .. src end
  return src
end

-- "nh:<id>/<variant>" -> absolute address; anything else unchanged. Quarto gives an image
-- target without an extension its default one ("nh:x/film-en.png"): a variant has no dots.
function M.resolve(value)
  local id, variant = tostring(value):match("^nh:([%w%-]+)/([%w%-]+)$")
  if not id then id, variant = tostring(value):match("^nh:([%w%-]+)/([%w%-]+)%.%w+$") end
  if id then return M.absolute_src(id, variant) end
  return nil
end

return M
