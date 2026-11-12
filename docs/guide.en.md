# Game Remote guide

[Русская версия](guide.md)

Game Remote is one file, `GameRemote.exe`, on a Windows PC and a page in the browser of a phone. On the PC you build a panel of buttons for each game, on the phone you press them, and the program sends the keys to the game.

## Where to get the exe

The ready `GameRemote.exe` is on the [Releases](https://github.com/godsfear/game-remote/releases) page. Next to it is the file `GameRemote.exe.sha256` with its checksum.

CI builds the exe of the latest commit: on the page of the repository open **Actions**, choose the latest **CI** run and download the **GameRemote** artifact at the bottom. It is a zip with one file.

To build it yourself on Windows:

```
python -m pip install -e ".[dev]"
python tools/build_exe.py
python tools/smoke_test.py dist/GameRemote.exe
```

## First start

1. Start `GameRemote.exe` with a double click. The file is not signed, so Windows warns with one of two windows:
   - "Windows protected your PC" (SmartScreen): press "More info", then "Run anyway".
   - "The publisher could not be verified. Are you sure you want to run this software?": press "Run". To stop the window from appearing at every start, clear the box "Always ask before opening this file".

   The checksum tells that the file is the right one: run `certutil -hashfile GameRemote.exe SHA256` in its folder and compare the result with the file `GameRemote.exe.sha256` of the release.
2. Windows asks about the firewall. Allow access on **private** networks, or the phone will not see the PC.
3. An icon appears in the tray, and the browser opens the Game Remote page with a QR code.
4. Point the camera of the phone at the QR code. The phone must be on the same Wi-Fi. The ready-made Star Citizen panel opens, three screens of six buttons, and the phone appears on the PC page in the list "Phones and tablets".
5. Open Notepad and press "Lights" on the phone: an `l` appears in Notepad. The page on the PC shows the recent presses.

The ready-made Star Citizen panel presses these keys:

| Screen | Button | Keys |
| --- | --- | --- |
| Takeoff/Landing | Flight Ready | right Alt + R |
| | ATC | left Alt + N |
| | Landing gear | N |
| | Lights | L |
| | VTOL | K |
| | Map | F2 |
| Flight | SCM ↔ NAV | B, hold |
| | Cruise control | left Alt + C |
| | Coupled ↔ Decoupled | C |
| | Scan | V |
| | Radar ping | Tab, hold |
| | Camera | F4 |
| Emotes | Wave | right Ctrl + F9 |
| | Salute | right Ctrl + F10 |
| | Sit | right Ctrl + F11 |
| | Clap | right Ctrl + O |
| | Laugh | right Ctrl + B |
| | Dance | right Ctrl + Y |

The buttons marked "hold" keep the key down while the finger is on the button. Compare the keys with the settings of the game: where they differ or are not set there, change them in the editor or set them in the game. The panel is not tied to the window of the game, so the first check in Notepad works; the card of the game ties it. The panel is installed once: when it is deleted, it does not come back. Game Remote is not affiliated with the developers of Star Citizen.

## The remote on the phone

The "⋮" button in the top right corner opens the settings of this device: "Full screen" hides the address bar of the browser, "Vibration on touch" turns the feedback on and off. The same place shows how many milliseconds a signal takes to the PC and back. An accepted press gives one short buzz, a rejected one gives two, and the reason appears at the bottom.

When a game has several screens of buttons, tabs appear under its name: a touch of a tab shows the other buttons at once. The remote remembers which screen was open for each game. When the screen changes, the buttons you were holding are released.

To open the remote with one tap, add the page to the home screen from the menu of the browser: it has its own icon. The page is served over plain `http`, so Android makes a shortcut, not a separate app: the remote opens in a browser tab, and full screen is turned on with the button in the settings.

When the connection to the PC is lost for more than a few seconds, the remote says what to check and reconnects by itself as soon as the connection is back: also after the screen was locked and after the phone returned to the Wi-Fi.

## The editor

The page on the PC is the editor. The list of games is on the left, the buttons of the chosen game are in the middle, the preview is on the right: the same code draws it as the remote on the phone.

1. Press "Add a game" and type its name.
2. Press "Add a button", type the label, then press "Record" and press the key or the shortcut on the keyboard. Shortcuts that the browser keeps for itself (`Ctrl+W`, `Alt+Tab`) are set in the block "Choose by hand".
3. Choose what a touch does, "Tap" or "Hold", then the colour of the button and, if you like, a picture. PNG, JPEG and WebP work; the editor makes a large picture smaller. The label stays visible on top of the picture.
4. The arrows or dragging in the list change the order of the buttons, the "−" and "+" buttons change the number of columns.
5. When there are many buttons, put them on screens: "Add a screen" above the list of buttons. The tabs switch the screen, the field under them renames the current screen, a new button lands on the open screen. The field "Screen" in the settings of a button moves it to another screen. "Delete the screen" deletes the screen with its buttons. There can be up to eight screens.

A game can have a cover: it shows in the list of games on the phone. "Background on the phone" puts a picture under the buttons. The switch "Buttons" chooses their shape: "Fill the screen" stretches the buttons over the grid, "Square" puts square buttons in the middle of the screen, and the background shows around them. The window of the game is set in the same place: start the game, press "Choose a window" and choose it in the list of open windows. After that the buttons work only while a window of this program is active, and a press does not land in a chat or a browser. Without that, the keys go to whatever window is active. The language is chosen at the bottom of the page. In the "Auto" mode the editor and every phone use the language of their own browser, and a chosen language becomes the language of all devices.

There is nothing to save: changes are written by themselves, and a panel that is open on a phone updates at once. A deleted game is not erased, it is moved to `%LOCALAPPDATA%\GameRemote\trash`.

To quit: the tray icon → "Quit", or the button "Quit Game Remote" at the bottom of the page on the PC. Starting the exe again opens the page of the program that is already running.

When the game runs as administrator, Game Remote must run as administrator too (right click → "Run as administrator"). Otherwise Windows drops the presses, and the phone says why. Such programs are marked "runs as administrator" in the list of windows.

When the window of another program becomes active while a button is held, the keys that are down are released by themselves.

## The panel file

The editor keeps every game in a folder inside `%LOCALAPPDATA%\GameRemote\panels`: the file `panel.json` and the pictures of the buttons. The button "Open the panels folder" at the bottom of the page opens it in Explorer. The folder can be copied to another PC, and the file can be edited by hand. The name of the folder: Latin letters, digits, `-` and `_`.

The program reads the files again by itself: save `panel.json`, and the panel on the phone and in the editor updates in about a second. When the file has a mistake, the editor shows where, and the other panels keep working.

An example, `panels\x4\panel.json`:

```json
{
  "name": "X4: Foundations",
  "columns": 3,
  "window": "X4.exe",
  "buttons": [
    { "id": "map", "label": "Map", "keys": "KeyM" },
    { "id": "radio", "label": "Comms", "keys": "ControlLeft+KeyR", "color": "#2b5fd9" },
    { "id": "boost", "label": "Boost", "keys": "Tab", "type": "hold", "color": "#2f9e62" },
    { "id": "stop", "label": "Stop", "keys": "Backspace", "image": "stop.png" }
  ]
}
```

| Field | What it means |
| --- | --- |
| `name` | The name of the panel, shown on the phone |
| `columns` | The number of columns in portrait, from 1 to 8. 3 by default. Landscape fits twice as many |
| `window` | Optional. The name of the exe of the game; the editor chooses it from the open windows. When it is set, presses are rejected while a window of another program is active |
| `buttons` | The buttons in the order they have on the screen |
| `id` | The name of the button inside the panel: Latin letters, digits, `-` and `_`. It is not repeated |
| `label` | The label, up to 40 characters |
| `keys` | A key, or a shortcut joined with `+`. The modifiers are pressed first |
| `type` | `tap` is a short press (the default). `hold` keeps the key down while the finger is on the button |
| `color` | The colour of the background as `#rrggbb` |
| `image` | The name of a PNG, JPEG or WebP file in the folder of the panel |
| `cover` | A field of the panel, not of a button. The cover of the game: the name of a file in the folder of the panel |
| `background` | A field of the panel. The background under the buttons on the phone: the name of a file in the folder of the panel |
| `shape` | A field of the panel. `fill` stretches the buttons over the whole screen (the default). `square` puts square buttons in the middle of the screen, and all of them fit without scrolling |
| `screens` | A field of the panel, optional. The names of the screens, from one to eight, each up to 24 characters: `"screens": ["Flight", "Combat"]`. Without it all buttons are on one screen |
| `screen` | A field of a button. The number of its screen in the list `screens`, counted from zero. 0 by default, which is the first screen |

Keys are written as the codes of the physical keys, as in a browser (`KeyboardEvent.code`), so they do not depend on the keyboard layout:

- letters and digits: `KeyA` … `KeyZ`, `Digit0` … `Digit9`;
- modifiers: `ControlLeft`, `ControlRight`, `ShiftLeft`, `ShiftRight`, `AltLeft`, `AltRight`;
- `F1` … `F24`, `Escape`, `Tab`, `Space`, `Enter`, `Backspace`, `CapsLock`;
- `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, `Home`, `End`, `PageUp`, `PageDown`, `Insert`, `Delete`;
- signs: `Minus`, `Equal`, `BracketLeft`, `BracketRight`, `Semicolon`, `Quote`, `Backquote`, `Backslash`, `Comma`, `Period`, `Slash`;
- the numeric pad: `Numpad0` … `Numpad9`, `NumpadAdd`, `NumpadSubtract`, `NumpadMultiply`, `NumpadDivide`, `NumpadDecimal`, `NumpadEnter`.

The full list is in [`src/game_remote/input/keys.py`](../src/game_remote/input/keys.py).

## Sets: how to share a game

A set is a game in one zip file: its buttons, screens and pictures. It can be shared with another player, or it can carry a game to another PC.

- **Export.** Choose the game and press "Export as a set" at the bottom of its card. The editor asks which language the labels of the game are in, and offers the language of its own interface. The browser saves a file named after the folder of the game, for example `star-citizen.zip`.
- **Import.** Press "Import a set" under the list of games and choose the zip. The set becomes a new game; from then on it can be changed like your own. When a game of that name is there already, the editor asks whether to add the set next to it or to replace the game with it. A replaced game is not erased, it is moved to `%LOCALAPPDATA%\GameRemote\trash`; the set takes its place, so the phones keep showing the same game.

A set holds only names, pictures and shortcuts. Before you play, look in the editor at the keys the buttons of someone else's set press: in your game they may be set differently.

The program checks the file at import and says what is wrong with it: it is not a zip, the zip is damaged or has a password, `panel.json` has a mistake, a picture is missing, the file is too large. A picture of a set can be up to 2 MB, the whole file up to 50 MB.

### Translations in a set

A set can carry its labels in several languages. An import takes the language chosen in the editor; when that is "Auto" or the set does not have it, the languages of your browser in their order; then English; when there is no English either, the language the set is written in. The language is chosen once: after the import the set is a plain game, and its labels do not change with the language of the interface.

A translation is added to the zip by hand. Unpack the set: `panel.json` names the language it is written in, for example `"language": "en"`. Put a file with the code of the language in its name next to it, for example `panel.ru.json`, and pack everything again:

```json
{
  "name": "Star Citizen",
  "screens": ["Взлёт/Посадка", "Полёт", "Эмоции"],
  "labels": {
    "landing-gear": "Шасси",
    "headlights": "Фары"
  }
}
```

| Field | What it means |
| --- | --- |
| `name` | The name of the game. Optional |
| `screens` | The names of all screens, in the same order as in `panel.json`. Optional |
| `labels` | The labels of the buttons by their `id`. A button that is not here keeps its label of `panel.json` |

A translation does not name keys or pictures: they are the same for all languages.

### The catalogue of sets

The ready-made sets of the community are on the page [Sets / Наборы](https://github.com/godsfear/game-remote/releases/tag/panel-sets): download the zip of your game and import it. The sets themselves are collected in the folder [`sets`](../sets/README.md) of the repository; it also says how to send your own set and which pictures may go into it. Every set of the catalogue is checked automatically: the program must import it in each of its languages.

## How access works

The QR code holds a link with a one-time code. The first device that opens it gets a key of its own, and the code stops working: a photo of the screen or a forwarded link lets nobody else in. A code that was not used lives for five minutes, then the page on the PC draws a new one. The device keeps the key in the browser and connects by itself from then on, without the QR code. Without a key the remote accepts no command.

The key belongs to the address the remote was opened at: a browser keeps it separately for every address. When the router gives the PC another IP address, the old link and the shortcut on the home screen stop opening, and at the new address the phone asks to scan the QR code again. The old entry stays in the list of devices; the cross removes it. To avoid this, give the PC a fixed address in the settings of the router, or choose the name of the computer (`pc-name.local`) in the list "Address" before you scan: it does not change with the IP. Not every phone and router opens a link by name, so check it once.

All paired devices are on the PC page in the list "Phones and tablets": who is connected now and when each was seen last. A click on a name renames the device, the cross disconnects it: the key stops working at once, the keys that are down are released, and the device asks to scan the QR code again. To connect one more, press "Connect another device". When the camera does not read the code, the button under it copies the link, which can be sent to the phone; it works once too.

The list is kept in `%LOCALAPPDATA%\GameRemote\game-remote.sqlite3`. The keys themselves are not there, only their hashes.

A phone that was connected to an earlier build with a shared key must be paired again: scan the QR code once more.

## Games with anti-cheat

Games that are protected against software input do not see the presses. Undecember behaves so: the game does not react to the buttons of the remote, also when Game Remote runs as administrator. The remote may say "Windows refused the key press" then, or it may show the press as sent: such protection is built in different ways. The program will not work around such protection.

## What to check and tell

- How the antivirus and SmartScreen react to the exe.
- Connect a second device, rename it and disconnect it. After the program is restarted, the phone must connect by itself, without the QR code. After the router is restarted too, when the address of the PC stayed the same.
- Tie a panel to the window of a game: outside the game the phone must say "The game window is not active", in the game the buttons must work. Is the game in the list of windows, and is there too much else in it?
- Does the remote open from the QR code at the first try? When the list of addresses on the PC page has the name of the computer (`pc-name.local`), does the remote open by it?
- Is it convenient to build a panel in the editor and to record shortcuts?
- An evening of play with a real panel: is a delay noticeable, are there missed presses or stuck keys?
- Does the screen of the phone go dark while the remote is open? The page plays an invisible video to keep the screen on; whether that works on your phone is not known in advance.
- The settings of the remote (the "⋮" button): which delay to the PC and back the remote shows on your home Wi-Fi, whether full screen works, whether the vibration is felt, how the shortcut on the home screen looks.
- Lock the phone for a minute and unlock it: the remote must be connected again within a couple of seconds.
- Are the size and the layout of the buttons convenient in portrait and in landscape?
- What happens when the Wi-Fi of the phone is turned off with a button held: the key must be released within 3 seconds.

The logs are in `%LOCALAPPDATA%\GameRemote\logs`.
