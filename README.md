# Game Remote

**Свои кнопки для каждой игры — на телефоне или планшете**  
**Custom buttons for every game — on your phone or tablet**

## Русский

Game Remote превращает телефон или планшет в пульт для игр на Windows. Кнопки настраиваются в редакторе на ПК и отображаются в браузере мобильного устройства. Например, кнопка «Карта» может отправлять клавишу `M` в активное окно игры.

Проект в начале разработки: [концепт](CONCEPT.md), [план](PLAN.md). В первую версию входят:

- На телефон ничего не ставится: пульт открывается в браузере.
- Кнопки двух типов: «нажать» и «держать», можно нажимать несколько сразу.
- Отдельная панель для каждой игры с настраиваемыми картинками, подписями и сочетаниями клавиш.
- Подключение телефона или планшета по QR-коду в локальной сети.
- Интерфейс на русском и английском.
- Автономный `GameRemote.exe` для Windows со встроенным Python.

## English

Game Remote turns your phone or tablet into a control panel for Windows games. Configure buttons in the PC editor, then use them in your mobile browser. For example, a Map button can send the `M` key to the active game window.

Development has just started: [concept](CONCEPT.md) and [plan](PLAN.md), both in Russian. The first release is planned to include:

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
python -m game_remote          # editor on http://127.0.0.1:8730, phone panel on port 8731
python tools/input_check.py -h # milestone 0: check that key presses reach your games
```

## License

[MIT](LICENSE)
