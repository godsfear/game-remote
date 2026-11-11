# Изменения / Changelog

## Не выпущено / Unreleased

- Импорт набора спрашивает, что делать, если игра с таким названием уже есть: добавить набор рядом или заменить им игру. Заменённая игра переносится в корзину программы.

- An import of a set asks what to do when a game of that name is there already: add the set next to it or replace the game with it. A replaced game is moved to the trash folder of the program.

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
