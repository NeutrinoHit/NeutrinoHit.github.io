# NeutrinoHit Reveal Footer

Shared footer for Quarto RevealJS talks and lectures.

The canonical copy lives here. Local copies are stored in each lecture/talk
repository so `quarto preview` works without waiting for GitHub Pages.

The sync target list is defined in `../../scripts/sync_reveal_assets.py`. It
copies the common footer/logo into each project-level `shared/reveal/`
directory and copies the common Reveal SCSS into project-level
`shared/styles/` directories where that style is used.

After editing the footer script, logo, or shared Reveal SCSS, run from
`neutrinohit-map`:

```bash
python scripts/sync_reveal_assets.py
```

Every presentation must define where the footer's context button returns. Add a
stable anchor to the relevant `neutrinohit-map` page, register the absolute URL
in `scripts/reveal_context_targets.json`, and use that URL in a project-level
`_quarto.yml` or directory-level `_metadata.yml`.

```yaml
format:
  revealjs:
    include-after-body:
      text: |
        <script data-external="1" data-context-home="https://neutrinohit.github.io/ru/education.html#qft" data-context-home-label="Карта курса КТП" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

`quarto render` runs `scripts/validate_reveal_context_homes.py` after rendering.
The build fails if a footer script is missing `data-context-home`, is missing
`data-context-home-label`, points to a local page such as `index.html`, or uses
an unregistered/missing anchor.

The footer button URL must be absolute and canonical:

```yaml
format:
  revealjs:
    include-after-body:
      text: |
        <script data-external="1" data-context-home="https://neutrinohit.github.io/ru/outreach.html#birth-life-universe" data-context-home-label="Карта лекции" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

The footer script also applies a MathJax2 SVG renderer fallback after RevealJS
initializes MathJax. This avoids browser/web-font issues with commands such as
`\mathcal` in RevealJS output. The default renderer is `SVG`.

To disable this fallback for a particular presentation, pass:

```yaml
format:
  revealjs:
    include-after-body:
      text: |
        <script data-external="1" data-context-home="https://neutrinohit.github.io/ru/education.html#qft" data-context-home-label="Карта курса КТП" data-mathjax-renderer="default" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

To choose another MathJax2 renderer explicitly, for example `HTML-CSS`, pass:

```yaml
format:
  revealjs:
    include-after-body:
      text: |
        <script data-external="1" data-context-home="https://neutrinohit.github.io/ru/education.html#qft" data-context-home-label="Карта курса КТП" data-mathjax-renderer="HTML-CSS" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

If a presentation already defines `format.revealjs.logo`, the script moves that
logo into the footer. Otherwise it uses:

```text
shared/reveal/dvnlogo.png
```

The shared dark Reveal SCSS is:

```text
shared/styles/neutrinohit-reveal.scss
```

It also provides reusable slide utility classes, including `.marginnote`
for yellow sticky-note annotations. Use it with Quarto RevealJS absolute
positioning:

```markdown
::: {.marginnote .absolute top=190 left=1160 width=330}
<span class="note-title">Key point</span>
Short explanation.
:::
```

The default sticky-note sizes are:

```css
--note-font-size: 0.68em;
--note-math-font-size: 1.04em;
```

Override them once per lecture in that lecture's CSS:

```css
.reveal {
  --note-font-size: 0.72em;
  --note-title-font-size: 1.1em;
  --note-math-font-size: 1.08em;
}
```

The same variables can be set on a slide heading, where they are inherited by
all notes on that slide:

```markdown
## Slide Title {style="--note-font-size: 0.72em; --note-math-font-size: 1.08em;"}
```

It can also be overridden on one note:

```markdown
::: {.marginnote style="--note-font-size: 0.74em;"}
Short explanation.
:::
```

`data-external="1"` is intentional: presentations with `embed-resources: true`
must keep loading the shared local script instead of embedding a stale copy into
each HTML file.
