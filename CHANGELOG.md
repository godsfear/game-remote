# Изменения / Changelog

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
