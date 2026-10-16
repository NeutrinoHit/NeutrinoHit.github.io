#!/bin/sh
# Prepare Quarto's Linux TinyTeX, not an unrelated system TeX installation.
# Canonical copy: neutrinohit-map/assets/books/setup_book_tex.sh; book courses
# receive it as scripts/setup_book_tex.sh through scripts/sync_book_assets.py.
# The package list covers the shared preamble neutrinohit-book.tex.
set -eu

if [ "${GITHUB_ACTIONS:-}" != true ]; then
  echo 'This setup is for the disposable GitHub Actions runner only.' >&2
  exit 1
fi

book_tex_bin="${BOOK_TEX_BIN:-$HOME/.TinyTeX/bin/$(uname -m)-linux}"
book_tex_repository="${BOOK_TEX_REPOSITORY:-https://tlnet.yihui.org}"
if [ ! -x "$book_tex_bin/tlmgr" ]; then
  echo "Quarto TinyTeX not found at $book_tex_bin; run quarto install tinytex first." >&2
  exit 1
fi
PATH="$book_tex_bin:$PATH"
export PATH

# Select one repository explicitly and provision named dependencies. Quarto's
# font-name search also matches unrelated Type 1/newtx packages for Libertinus.
tlmgr --version
tlmgr option repository "$book_tex_repository"
tlmgr update --self
tlmgr install \
  amsmath booktabs caption colortbl enumitem etoc float fontspec footnotehyper \
  framed fvextra graphics hyperref hyphen-russian koma-script \
  libertinus-fonts listingsutf8 lua-ul luatexbase marginnote mathtools microtype \
  needspace pdfpages pgf polyglossia ragged2e selnolig tcolorbox \
  tools unicode-math upquote xcolor xurl

# Fonts are now installed, so build LuaLaTeX's name index before the first page.
luaotfload-tool --update --force
for book_font in LibertinusSerif-Regular.otf LibertinusSans-Regular.otf \
                 LibertinusMono-Regular.otf LibertinusMath-Regular.otf; do
  if ! kpsewhich "$book_font"; then
    echo "Missing required book font after TeX setup: $book_font" >&2
    exit 1
  fi
done
