// Interface texts for the editor and the phone panel. Names of games and
// buttons are shown as the user typed them and never go through here.
const TEXTS = {
  en: {
    'remote.scan': 'Scan the QR code on your PC screen to connect this device.',
    'remote.badKey': 'This link no longer works. Scan the QR code on your PC again.',
    'remote.connecting': 'Connecting…',
    'remote.online': 'Connected',
    'remote.offline': 'No connection to the PC',
    'remote.noPanels': 'There are no panels yet. Add one on the PC.',
    'remote.emptyPanel': 'This panel has no buttons yet.',
    'remote.choosePanel': 'Choose a game',
    'reason.elevated': 'The game runs as administrator. Start Game Remote as administrator too.',
    'reason.not_focused': 'The game window is not active.',
    'reason.input_error': 'Windows refused the key press.',
    'reason.unknown_button': 'This button no longer exists.',
    'editor.subtitle': 'Custom buttons for every game — on your phone or tablet',
    'editor.connect': 'Connect a phone',
    'editor.connectHint': 'Point the phone camera at the code. The phone and the PC must be on the same Wi-Fi.',
    'editor.address': 'Address',
    'editor.addressIp': 'network address',
    'editor.addressName': 'computer name, survives an IP change',
    'editor.noAddress': 'This PC has no network address. Connect it to your home network.',
    'editor.waiting': 'Waiting for a phone…',
    'editor.phones': 'Phones connected: {n}',
    'editor.trouble': 'The phone does not open the page?',
    'editor.trouble1': 'Allow Game Remote in Windows Firewall for private networks.',
    'editor.trouble2': 'In Windows the network must be marked as private, not public.',
    'editor.trouble3': 'Guest Wi-Fi often isolates devices: use the main network.',
    'editor.trouble4': 'Try another address from the list above.',
    'editor.panelError': 'not loaded',
    'editor.openFolder': 'Open the panels folder',
    'editor.recent': 'Recent presses',
    'editor.noRecent': 'Nothing yet. Press a button on the phone.',
    'editor.sent': 'sent',
    'editor.rejected': 'rejected',
    'editor.releaseKeys': 'Release all keys',
    'editor.fakeInput': 'Test mode: key presses are only recorded, nothing is sent to Windows.',
    'editor.offline': 'Game Remote is not running.',
    'editor.quit': 'Quit Game Remote',
    'editor.showQr': 'Show the QR code',
    'editor.hideQr': 'Hide the QR code',
    'editor.games': 'Games',
    'editor.addGame': 'Add a game',
    'editor.newGame': 'New game',
    'editor.unnamed': 'No name',
    'editor.noGame': 'Add a game to make its panel of buttons.',
    'editor.game': 'Game',
    'editor.gameName': 'Name',
    'editor.columns': 'Columns on the phone',
    'editor.deleteGame': 'Delete the game',
    'editor.confirmDeleteGame': 'Delete the game "{name}" and its buttons?',
    'editor.buttons': 'Buttons',
    'editor.addButton': 'Add a button',
    'editor.noLabel': 'no label',
    'editor.noKeys': 'no key yet',
    'editor.moveUp': 'Move up',
    'editor.moveDown': 'Move down',
    'editor.button': 'Button',
    'editor.label': 'Label',
    'editor.keys': 'Key or shortcut',
    'editor.record': 'Record',
    'editor.cancel': 'Cancel',
    'editor.pressKeys': 'Press the key or shortcut…',
    'editor.unknownKey': 'The key {key} is not supported.',
    'editor.manual': 'Choose by hand',
    'editor.manualHint': 'For shortcuts the browser keeps for itself, such as Ctrl+W or Alt+Tab.',
    'editor.type': 'What a touch does',
    'editor.typeTap': 'Tap',
    'editor.typeHold': 'Hold',
    'editor.typeTapHint': 'One short key press on every touch.',
    'editor.typeHoldHint': 'The key stays down while the finger is on the button.',
    'editor.color': 'Colour',
    'editor.noColor': 'No colour',
    'editor.customColor': 'Another colour',
    'editor.duplicate': 'Duplicate',
    'editor.deleteButton': 'Delete the button',
    'editor.preview': 'On the phone',
    'editor.rotate': 'Rotate',
    'editor.previewHint': 'Click a button to edit it.',
    'editor.save.pending': 'Saving…',
    'editor.save.saved': 'Saved',
    'editor.save.error': 'Not saved:',
    'editor.needName': 'the game needs a name.',
    'editor.cover': 'Cover',
    'editor.image': 'Picture',
    'editor.chooseImage': 'Choose a file',
    'editor.removeImage': 'Remove',
    'editor.imageError': 'This file is not a picture the program can read. Use PNG, JPEG or WebP.',
    'editor.language': 'Language',
    'editor.languageAuto': 'Auto: as in the browser',
  },
  ru: {
    'remote.scan': 'Отсканируйте QR-код на экране ПК, чтобы подключить это устройство.',
    'remote.badKey': 'Эта ссылка больше не работает. Отсканируйте QR-код на ПК ещё раз.',
    'remote.connecting': 'Подключение…',
    'remote.online': 'На связи',
    'remote.offline': 'Нет связи с ПК',
    'remote.noPanels': 'Панелей пока нет. Добавьте панель на ПК.',
    'remote.emptyPanel': 'На этой панели пока нет кнопок.',
    'remote.choosePanel': 'Выберите игру',
    'reason.elevated': 'Игра запущена от администратора. Запустите Game Remote тоже от администратора.',
    'reason.not_focused': 'Окно игры не активно.',
    'reason.input_error': 'Windows не принял нажатие.',
    'reason.unknown_button': 'Этой кнопки больше нет.',
    'editor.subtitle': 'Свои кнопки для каждой игры — на телефоне или планшете',
    'editor.connect': 'Подключить телефон',
    'editor.connectHint': 'Наведите камеру телефона на код. Телефон и ПК должны быть в одной Wi-Fi.',
    'editor.address': 'Адрес',
    'editor.addressIp': 'сетевой адрес',
    'editor.addressName': 'имя компьютера, не меняется при смене IP',
    'editor.noAddress': 'У этого ПК нет сетевого адреса. Подключите его к домашней сети.',
    'editor.waiting': 'Жду телефон…',
    'editor.phones': 'Подключено телефонов: {n}',
    'editor.trouble': 'Телефон не открывает страницу?',
    'editor.trouble1': 'Разрешите Game Remote в брандмауэре Windows для частных сетей.',
    'editor.trouble2': 'Сеть в Windows должна быть помечена как частная, а не общедоступная.',
    'editor.trouble3': 'Гостевая Wi-Fi часто изолирует устройства: используйте основную сеть.',
    'editor.trouble4': 'Попробуйте другой адрес из списка выше.',
    'editor.panelError': 'не загружена',
    'editor.openFolder': 'Открыть папку с панелями',
    'editor.recent': 'Последние нажатия',
    'editor.noRecent': 'Пока пусто. Нажмите кнопку на телефоне.',
    'editor.sent': 'отправлено',
    'editor.rejected': 'отклонено',
    'editor.releaseKeys': 'Отпустить все клавиши',
    'editor.fakeInput': 'Тестовый режим: нажатия только записываются, в Windows ничего не отправляется.',
    'editor.offline': 'Game Remote не запущен.',
    'editor.quit': 'Выйти из Game Remote',
    'editor.showQr': 'Показать QR-код',
    'editor.hideQr': 'Скрыть QR-код',
    'editor.games': 'Игры',
    'editor.addGame': 'Добавить игру',
    'editor.newGame': 'Новая игра',
    'editor.unnamed': 'Без названия',
    'editor.noGame': 'Добавьте игру, чтобы собрать для неё панель кнопок.',
    'editor.game': 'Игра',
    'editor.gameName': 'Название',
    'editor.columns': 'Колонок на телефоне',
    'editor.deleteGame': 'Удалить игру',
    'editor.confirmDeleteGame': 'Удалить игру «{name}» и её кнопки?',
    'editor.buttons': 'Кнопки',
    'editor.addButton': 'Добавить кнопку',
    'editor.noLabel': 'без подписи',
    'editor.noKeys': 'клавиша не задана',
    'editor.moveUp': 'Выше',
    'editor.moveDown': 'Ниже',
    'editor.button': 'Кнопка',
    'editor.label': 'Подпись',
    'editor.keys': 'Клавиша или сочетание',
    'editor.record': 'Записать',
    'editor.cancel': 'Отмена',
    'editor.pressKeys': 'Нажмите клавишу или сочетание…',
    'editor.unknownKey': 'Клавиша {key} не поддерживается.',
    'editor.manual': 'Выбрать вручную',
    'editor.manualHint': 'Для сочетаний, которые браузер забирает себе, например Ctrl+W или Alt+Tab.',
    'editor.type': 'Что делает касание',
    'editor.typeTap': 'Нажать',
    'editor.typeHold': 'Держать',
    'editor.typeTapHint': 'Одно короткое нажатие клавиши на каждое касание.',
    'editor.typeHoldHint': 'Клавиша зажата, пока палец на кнопке.',
    'editor.color': 'Цвет',
    'editor.noColor': 'Без цвета',
    'editor.customColor': 'Другой цвет',
    'editor.duplicate': 'Дублировать',
    'editor.deleteButton': 'Удалить кнопку',
    'editor.preview': 'На телефоне',
    'editor.rotate': 'Повернуть',
    'editor.previewHint': 'Щёлкните по кнопке, чтобы изменить её.',
    'editor.save.pending': 'Сохраняю…',
    'editor.save.saved': 'Сохранено',
    'editor.save.error': 'Не сохранено:',
    'editor.needName': 'у игры должно быть название.',
    'editor.cover': 'Обложка',
    'editor.image': 'Картинка',
    'editor.chooseImage': 'Выбрать файл',
    'editor.removeImage': 'Убрать',
    'editor.imageError': 'Этот файл не удалось прочитать как картинку. Подойдут PNG, JPEG и WebP.',
    'editor.language': 'Язык',
    'editor.languageAuto': 'Авто: как в браузере',
  },
};

export const LANGUAGES = Object.keys(TEXTS);

export function pickLanguage(preferred = navigator.languages || [navigator.language]) {
  for (const tag of preferred) {
    const short = String(tag || '').toLowerCase().split('-')[0];
    if (TEXTS[short]) return short;
  }
  return 'en';
}

let current = pickLanguage();

// A language chosen on the PC wins over the browser's; null or "auto" gives
// the choice back to the browser.
export function setLanguage(code) {
  current = TEXTS[code] ? code : pickLanguage();
}

export function language() {
  return current;
}

export function t(key, params = {}) {
  const text = TEXTS[current][key] ?? TEXTS.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? ''));
}

// Fills every element that has data-i18n="key" and sets <html lang>.
export function applyTexts(root = document) {
  document.documentElement.lang = current;
  for (const el of root.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);
}

export function allKeys() {
  return Object.fromEntries(LANGUAGES.map((lang) => [lang, Object.keys(TEXTS[lang])]));
}
