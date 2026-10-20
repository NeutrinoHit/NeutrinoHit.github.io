# neutrinohit-map

Центральная карта NeutrinoHit на Quarto.

## Сборка и публикация

NeutrinoHit состоит из независимых Git-репозиториев. Каждый публикуемый
репозиторий собирается одной командой:

```bash
make site
```

Она должна создать полный сайт в `_site/`. GitHub Actions использует эту же
точку входа. Специфика сборки проекта должна находиться в его `Makefile` и
вызываемых им скриптах, а не дублироваться в workflow.

Для интерактивной работы используется `quarto preview` или специальная
preview-цель проекта. Перед push следует проверить `make site`.

Push в `main` автоматически публикует только сайт изменённого репозитория.
`workflow_dispatch` позволяет повторить публикацию вручную.

Общая логика публикации GitHub Pages находится в
`.github/workflows/publish-reusable.yml`. Дочерние репозитории вызывают её из
`.github/workflows/publish-site.yml`. Версия Quarto для публикации задаётся
только в reusable workflow.

Центральный сайт не собирает и не публикует сайты других репозиториев.

## Файлы сайта

`_site/` и другие воспроизводимые результаты сборки в Git не хранятся.

Готовый статический файл хранится в Git, если он является публичным материалом
сайта и не создаётся командой `make site`. Например, опубликованная PDF-лекция
является таким файлом.

## Курсы и страница «Образование»

Курсы описаны в `courses.catalog.yml`: разделы страницы «Образование», плитки,
лекции со ссылками на слайды, PDF, видео, задачи и главы книг. Страницы
`ru|en/education.qmd` и `ru|en/courses/<курс>.qmd` пишет генератор, их не правят
руками:

```bash
python scripts/build_course_pages.py          # записать страницы
python scripts/build_course_pages.py --check  # проверить, что страницы не устарели
```

Карточка программы Teach-in лежит в `_includes/education-program-ru.html` и
`-en.html`. Кнопка «← Курс» в слайдах курса ведёт на его страницу
`https://neutrinohit.github.io/<lang>/courses/<курс>.html`; такие адреса
зарегистрированы в `scripts/reveal_context_targets.json` с типом `course-page`.

## Научная коммуникация, наука, моделирование, интерактивы, школа и фото

Страницы-списки пишет `scripts/build_outreach_pages.py`, их не правят руками:
`outreach.catalog.yml` → `ru|en/outreach.qmd`, `cinema.qmd`, `interviews.qmd`;
`research.catalog.yml` → `ru|en/research.qmd`; `modeling.catalog.yml` → `ru|en/modeling.qmd`;
`interactives.catalog.yml` → `ru|en/interactives.qmd`; `school.catalog.yml` → `ru|en/school.qmd`;
`photos.catalog.yml` → `ru|en/photos.qmd`.
Строка — материал: название открывает его, рядом форматы. Группа может держать плитки
(эксперименты; галерея — плитка `gallery: <раздел>` или `gallery: all` берёт название, число сюжетов
и кадр из `animations.catalog.json`; альбом — плитка `album: <slug>` берёт обложку и число фото
из `albums/<slug>/album.json`; `count_of: <каталог>` считает его записи), команду установки пакета
(`install`, LightHit из PyPI) и, в «Школе», счётчики по видам работ, которые фильтруют список.
В «Интерактивы» входят только опубликованные публичные страницы (апплет или слайд с ним), отвечающие 200.
Подробная программа Байкальской школы 2026 — `ru|en/baikal-school-2026.qmd`; старые адреса
`ru|en/students.html` ведут на «Школу».

Логотип в шапке — `assets/site/neutrinohit-logo.png` (192 px), вырезан из логотипа QR-кодов
`assets/books/qr_center_logo_globe_bw.png`.
Векторный логотип и опись всех фирменных файлов (логотип, шрифты, цвета) —
`assets/brand/README.md`.

```bash
python scripts/build_outreach_pages.py          # записать страницы
python scripts/build_outreach_pages.py --check  # проверить, что страницы не устарели
```

Якоря докладов `#talk-georgia-2026` и `#talk-protvino-2026` на «Науке» — цели кнопки
«← Курс» слайдов (`scripts/reveal_context_targets.json`).

## Локальный preview всего сайта

`make site` собирает только центральный сайт. Для полного локального preview
workspace сначала собрать нужные дочерние репозитории через `make site`, затем
из `neutrinohit-map` выполнить:

```bash
make local-aggregate
```

Эта команда добавляет уже собранные сайты соседних проектов в `_site/<slug>/`:

