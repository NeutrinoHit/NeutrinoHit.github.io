.PHONY: site check

# Downloads the films of media.manifest.json from the Releases of this repository,
# verifies SHA-256 and size and writes the Pages site to _site/.
site:
	python3 scripts/build_site.py
	test -s _site/index.html

# Local build from the shared cache of neutrinohit-map (no download).
check:
	python3 scripts/build_site.py --from-cache ../neutrinohit-map/.cache/media --out .work/_site
