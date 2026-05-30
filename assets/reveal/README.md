# NeutrinoHit Reveal Footer

Shared footer for Quarto RevealJS talks and lectures.

The canonical copy lives here. Local copies are stored in each lecture/talk
repository so `quarto preview` works without waiting for GitHub Pages.

After editing the footer script or logo, run from `neutrinohit-map`:

```bash
python scripts/sync_reveal_assets.py
```

Add one of these snippets to a project-level `_quarto.yml` or a
directory-level `_metadata.yml`, choosing the relative path for the rendered
HTML location:

```yaml
format:
  revealjs:
    include-after-body:
      text: |
        <script data-external="1" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

To add a project-specific home link next to the NeutrinoHit logo, pass its URL
relative to the rendered presentation:

```yaml
format:
  revealjs:
    include-after-body:
      text: |
        <script data-external="1" data-context-home="index.html" data-context-home-label="Главная страница курса" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

If a presentation already defines `format.revealjs.logo`, the script moves that
logo into the footer. Otherwise it uses:

```text
shared/reveal/dvnlogo.png
```

`data-external="1"` is intentional: presentations with `embed-resources: true`
must keep loading the shared local script instead of embedding a stale copy into
each HTML file.
