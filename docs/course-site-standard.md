# NeutrinoHit Course Site Standard

This note defines how standalone course sites coexist with the main
NeutrinoHit map.

## Architecture

NeutrinoHit has two levels.

1. The main site is a map of research, education, outreach, and materials. It
   gives short context and direct entry points.
2. A course site is the working home of a course. It can be developed,
   rendered, and published independently.

The main site should not absorb full course structure. Course sites should not
be disconnected from NeutrinoHit.

## Canonical targets

Every course-related target used by a slide footer or a main-site card must be
registered as one of two types.

- `map-card`: an anchor on the main NeutrinoHit map, for example
  `https://neutrinohit.github.io/ru/education.html#particles`.
- `course-home`: a standalone course home page, for example
  `https://neutrinohit.github.io/particlephysics/ParticlePhysics/`.

Slides should return to the nearest useful course context. If a standalone
course page exists, even as a structured scaffold, the slide footer may point to
that course home. If a material is truly standalone, it can point to a map card.

## Course Shell

Every standalone course site should use the same shell.

- A top navigation link or button to `NeutrinoHit`.
- A link to the corresponding main-site map card.
- A course header with title, language/status, and a short course purpose.
- A short author note with one link to the main profile/site; no full biography.
- Lecture cards or placeholder lecture cards.
- Additional-material sections: notes, book, exercises, exams, applets,
  notebooks, datasets, references.
- The shared NeutrinoHit footer, analytics, and RevealJS footer for slides.

## Empty Or Draft Courses

An unfinished course should still have a proper course home. It must not be a
blank page or a one-line placeholder. Use the same Course Shell and mark missing
pieces clearly as `in preparation` / `готовится`.

This reduces ambiguity: every course has one stable URL from the start, and the
site grows in place.

## Main-Site Cards

Main-site cards should stay compact. They may include:

- a primary link to the course home;
- direct links to the most important materials;
- a short status label;
- a note about language when needed.

They should not duplicate the full course syllabus.

## Build Contract

`neutrinohit-map/scripts/validate_reveal_context_homes.py` validates all Reveal
footer context links after render. A new course material must register its
canonical target in `scripts/reveal_context_targets.json`; otherwise the build
must fail.