- `talks/_site` -> `_site/talks`;
- `qft-lectures/_site` -> `_site/qft-lectures`;
- `gravity/_site` -> `_site/gravity`;
- `sciencepop/_site` -> `_site/sciencepop`;
- `neutrinophysics/_site` -> `_site/neutrinophysics`;
- `particlephysics/_site` -> `_site/particlephysics`;
- `stat-course/_site` -> `_site/statistical-analysis-course`.

На `localhost` скрипт `assets/local-preview-links.js` переписывает ссылки вида
`https://neutrinohit.github.io/...` в локальные `/...`, поэтому из preview можно
переходить по разделам так, как на опубликованном сайте.

`make local-aggregate` используется только для локального preview и не
участвует в GitHub Actions.

## CV

Профессиональные CV хранятся как обычные страницы сайта:

- `ru/cv.qmd` -> `ru/cv.html`;
- `en/cv.qmd` -> `en/cv.html`.

PDF-файлы `ru/cv.pdf` и `en/cv.pdf` публикуются как готовые статические
ресурсы. Обычная сборка сайта через `make site` не должна заново собирать PDF.

Если нужно обновить PDF после правки CV, собрать его вручную из
`neutrinohit-map`:

```bash
NEUTRINOHIT_SYNC_PROJECT_SITES=0 NEUTRINOHIT_VALIDATE_REVEAL_CONTEXTS=0 quarto render ru/cv.qmd --to pdf \
  -H ../assets/cv-pdf-compact.tex \
  -M pdf-engine:xelatex \
  -M papersize:a4 \
  -M mainfont:'PT Serif' \
  -M sansfont:'PT Serif' \
  -M monofont:Menlo \
  -M fontsize:9pt \
  -M geometry:top=14mm,bottom=14mm,left=16mm,right=16mm \
  -M colorlinks:true
cp _site/ru/cv.pdf ru/cv.pdf

NEUTRINOHIT_SYNC_PROJECT_SITES=0 NEUTRINOHIT_VALIDATE_REVEAL_CONTEXTS=0 quarto render en/cv.qmd --to pdf \
  -H ../assets/cv-pdf-compact.tex \
  -M pdf-engine:xelatex \
  -M papersize:a4 \
  -M mainfont:'PT Serif' \
  -M sansfont:'PT Serif' \
  -M monofont:Menlo \
  -M fontsize:9pt \
  -M geometry:top=14mm,bottom=14mm,left=16mm,right=16mm \
  -M colorlinks:true
cp _site/en/cv.pdf en/cv.pdf
```

`assets/cv-pdf-compact.tex` используется только для ручной PDF-сборки CV:
он уплотняет списки и заголовки в PDF и не влияет на HTML-страницы.
`NEUTRINOHIT_VALIDATE_REVEAL_CONTEXTS=0` отключает проверку RevealJS-контекстов
только в этом ручном PDF-сценарии, чтобы сборка CV не зависела от локальных
копий соседних курсов. Обычный `quarto render` запускается без этой переменной
и сохраняет проверку. Ручной PDF-рендер Quarto пишет результат в `_site`,
поэтому после него PDF нужно скопировать в исходные `ru/cv.pdf` и `en/cv.pdf`.
При следующем обычном `make site` эти готовые PDF будут скопированы в
`_site` как ресурсы.

## Фотоальбомы

Перед публикацией альбомов сжимать фото и обновлять превью:

```bash
python scripts/optimize_album_media.py
```

Скрипт пересобирает `albums/*/photos` как web-JPEG с длинной стороной до
2560 px, создает `albums/*/previews` до 1280 px и обновляет `album.json` и
`index.qmd`. Видео скрипт не пережимает.

## QR-коды

Общий генератор QR-кодов NeutrinoHit — `scripts/generate_qrcode.py`. По умолчанию
он делает код по стандарту книг (принят в TheBook 2026-10-10): скругленные модули,
коррекция ошибок `H`, тихий пояс 4 модуля, в центре логотип-глобус
`assets/books/qr_center_logo_globe_bw.png` на 0,32 стороны кода (у логотипа своё
кольцо, белый круг не нужен). При доле 0,40 и больше zbar читает код ненадёжно.
Выходной файл — `.png` или `.pdf`.

Один код:

```bash
python scripts/generate_qrcode.py \
  --url https://neutrinohit.github.io/sciencepop/BirthAndLifeUniverse/bbn-game/bbn_applet.html \
  --out assets/site/bbn_game_qr.png \
  --selfcheck
```

