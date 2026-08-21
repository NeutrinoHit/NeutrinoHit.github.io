# NeutrinoHit Site Migration Audit

Рабочий документ для поэтапной миграции NeutrinoHit к крупным смысловым
разделам, равноправным RU/EN версиям и общей дизайн-системе.

## Инварианты

- Существующие проекты остаются самостоятельными: `sciencepop`, `neutrinophysics`,
  `particlephysics`, `qft-lectures`, `stat-course`, `talks`, книги и локальные
  архивы не переносятся внутрь одного монолита.
- На первом этапе меняются точки входа, навигация и оболочка сайта, а не
  физическое расположение материалов.
- Старые URL сохранялись на переходном этапе. После переноса каталогов под
  `ru/` и `en/` старые корневые страницы удалены из исходников.
- RU и EN версии проектируются как равноправные витрины. Материалы, существующие
  только на русском, в английской версии помечаются как `in Russian`.
- Общий визуальный язык должен жить в корневом `neutrinohit-map` и подключаться
  подпроектами как базовый слой. Локальные CSS остаются только для уникальной
  специфики проекта.

## Checkpoint log

- Phase 1: shared CSS foundation added in `assets/site/` and connected to the
  root site plus active educational subprojects.
- Phase 2: Russian top-level entry pages added at the root: `research.qmd`,
  `education.qmd`, `outreach.qmd`, `materials.qmd`, `school.qmd`, `about.qmd`.
  The navbar now points to these semantic sections. Legacy pages and URLs remain
  in place and are linked from the new sections.
- Phase 3: root `/` changed to a bilingual landing page with visible RU/EN
  choices and soft browser-language suggestion. The Russian semantic pages moved
  to `/ru/`; English counterpart entry pages were added under `/en/`. Root
  semantic URLs remain as transition pages to the Russian version.
- Phase 4 prep: public section `People / Люди` renamed to `School / Школа` with old `people.html` URLs kept as redirects.
- Phase 4: English catalog pages added for books, lectures, software, science communication, visual materials, talks, schools, theses, and supervised works; English section pages now link to these EN pages instead of using root Russian catalogs as the primary path.
- Phase 4 cleanup: public render is scoped to `index.qmd`, `ru/*.qmd`,
  `en/*.qmd`, and shared `albums/**/*.qmd`. Legacy root catalog pages,
  `obsolete/**/*.qmd`, and the empty
  `neutrino_introduction/neutrino-interactions.qmd` are no longer rendered.
  Russian catalog pages for animations, talks, theses, and supervised works
  were moved under `ru/` before root pages were excluded.
- Phase 4 deletion: legacy root catalog pages, `obsolete/`, and the empty
  `neutrino_introduction/neutrino-interactions.qmd` were removed after the
  bilingual entry points covered the public content.
- Deferred projects for later passes: `QFT-book-ru`, `QFT-book-en`, `dvnanima`,
  `gTracker`.

## Текущая топология

### Корневой сайт `neutrinohit-map`

Текущий public render содержит только:

- `index.qmd` -> `/`
- `ru/*.qmd` -> русская версия сайта
- `en/*.qmd` -> английская версия сайта
- `albums/**/*.qmd` -> общий архив фото/видео, на который ссылаются обе
  языковые версии

Технические страницы и инструменты:

- `photo-studio.qmd` excluded from render in `_quarto.yml`.
- `albums/**/*.qmd` rendered separately.
- `scripts/sync_local_project_sites.py` copies sibling project builds into
  `_site/<slug>/` for local preview only.

Legacy root catalog pages such as `animations.qmd`, `lectures.qmd`,
`students.qmd`, `theses.qmd`, `talks.qmd`, `books.qmd`, `cinema.qmd`,
`photos.qmd`, `schools.qmd`, `software.qmd`, and `interviews.qmd` were deleted
after their public content moved to the RU/EN pages.

### Obsolete directory audit

The deleted `obsolete/` pages did not contain unique migrated content:

| File | Current status |
| --- | --- |
| `obsolete/about.qmd` | Redirect wrapper to `/ru/about.html`. |
| `obsolete/education.qmd` | Redirect wrapper to `/ru/education.html`. |
| `obsolete/materials.qmd` | Redirect wrapper to `/ru/materials.html`. |
| `obsolete/outreach.qmd` | Redirect wrapper to `/ru/outreach.html`. |
| `obsolete/research.qmd` | Redirect wrapper to `/ru/research.html`. |
| `obsolete/people.qmd`, `obsolete/school.qmd`, `obsolete/ru/people.qmd` | Redirect wrappers to `/ru/school.html`. |
| `obsolete/en/people.qmd` | Redirect wrapper to `/en/school.html`. |
| `obsolete/sciencepop.qmd`, `obsolete/en/sciencepop.qmd` | Cards pointing users to current Outreach pages and the standalone `sciencepop` archive. |

These files were removed after the audit above; `!obsolete/**/*.qmd` may remain
in `_quarto.yml` as a harmless guard if the folder is temporarily restored for
local comparison.

### Подпроекты, подключаемые локально

Defined in `scripts/sync_local_project_sites.py`:

- `talks/_site` -> `_site/talks`
- `qft-lectures/_site` -> `_site/qft-lectures`
- `gravity/_site` -> `_site/gravity`
- `sciencepop/_site` -> `_site/sciencepop`
- `neutrinophysics/_site` -> `_site/neutrinophysics`
- `particlephysics/_site` -> `_site/particlephysics`
- `stat-course/_site` -> `_site/statistical-analysis-course`

### CSS observations

- Root `styles.css` already has reusable patterns:
  `profile-*`, `lecture-course-*`, `lecture-material-*`, `resource-*`,
  `thesis-*`, `nh-card`, `nh-button`, animation and album tooling classes.
- `qft-lectures/styles.css`, `neutrinophysics/styles.css` and
  `particlephysics/styles.css` are identical. They define the `course-*`
  pattern used by educational subprojects.
- This duplicate `course-*` layer is the best first candidate for extraction
  into a shared site CSS package.
- `sciencepop/index.html` is standalone static HTML with its own embedded style.
  It should be treated as a later migration target, not as the first CSS
  extraction target.

## Target information architecture

The top-level site should be organized by professional meaning, not by file type:

- `Research / Наука`
- `Education / Образование`
- `Outreach / Научная коммуникация`
- `Materials / Материалы`
- `School / Школа`
- `About / Обо мне`

Recommended navbar:

```text
RU: Главная | Наука | Образование | Научная коммуникация | Материалы | Школа | Обо мне | EN
EN: Home | Research | Education | Outreach | Materials | School | About | RU
```

Shorter variants can be considered after content is drafted, but `Наука` must be
a first-class section.

Decision: use `Научная коммуникация` in Russian and `Outreach` in English.

## Mapping of current pages to target sections

| Legacy URL | Current status | Primary new section | Secondary section | Notes |
| --- | --- | --- | --- | --- |
| `/books.html` | deleted after RU/EN migration | Education | Outreach | Textbooks and popular books appear in both language contexts. |
| `/lectures.html` | deleted after RU/EN migration | Education | Materials | Course catalogs live under language-specific pages. |
| `/students.html` | deleted after RU/EN migration | School | Education | Scientific school, supervision, theses. |
| `/theses.html` | deleted after RU/EN migration | Research | About | Personal degrees are part of research identity. |
| `/schools.html` | deleted after RU/EN migration | School | Education | School archive and teaching ecosystem. |
| `/talks.html` | deleted after RU/EN migration | Research | Materials | Talks are no longer a top-level root page. |
| `/interviews.html` | deleted after RU/EN migration | Outreach | About | Public communication and media. |
| `/photos.html` | deleted after RU/EN migration | School | Outreach | Scientific life and archive. |
| `/sciencepop.html` | deleted after RU/EN migration | Outreach | Materials | Current pages link to the standalone `sciencepop` archive. |
| `/cinema.html` | deleted after RU/EN migration | Outreach | Materials | Films and animation-style outreach. |
| `/animations.html` | deleted after RU/EN migration | Materials | Education | Visual assets, videos, reusable illustrations. |
| `/software.html` | deleted after RU/EN migration | Materials | Research | Code, models, tools. |

