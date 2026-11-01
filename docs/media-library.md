# Общая медиатека NeutrinoHit

Один опубликованный фильм, много потребителей: галерея, QR-страницы книг,
лекции и доклады ссылаются на один файл вместо собственных копий MP4.

```
рендер (dvnanima) → Release медиапроекта → Pages медиапроекта → галерея, QR, лекции, доклады
                                                              → офлайн-комплект доклада
```

## Кто за что отвечает

| Где | Что |
|---|---|
| `dvnanima` (частный) | исходники анимаций, настройки, рендеры |
| `neutrinohit-map` | каталог `media.catalog.json`, инструменты `scripts/nh_media.py`, шаблон медиапроекта `assets/media/project/`, расширение для лекций `assets/media/_extensions/neutrinohit-media/` |
| `media-neutrino`, `media-qft`, `media-mechanics`; `media-talks`, `media-particlephysics`, `media-sciencepop`, `media-stat-course`, `media-qft-lectures`, `media-albums` | `media.manifest.json` и сборка в git; файлы — в GitHub Releases; раздача — Pages |
| репозитории курсов и докладов | текст, рисунки, постеры, `media.lock.json` и ссылки `nh-video` |
| офлайн-комплект | выбранные доклады + один экземпляр каждого фильма; результат сборки вне git |

Медиапроекты делятся так, чтобы ни один не подходил к пределу Pages 1 ГБ.
Фильмы галереи и QR книг — по теме: `media-neutrino` — нейтрино, частицы,
астрофизика (и QR книг о нейтрино и частицах); `media-qft` — поля, волны,
относительность (и QR книг КТП и ОТО); `media-mechanics` — механика,
динамические системы, оптика. Фильмы, которые нужны только одному проекту
курсов или докладов, живут в его собственном медиапроекте `media-<проект>`:
`media-talks` — доклады, `media-particlephysics`, `media-sciencepop`,
`media-stat-course`, `media-qft-lectures`, `media-albums` — видео фотоальбомов.
Фильм, который нужен нескольким проектам, остаётся в тематическом. Бюджет в
каталоге 900 МБ; заполненный проект продолжает `media-<проект>-2`.
`nh_media.py report` показывает заполнение. Новый медиапроект: строка в
`.neutrinohit/PROJECTS.md`, запись в `projects` каталога, затем первая
публикация (ниже).

## Адреса и версии

Запись каталога: `id` (сюжет), `variant`, `version`, `home`, `status`, SHA-256,
размер, длительность, кадр, кодек, звук, футер, `replaces` (какие копии она
заменяет) и подписи. Адрес фильма на сайте:

    /<home>/<id>/<variant>-v<version>.mp4        например /media-neutrino/star-in-jet/film-en-v1.mp4

Release: тег = `id`, файл = `<id>--<variant>--v<version>.mp4`.

- **Опубликованные байты не меняются.** Новый рендер — новая версия и новый адрес;
  `publish` никогда не перезаписывает файл Release.
- **Одинаковый SHA-256 — одна запись**, даже под разными именами; второй потребитель
  добавляется в `replaces`.
- **RU/EN, горизонтальный/вертикальный, разные сценарии — разные варианты.**
  Галерейные копии — `web-…` (облегчённые), полные фильмы для докладов — `film-…`.
- **Версия закрепляется у потребителя** (`media.lock.json`). `nh_media.py lock`
  сохраняет закреплённую версию и сообщает о более новой; переход — сознательная правка.
- **Удаление опубликованного** — только отдельным решением после проверки всех
  потребителей; автоматической чистки нет.

Статус: `prepared` — зарегистрирован и лежит в `.cache/media/<sha256>.mp4`;
`published` — проверен по адресу Pages. Страницы меняются только для `published`;
`NH_MEDIA_PREVIEW=1` включает `prepared` для локального предпросмотра.

## Новый ролик

1. Рендер готов, DN его посмотрел.
2. Регистрация (проверяет h264, faststart, футер; считает SHA-256; ищет дубликат):

   ```bash
   python3 scripts/nh_media.py prepare <файл.mp4> --id <сюжет> --variant <вариант> --home media-neutrino \
       [--replaces <путь копии на сайте>] [--replaces talks:<путь в докладе>] --title-ru "…" --title-en "…"
   python3 scripts/nh_media.py check
   python3 scripts/nh_media.py project media-neutrino        # обновить манифест медиапроекта
   ```
