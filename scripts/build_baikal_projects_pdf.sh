#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "${script_dir}/.." && pwd)"
intro_md="${repo_dir}/assets/schools/baikal-2026/baikal-projects-pdf-intro.md"
projects_qmd="${repo_dir}/_includes/baikal-school-2026-projects.qmd"
target_pdf="${repo_dir}/assets/schools/baikal-2026/baikal-school-2026-projects.pdf"

cd "${repo_dir}"

quarto pandoc "${intro_md}" "${projects_qmd}" \
  --from=markdown \
  --to=pdf \
  --output="${target_pdf}" \
  --standalone \
  --lua-filter="${repo_dir}/filters/baikal-projects-pdf.lua" \
  --include-in-header="${repo_dir}/assets/schools/baikal-2026/baikal-projects-pdf.tex" \
  --pdf-engine=lualatex \
  --toc \
  --toc-depth=1 \
  --resource-path="${repo_dir}/en" \
  -V documentclass=scrartcl \
  -V papersize=a4 \
  -V colorlinks=true \
  -V linkcolor=NHBlue \
  -V urlcolor=NHBlue \
  -V geometry:top=18mm,bottom=18mm,left=18mm,right=18mm \
  -V mainfont='TeX Gyre Pagella' \
  -V sansfont='TeX Gyre Heros'

printf 'Updated %s\n' "${target_pdf}"
