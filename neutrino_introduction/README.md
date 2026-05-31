# Введение в физику нейтрино

В папке хранятся опубликованные лекции вводного курса:

- HTML-экспорты из Keynote лежат в отдельных подпапках с `index.html`;
- новые лекции Quarto можно добавлять непосредственно как `.qmd`-файлы;
- общие настройки будущих Quarto-слайдов находятся в `_metadata.yml`.

Для новой лекции Quarto достаточно создать файл, например
`neutrino-interactions.qmd`, и выполнить из корня репозитория:

```bash
quarto render
```

Страница лекции будет опубликована по адресу
`https://neutrinohit.github.io/neutrino_introduction/neutrino-interactions.html`.