Все коды книги из каталога (`books.catalog.json` → `<book>.catalog.json`): по
файлу на каждую опубликованную запись, имя — её `qr_file`, адрес —
постоянная страница `/qr/<slug>/<id>/`:

```bash
python scripts/generate_qrcode.py --book neutrino-physics --out-dir <каталог> --fmt png --selfcheck
python scripts/generate_qrcode.py --book qft --out-dir <каталог>     # PDF, как в qr_file
```

`--fmt` заменяет расширение из `qr_file`; `--include-proposed` добавляет записи
со `status: "proposed"` (только для локальной проверки: у них нет страницы).
Другие скрипты (QR на слайды и апплеты в книгах) импортируют из генератора
`build_qr`, `build_robust_qr` и `save_image`, чтобы все коды выглядели одинаково.

Опция `--selfcheck` декодирует каждый код через `zbarimg` (если его нет — через
OpenCV) и сравнивает с адресом; в пакетном режиме ненайденный код даёт код
возврата 1.

Логотип 0,32 надёжен для коротких адресов `/qr/<slug>/<id>/` (версия QR до 6). У
длинного адреса (апплет, слайд, прямая ссылка на видео; версия 7 и выше) в центре
кода есть выравнивающий узор: логотип его закрывает, и zbar теряет код на части
масштабов. Опция `--robust` проверяет код через `zbarimg` на сторонах 200–1100 px
(не меньше 4 px на модуль и не больше 0,9 стороны файла) и при отказе берёт логотип
0,18, затем код без логотипа, с предупреждением. Проверено 2026-10-14: все коды
каталогов QFT и нейтринной книги проходят со стандартным логотипом. Длинным
адресам лучше дать страницу `/qr/`.

Если в окружении нет зависимости:

```bash
python -m pip install 'qrcode[pil]'
```

В печати под кодом стоит короткий адрес в две строки (хост / путь), код и адрес
кликабельны, кадр из фильма рядом с QR не печатается; блок «Отсканируйте» —
шириной в текст, код и подпись рядом. Для Quarto-книг это делает общий
Lua-фильтр `assets/books/neutrinohit-book.lua` (блоки `.animation` и
`.interactive` с атрибутами `url` и `qr`), для TheBook — `\dvnQRimage` в `dvn.sty`.

## Страницы анимаций из книги (QR)

QR-коды в книге «Квантовая теория поля для экспериментаторов и не только» ведут
на постоянные страницы `https://neutrinohit.github.io/qr/qft/<id>/` (четыре цифры;
номера сохранены из прежних коротких ссылок `dnaumov-qft-book-<id>`). Страница
двуязычная (RU/EN по языку браузера, переключатель сохраняется), воспроизводит
анимацию на телефоне, показывает автора, лицензию и место в книге. Список всех
анимаций книги: `/qr/qft/`, машинный индекс: `/qr/qft/manifest.json`; адреса всех книг и общая страница — в разделе «Несколько книг».

Источник правды — `book-animations.catalog.json`. Страницы, MP4 и постеры
получаются генератором, вручную их не править:

```bash
python scripts/build_book_animations.py          # media + qr/ + assets/book-animations/
python scripts/build_book_animations.py --check  # только проверка каталога
python scripts/build_book_animations.py --urls   # строки для pyplots/qrcodes/urls.txt в TheBook
```

Поле `hosting` у записи: `self` — анимация показывается на странице; `external` —
права не у нас, страница даёт ссылку на сайт автора; `pending` — страница
говорит, что анимация скоро появится; `link` — наш апплет, слайд лекции или интерактив
электронной книги в другом месте NeutrinoHit (`link.kind`, `link.url`), страница даёт кнопку
перехода, так что и такой QR-код короткий. Видео для `self` берётся либо из
`data/book-animations-src/` (`media.source`, кодируется в `assets/book-animations/`; каталог в git не входит,
исходники копируются туда из рендеров dvnanima и лекционных проектов),
либо прямо из галереи (`media.site_asset`, копий нет). Свои анимации лучше сначала
добавить в галерею (`animations.catalog.json`, `scripts/sync_dvnanima_gallery.py`),
а книжной записи дать `media.site_asset` и `gallery` (раздел/сюжет галереи): на странице
появится ссылка на сюжет в галерее. Страница `/qr/<slug>/<id>/` остаётся стабильным адресом
для печати, галерея — полной библиотекой. Репозиторий dvnanima закрытый: в каталогах нет ссылок
на его код (`credit.code_url`, `source_url`), `source_dir` галереи служит только для синхронизации;
оба генератора отклоняют такие ссылки. Страницы галереи `ru|en/animations.qmd` без пересборки
медиа обновляет `scripts/sync_dvnanima_gallery.py --render-only`. Английская страница берёт
`title_en`, `summary_en`, `description_en` и `label_en` из каталога; английская версия фильма —
ролик сразу после русской. Обложку с другого кадра (`poster_time` ролика в каталоге) пересобирает
`--posters-only --item <раздел>/<сюжет>` из опубликованного ролика, сам ролик не меняется.
Якоря `#<раздел>` и `#animation-<раздел>-<сюжет>` постоянные: на них ведут «Моделирование»
и QR-страницы книг.

