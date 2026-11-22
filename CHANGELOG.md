# Изменения / Changelog

## 0.12.1

Телефон может писать на кнопках клавиши, которые они нажимают.

- В настройках телефона (кнопка «⋮») появился пункт «Клавиши на кнопках». Он пишет в углу каждой кнопки её клавиши, например «Alt+N»: панель заодно становится шпаргалкой по раскладке игры. Пункт выключен, пока вы его не включите, и телефон помнит выбор.
- Подпись стоит в левом верхнем углу, правый остаётся метке кнопки. Если клавиши не помещаются, обрезается их начало: последняя клавиша видна всегда.
- Для этого ПК сообщает подключённым телефонам названия клавиш каждой кнопки. Раньше телефон о клавишах не знал ничего. Коды клавиш по-прежнему остаются на ПК, и нажать телефон может только кнопку панели.

Файл панели не изменился: наборы, сделанные в 0.12.0, читаются как прежде.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии начиная с 0.5.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

A phone can write onto the buttons the keys they press.

- The settings of a phone (the "⋮" button) have a new item, "Keys on the buttons". It writes into the corner of every button its keys, for example "Alt+N": the panel becomes a cheat sheet for the bindings of the game as well. The item is off until you turn it on, and the phone remembers the choice.
- The keys stand in the top left corner; the right one stays with the mark of the button. Keys that do not fit lose their beginning: the last key always shows.
- For this the PC tells the paired phones the names of the keys of every button. Before, a phone knew nothing about the keys. The codes of the keys stay on the PC as before, and a phone can press nothing but a button of a panel.

The file of a panel did not change: sets made in 0.12.0 are read as before.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions from 0.5.0 on tell about this release by themselves, in a line at the top of the page on the PC.

## 0.12.0

Кнопки могут быть разного размера.

- У кнопки появился «Размер»: ширина и высота в клетках сетки, от одной до четырёх. Главное действие можно сделать широкой полосой или большой кнопкой в четыре клетки.
- Кнопки поменьше сами занимают места рядом с большой, чтобы на панели не оставалось дыр там, где без них можно обойтись. Поэтому на телефоне кнопки могут стоять не в том порядке, что в списке; превью в редакторе показывает, как получится.
- Кнопка шире, чем у панели колонок, рисуется во всю ширину панели. Когда телефон повёрнут набок, колонок вдвое больше, а размер кнопки в клетках остаётся тем же.
- Плитка игры растягивается на всю большую кнопку, значок остаётся в её середине. У квадратных кнопок большая кнопка занимает ровно свои клетки вместе с промежутками между ними.

У файла панели новый формат, четвёртый. Панели и наборы прежних версий читаются как раньше. Набор, экспортированный из 0.12.0, откроет только 0.12.0 и новее: более старая версия попросит обновить программу. Готовый набор Star Citizen не изменился и по-прежнему открывается в 0.11.0.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии начиная с 0.5.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

Buttons can be of different sizes.

- A button has a "Size" now: its width and its height in cells of the grid, from one to four. The main action can be a wide bar or a large button of four cells.
- Smaller buttons take the places next to a large one by themselves, so that a panel has no holes where it can do without them. That is why the buttons may stand on the phone in another order than in the list; the preview in the editor shows what comes of it.
- A button wider than the panel has columns is drawn as wide as the panel. On a phone on its side there are twice the columns, and the size of a button in cells stays the same.
- The tile of the game is stretched over the whole of a large button, and the icon stays in its middle. Where the buttons are square, a large one takes exactly its cells and the gaps between them.

The file of a panel has a new format, the fourth. Panels and sets of earlier versions are read as before. A set exported from 0.12.0 is read by 0.12.0 and newer only: an older version asks to be updated. The ready-made Star Citizen set did not change and is still read by 0.11.0.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions from 0.5.0 on tell about this release by themselves, in a line at the top of the page on the PC.

## 0.11.1

Свечение значка теперь показывает, что кнопка делает, а не украшает все кнопки сразу.

