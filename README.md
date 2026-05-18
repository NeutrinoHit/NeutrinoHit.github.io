# neutrinohit-map

Центральная карта NeutrinoHit на Quarto.

Публикация сайта настроена через GitHub Actions: push в `main` рендерит Quarto и обновляет ветку `gh-pages`, из которой GitHub Pages отдаёт сайт.

## Фотоальбомы

Интерфейс сборки альбома: `photo-studio.qmd`. Это внутренняя страница, она исключена из обычного `quarto render` и не должна публиковаться на сайте.

Типовой поток:

1. Запустить локальный предпросмотр внутренней Studio:

```bash
quarto preview photo-studio.qmd --port 4201 --no-browser
```

2. Открыть `http://localhost:4201/`.
3. Выбрать фотографии, заполнить метаданные, порядок, подписи и alt-тексты.
4. Нажать `Сохранить папку` и выбрать `neutrinohit-map/albums`.
5. Получить `albums/<slug>/album.json`, `index.qmd`, `telegram-queue.json`, `social-posts.md` и `photos/`.

Чтобы редактировать существующий альбом, в Studio нажать `Открыть папку` и выбрать папку конкретного альбома, например `neutrinohit-map/albums/10-17-may-2026`. Studio прочитает `album.json` и загрузит фото. После этого `Сохранить папку` обновляет эту же папку.

Публикация в Telegram:

```bash
export TELEGRAM_BOT_TOKEN="..."
python neutrinohit-map/scripts/publish_album.py neutrinohit-map/albums/<slug>/album.json --chat @your_channel
python neutrinohit-map/scripts/publish_album.py neutrinohit-map/albums/<slug>/album.json --chat @your_channel --send
```

Первая команда делает dry-run, вторая отправляет посты в канал.
