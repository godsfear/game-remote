# Game Remote

**Свои кнопки для каждой игры — на телефоне или планшете**  
**Custom buttons for every game — on your phone or tablet**

## Русский

Game Remote превращает телефон или планшет в пульт для игр на Windows. Кнопки настраиваются в редакторе на ПК и отображаются в браузере мобильного устройства. Например, кнопка «Карта» может отправлять клавишу `M` в активное окно игры.

Проект в разработке: [концепт](CONCEPT.md), [план](PLAN.md). Уже есть прототип, которым можно играть: панель пока описывается файлом, редактора кнопок ещё нет. [Как попробовать](docs/prototype.md). В первую версию входят:

- На телефон ничего не ставится: пульт открывается в браузере.
- Кнопки двух типов: «нажать» и «держать», можно нажимать несколько сразу.
- Отдельная панель для каждой игры с настраиваемыми картинками, подписями и сочетаниями клавиш.
- Подключение телефона или планшета по QR-коду в локальной сети.
- Интерфейс на русском и английском.
- Автономный `GameRemote.exe` для Windows со встроенным Python.

## English

Game Remote turns your phone or tablet into a control panel for Windows games. Configure buttons in the PC editor, then use them in your mobile browser. For example, a Map button can send the `M` key to the active game window.

Work in progress: [concept](CONCEPT.md) and [plan](PLAN.md), both in Russian. A playable prototype exists: panels are JSON files for now, the button editor comes next. See [how to try it](docs/prototype.md) (in Russian). The first release is planned to include:

- Nothing to install on the phone: the panel opens in the browser.
- Two button types, tap and hold, with multi-touch.
- A panel per game with custom button images, labels, and keyboard shortcuts.
- QR code pairing on the local network.
- English and Russian interfaces.
- A standalone `GameRemote.exe` for Windows with Python bundled.

## Stack

Python · FastAPI · Uvicorn · SQLite · Windows `SendInput` · PyInstaller

## Development

```
python -m pip install -e ".[dev]"
pytest -q
python -m game_remote          # PC page on http://127.0.0.1:8730, phone panel on port 8731
python -m game_remote --fake-input --no-tray   # record key presses instead of sending them
python tools/input_check.py -h # milestone 0: check that key presses reach your games
python tools/build_exe.py      # dist/GameRemote.exe
python tools/smoke_test.py dist/GameRemote.exe
node tests/browser/check.js    # phone panel in a real browser; needs `npm install --no-save playwright`
```

## License

[MIT](LICENSE)