Для обновления одного готового сюжета без замены медиа остальных анимаций:

```bash
pyenv exec python scripts/sync_dvnanima_gallery.py \
  --item neutrino-particles/cherenkov-radiation --copy-only --force
```

Карточки остальных сюжетов сохраняются. При замене версии существующей
анимации её gallery ID и напечатанные QR-адреса остаются прежними; подписи
обновляются в каталогах соответствующих книг.

Запись со `status: "proposed"` проверяется, но не публикуется (нет страницы, строки в
индексе и адреса для QR); для локального просмотра: `--include-proposed --out-dir <каталог>`,
рядом с которым `assets/` указывает на `assets/` сайта. Номер `id` после печати менять нельзя;
`legacy_codes` делают редирект со старого номера. Новая анимация — новая запись с новым `id` и `qr_file`.

QR-картинки книги QFT делает `TheBook/pyplots/qrcodes/make_qrcode.py`, проверяет —
`TheBook/pyplots/qrcodes/check_qrcodes.py` (декодирует PDF и открывает страницы,
в том числе на локальной сборке `--base http://127.0.0.1:8765`). Для остальных книг
те же коды даёт `scripts/generate_qrcode.py --book <slug>` (раздел «QR-коды»).

### Несколько книг

Книги (QFT, введение в физику нейтрино, статистический анализ, ФЭЧ, гравитация, численные методы) зарегистрированы в
`books.catalog.json`: `slug`, название, файл каталога, адрес страниц, каталог постеров, `status` (`published` — собирается;
`planned` — заготовка без анимаций). Единая схема адресов для всех книг:

| что | адрес | где лежит |
|---|---|---|
| страница анимации | `/qr/<slug>/<id>/` | `qr/<slug>/<id>/index.html` (генератор) |
| список анимаций книги | `/qr/<slug>/` | `qr/<slug>/index.html` |
| манифест книги | `/qr/<slug>/manifest.json` | то же |
| видео и постеры | `/assets/book-animations/<slug>/<id>.mp4`, `.jpg` | либо `media.site_asset` (видео уже на сайте) |
| все книги | `/qr/`, `/qr/books.json` | `qr/index.html` |

Примеры: `/qr/qft/0017/`, `/qr/neutrino-physics/0014/`, `/qr/particle-physics/0021/`, `/qr/gravity/0001/`. Номера `id` (четыре
цифры) уникальны внутри книги. Адресов вида `/qr/<id>/` больше нет: QR-коды всех книг печатаются с адресом `/qr/<slug>/<id>/`.

Запись каталога книги без томов (`book` без `volume`/`chapter`) группируется по разделам: `book.order` и
`book.section_title` (`ru`, `en`); у печатной книги остаются `volume`, `chapter`, `chapter_title`. Если анимация уже
опубликована в другой книге, запись повторяет её: тот же `media.site_asset` (копии видео нет), подпись, `credit` и `gallery`;
новая лекционная анимация кладётся в `data/book-animations-src/<slug>/` и описывается через `media.source`.

Новая книга или новая запись:

```bash
python scripts/build_book_animations.py --book <slug>            # одна книга
python scripts/build_book_animations.py --book <slug> --urls     # строки "url, файл QR" для urls.txt книги
python scripts/build_book_animations.py                          # все книги и общая страница /qr/
python ../TheBook/pyplots/qrcodes/make_previews.py --book <slug> <id> ...     # превью для печати
```

Для новой книги достаточно перевести `status` в `published` и заполнить `books/<slug>.catalog.json` (шаблон записей: `books/README.md`).
Названия книг в реестре предварительные: проверить английские названия и страницы книг (`book.page`).

### Формулы в подписях

В `caption` и `credit.note` формулы пишутся в LaTeX между `$...$` (KaTeX подгружается на странице автоматически, только если
в тексте есть `$`). В заголовках `title` формул нет. Знак `<` внутри формулы допустим (экранируется генератором);
`\bm` в KaTeX нет, пользуйтесь `\mathbf`.