- В 0.11.0 светились все значки игры, а кнопка под пальцем, наоборот, белела и теряла ореол. Теперь в покое значок не светится. Он светится, пока палец на кнопке, а у переключателя и макроса — всё время, пока они включены.
- Кнопка со значком больше не выгорает в белый при нажатии: значок остаётся своего цвета и светится. Белая рамка и лёгкое сжатие под пальцем остались.
- Галочка в настройках игры называется «Свечение при нажатии», под ней сказано, когда значок светится. Игра без этой галочки ведёт себя как раньше: значки не светятся, а кнопка под пальцем становится ярче.
- Готовая панель Star Citizen светится более ярким цветом. Если вы импортировали набор Star Citizen в 0.11.0, в вашей панели остался прежний тёмный цвет, и свечение будет слабым: выберите в настройках игры цвет светлее или импортируйте набор со [страницы наборов](https://github.com/godsfear/game-remote/releases/tag/panel-sets) заново.

Файл панели не изменился: наборы, сделанные в 0.11.0, читаются как прежде.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии начиная с 0.5.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

The glow of an icon now tells what its button does, where it used to adorn every button at once.

- In 0.11.0 every icon of a game glowed, and the button under a finger turned white and lost its glow. Now an icon does not glow at rest. It glows while a finger is on its button, and for as long as a toggle is on or a macro runs.
- A button with an icon no longer burns out to white when it is pressed: the icon keeps its colour and glows. The white frame and the slight squeeze under a finger stay.
- The box in the settings of a game is called "Glow when pressed", and a line under it says when an icon glows. A game without that box behaves as before: its icons do not glow, and a button grows brighter under a finger.
- The ready-made Star Citizen panel glows in a brighter colour. When you imported the Star Citizen set in 0.11.0, your panel has the dark colour it came with, and the glow is faint: choose a lighter colour in the settings of the game, or import the set from the [page of sets](https://github.com/godsfear/game-remote/releases/tag/panel-sets) again.

The file of a panel did not change: sets made in 0.11.0 are read as before.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions from 0.5.0 on tell about this release by themselves, in a line at the top of the page on the PC.

## 0.11.0

Кнопка собирается из плитки и значка: панель в стиле игры теперь делается без графического редактора.

- У кнопки появился значок. В её настройках «Выбрать значок» открывает окно с тремя сотнями значков по группам: системы, транспорт, навигация, связь, бой и другие. Поиск находит значок по названию на русском и на английском. Значок рисуется поверх цвета кнопки, её картинки или плитки.
- «Свой файл» делает значок из вашей картинки: PNG или WebP с прозрачным фоном. От неё берётся только форма, а прозрачные поля обрезаются, поэтому свой значок выходит того же размера, что и готовые. Картинку без прозрачного фона редактор не примет и скажет почему.
- У игры появилась «Плитка кнопок» — картинка под каждой кнопкой, у которой нет своей, — а рядом цвет значков и их свечение. Одна плитка и значки дают всей панели вид игры. Плитка растягивается по кнопке любой формы. Цвет кнопки под непрозрачной плиткой не виден; редактор об этом напоминает.
- Готовая панель Star Citizen собрана по-новому: одна плитка и восемнадцать значков вместо восемнадцати картинок. Выглядит она как прежде. Её значки стоят в окне выбора отдельной группой «Star Citizen», и их можно брать в любую панель.
- Если панель Star Citizen у вас уже есть, программа её не трогает: она остаётся с картинками и работает как раньше. Новый вид даёт набор `star-citizen.zip` со [страницы наборов](https://github.com/godsfear/game-remote/releases/tag/panel-sets), импортированный с заменой. Прежняя панель при этом переносится в папку `trash`, а свои изменения в ней придётся внести заново.
- Набор с плиткой или значками читает версия 0.11.0 и новее; более старая попросит обновить программу. То же относится к любому набору, экспортированному из 0.11.0.
- Страницы программы больше не зависят от записей о типах файлов в реестре Windows. Если другая программа испортила там запись для `.js`, `.css` или `.svg`, страницы Game Remote могли не открыться.

Готовые значки взяты из Material Design Icons (Pictogrammers), лицензия Apache 2.0.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии начиная с 0.5.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

A button is put together of a tile and an icon: a panel in the look of a game now takes no graphics editor.

- A button has an icon. In its settings "Choose an icon" opens a window with three hundred icons in groups: systems, vehicles, navigation, comms, combat and others. The search finds an icon by its name in Russian and in English. The icon is drawn over the colour of the button, over its picture or over the tile.
- "Own file" makes an icon of your picture: a PNG or WebP with a transparent background. Only its shape is taken, and the transparent margins are cut away, so an icon of your own is as large as the ready ones. A picture without a transparent background is refused, with the reason.
- A game has a "Button tile", a picture under every button that has none of its own, and next to it the colour of the icons and their glow. One tile and icons give the whole panel the look of a game. The tile is stretched over a button of any shape. The colour of a button does not show under a tile that is not transparent; the editor says so.
- The ready-made Star Citizen panel is built anew: one tile and eighteen icons in place of eighteen pictures. It looks as it did. Its icons stand in the window in a group of their own, "Star Citizen", and any panel can use them.
- When you have the Star Citizen panel already, the program leaves it alone: it keeps its pictures and works as before. The new look comes with the set `star-citizen.zip` from the [page of sets](https://github.com/godsfear/game-remote/releases/tag/panel-sets), imported as a replacement. The panel you had goes to the folder `trash`, and the changes you made in it have to be made again.
- A set with a tile or icons is read by version 0.11.0 and newer; an older one asks to be updated. The same goes for any set exported from 0.11.0.
- The pages of the program no longer depend on what the registry of Windows says about the types of files. When another program spoiled the entry for `.js`, `.css` or `.svg` there, the pages of Game Remote could fail to open.

The ready icons are from Material Design Icons (Pictogrammers), under the Apache License 2.0.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions from 0.5.0 on tell about this release by themselves, in a line at the top of the page on the PC.

## 0.10.1

Исправления к 0.10.0.

- На странице ПК в «Последних нажатиях» длинный текст справа больше не сжимает название кнопки в узкий столбик: он уходит на отдельную строку под названием. Так выглядели отклонённые нажатия и долгое касание переключателя.
- Внизу страницы ПК галочки «Проверять новую версию на GitHub» и «Запускать вместе с Windows» стоят одна под другой, и кнопки рядом с ними снова умещаются в одну строку.
- Макрос, который прервал ПК, теперь виден в «Последних нажатиях» отдельной строкой «макрос прерван» с причиной, например «Окно игры не активно». Раньше причина попадала только в журнал программы.
- Файл панели стал короче: в него пишется только то, что отличается от значений по умолчанию. Панели читаются как прежде, а сохранённые раньше перепишутся в коротком виде при первом изменении.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии начиная с 0.5.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

Fixes for 0.10.0.

- On the PC page a long text on the right of "Recent presses" no longer squeezes the name of the button into a narrow column: it goes to a line of its own under the name. Rejected presses and a long touch on a toggle looked so.
- At the bottom of the PC page the boxes "Check GitHub for a new version" and "Start with Windows" stand one under another, and the buttons next to them fit into one line again.
- A macro the PC stopped now shows in "Recent presses" as a line of its own, "macro stopped", with the reason, for example "The game window is not active". The reason used to go to the log of the program only.
- The panel file got shorter: it holds only what differs from the defaults. Panels are read as before, and those saved earlier are rewritten in the short form at their first change.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions from 0.5.0 on tell about this release by themselves, in a line at the top of the page on the PC.

## 0.10.0

Автозапуск с Windows и два пояснения там, где программу было легко понять неправильно.

- В редакторе внизу страницы появилась галочка «Запускать вместе с Windows». Когда она стоит, программа при входе в Windows стартует сама и появляется значком в трее, страница в браузере при этом не открывается. Для этого программа записывает одну строку в список автозагрузки вашей учётной записи; снимите галочку — и строка исчезнет. Галочка показывает то, что есть в Windows: если отключить Game Remote в «Диспетчере задач» или в «Параметрах», она тоже снимется. После обновления запустите новый `GameRemote.exe` один раз, и автозапуск переключится на него.
- Автозапуск стартует программу без прав администратора. Если ваша игра идёт от администратора, программу по-прежнему нужно запускать вручную от его имени.
- Долгое касание переключателя меняет только его подсветку и клавишу не нажимает; так было и раньше, но выглядело как сработавшее нажатие. Теперь телефон прямо пишет, что клавиша не нажата, а на странице ПК такое касание стоит в «Последних нажатиях» отдельной строкой.
- Кнопка «Подключить ещё одно устройство» теперь называется «Показать QR-код», а под ней сказано, что этим же кодом можно снова открыть пульт на уже привязанном телефоне. Привязка при этом сохраняется: удалять телефон из списка, чтобы добраться до кода, не нужно.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии начиная с 0.5.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

Start with Windows, and two explanations where the program was easy to misread.

- The editor has a new box at the bottom of the page, "Start with Windows". While it is ticked, the program starts by itself when you sign in to Windows and shows its icon in the tray, without opening the page in the browser. For that the program writes one line into the startup list of your account; clear the box and the line is gone. The box shows what Windows has: when you switch Game Remote off in the Task Manager or in Settings, it is cleared too. After an update run the new `GameRemote.exe` once, and the autostart switches to it.
- The autostart runs the program without administrator rights. When your game runs as administrator, you still have to start the program by hand as administrator.
- A long touch on a toggle changes only its light and presses no key; it was so before, but it looked like a press that worked. Now the phone says in words that no key was pressed, and the PC page lists such a touch in "Recent presses" as a line of its own.
- The button "Connect another device" is now called "Show the QR code", and a line under it says that the same code opens the remote again on a phone that is paired already. The pairing stays: there is no need to remove the phone from the list to get to the code.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions from 0.5.0 on tell about this release by themselves, in a line at the top of the page on the PC.

## 0.9.0

Телефон может растянуть кнопки на весь свой экран.

- В настройках пульта (кнопка «⋮» на телефоне) появился переключатель «Кнопки на весь экран». Когда он включён, телефон растягивает кнопки по экрану и там, где у игры они квадратные и стоят посередине. Удобно на небольшом экране: кнопки становятся крупнее.
- Настройка своя у каждого телефона и запоминается на нём. Сама игра не меняется: в редакторе и на других устройствах она выглядит как прежде.
- Картинка заполняет растянутую кнопку целиком, поэтому её края могут обрезаться.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии начиная с 0.5.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

A phone can stretch the buttons over its whole screen.

- The settings of the remote (the "⋮" button on the phone) have a new switch, "Buttons fill the screen". When it is on, the phone stretches the buttons over the screen, also where the game has them square and in the middle. It helps on a small screen: the buttons get larger.
- The setting belongs to the phone and is kept there. The game itself does not change: the editor and other devices show it as before.
- A picture fills a stretched button entirely, so its edges may be cut off.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions from 0.5.0 on tell about this release by themselves, in a line at the top of the page on the PC.

## 0.8.0

Макросы: одно касание нажимает несколько клавиш подряд.

- Новый вид кнопки, «Макрос». Вместо одного сочетания у неё список шагов: в каждом клавиша или сочетание, сколько их держать и сколько ждать перед следующим шагом. Шагов может быть до 20, весь макрос длится не дольше 30 секунд. В редакторе шаги записываются с клавиатуры так же, как сочетание обычной кнопки.
- Пока макрос идёт, его кнопка светится на всех телефонах. Касание светящейся кнопки останавливает макрос.
- Макрос работает только у игры, которой задано окно («Выбрать окно» в настройках игры), и только пока это окно активно. Он прерывается, если вы переключились в другое окно, если телефон потерял связь, заблокирован или страница пульта свёрнута, а также по кнопке «Отпустить все клавиши» на странице ПК. Клавиши при этом отпускаются, а телефон показывает причину.
- О наборе с макросами редактор при импорте сначала спрашивает: он называет число макросов и окно, в котором они нажимают клавиши. Импортируйте такой набор, только если доверяете его автору.
- У файла панели новый формат. Программа записывает его номер в каждую панель и каждый набор, которые сохраняет, поэтому версия 0.7.0 на такие файлы отвечает «обновите программу», а более ранние версии их не читают. Панели прежних версий новая программа читает как раньше. Если собираетесь вернуться на старую версию, заранее скопируйте папку `%LOCALAPPDATA%\GameRemote\panels`.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии начиная с 0.5.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

Macros: one touch presses several keys one after another.

- A new kind of button, "Macro". In place of one shortcut it has a list of steps: each has a key or a shortcut, how long to hold it and how long to wait before the next step. There can be up to 20 steps, and the whole macro takes no longer than 30 seconds. The editor records the steps from the keyboard like the shortcut of a plain button.
- While a macro runs its button is lit on every phone. A touch of the lit button stops the macro.
- A macro works only for a game that has a window set ("Choose a window" in the settings of the game), and only while that window is active. It stops when you switch to another window, when the phone loses the connection, is locked or the page of the remote is left, and when "Release all keys" is pressed on the PC page. Its keys are let go then, and the phone says why.
- About a set with macros the editor asks before it imports it: it names the number of macros and the window they press their keys in. Import such a set only if you trust its author.
- The panel file has a new format. The program writes its number into every panel and every set it saves, so version 0.7.0 answers such files with "update the program", and earlier versions do not read them. The new program reads the panels of earlier versions as before. If you mean to go back to an old version, copy the folder `%LOCALAPPDATA%\GameRemote\panels` first.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions from 0.5.0 on tell about this release by themselves, in a line at the top of the page on the PC.

## 0.7.0

Телефон сам открывает панель игры, в окно которой вы переключились на ПК.

- Когда на ПК активным становится окно игры, к которой привязана панель, телефон открывает эту панель сам. Он отзывается тремя короткими вибрациями и долю секунды не принимает касания, чтобы палец не нажал кнопку новой панели по ошибке. Телефон, который взяли в руки уже во время игры, открывает её панель сразу. Для этого у игры должно быть задано окно: «Выбрать окно» в настройках игры в редакторе.
- Другую игру на телефоне по-прежнему можно выбрать вручную: она остаётся на экране, пока вы не уйдёте из окна игры и не вернётесь в него.
- Набор, сделанный для более новой версии Game Remote, редактор не импортирует и прямо просит обновить программу. Раньше в таком случае он показывал ошибку проверки файла, из которой этого было не понять. Сообщение появится, когда у наборов сменится формат; версии до 0.6.0 включительно его не знают.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версии 0.5.0 и 0.6.0 сообщат об этом выпуске сами, строкой вверху страницы на ПК.

The phone opens the panel of the game whose window you switched to on the PC.

- When the window of a game that a panel is bound to becomes active on the PC, the phone opens that panel by itself. It answers with three short pulses and takes no touches for a fraction of a second, so that a finger does not press a button of the new panel by mistake. A phone that is taken in hand when the game is running already opens its panel at once. The game needs its window set for that: "Choose a window" in the settings of the game in the editor.
- Another game can still be chosen on the phone by hand: it stays on the screen until you leave the window of the game and come back to it.
- A set made for a newer version of Game Remote is not imported: the editor says plainly that the program has to be updated. It used to show an error of the file check, which did not tell that. The message will show once the format of sets changes; the versions up to 0.6.0 do not know it.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Versions 0.5.0 and 0.6.0 tell about this release by themselves, in a line at the top of the page on the PC.

## 0.6.0

Кнопки-переключатели: кнопка показывает, включено или выключено то, что она переключает.

- Новый вид кнопки, «Переключатель»: нажимает клавишу как обычная и после этого светится до следующего нажатия. Подходит для того, что в игре включается и выключается: фары, шасси, режимы полёта. В редакторе задаётся, светится ли кнопка с самого начала. Подсветку помнит ПК: она одинакова на всех телефонах и сбрасывается при перезапуске программы.
- Программа не видит игру и считает только свои нажатия. Если подсветка разошлась с игрой, подержите палец на кнопке около секунды: подсветка сменится, клавиша не нажмётся.
- В наборе Star Citizen переключателями стали «Шасси», «Фары», «VTOL», «Круиз-контроль» и «Coupled». Панель, которая уже стоит на ПК, не меняется: импортируйте `star-citizen.zip` со страницы наборов и выберите «Заменить». Набор с переключателями открывается только этой версией и новее.
- Метки кнопок видны и поверх картинок: кружок у кнопок «держать», рамка нажатой и отклонённой кнопки, рамка выбранной кнопки в предпросмотре редактора. Раньше картинка их закрывала.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Версия 0.5.0 сообщит об этом выпуске сама, строкой вверху страницы на ПК.

Toggle buttons: a button shows whether what it switches is on or off.

- A new kind of button, "Toggle": it presses its key like a plain one and is lit after that until the next press. It suits what a game switches on and off: lights, landing gear, flight modes. The editor sets whether the button is lit from the start. The PC remembers the light: it is the same on every phone and is reset when the program is started again.
- The program does not see the game and counts only its own presses. When the light and the game go apart, keep the finger on the button for about a second: the light changes, no key is pressed.
- In the Star Citizen set "Landing gear", "Lights", "VTOL", "Cruise control" and "Coupled" are toggles now. A panel that is already on the PC is not changed: import `star-citizen.zip` from the page of sets and choose "Replace". A set with toggles is read by this version and newer ones only.
- The marks of a button show on top of its picture too: the ring of a hold button, the frame of a pressed and of a rejected button, the frame of the selected button in the preview of the editor. The picture used to cover them.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Version 0.5.0 tells about this release by itself, in a line at the top of the page on the PC.

## 0.5.0

Программа сама сообщает о новой версии.

- Редактор сообщает, что вышла новая версия, и даёт ссылку на неё. Для этого программа через минуту после запуска и затем раз в сутки спрашивает у GitHub номер последнего выпуска; сама ничего не скачивает. Если GitHub не ответил, она спросит ещё раз через час, а дальше всё реже. Проверка отключается галочкой «Проверять новую версию на GitHub» внизу страницы на ПК; если снять её в первую минуту, не уйдёт ни одного запроса.
- Настройки сохраняются и тогда, когда их файл в этот момент читает другая программа, например антивирус: раньше смена языка в таком случае заканчивалась ошибкой.
- Руководство переведено на английский: [docs/guide.en.md](https://github.com/godsfear/game-remote/blob/main/docs/guide.en.md).

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Об этой версии прежние ещё не сообщают; о следующих редактор скажет сам.

The program tells about a new version by itself.

- The editor tells that a newer version is out and links to it. For that the program asks GitHub for the number of the latest release a minute after its start and then once a day; it downloads nothing by itself. When GitHub does not answer, it asks again in an hour, and then less and less often. The box "Check GitHub for a new version" at the bottom of the page on the PC turns the check off; cleared within the first minute, it stops every request.
- Settings are saved also while another program, an antivirus for one, reads their file at that moment: a change of the language used to end in an error then.
- The guide is in English too: [docs/guide.en.md](https://github.com/godsfear/game-remote/blob/main/docs/guide.en.md).

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. The versions before this one do not tell about it yet; the editor will tell about the next ones.

## 0.4.0

Каталог наборов: готовые наборы скачиваются с GitHub, а набор обновляется заменой.

- У готовых наборов появилась страница: [Наборы](https://github.com/godsfear/game-remote/releases/tag/panel-sets). Скачайте zip своей игры и нажмите «Импортировать набор». Как прислать свой набор, описано в [sets/README.md](https://github.com/godsfear/game-remote/blob/main/sets/README.md).
- Импорт набора спрашивает, что делать, если игра с таким названием уже есть: добавить набор рядом или заменить им игру. Заменённая игра переносится в корзину программы.
- После замены телефон и редактор сразу показывают новые картинки, даже если их файлы называются так же, как старые.
- В наборе Star Citizen три экрана по шесть кнопок: к «Взлёт/Посадка» добавились «Полёт» и «Эмоции». Панель, которая уже стоит на ПК, не меняется: чтобы получить новые кнопки, импортируйте `star-citizen.zip` со страницы наборов и выберите «Заменить».

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте.

The catalogue of sets: ready-made sets are downloaded from GitHub, and a set is updated by replacing it.

- Ready-made sets have a page: [Sets](https://github.com/godsfear/game-remote/releases/tag/panel-sets). Download the zip of your game and press "Import a set". [sets/README.md](https://github.com/godsfear/game-remote/blob/main/sets/README.md) says how to send your own set.
- An import of a set asks what to do when a game of that name is there already: add the set next to it or replace the game with it. A replaced game is moved to the trash folder of the program.
- After a replacement the phone and the editor show the new pictures at once, also when their files have the names of the old ones.
- The Star Citizen set has three screens of six buttons: "Flight" and "Emotes" joined "Takeoff/Landing". A panel that is already on the PC is not changed: to get the new buttons, import `star-citizen.zip` from the page of sets and choose "Replace".

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are.

## 0.3.0

Наборы: игрой теперь можно поделиться.

- «Экспортировать набор» в карточке игры сохраняет её в zip: кнопки, экраны и картинки. «Импортировать набор» под списком игр добавляет игру из такого файла. Своя игра с тем же названием не заменяется.
- У набора могут быть подписи на нескольких языках. При импорте берётся язык редактора или браузера, иначе английский, иначе язык автора. Как добавить перевод, описано в руководстве.
- Файл набора проверяется: программа берёт из него только описание кнопок и картинки и говорит, что не так, если архив повреждён, закрыт паролем или в нём чего-то не хватает.
- Запись сочетания больше не перехватывает ввод: если во время записи перейти в поле подписи или названия, клавиши попадают в текст, а не в сочетание кнопки.
- Сообщения редактора стали точнее: «Не сохранено» пишется только тогда, когда правки действительно не дошли до ПК.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Импортированная игра — обычная игра: её открывает и версия 0.2.0.

Sets: a game can now be shared.

- "Export as a set" on the card of a game saves it as a zip: the buttons, the screens and the pictures. "Import a set" under the list of games adds the game of such a file. A game of your own with the same name is not replaced.
- A set can carry its labels in several languages. An import takes the language of the editor or the browser, else English, else the language of the author. The guide says how to add a translation.
- The file of a set is checked: the program takes only the description of the buttons and the pictures from it, and says what is wrong when the zip is damaged, has a password or misses something.
- Recording a shortcut no longer swallows typing: go to the field of a label or a name while it records, and the keys become text, not the shortcut of the button.
- The messages of the editor are more exact: "Not saved" appears only when the edits really did not reach the PC.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. An imported game is a plain game: version 0.2.0 opens it too.

## 0.2.0

Экраны кнопок: у одной игры теперь может быть несколько наборов кнопок.

- Кнопки игры можно разложить по экранам, до восьми. В редакторе: «Добавить экран» над списком кнопок, у каждого экрана своё название, кнопку можно перенести на другой экран.
- На телефоне под названием игры появляются вкладки. Экран переключается одним касанием, в том числе вторым пальцем, пока первый держит кнопку. Пульт помнит, какой экран был открыт у каждой игры.
- Готовая панель Star Citizen при первом запуске идёт с обложкой и двумя экранами: «Взлёт/Посадка» с шестью кнопками и пустой «Полёт». Панель, которая уже стоит на ПК, не меняется.

Обновление: скачайте новый `GameRemote.exe` и запускайте его вместо старого. Игры, кнопки и подключённые устройства остаются на месте. Игры без экранов открываются и в версии 0.1.0, игры с экранами — только в этой.

Screens: one game can now have several sets of buttons.

- The buttons of a game can be grouped into screens, up to eight. In the editor: "Add a screen" above the list of buttons, every screen has its own name, and a button can be moved to another screen.
- On the phone, tabs appear under the game's name. One touch switches the screen, also with a second finger while the first one holds a button. The phone remembers the screen it showed for every game.
- On the first start the ready-made Star Citizen panel comes with a cover and two screens: "Takeoff/Landing" with the six buttons and an empty "Flight". A panel that is already on the PC is not changed.

Updating: download the new `GameRemote.exe` and start it in place of the old one. Games, buttons and paired devices stay where they are. Games without screens still open in version 0.1.0; games with screens need this one.

## 0.1.0

Первая версия. Телефон или планшет становится пультом для игр на Windows: кнопки собираются на ПК, нажимаются в браузере телефона.

- Один файл `GameRemote.exe`, Python ставить не нужно. На телефон ничего не ставится.
- Редактор на ПК: игры и кнопки, запись сочетания с клавиатуры, цвета и картинки, обложки игр, порядок кнопок и число колонок, предпросмотр. Изменения сохраняются сами и сразу видны на телефоне.
- Фон панели и квадратные кнопки: панель можно собрать из своих картинок.
- Готовая панель Star Citizen с шестью кнопками при первом запуске.
- Кнопки «нажать» и «держать», несколько пальцев одновременно.
- Подключение по QR-коду с одноразовым кодом. У каждого устройства свой ключ; устройство можно переименовать и отключить на ПК.
- Привязка панели к окну игры: нажатия не попадают в другие программы. Зажатые клавиши отпускаются при обрыве связи и при смене активного окна.
- На пульте: полный экран, вибрация, значок для главного экрана, задержка до ПК, объяснение при потере связи.
- Русский и английский интерфейс, один язык можно задать для всех устройств.

Известные ограничения:

- Игры с античитом, который отбрасывает программный ввод, нажатия не видят. Проверено на Undecember. Обходить такую защиту программа не будет.
- Если игра запущена от администратора, Game Remote тоже нужно запускать от администратора.
- Файл не подписан: SmartScreen предупреждает при первом запуске.
- Связь между телефоном и ПК не шифруется. Программа рассчитана на домашнюю сеть.
- Проверено на Android и Chrome. На iOS не проверялось.

First release. A phone or tablet becomes a button panel for Windows games: build the buttons on the PC, press them in the phone's browser.

- A single `GameRemote.exe`, no Python needed. Nothing to install on the phone.
- An editor on the PC: games and buttons, shortcuts recorded from the keyboard, colours and pictures, game covers, button order and column count, a live preview. Changes are saved by themselves and reach the phone at once.
- A background picture and square buttons: a panel can be built from your own artwork.
- A ready-made Star Citizen panel with six buttons on the first start.
- Tap and hold buttons, several fingers at a time.
- Pairing by a QR code with a one-time code. Every device has its own key and can be renamed or disconnected on the PC.
- A panel can be bound to the game's window, so presses never land in another program. Held keys are released when the connection drops or another window becomes active.
- On the phone: full screen, vibration, a home screen icon, the delay to the PC, help when the connection is lost.
- English and Russian; one language can be set for all devices.

Known limitations:

- Games whose anti-cheat drops synthetic input do not see the presses. Checked with Undecember. The program will not work around such protection.
- If the game runs as administrator, Game Remote must run as administrator too.
- The file is not signed: SmartScreen warns on the first start.
- Traffic between the phone and the PC is not encrypted. The program is made for a home network.
- Checked on Android with Chrome. Not checked on iOS.
