# NeutrinoHit Reveal Footer

Shared footer for Quarto RevealJS talks and lectures.

Add this to a project-level `_quarto.yml` or a directory-level `_metadata.yml`:

```yaml
format:
  revealjs:
    include-after-body:
      text: |
        <script data-external="1" src="https://neutrinohit.github.io/assets/reveal/neutrinohit-reveal-footer.js"></script>
```

If a presentation already defines `format.revealjs.logo`, the script moves that
logo into the footer. Otherwise it uses:

```text
https://neutrinohit.github.io/assets/reveal/dvnlogo.png
```

`data-external="1"` is intentional: presentations with `embed-resources: true`
must keep loading the live shared script instead of embedding a stale copy.