## Общие RevealJS-классы для лекций

Канонический общий стиль для RevealJS-лекций хранится здесь:

```text
assets/reveal/neutrinohit-reveal.scss
```

Локальные копии лежат в проектах: `<repo>/shared/reveal/` (футер, подписи
к видео, CSS викторин, логотип) и `<repo>/shared/styles/neutrinohit-reveal.scss`.
Потребители: talks, qft-lectures, gravity, sciencepop, stat-course,
neutrinophysics, particlephysics, numerical_methods, rte_lectures; полный
список с путями — `python scripts/sync_reveal_assets.py --list`.

Проверка расхождений (ничего не пишет, код выхода 1 при расхождении):

```bash
python scripts/sync_reveal_assets.py --check --all
python scripts/sync_reveal_assets.py --check --target talks --diff
make check-shared-assets
```

Обновление копий — только с явными адресатами:

```bash
python scripts/sync_reveal_assets.py --target talks --target gravity
python scripts/sync_reveal_assets.py --all
```

Скрипт не перезаписывает файл, у которого в репозитории-потребителе есть
незакоммиченные изменения (изменён, в индексе или не отслеживается), и не
трогает копии, помеченные как удерживаемые (`held`: потребитель сначала должен
перенести локальные правила); и то и другое снимается флагом `--force`.
Совпадающие файлы не переписываются. Без `--target`/`--all` скрипт, как и
раньше, обновляет исходный набор: Reveal-файлы в talks, qft-lectures, gravity,
sciencepop, stat-course, neutrinophysics, particlephysics и SCSS в talks,
qft-lectures, gravity, neutrinophysics, particlephysics.

## Общий стиль книг

Каноническая основа оформления Quarto-книг хранится в трёх файлах:

```text
assets/books/neutrinohit-book.css
assets/books/neutrinohit-book.tex
assets/books/neutrinohit-book.lua
```

Там же лежат общие фильтры:

- `hide-book-index.lua` убирает заголовок первого уровня на главной странице
  книги, если он повторяет название. Название берётся из
  `hide-book-index-title`, иначе из `book.title`, иначе из `title`. Режим
  задаётся ключом `hide-book-index`: `combined` (по умолчанию, только PDF/LaTeX
  и EPUB), `all` (все форматы, включая HTML) или `false`.
- `chapter-bibliographies.lua` запускает citeproc отдельно для каждой главы,
  чтобы у каждой главы был свой список литературы.

CSS задаёт общую типографику HTML и EPUB, ритм страницы, навигацию, таблицы
и базовую палитру. TeX задаёт те же шрифты и цвета для PDF. Lua-фильтр
определяет общие для всех форматов блоки: биографии, медиа, подписи упражнений
и заставки глав в PDF. Правила,
относящиеся к предмету конкретной книги, остаются в её локальных стилях:
например, тематическая навигация и биографии во «Введении в физику
нейтрино» или интерактивные статистические апплеты в курсе анализа данных.

После изменения общей основы синхронизировать локальные копии:

```bash
python scripts/sync_book_assets.py --check --all
python scripts/sync_book_assets.py --target stat-course
```

Скрипт кладёт CSS внутрь `assets/styles` каждой книги, чтобы Quarto включал его
в HTML и EPUB, Lua-фильтры — в `assets/filters`, а TeX-основу — в `shared/latex`
проектов-потребителей: stat-course, neutrinophysics, gravity, numerical_methods
(`--list` показывает пути). Ключи `--check`, `--diff`, `--force` и защита
незакоммиченных изменений работают так же, как у `sync_reveal_assets.py`.
`make sync-book-assets` (без адресатов) по-прежнему обновляет CSS, TeX и
`neutrinohit-book.lua` в stat-course и neutrinophysics.

### Серия обложек

Канонические SVG-исходники обложек пяти книг и их воспроизводимый генератор
хранятся в `assets/books/covers/`. Серия включает лицевые и задние стороны,
отдельные научные иллюстрации, обзорный лист и параметрические макеты разворота
с временным корешком. Рабочие версии статистической и нейтринной книг находятся в `svg/v2/`;
на их лицевых сторонах нет нумерации и брендинга, а верхняя зона оставлена под будущие логотипы партнёров.

```bash
make book-covers
make check-book-covers
```

Подробности о структуре, физическом содержании и производственных ограничениях
см. в `assets/books/covers/README.md` и `assets/books/covers/docs/AUDIT.md`.

