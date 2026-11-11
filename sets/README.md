# Наборы для Game Remote / Sets for Game Remote

[Русский](#русский) · [English](#english)

## Русский

Здесь собираются наборы кнопок для игр. Набор — это папка с описанием кнопок и картинками; Game Remote импортирует его как игру. Образец — набор Star Citizen, который идёт с программой: [`src/game_remote/samples/star-citizen`](../src/game_remote/samples/star-citizen).

### Как взять набор

Готовые файлы наборов лежат на странице [Sets / Наборы](https://github.com/godsfear/game-remote/releases/tag/sets). Скачайте zip нужной игры и нажмите «Импортировать набор» в редакторе Game Remote на ПК. Файлы на этой странице обновляются сами, когда в каталоге появляется или меняется набор.

Набор нажимает клавиши, которые стоят в игре по умолчанию. Если вы их переназначили, поправьте кнопки в редакторе после импорта.

### Как добавить набор

1. Соберите игру в редакторе Game Remote и проверьте кнопки в самой игре.
2. Нажмите «Экспортировать набор» и укажите язык подписей.
3. Распакуйте zip в новую папку здесь. Имя папки — маленькие латинские буквы, цифры и `-`, например `sets/elite-dangerous`. Оно станет именем файла набора.
4. По желанию добавьте переводы и файл `README.md` с пояснениями (см. ниже).
5. Проверьте набор: `python tools/build_sets.py`. Перед этим один раз выполните `python -m pip install -e .` в корне репозитория.
6. Откройте pull request.

### Что лежит в папке набора

| Файл | Зачем |
| --- | --- |
| `panel.json` | Кнопки, экраны и клавиши. Обязательно с языком подписей: `"language": "en"` |
| `panel.ru.json` и другие | Переводы, по файлу на язык. Необязательно. Формат описан в [руководстве](../docs/guide.md#переводы-в-наборе) |
| картинки | Только те, что набор показывает: обложка, фон, картинки кнопок |
| `README.md` | Ваши пояснения: откуда картинки, для какой версии игры клавиши. Необязательно, в файл набора не попадает |

Других файлов в папке быть не должно.

### Клавиши

- Ставьте клавиши, которые назначены в игре по умолчанию. Если набор рассчитан на другую раскладку, напишите об этом в `README.md` набора.
- Набор нажимает только клавиши и сочетания, которые видны в редакторе. Макросов и скриптов в нём нет.
- Привязку к окну игры (`"window": "Game.exe"`) указывайте, если знаете имя exe: тогда нажатия не попадут в другую программу.

### Картинки

- Присылайте картинки, которые сделали сами или которые разрешено распространять. Источник и лицензию укажите в `README.md` набора.
- Логотипы, иконки и кадры из игры — только если правила издателя разрешают использовать их в фанатских материалах. Дайте ссылку на эти правила.
- Картинка — PNG, JPEG или WebP до 2 МБ. Редактор сам уменьшает картинки кнопок при загрузке, так что экспортированный набор уже подходит.

### Что проверяется автоматически

При каждом pull request тесты запускают `tools/build_sets.py`. Набор проходит, если программа сама импортирует его на каждом его языке. Это значит:

- `panel.json` верный, и в нём указан язык;
- все картинки на месте и действительно картинки;
- переводы ссылаются на существующие кнопки и называют все экраны;
- в папке нет лишних файлов, а её имя подходит.

Сообщение об ошибке называет набор и файл, в котором проблема.

## English

Sets of buttons for games are collected here. A set is a folder with the description of the buttons and the pictures; Game Remote imports it as a game. The example is the Star Citizen set that ships with the program: [`src/game_remote/samples/star-citizen`](../src/game_remote/samples/star-citizen).

### How to get a set

The files of the sets are on the page [Sets / Наборы](https://github.com/godsfear/game-remote/releases/tag/sets). Download the zip of your game and press "Import a set" in the editor of Game Remote on the PC. The files on that page are updated by themselves when a set is added to the catalogue or changed.

A set presses the keys the game has by default. If you changed them in the game, change the buttons in the editor after the import.

### How to add a set

1. Build the game in the editor of Game Remote and try the buttons in the game itself.
2. Press "Export as a set" and say the language of the labels.
3. Unpack the zip into a new folder here. Name the folder with small Latin letters, digits and `-`, for example `sets/elite-dangerous`. It becomes the name of the set's file.
4. Add translations and a `README.md` with notes if you like (see below).
5. Check the set: `python tools/build_sets.py`. Before that, run `python -m pip install -e .` once in the root of the repository.
6. Open a pull request.

### What the folder of a set holds

| File | What for |
| --- | --- |
| `panel.json` | The buttons, the screens and the keys. It must say the language of the labels: `"language": "en"` |
| `panel.ru.json` and others | Translations, one file per language. Optional. The [guide](../docs/guide.md#переводы-в-наборе) describes the format (in Russian) |
| pictures | Only those the set shows: the cover, the background, the pictures of the buttons |
| `README.md` | Your notes: where the pictures come from, which version of the game the keys are for. Optional; it does not go into the file of the set |

The folder holds no other files.

### Keys

- Use the keys the game has by default. If the set is made for another layout, say so in the `README.md` of the set.
- A set presses only the keys and shortcuts that the editor shows. It has no macros and no scripts.
- Bind the set to the game's window (`"window": "Game.exe"`) if you know the name of the exe: then a press never lands in another program.

### Pictures

- Send pictures you made yourself or that may be distributed. Name the source and the licence in the `README.md` of the set.
- Logos, icons and screenshots of a game only if the publisher's rules allow them in fan-made material. Link to those rules.
- A picture is a PNG, JPEG or WebP of up to 2 MB. The editor shrinks the pictures of buttons when they are uploaded, so an exported set already fits.

### What is checked automatically

On every pull request the tests run `tools/build_sets.py`. A set passes when the program itself imports it in every language it has. That means:

- `panel.json` is valid and says its language;
- every picture is there and really is a picture;
- the translations refer to buttons that exist and name every screen;
- the folder holds no other files and has a fitting name.

A failure names the set and the file that is wrong.
