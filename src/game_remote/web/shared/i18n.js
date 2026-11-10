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
    'editor.panels': 'Panels',
    'editor.buttons': 'buttons: {n}',
    'editor.noPanels': 'No panels yet.',
    'editor.panelError': 'not loaded',
    'editor.files': 'For now a panel is a file: edit panel.json and the phone updates at once. The visual editor arrives in the next milestone.',
    'editor.openFolder': 'Open the panels folder',
    'editor.folder': 'Folder',
    'editor.recent': 'Recent presses',
    'editor.noRecent': 'Nothing yet. Press a button on the phone.',
    'editor.sent': 'sent',
    'editor.rejected': 'rejected',
    'editor.releaseKeys': 'Release all keys',
    'editor.fakeInput': 'Test mode: key presses are only recorded, nothing is sent to Windows.',
    'editor.offline': 'Game Remote is not running.',
    'editor.quit': 'Quit Game Remote',
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
    'editor.panels': 'Панели',
    'editor.buttons': 'кнопок: {n}',
    'editor.noPanels': 'Панелей пока нет.',
    'editor.panelError': 'не загружена',
    'editor.files': 'Пока панель — это файл: измените panel.json, и телефон обновится сразу. Визуальный редактор появится на следующей вехе.',
    'editor.openFolder': 'Открыть папку с панелями',
    'editor.folder': 'Папка',
    'editor.recent': 'Последние нажатия',
    'editor.noRecent': 'Пока пусто. Нажмите кнопку на телефоне.',
    'editor.sent': 'отправлено',
    'editor.rejected': 'отклонено',
    'editor.releaseKeys': 'Отпустить все клавиши',
    'editor.fakeInput': 'Тестовый режим: нажатия только записываются, в Windows ничего не отправляется.',
    'editor.offline': 'Game Remote не запущен.',
    'editor.quit': 'Выйти из Game Remote',
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