## RU/EN structure

Preferred structure:

```text
/ru/
  index.qmd
  research.qmd
  education.qmd
  outreach.qmd
  materials.qmd
  people.qmd
  about.qmd
/en/
  index.qmd
  research.qmd
  education.qmd
  outreach.qmd
  materials.qmd
  people.qmd
  about.qmd
```

Root `/` should remain a real landing page with visible RU/EN choices and soft
automatic language suggestion. It should not be a blank redirect-only gateway.
Legacy root catalog pages were kept only during transition and are now removed
from the source tree after the bilingual structure became the public entry
point.

Language routing rules:

1. If user selected RU/EN manually, persist that choice in `localStorage`.
2. Otherwise inspect `navigator.languages`.
3. Route Russian and CIS-adjacent browser languages to `/ru/`.
4. Route other languages to `/en/`.
5. Do not use hard geoblocking logic. On GitHub Pages there is no reliable
   server-side country detection; country routing would require an edge layer
   such as Cloudflare Workers on a custom domain.

Suggested language pool for RU default:

```text
ru, be, uk, kk, ky, uz, tg, tk, hy, az, ka, ro, mo
```

This is only a default. The visible switcher must always be available.

## Shared CSS strategy

Create a shared layer in `neutrinohit-map`:

```text
assets/site/neutrinohit-tokens.css
assets/site/neutrinohit-base.css
assets/site/neutrinohit-components.css
assets/site/neutrinohit-projects.css
```

Responsibilities:

- `tokens`: colors, spacing, typography scale, radii, shadows, breakpoints.
- `base`: body, Quarto container resets, links, headings, common layout.
- `components`: cards, action rows, buttons, pills, accordions, language switcher.
- `projects`: compatibility aliases for existing `profile-*`, `lecture-*`,
  `course-*`, `resource-*`, `thesis-*` classes while pages are migrated.

Initial component namespace:

```text
nh-page
nh-shell
nh-hero
nh-section
nh-section-header
nh-grid
nh-card
nh-card-title
nh-card-meta
nh-card-body
nh-card-actions
nh-button
nh-button-primary
nh-pill
nh-accordion
nh-accordion-item
nh-language-switch
```

Compatibility principle:

- Do not rewrite all markup first.
- First, make shared CSS support existing `course-*` and `lecture-course-*`
  patterns.
- Then new pages can use `nh-*`.
- Old pages can be migrated gradually.

## Access control and private pages

GitHub Pages is a static public hosting target. It can support hidden or
unlisted pages, but not real private access control by itself.

Recommended handling:

- Public site content: render normally.
- Personal local tools such as `photo-studio.qmd`: keep excluded from render and
  use through local preview or a local static HTML file. This is already aligned
  with the current `!photo-studio.qmd` setup.
- Semi-hidden public pages: possible through obscure URLs and by excluding from
  navbar, sitemap and search. This is not security; anyone with the URL or repo
  access can open it.
- Truly private pages: use a separate private deployment target, not public
  GitHub Pages. Options include a private internal server, Cloudflare Access on a
  custom domain, Netlify/Vercel with password/auth, or GitHub-authenticated
  pages where the hosting plan supports it.
- Paid courses: do not implement access by a client-side code in a static page
  if the content is valuable. A code checked in JavaScript can be bypassed. Use a
  real backend or an access provider that validates entitlement server-side.

For paid or code-gated course access, safe architectures:

1. External learning/payment platform hosts the restricted material.
2. Static public pages advertise the course and link to the restricted platform.
3. If hosting ourselves, put protected materials behind a server or edge access
   layer that validates tokens outside the browser.

Possible later custom domain work:

- A custom domain is useful for language routing and access control only if it is
  paired with a free or acceptable-cost edge/auth layer.
- If the required routing/auth is paid, this stays lower priority.

## Migration phases

### Phase 0: Audit and design contract

Status: in progress.

Checklist:

- [x] Confirm root `neutrinohit-map` git worktree is clean.
- [x] Inventory root pages and sibling projects.
- [x] Identify duplicate CSS across educational subprojects.
- [x] Decide final top-level RU/EN labels.
- [x] Decide whether legacy root pages remain permanently or become redirects
      after RU/EN launch.
- [x] Scope public render to RU/EN plus shared album pages.
- [x] Exclude `obsolete/**/*.qmd` from render.
- [x] Exclude empty `neutrino_introduction/neutrino-interactions.qmd` from
      render by removing broad root/discovery globs.
- [x] Delete legacy root catalog pages, `obsolete/`, and the empty
      `neutrino_introduction/neutrino-interactions.qmd`.

### Phase 1: Shared CSS foundation

Checklist:

- [x] Add shared CSS files under `assets/site/`.
- [x] Include them in root `_quarto.yml` before local `styles.css`.
- [ ] Keep visual output equivalent on existing pages.
- [x] Extract duplicated `course-*` CSS from one source into shared layer.
- [x] Update `qft-lectures`, `neutrinophysics`, `particlephysics` to include the
      shared layer, leaving their local `styles.css` as overrides.
- [ ] Render and compare root plus three educational subprojects.
      Current checkpoint rendered root plus `index.qmd` for the three
      educational subprojects; visual screenshot comparison remains next.

### Phase 2: New RU top-level pages

Checklist:

- [ ] Add `research.qmd`, `education.qmd`, `outreach.qmd`,
      `materials.qmd`, `school.qmd`, `about.qmd`.
- [ ] Add `Физика нейтрино и астрофизика частиц` as an online program item in education.
- [ ] Add explicit research section with experiments, interests, INSPIRE, talks.
- [ ] Keep old root pages reachable.
- [ ] Change navbar only after new pages exist.

### Phase 3: Equal EN structure

Checklist:

- [ ] Add `en/` pages mirroring the RU top-level structure.
- [ ] Add language labels for Russian-only materials: `in Russian`.
- [ ] Add language labels for English materials: `in English`.
- [ ] Add RU/EN switcher links between corresponding pages.
- [ ] Add root language gateway.
- [ ] Add `hreflang` metadata if Quarto setup permits cleanly.

### Phase 4: Legacy page normalization

Checklist:

- [ ] Migrate high-level root pages to `nh-*` components gradually.
- [ ] Keep specialized pages such as `photo-studio.qmd` isolated from public
      design-system changes unless explicitly needed.
- [ ] Move repeated styles out of local project CSS into the shared layer.
- [ ] Remove duplicated CSS only after each affected project renders cleanly.

### Phase 5: Validation and publication

Checklist:

- [ ] Run `quarto render` in `neutrinohit-map`.
- [ ] Render `qft-lectures`, `neutrinophysics`, `particlephysics`.
- [ ] Check old URLs manually.
- [ ] Check new RU/EN pages manually.
- [ ] Verify local preview still copies sibling projects.
- [ ] Check mobile layout for navbar, cards and language switcher.
- [ ] Commit in small units.

## Suggested commit sequence

```text
1. Document migration audit and checkpoints
2. Add shared NeutrinoHit CSS foundation
3. Wire shared CSS into root site
4. Wire shared CSS into educational subprojects
5. Add RU top-level architecture pages
6. Add Neutrino Physics and Astroparticle Physics Education Program entry points
7. Add EN architecture pages and language switcher
8. Normalize legacy page styling incrementally
```

## Decisions

- Russian label: `Научная коммуникация`.
- English label: `Outreach`.
- Root behavior after RU/EN launch: keep a full landing page with visible RU/EN
  choices and auto-suggested language.
- Legacy pages: no longer rendered as root catalog pages; keep sources for now
  and delete them in a separate cleanup commit after old external URLs are
  checked.
- Custom domain plus edge routing/auth: desirable later only if free or
  low-friction; lower priority if paid.
- Avoid abbreviations for the education program in both languages. Use full
  names: `Физика нейтрино и астрофизика частиц` and
  `Neutrino Physics and Astroparticle Physics Education Program`.