Правило: если настройка нужна больше чем в одной лекции или потенциально
повторится в другом проекте, она должна быть классом или CSS-переменной в
`neutrinohit-map/assets/reveal/neutrinohit-reveal.scss`. CSS конкретной лекции
используется только для уникальных сцен, апплетов и специальных слайдов.

### Текстовые утилиты

```markdown
::: {.compact}
- Smaller vertical gaps between list items.
- Useful for dense summary slides.
:::
```

- `.compact` уменьшает вертикальные отступы между пунктами списка.
- `.small` делает блок примерно `0.76em`.
- `.tiny` делает блок примерно `0.62em`.
- `.muted` задает приглушенный цвет текста.
- `.question` выделяет вопрос голубым и жирным.
- `.takeaway` выделяет ключевой вывод теплым цветом и жирным.

Пример:

```markdown
::: {.takeaway}
The sign of the charge product changes the interference pattern.
:::
```

Настраиваемые акценты (оттенок, размер, выравнивание и насыщенность задаются
атрибутами независимо):

```markdown
::: {.nh-box tone="success" size="lg" align="center" weight="bold"}
Boxed statement with a coloured left rule.
:::

::: {.nh-text tone="muted" size="sm"}
Plain coloured text.
:::

::: {.nh-statement size="xxl" weight="bold"}
One centred statement on an otherwise empty slide.
:::
```

- `tone`: `question`, `success`, `warning`, `danger`, `muted` (у `.nh-text`
  ещё `accent`); `size`: `sm`, `md`, `lg`, `xl`, `xxl`; `align`: `center`,
  `right`; `weight`: `bold`. Работают и формы `data-tone` и т. п.
- `{.panel-tabset .nh-story-tabs}` удерживает размер шрифта вкладок: Quarto
  копирует классы набора вкладок на внутренний `.tab-content`, и размер,
  заданный классу, иначе применяется дважды.

### Тайминг

Для слайдов с планом лекции или расписанием:

```markdown
::: {.timing}
<span class="time">00:00</span><span>Introduction</span>
<span class="time">12:00</span><span>Main idea</span>
<span class="time">35:00</span><span>Examples</span>
:::
```

`.timing` задает двухколоночную сетку, `.time` выделяет левую колонку со
временем.

### Подписи к медиа

```markdown
::: {.media-caption}
Particle-particle configuration: \(Q_1Q_2>0\).
:::
```

`.media-caption` задает компактную серую подпись под видео, рисунком или
апплетом.

### Изображения

Простой центрированный рисунок:

```markdown
![](media/picture.png){.slide-image-center .nostretch width=80% fig-align="center"}
```

- `.slide-image-center` центрирует картинку.
- `.nostretch` полезен для Quarto RevealJS: он запрещает автоматическое
  растягивание картинки в `r-stretch`.
- `width=...` остается обычным Quarto-параметром и должен работать, когда
  картинка не растянута RevealJS автоматически.

Для более управляемого центрирования использовать `.centered-figure`:

```markdown
::: {.centered-figure style="--figure-width: 72%; --figure-max-height: 68vh;"}
![](media/picture.png)
:::
```

Переменные:

- `--figure-width`: ширина рисунка, по умолчанию `80%`;
- `--figure-max-height`: максимальная высота, по умолчанию `72vh`.

Чтобы на первом шаге показать только часть картинки, а по следующему клику
раскрыть ее целиком, использовать обычный Reveal fragment с классом
`.image-uncover`:

```markdown
![](media/picture.png){.fragment .image-uncover .from-left style="--uncover-amount: 42%; --uncover-width: 90%;"}
```

Направление начального фрагмента задается классом:

- `.from-left`: сначала видна левая часть;
- `.from-right`: сначала видна правая часть;
- `.from-top`: сначала видна верхняя часть;
- `.from-bottom`: сначала видна нижняя часть.

Переменные:

- `--uncover-amount`: доля картинки, видимая до клика, по умолчанию `50%`;
- `--uncover-width`: ширина картинки, по умолчанию `100%`;
- `--uncover-max-width`: максимальная ширина, по умолчанию `100%`;
- `--uncover-max-height`: максимальная высота, по умолчанию `72vh`;
- `--uncover-duration`: длительность раскрытия, по умолчанию `0.35s`.

### Видео и произвольные медиа

Базовый класс для видео:

```html
<video class="slide-video" data-autoplay loop muted playsinline controls>
  <source src="media/movie.mp4" type="video/mp4">
</video>
```

По умолчанию:

