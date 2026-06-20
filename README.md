# neutrinohit-map

Центральная карта NeutrinoHit на Quarto.

Публикация сайта настроена через GitHub Actions: push в `main` рендерит Quarto и обновляет ветку `gh-pages`, из которой GitHub Pages отдаёт сайт.

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
