# Изменения / Changelog

## Не выпущено / Unreleased

- Новый вид кнопки, «Переключатель»: нажимает клавишу как обычная и после этого светится до следующего нажатия. Подходит для того, что в игре включается и выключается: фары, шасси, режимы полёта. В редакторе задаётся, светится ли кнопка с самого начала. Подсветку помнит ПК: она одинакова на всех телефонах и сбрасывается при перезапуске программы.
- Программа не видит игру и считает только свои нажатия. Если подсветка разошлась с игрой, подержите палец на кнопке около секунды: подсветка сменится, клавиша не нажмётся.
- В наборе Star Citizen переключателями стали «Шасси», «Фары», «VTOL», «Круиз-контроль» и «Coupled». Панель, которая уже стоит на ПК, не меняется: импортируйте `star-citizen.zip` со страницы наборов и выберите «Заменить». Набор с переключателями открывается только этой версией и новее.
- Метки кнопок видны и поверх картинок: кружок у кнопок «держать», рамка нажатой и отклонённой кнопки, рамка выбранной кнопки в предпросмотре редактора. Раньше картинка их закрывала.

- A new kind of button, "Toggle": it presses its key like a plain one and is lit after that until the next press. It suits what a game switches on and off: lights, landing gear, flight modes. The editor sets whether the button is lit from the start. The PC remembers the light: it is the same on every phone and is reset when the program is started again.
- The program does not see the game and counts only its own presses. When the light and the game go apart, keep the finger on the button for about a second: the light changes, no key is pressed.
- In the Star Citizen set "Landing gear", "Lights", "VTOL", "Cruise control" and "Coupled" are toggles now. A panel that is already on the PC is not changed: import `star-citizen.zip` from the page of sets and choose "Replace". A set with toggles is read by this version and newer ones only.
- The marks of a button show on top of its picture too: the ring of a hold button, the frame of a pressed and of a rejected button, the frame of the selected button in the preview of the editor. The picture used to cover them.

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
