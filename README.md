# Game Remote

**Свои кнопки для каждой игры — на телефоне или планшете**  
**Custom buttons for every game — on your phone or tablet**

## Русский

Game Remote превращает телефон или планшет в пульт для игр на Windows. Кнопки настраиваются в редакторе на ПК и отображаются в браузере мобильного устройства. Например, кнопка «Карта» может отправлять клавишу `M` в активное окно игры.

Проект на стадии концепта. В первую версию входят:

- Отдельная панель для каждой игры с настраиваемыми картинками, подписями и сочетаниями клавиш.
- Подключение телефона или планшета по QR-коду в локальной сети.
- Интерфейс на русском и английском.
- Автономный `GameRemote.exe` для Windows со встроенным Python.

## English

Game Remote turns your phone or tablet into a control panel for Windows games. Configure buttons in the PC editor, then use them in your mobile browser. For example, a Map button can send the `M` key to the active game window.

The project is at the concept stage. The first release is planned to include:

- A panel per game with custom button images, labels, and keyboard shortcuts.
- QR code pairing on the local network.
- English and Russian interfaces.
- A standalone `GameRemote.exe` for Windows with Python bundled.

## Stack

Python · Flask · Waitress · SQLite · Windows `SendInput` · PyInstaller