3. Публикация (DN): загрузка в Release, коммит манифеста, пуш —
   `python3 scripts/nh_media.py publish media-neutrino --yes`, затем в `media-neutrino`
   `git commit` + `git push`; Actions скачивает файлы, сверяет суммы и размер и публикует Pages.
4. Проверка и отметка: `python3 scripts/nh_media.py verify media-neutrino --full --mark`
   (диапазонные запросы начала и конца файла, тип `video/mp4`, полный SHA-256).
5. Потребители: галерея и QR — `python3 scripts/sync_dvnanima_gallery.py --render-only`
   и `python3 scripts/build_book_animations.py --skip-media`; лекции — `nh_media.py lock <репозиторий>`.
   Локальные копии убрать из git: `python3 scripts/nh_media.py replaced | xargs git rm -q --`.

Пока фильм не опубликован, страницы продолжают показывать прежние локальные копии;
неудачная публикация медиа не ломает сайт.

## Лекции и доклады

Расширение ставится в проект из канонической копии:
`python3 ../neutrinohit-map/scripts/nh_media.py extension .`. В `_quarto.yml`:

```yaml
project:
  post-render:
    - _extensions/neutrinohit-media/prune.py   # убирает из _site копии опубликованных фильмов
```

Вставка в слайд (атрибуты передаются в `<video>`; `true` — атрибут без значения):

```markdown
{{< nh-video star-in-jet variant="film-en" class="slide-video" controls=true muted=true preload="metadata" poster="media/jets/jet_star_en.jpg" >}}
```

Шорткод работает и внутри блока ` ```{=html} ` (карточки, сетки роликов): там
он выдаёт готовый тег `<video>`.

Фон слайда: `## Заголовок {background-video="nh:star-in-jet/film-en"}` при
`filters: [neutrinohit-media]`. Список фильмов проекта с закреплёнными версиями —
`media.lock.json`, его пишет `python3 ../neutrinohit-map/scripts/nh_media.py lock .`.
Пока фильм не опубликован, вставка даёт локальный файл (`fallback`).

## Офлайн-комплект

```bash
python3 _extensions/neutrinohit-media/media.py offline talk/lecture.html other/lecture.html \
    --out .work/offline-<имя> --cache ../neutrinohit-map/.cache/media \
    --mathjax ../neutrinohit-map/.cache/vendor/mathjax-2.7.9 [--download]
```

Папка содержит страницы, их ресурсы, `media/<sha256>.mp4` (один экземпляр на
фильм, даже если он в нескольких докладах), MathJax и `start.command` — двойной
щелчок запускает локальный сервер с поддержкой перемотки на http://127.0.0.1:8790/.
Статистика посещений из комплекта убирается; оставшиеся внешние адреса печатаются.
Комплекты пересобираются по запросу и в git и на сайт не попадают.

## Локальный предпросмотр всего сайта

```bash
NH_MEDIA_PREVIEW=1 python3 scripts/sync_dvnanima_gallery.py --render-only
NH_MEDIA_PREVIEW=1 python3 scripts/build_book_animations.py --skip-media
NH_MEDIA_PREVIEW=1 make site
(cd ../media-neutrino && make check)       # так же media-qft, media-mechanics
python3 scripts/media_preview_server.py    # http://127.0.0.1:8780/, сайты проектов — /<проект>/
```

После предпросмотра вернуть страницы: те же два генератора без `NH_MEDIA_PREVIEW`.

## Защита и проверки

- `nh_media.py guard-install <репозитории>` ставит локальный pre-commit: видеофайлы
  и файлы больше 25 МБ не попадают в коммит; сознательное исключение —
  `NH_ALLOW_VIDEO=1 git commit …`.
- `make site` карты убирает из `_site` копии опубликованных фильмов и папку `assets/media`.
- Общий CI печатает объём видео в публикуемом сайте и предупреждает выше 300 МБ;
  предел 1 ГБ по-прежнему останавливает публикацию.
