# @HOME@

@TITLE@.

This repository publishes films of [NeutrinoHit](https://neutrinohit.github.io/)
used by its animation gallery, the QR pages of the books, lectures and talks.
Git holds only the list of films; the files are assets of the GitHub Releases
of this repository (one release per story, tag = story id), and the Pages site
serves them at

    https://neutrinohit.github.io/@HOME@/<id>/<variant>-v<version>.mp4

- `media.manifest.json` lists every film: id, variant, version, size,
  SHA-256, duration and frame size. It is generated from the shared catalog
  of the main site (`media.catalog.json` of NeutrinoHit.github.io).
- `make site` downloads the films, verifies size and SHA-256 and writes `_site/`;
  the publish workflow runs it on every push to `main`.

Published files never change: a new render gets a new version and a new
address, so a prepared lecture keeps the film it was made with.