```css
--media-width: 100%;
--media-max-width: 100%;
--media-max-height: 560px;
--media-margin: 0 auto;
```

Готовые классы высоты:

- `.media-height-sm`: `448px`;
- `.media-height-md`: `560px`;
- `.media-height-lg`: `672px`;
- `.media-height-xl`: `784px`.

Например, увеличить стандартное видео на 20%:

```html
<video class="slide-video media-height-lg" data-autoplay loop muted playsinline controls>
  <source src="media/movie.mp4" type="video/mp4">
</video>
```

Готовые классы ширины:

- `.media-width-sm`: `60%`;
- `.media-width-md`: `75%`;
- `.media-width-lg`: `90%`;
- `.media-width-full`: `100%`.

Можно задавать точные параметры прямо на элементе:

```html
<video
  class="slide-video"
  style="--media-width: 92%; --media-max-height: 616px;"
  data-autoplay loop muted playsinline controls>
  <source src="media/movie.mp4" type="video/mp4">
</video>
```

Для произвольного HTML/SVG/canvas-медиа использовать `.slide-media` и те же
переменные:

```html
<svg class="slide-media media-width-lg" style="--media-max-height: 70vh;">
  ...
</svg>
```

### Sticky notes

Короткие пояснения на слайде можно оформлять как желтые заметки:

```markdown
::: {.marginnote .absolute top=190 left=1160 width=330}
<span class="note-title">Key point</span>
The field shifts the wave; the wave sources the field.
:::
```

Позиционирование лучше делать штатным механизмом Quarto RevealJS:
`.absolute top=... left=... width=...`. Если `.absolute` не указан, заметка ставится абсолютно в правый
верхний угол текущего слайда, а положение можно менять CSS-переменными:

```markdown
::: {.marginnote style="--note-top: 6rem; --note-right: 2rem; --note-width: 14rem; --note-font-size: 0.7em;"}
Short explanation.
:::
```

По умолчанию sticky note использует:

```css
--note-font-size: 0.68em;
--note-math-font-size: 1.04em;
```

Для всей лекции эти значения можно задать один раз в CSS-файле конкретной
лекции:

```css
.reveal {
  --note-font-size: 0.72em;
  --note-title-font-size: 1.1em;
  --note-math-font-size: 1.08em;
}
```

Для одного слайда размеры можно задать прямо в заголовке слайда:

```markdown
## Equations of Motion {style="--note-font-size: 0.72em; --note-math-font-size: 1.08em;"}
```

Локальные параметры на самой заметке имеют наивысший приоритет. Полезные
переменные:

- `--note-width`: ширина заметки, если не используется Quarto `width=...`;
- `--note-padding`: внутренние поля;
- `--note-top`, `--note-right`, `--note-left`: положение без `.absolute`;
- `--note-rotate`: небольшой поворот, например `-1deg` или `1deg`;
- `--note-font-size`: основной текст;
- `--note-title-font-size`: заголовок `.note-title`;
- `--note-math-font-size`: display math внутри заметки;
- `--note-bg`, `--note-bg-2`: верхний и нижний желтый цвет фона;
- `--note-color`: цвет текста;
- `--note-pin-color`: цвет маленькой верхней полоски;
- `--note-shadow`: тень всей заметки.

Пример локальной настройки:

```markdown
::: {.marginnote .absolute top=120 left=1180 width=360 style="--note-font-size: 0.72em;"}
<span class="note-title">Euler-Lagrange equations</span>
$$
\frac{\partial \mathcal L}{\partial \varphi}
=
\partial_\mu
\frac{\partial\mathcal L}{\partial\partial_\mu\varphi}
$$
:::
```

Варианты: `.note-sm`, `.note-lg`, `.note-flat`, `.note-right`.

### Номера слайдов

Общий стиль переносит номер слайда в правый верхний угол. Это управляется
самим `neutrinohit-reveal.scss`; отдельный класс в слайде добавлять не нужно.

### Математика и `\mathcal`

RevealJS-презентации используют MathJax 2, который Quarto подключает по
умолчанию: плагин math.js в шаблоне RevealJS вызывает API MathJax 2
(`MathJax.Hub`). Поэтому `html-math-method` в metadata слайдов не задавать.
Строка `html-math-method: mathjax` подставляет адрес MathJax 3 из pandoc;
формулы при этом набираются, но плагин падает в консоли с ошибкой
`Cannot read properties of undefined (reading 'Config')`. Если адрес нужно
указать явно, то только MathJax 2:

```yaml
format:
  revealjs:
    html-math-method:
      method: mathjax
      url: https://cdn.jsdelivr.net/npm/mathjax@2.7.9/MathJax.js
```

Общий footer script `assets/reveal/neutrinohit-reveal-footer.js` после
инициализации RevealJS задаёт MathJax2 renderer `CommonHTML` (решение
2026-10-16): формулы выглядят как прежде с MathJax 3 и не бледнеют на тёмном
фоне; `\mathcal` и `\mathbb` проверены. `SVG` (тоньше, не зависит от
web-fonts) выбирается для отдельной презентации атрибутом
`data-mathjax-renderer="SVG"`. Он же набирает формулы в заголовках меню
слайдов: плагин MathJax2 обрабатывает только сами слайды.

Скрипты слайдов, которые вставляют TeX динамически, вызывают
`MathJax.Hub.Queue(["Typeset", MathJax.Hub, element])`; API MathJax 3
(`MathJax.typesetPromise`) в RevealJS-презентациях недоступен.

Все презентации с этим footer обязаны задавать контекстную кнопку возврата:

```html
<script data-external="1" data-context-home="https://neutrinohit.github.io/ru/education.html#qft" data-context-home-label="Карта курса КТП" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

Правило добавления нового материала:

1. Добавить устойчивый `id` на карточку или вложенный материал в `ru/*.qmd` и/или `en/*.qmd`.
2. Добавить абсолютный URL `https://neutrinohit.github.io/...#id` в `scripts/reveal_context_targets.json`.
3. В metadata слайдов указать и `data-context-home`, и `data-context-home-label`.

Для полноценных автономных курсов можно регистрировать не только якорь карты,
но и `course-home` URL вида `https://neutrinohit.github.io/<course>/`.
Письменный стандарт: `docs/course-site-standard.md`.

После `quarto render` скрипт `scripts/validate_reveal_context_homes.py` проверяет
все footer-вставки в карте сайта и соседних проектах. Сборка падает, если
context-home отсутствует, ведёт на локальную страницу вроде `index.html`, не
зарегистрирован или указывает на несуществующий якорь.

По умолчанию footer включает renderer `CommonHTML`; другой renderer задаётся
атрибутом, например `data-mathjax-renderer="SVG"`:

```html
<script data-external="1" data-context-home="https://neutrinohit.github.io/ru/education.html#qft" data-context-home-label="Карта курса КТП" data-mathjax-renderer="SVG" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

Если нужно оставить renderer самого MathJax на отдельной презентации:

```html
<script data-external="1" data-context-home="https://neutrinohit.github.io/ru/education.html#qft" data-context-home-label="Карта курса КТП" data-mathjax-renderer="default" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

## Фотоальбомы

Интерфейс сборки альбома: `photo-studio.qmd`. Это внутренняя страница, она исключена из обычного `quarto render` и не должна публиковаться на сайте.

Типовой поток:

1. Запустить локальный предпросмотр внутренней Studio:

```bash
quarto preview photo-studio.qmd --port 4201 --no-browser
```

2. Открыть `http://localhost:4201/`.
3. Выбрать фотографии и видео, заполнить метаданные, текст поста, порядок, подписи и alt-тексты.
4. Нажать `Сохранить папку` и выбрать `neutrinohit-map/albums`.
5. Получить `albums/<slug>/album.json`, `index.qmd`, `telegram-queue.json`, `social-posts.md`, `photos/`, `videos/` и `previews/`.

Чтобы редактировать существующий альбом, в Studio нажать `Открыть папку` и выбрать папку конкретного альбома, например `neutrinohit-map/albums/10-17-may-2026`. Studio прочитает `album.json` и загрузит медиафайлы. После этого `Сохранить папку` обновляет эту же папку.

Для фотографий Studio создает уменьшенные JPEG-превью в `previews/`. Страница альбома загружает превью, а lightbox открывает оригинал из `photos/`. Видео остаются в `videos/` и публикуются в Telegram как `sendVideo` или как элементы `sendMediaGroup`.

Поле `Текст поста` хранится в `album.json` как `postText`, выводится на странице альбома над галереей и используется как текст Telegram-поста.

Публикация в Telegram:

```bash
export TELEGRAM_BOT_TOKEN="..."
python neutrinohit-map/scripts/publish_album.py neutrinohit-map/albums/<slug>/album.json --chat @your_channel
python neutrinohit-map/scripts/publish_album.py neutrinohit-map/albums/<slug>/album.json --chat @your_channel --send
```

Первая команда делает dry-run, вторая отправляет посты в канал.
