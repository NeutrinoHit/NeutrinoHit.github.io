# neutrinohit-map

Центральная карта NeutrinoHit на Quarto.

Публикация сайта настроена через GitHub Actions: push в `main` рендерит Quarto и обновляет ветку `gh-pages`, из которой GitHub Pages отдаёт сайт.

## Миграция структуры сайта

Рабочий аудит для перехода к крупным разделам, равноправным RU/EN версиям и
общей дизайн-системе хранится в
[`docs/site-migration-audit.md`](docs/site-migration-audit.md).

## Локальный preview всего сайта

Корневой сайт можно смотреть из `neutrinohit-map`:

```bash
quarto preview
```

После рендера локальный post-render скрипт `scripts/sync_local_project_sites.py`
копирует уже собранные сайты соседних проектов в `_site/<slug>/`:

- `talks/_site` -> `_site/talks`;
- `qft-lectures/_site` -> `_site/qft-lectures`;
- `sciencepop/_site` -> `_site/sciencepop`;
- `neutrinophysics/_site` -> `_site/neutrinophysics`;
- `particlephysics/_site` -> `_site/particlephysics`;
- `stat-course/pages` -> `_site/statistical-analysis-course`.

На `localhost` скрипт `assets/local-preview-links.js` переписывает ссылки вида
`https://neutrinohit.github.io/...` в локальные `/...`, поэтому из preview можно
переходить по разделам так, как на опубликованном сайте.

В GitHub Actions этот локальный compose автоматически пропускается по
`GITHUB_ACTIONS=true`: корневой сайт публикует только карту NeutrinoHit, а
отдельные проекты публикуют свои Pages самостоятельно.

Если нужно отключить локальное копирование подпроектов:

```bash
NEUTRINOHIT_SYNC_PROJECT_SITES=0 quarto preview
```

## QR-коды с логотипом

Общий генератор QR-кодов с логотипом NeutrinoHit:

```bash
python scripts/generate_qrcode.py \
  --url https://neutrinohit.github.io/sciencepop/BirthAndLifeUniverse/bbn-game/bbn_applet.html \
  --out assets/site/bbn_game_qr.png \
  --selfcheck
```

По умолчанию скрипт использует `assets/reveal/dvnlogo.png`, высокий уровень
коррекции ошибок `H`, скругленные модули и белый круг под логотипом. Выходной
файл должен иметь расширение `.png` или `.pdf`.

Если в окружении нет зависимости:

```bash
python -m pip install 'qrcode[pil]'
```

Опция `--selfcheck` пытается декодировать результат через OpenCV, если он
установлен. Если OpenCV нет, QR всё равно сохраняется.

## Общие RevealJS-классы для лекций

Канонический общий стиль для RevealJS-лекций хранится здесь:

```text
assets/reveal/neutrinohit-reveal.scss
```

Локальные копии лежат в проектах, например:

```text
qft-lectures/shared/styles/neutrinohit-reveal.scss
particlephysics/shared/styles/neutrinohit-reveal.scss
neutrinophysics/shared/styles/neutrinohit-reveal.scss
```

После изменения общего стиля запускать из `neutrinohit-map`:

```bash
python scripts/sync_reveal_assets.py
```

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

Для RevealJS-презентаций использовать MathJax:

```yaml
format:
  revealjs:
    html-math-method: mathjax
```

Общий footer script `assets/reveal/neutrinohit-reveal-footer.js` после
инициализации RevealJS переключает MathJax2 на SVG renderer. Это сделано
системно, чтобы команды вроде `\mathcal`, `\mathbb`, `\mathfrak` не зависели от
загрузки web-fonts в браузере.

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

По умолчанию MathJax fallback включен автоматически; явно это выглядит так же,
как обычная footer-вставка, но с `data-mathjax-renderer="SVG"`:

```html
<script data-external="1" data-context-home="https://neutrinohit.github.io/ru/education.html#qft" data-context-home-label="Карта курса КТП" data-mathjax-renderer="SVG" src="shared/reveal/neutrinohit-reveal-footer.js"></script>
```

Если нужно отключить этот fallback на отдельной презентации:

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
3. Выбрать фотографии, заполнить метаданные, текст поста, порядок, подписи и alt-тексты.
4. Нажать `Сохранить папку` и выбрать `neutrinohit-map/albums`.
5. Получить `albums/<slug>/album.json`, `index.qmd`, `telegram-queue.json`, `social-posts.md` и `photos/`.

Чтобы редактировать существующий альбом, в Studio нажать `Открыть папку` и выбрать папку конкретного альбома, например `neutrinohit-map/albums/10-17-may-2026`. Studio прочитает `album.json` и загрузит фото. После этого `Сохранить папку` обновляет эту же папку.

Поле `Текст поста` хранится в `album.json` как `postText`, выводится на странице альбома над галереей и используется как текст Telegram-поста.

Публикация в Telegram:

```bash
export TELEGRAM_BOT_TOKEN="..."
python neutrinohit-map/scripts/publish_album.py neutrinohit-map/albums/<slug>/album.json --chat @your_channel
python neutrinohit-map/scripts/publish_album.py neutrinohit-map/albums/<slug>/album.json --chat @your_channel --send
```

Первая команда делает dry-run, вторая отправляет посты в канал.
