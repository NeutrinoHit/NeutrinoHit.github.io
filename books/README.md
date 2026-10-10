# Каталоги книг

Один файл на книгу: `<slug>.catalog.json` (реестр: `../books.catalog.json`; QFT лежит в `../book-animations.catalog.json`).

```json
{
  "base_url": "https://neutrinohit.github.io",
  "qr_path": "/qr/<slug>/",
  "book": {"title": {"ru": "...", "en": "..."}, "author": {"ru": "Д. В. Наумов", "en": "D. V. Naumov"}, "page": {"ru": "/...", "en": "/..."}},
  "items": [ ... ]
}
```

Запись (все тексты двуязычные; формулы в `caption` и `credit.note` пишутся в LaTeX между `$...$`, в `title` формул нет):

```json
{
  "id": "0001", "slug": "short-latin-name", "qr_file": "ShortLatinName.pdf", "hosting": "self",
  "title":   {"ru": "...", "en": "..."},
  "caption": {"ru": "... $E=mc^2$ ...", "en": "... $E=mc^2$ ..."},
  "book":    {"order": 1, "section_title": {"ru": "Раздел", "en": "Section"}},
  "credit":  {"author": {"ru": "Д. В. Наумов", "en": "D. V. Naumov"}, "code_url": "https://github.com/NeutrinoHit/dvnanima/tree/main/<project>"},
  "media":   {"source": "<slug>/file.mp4", "poster_time": 12.0},
  "legacy_codes": []
}
```

`media.source` — файл в `not-to-commit/book-animations-src/` (в git не входит; на сайт идёт кодированная копия в
`assets/book-animations/<slug>/`). Анимация, которая уже есть на сайте, задаётся как `"media": {"site_asset": {"ru": "assets/...mp4", "en": "assets/...-en.mp4"}, "poster_time": 12.0}`
(строка вместо пары — одно видео для обоих языков); можно добавить `"gallery": "раздел/сюжет"`.
Для книги с томами в `book` вместо `order`/`section_title` указываются `volume`, `chapter`, `chapter_title`.
`hosting`: `self` — видео на странице; `external` — права не у нас, нужен `external_url`; `pending` — «скоро».
Номер `id` после печати менять нельзя.