- `nh_media.py check`: уникальность записей и SHA-256, бюджеты, кеш, отсутствие
  частных путей; `scripts/test_nh_media.py` — модульные тесты.

## Учёт всех фильмов

`python3 scripts/nh_media.py inventory` сводит все фильмы: кто их делает
(сцена dvnanima по SHA-256 или по имени; иначе `credit` записи), где они
используются (галерея, QR, страницы с `nh-video`), какие видеофайлы лежат в
опубликованных репозиториях вне медиатеки и какие рендеры dvnanima ещё не
зарегистрированы. `--json` даёт данные страницы «Фильмы» локальной доски
(сборщик nh-tasks), `--check` завершается ошибкой, если есть нарушения; их же
показывают `./nh check` и `./nh issues`. Нарушение — видеофайл в репозитории,
которого нет в каталоге, или копия опубликованного фильма. Сознательные
исключения (чужие фильмы с источником, исходники книги) перечислены в
`media.kept.json` шаблонами `проект:путь`. Новая анимация попадает на сайт
только через `prepare` → публикацию → `nh-video`; положить MP4 в `assets/`
нельзя: pre-commit отказывает, а проверка покажет файл.

## Первая публикация (один раз, DN)

Репозиторий медиапроекта создаётся локально генератором
(`python3 scripts/nh_media.py project <home>`). Так открыты `media-neutrino`,
`media-qft`, `media-mechanics` и `media-talks`; для нового медиапроекта:

```bash
cd ~/NeutrinoHit/<home>
git add -A && git commit -m "Shared films of NeutrinoHit: manifest, build and Pages workflow"
gh repo create NeutrinoHit/<home> --public --source . --push
cd ~/NeutrinoHit/neutrinohit-map && python3 scripts/nh_media.py publish <home> --yes
gh api -X POST repos/NeutrinoHit/<home>/pages -f build_type=workflow
gh workflow run publish-site.yml -R NeutrinoHit/<home>
gh run watch -R NeutrinoHit/<home>                                # дождаться зелёного запуска
```

Первый автоматический запуск после пуша завершится ошибкой (файлов в Releases ещё
нет, Pages не включены) — это ожидаемо; запуск через `gh workflow run` проходит.

Файлы `.github/workflows/` GitHub принимает только по SSH или с токеном, у которого
есть право `workflow` (`gh auth refresh -h github.com -s workflow`); токену с одним
`repo` пуш такого коммита отказан. Тогда workflow отправляется отдельным коммитом
позже, а Releases и включение Pages от него не зависят. `requirements.txt` в
медиапроекте нужен общему workflow для кеша pip, сборка обходится стандартной
библиотекой Python.
Затем:

```bash
cd ~/NeutrinoHit/neutrinohit-map
python3 scripts/nh_media.py verify <home> --full --mark          # для всех трёх
python3 scripts/sync_dvnanima_gallery.py --render-only
python3 scripts/build_book_animations.py --skip-media
python3 scripts/nh_media.py replaced | xargs git rm -q --
make site                                                       # около 0,46 ГБ вместо 1,18 ГБ
```

и обычный коммит карты (каталог, инструменты, страницы, удалённые копии).

## Что дальше

- Альбом Байкальской школы 2026 (3 видео, 133 МБ) — через ту же регистрацию, в своём медиапроекте.
- Курсы и доклады по одному: `neutrinophysics` переведён (лекции 01–15 и мини-курс
  осцилляций; книга с сайта снята, её ассеты и чужие ролики NASA остаются в
  репозитории); фильмы `talks` опубликованы, доклады переключает
  `talks/.work/finish-media-move.sh` (18 фильмов, нужных только докладам, перенесены
  из `media-neutrino` в `media-talks`); дальше `particlephysics` в своём
  `media-particlephysics`, затем остальные; в
  каждом — онлайн-версия, PDF и офлайн-комплект.
- PDF: генерируемые из исходников — собирать при сборке; исходные рисунки,
  дипломы и сторонние документы — по роли, без общего правила по расширению.
- Чистка старой истории git — последней, отдельным решением, в свежем клоне;
  TheBook не входит.
