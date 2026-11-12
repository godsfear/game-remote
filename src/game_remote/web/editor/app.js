import {
  applyTexts, browserLanguages, language as currentLanguage, setLanguage, t,
} from '/shared/i18n.js';
import {
  renderGrid, renderTabs, screenIndex, screenView, showBackground,
} from '/shared/panel-view.js';

const SAVE_DELAY_MS = 400;
const PANEL_STORE = 'gameRemote.editor.panel';
const IMAGE_MAX_SIDE = 512; // pictures are shrunk to this before upload
const BACKGROUND_MAX_SIDE = 1920; // a background fills the whole phone screen
const MAX_SCREENS = 8; // the PC accepts no more
const COLORS = ['#2b5fd9', '#7a4fd1', '#2f9e62', '#1f8a8a', '#c9822b', '#c44f6a', '#8a8f9c'];

const el = Object.fromEntries([
  'save-state', 'fake', 'offline', 'game-list', 'panel-errors', 'add-game', 'connect', 'phones',
  'show-qr', 'connect-body', 'qr', 'no-address', 'address', 'address-row', 'no-game', 'game-card',
  'game-name', 'columns', 'columns-less', 'columns-more', 'delete-game', 'buttons-card',
  'button-list', 'add-button', 'button-card', 'button-label', 'combo', 'record', 'combo-error',
  'manual', 'manual-key', 'button-type', 'type-hint', 'colors', 'duplicate-button',
  'delete-button', 'preview-card', 'rotate', 'phone', 'phone-name', 'preview', 'preview-empty',
  'recent', 'release', 'version', 'open-folder', 'quit', 'cover-thumb', 'cover-choose',
  'cover-remove', 'image-thumb', 'image-choose', 'image-remove', 'file', 'language',
  'device-list', 'copy-link', 'background-thumb', 'background-choose', 'background-remove',
  'shape', 'window-name', 'window-choose', 'window-remove', 'window-list',
  'window-hint', 'add-screen', 'screen-tabs', 'screen-row', 'screen-name', 'delete-screen',
  'screens-hint', 'preview-screens', 'button-screen', 'button-screen-field',
  'import-set', 'export-set', 'set-file', 'export-dialog', 'export-language',
  'same-dialog', 'same-text', 'update', 'update-text', 'check-updates',
  'toggle-on', 'toggle-on-field',
].map((id) => [id, document.getElementById(id)]));

const store = {
  get(name) { try { return localStorage.getItem(name); } catch { return null; } },
  set(name, value) { try { localStorage.setItem(name, value); } catch { /* private mode */ } },
};

// ---- state -----------------------------------------------------------------

let panels = []; // as the PC stores them, plus buttons that have no keys yet
let panelErrors = {};
let versions = {}; // panel id -> file name -> the time of the picture on the PC
let revision = 0; // the last state of the panel files this page knows
let currentId = store.get(PANEL_STORE);
let selectedId = null; // the button being edited
let screen = 0; // the screen of the current game that the list and the preview show
let keyLabels = new Map(); // key code -> short label
let modifiers = [];
let wide = false;
let showQrAnyway = false;
let phones = 0;
let devices = []; // phones and tablets paired with this PC
let renaming = null; // id of the device whose name is being typed
let links = []; // addresses for the QR code, with the one-time code inside
let pairing = 0; // changes when the code does
let windowChoice = null; // open windows offered for the current game, or null
let elevatedWindow = null; // id of the game that was just bound to an elevated program
let capture = null; // { down: Set, all: [] } while a combo is being recorded
let saveTimer = 0;
let saving = null; // the save that runs now, as a promise
let savingCheck = false; // the box of the update check is being saved
const dirty = new Set(); // ids of panels with changes not yet on the PC

// The name of each kind of button; its hint has the same key with "Hint".
const TYPE_TEXTS = { tap: 'editor.typeTap', hold: 'editor.typeHold', toggle: 'editor.typeToggle' };

const currentPanel = () => panels.find((panel) => panel.id === currentId) || null;
const selectedButton = () => currentPanel()?.buttons.find((b) => b.id === selectedId) || null;
const currentScreen = () => (currentPanel() ? screenIndex(currentPanel(), screen) : 0);
const screenButtons = (panel) => screenView(panel, currentScreen()).buttons;
// A screen whose name was wiped keeps a name: the file needs one.
const screenNames = (panel) => panel.screens.map(
  (name, index) => name.trim() || t('editor.screenDefault', { n: index + 1 }),
);

async function api(path, options = {}) {
  const init = { ...options };
  if (init.body !== undefined) {
    init.body = JSON.stringify(init.body);
    init.headers = { 'Content-Type': 'application/json' };
  }
  const response = await fetch(path, init);
  let data = null;
  try { data = await response.json(); } catch { /* no body */ }
  if (!response.ok) {
    const error = new Error(data?.error || `${path}: ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

function comboLabel(keys) {
  if (!keys) return '';
  return keys.split('+').map((code) => keyLabels.get(code) || code).join('+');
}

function newButtonId(panel) {
  for (;;) {
    const id = `b${Math.random().toString(36).slice(2, 8)}`;
    if (!panel.buttons.some((button) => button.id === id)) return id;
  }
}

// ---- small DOM helpers -----------------------------------------------------

function node(tag, className, text) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== undefined) result.textContent = text;
  return result;
}

function setSaveState(state, detail = '') {
  el['save-state'].className = state === 'error' ? 'error' : 'hint';
  el['save-state'].textContent = state ? t(`editor.save.${state}`) + (detail ? ` ${detail}` : '') : '';
}

// ---- loading and saving ----------------------------------------------------

function takePanels(data) {
  // A game whose changes did not reach the PC keeps what the page has.
  const unsaved = new Map(panels.filter((panel) => dirty.has(panel.id)).map((panel) => [panel.id, panel]));
  panels = data.panels.map((panel) => unsaved.get(panel.id) || panel);
  panelErrors = data.errors;
  versions = data.versions || {};
  revision = data.revision;
  if (!currentPanel()) currentId = panels[0]?.id || null;
  if ((selectedButton()?.screen || 0) !== currentScreen()) selectedId = null;
  renderAll();
}

async function loadPanels() {
  takePanels(await api('/api/panels'));
}

function changed() {
  const panel = currentPanel();
  if (!panel) return;
  dirty.add(panel.id);
  setSaveState('pending');
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, SAVE_DELAY_MS);
}

// What goes into the file: a button without keys is not a button yet.
function forFile(panel) {
  return {
    format: 1,
    name: panel.name.trim(),
    columns: panel.columns,
    window: panel.window || null,
    cover: panel.cover || null,
    background: panel.background || null,
    shape: panel.shape || 'fill',
    screens: screenNames(panel),
    buttons: panel.buttons.filter((button) => button.keys).map((button) => ({
      id: button.id,
      label: button.label,
      keys: button.keys,
      type: button.type,
      // Only a toggle starts on, and the file says so only when it does.
      ...(button.type === 'toggle' && button.on ? { on: true } : {}),
      color: button.color || null,
      image: button.image || null,
      screen: button.screen || 0,
    })),
  };
}

// Writes every changed game to the PC. A call during a save waits for that
// save, which takes the games changed meanwhile too: whoever awaits this can
// rely on the PC having what the page shows, unless a game is still in `dirty`.
function save() {
  clearTimeout(saveTimer);
  saving ||= writeChanges().finally(() => { saving = null; });
  return saving;
}

async function writeChanges() {
  // Panels that did not reach the PC stay marked as changed: the next change
  // or closing the tab tries again, and until then the page does not replace
  // the edit with the older file.
  const failed = [];
  let problem = '';
  try {
    while (dirty.size) {
      const id = dirty.values().next().value;
      dirty.delete(id);
      const panel = panels.find((candidate) => candidate.id === id);
      if (!panel) continue;
      if (!panel.name.trim()) {
        failed.push(id);
        problem = t('editor.needName');
        continue;
      }
      try {
        const result = await api(`/api/panels/${id}`, { method: 'PUT', body: forFile(panel) });
        revision = result.revision;
      } catch (error) {
        if (error.status !== 404) failed.push(id); // 404: the game was deleted meanwhile
        problem = error.message;
      }
    }
  } finally {
    for (const id of failed) dirty.add(id);
  }
  setSaveState(problem ? 'error' : 'saved', problem);
}

// ---- games -----------------------------------------------------------------

function renderGames() {
  el['game-list'].replaceChildren(...panels.map((panel) => {
    const button = node('button');
    button.type = 'button';
    button.dataset.panel = panel.id;
    button.setAttribute('aria-current', String(panel.id === currentId));
    if (panel.cover) {
      const cover = node('span', 'cover');
      cover.style.backgroundImage = imageUrl(panel, panel.cover);
      button.append(cover);
    }
    button.append(
      node('span', 'name', panel.name || t('editor.unnamed')),
      node('span', 'count', String(panel.buttons.length)),
    );
    button.addEventListener('click', () => selectPanel(panel.id));
    const li = node('li');
    li.append(button);
    return li;
  }));
  el['panel-errors'].replaceChildren(...Object.entries(panelErrors).map(([id, error]) => {
    const li = node('li');
    li.append(node('span', '', `${id} — ${t('editor.panelError')}`), node('small', '', error));
    return li;
  }));
}

function selectPanel(id) {
  if (id === currentId) return;
  stopCapture();
  windowChoice = null;
  currentId = id;
  selectedId = null;
  screen = 0;
  store.set(PANEL_STORE, id || '');
  renderAll();
}

async function addGame() {
  await save();
  const data = await api('/api/panels', { method: 'POST', body: { name: t('editor.newGame') } });
  currentId = data.id;
  selectedId = null;
  screen = 0;
  store.set(PANEL_STORE, currentId);
  takePanels(data);
  el['game-name'].focus();
  el['game-name'].select();
}

async function deleteGame() {
  const panel = currentPanel();
  if (!panel || !window.confirm(t('editor.confirmDeleteGame', { name: panel.name }))) return;
  clearTimeout(saveTimer);
  dirty.delete(panel.id);
  await api(`/api/panels/${panel.id}`, { method: 'DELETE' });
  currentId = null;
  screen = 0;
  await loadPanels();
  setSaveState('saved');
}

// ---- sets: a game as a file to share ----------------------------------------

// A set is marked with the language of its texts. Only the author knows it:
// the page asks, and offers its own language as a guess.
function askExportLanguage() {
  if (!currentPanel()) return;
  el['export-language'].value = currentLanguage();
  el['export-dialog'].returnValue = '';
  el['export-dialog'].showModal();
  el['export-language'].select();
}

// Runs when that question is answered. The zip holds the game as the PC has
// it, so a game that could not be saved is not exported: the page says why.
async function exportSet() {
  const panel = currentPanel();
  if (!panel || el['export-dialog'].returnValue !== 'ok') return;
  await save();
  if (dirty.has(panel.id)) return;
  const link = node('a');
  link.href = `/api/panels/${panel.id}/export?language=${el['export-language'].value.toLowerCase()}`;
  link.download = '';
  link.click();
}

// The languages to look for in a set, best first: the one chosen on the PC for
// every device, then those of this browser. The interface itself has fewer.
function wantedLanguages() {
  const chosen = el.language.value === 'auto' ? [] : [el.language.value];
  return [...new Set([...chosen, ...browserLanguages()])]
    .filter((code) => /^[a-z]{2}$/.test(code)).slice(0, 10);
}

// The set becomes a game, in the first of these languages the set has. When a
// game of that name is on the PC already, the PC changes nothing and says so:
// the page asks, and the answer sends the same file again (see the wiring).
async function importSet(sameName = 'ask') {
  const [file] = el['set-file'].files;
  if (!file) return;
  await save();
  const query = `languages=${wantedLanguages().join(',')}&same_name=${sameName}`;
  const response = await fetch(`/api/sets?${query}`, {
    method: 'POST',
    body: file,
    headers: { 'Content-Type': 'application/zip' },
  });
  let data = null;
  try { data = await response.json(); } catch { /* no body */ }
  if (response.status === 409 && data?.error === 'same_name') {
    el['same-text'].textContent = t('editor.sameName', { name: data.name });
    el['same-dialog'].returnValue = '';
    el['same-dialog'].showModal();
    return;
  }
  if (!response.ok) throw new Error(`${t('editor.importError')} ${data?.error || response.status}`);
  dirty.delete(data.id); // a game that was replaced is what the set says now
  currentId = data.id;
  selectedId = null;
  screen = 0;
  store.set(PANEL_STORE, currentId);
  takePanels(data);
  if (!dirty.size) setSaveState('saved'); // else the reason of the failed save stays
}

function fillGameForm() {
  const panel = currentPanel();
  for (const id of ['game-card', 'buttons-card', 'preview-card']) el[id].hidden = !panel;
  el['no-game'].hidden = Boolean(panel);
  if (!panel) return;
  if (document.activeElement !== el['game-name']) el['game-name'].value = panel.name;
  el.columns.textContent = String(panel.columns);
  el['columns-less'].disabled = panel.columns <= 1;
  el['columns-more'].disabled = panel.columns >= 8;
  showThumb(el['cover-thumb'], el['cover-remove'], panel, panel.cover);
  showThumb(el['background-thumb'], el['background-remove'], panel, panel.background);
  for (const choice of el.shape.children) {
    choice.setAttribute('aria-pressed', String(choice.dataset.shape === (panel.shape || 'fill')));
  }
  fillWindow(panel);
}

// ---- the game's window -----------------------------------------------------

// A panel bound to a program presses keys only while that program's window is
// active, so a press never lands in a chat or a browser by mistake.
function fillWindow(panel) {
  el['window-name'].textContent = panel.window || t('editor.anyWindow');
  el['window-name'].classList.toggle('any', !panel.window);
  el['window-remove'].hidden = !panel.window;
  const elevated = panel.window && elevatedWindow === panel.id;
  el['window-hint'].classList.toggle('warn', Boolean(elevated));
  el['window-hint'].textContent = t(
    elevated ? 'reason.elevated' : panel.window ? 'editor.windowBound' : 'editor.windowAny',
  );
  el['window-list'].hidden = !windowChoice;
  if (!windowChoice) return;
  const items = windowChoice.windows.map((found) => {
    const button = node('button');
    button.type = 'button';
    button.dataset.exe = found.exe;
    button.append(node('span', '', found.title), node('small', '', found.exe));
    if (found.elevated) button.append(node('small', 'warn', t('editor.windowElevated')));
    button.addEventListener('click', () => setWindow(found.exe, found.elevated));
    const li = node('li');
    li.append(button);
    return li;
  });
  if (!items.length) {
    items.push(node('li', 'empty', t(windowChoice.supported ? 'editor.noWindows' : 'editor.windowsOnly')));
  }
  el['window-list'].replaceChildren(...items);
}

async function chooseWindow() {
  windowChoice = windowChoice ? null : await api('/api/windows');
  fillWindow(currentPanel());
}

function setWindow(exe, elevated = false) {
  const panel = currentPanel();
  panel.window = exe;
  elevatedWindow = exe && elevated ? panel.id : null;
  windowChoice = null;
  fillWindow(panel);
  changed();
}

function changeColumns(step) {
  const panel = currentPanel();
  panel.columns = Math.min(8, Math.max(1, panel.columns + step));
  fillGameForm();
  renderPreview();
  changed();
}

// ---- screens of the game ---------------------------------------------------

// The buttons of one game can be grouped into screens; the phone switches
// between them with the same tabs. A game without screens has them all on one.
function renderScreens() {
  const panel = currentPanel();
  if (!panel) return;
  const names = screenNames(panel);
  el['add-screen'].disabled = names.length >= MAX_SCREENS;
  for (const id of ['screen-tabs', 'screen-row', 'screens-hint']) el[id].hidden = !names.length;
  renderTabs(el['screen-tabs'], names, currentScreen(), showScreen);
  if (names.length && document.activeElement !== el['screen-name']) {
    el['screen-name'].value = panel.screens[currentScreen()];
  }
}

function showScreen(index) {
  if (index === currentScreen()) return;
  stopCapture();
  screen = index;
  selectedId = null;
  renderAll();
}

function addScreen() {
  const panel = currentPanel();
  const name = () => t('editor.screenDefault', { n: panel.screens.length + 1 });
  // The buttons made so far are a screen too, so it gets a name as well.
  if (!panel.screens.length) panel.screens.push(name());
  panel.screens.push(name());
  showScreen(panel.screens.length - 1);
  changed();
  el['screen-name'].focus();
  el['screen-name'].select();
}

function deleteScreen() {
  const panel = currentPanel();
  const index = currentScreen();
  const count = screenButtons(panel).length;
  const question = t('editor.confirmDeleteScreen', { name: screenNames(panel)[index], count });
  if (count && !window.confirm(question)) return;
  stopCapture();
  panel.buttons = panel.buttons.filter((button) => (button.screen || 0) !== index);
  for (const button of panel.buttons) if (button.screen > index) button.screen -= 1;
  panel.screens.splice(index, 1);
  if (panel.screens.length < 2) panel.screens = []; // one screen is a game without screens
  screen = Math.max(0, index - 1);
  selectedId = null;
  renderAll();
  changed();
}

// ---- list of buttons -------------------------------------------------------

let dragged = null;

function renderButtons() {
  const panel = currentPanel();
  if (!panel) return;
  const shown = screenButtons(panel);
  el['button-list'].replaceChildren(...shown.map((button, index) => {
    const li = node('li');
    li.dataset.button = button.id;
    li.draggable = true;
    li.setAttribute('aria-current', String(button.id === selectedId));
    const swatch = node('span', 'swatch');
    if (button.color) swatch.style.setProperty('--color', button.color);
    const name = node('span', button.label ? 'name' : 'name unnamed', button.label || t('editor.noLabel'));
    const keys = node('span', button.keys ? 'keys' : 'keys missing', button.keys ? comboLabel(button.keys) : t('editor.noKeys'));
    const kind = node('span', 'kind', t(TYPE_TEXTS[button.type] || TYPE_TEXTS.tap));
    const move = node('span', 'move');
    for (const [step, sign, key] of [[-1, '↑', 'editor.moveUp'], [1, '↓', 'editor.moveDown']]) {
      const arrow = node('button', '', sign);
      arrow.type = 'button';
      arrow.title = t(key);
      arrow.setAttribute('aria-label', t(key));
      arrow.disabled = index + step < 0 || index + step >= shown.length;
      arrow.addEventListener('click', (event) => {
        event.stopPropagation();
        moveButton(index, index + step);
      });
      move.append(arrow);
    }
    li.append(swatch, name, keys, kind, move);
    li.addEventListener('click', () => selectButton(button.id));
    li.addEventListener('dragstart', (event) => {
      dragged = index;
      li.classList.add('dragging');
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', button.id);
    });
    li.addEventListener('dragend', () => {
      dragged = null;
      for (const item of el['button-list'].children) item.classList.remove('dragging', 'drop-target');
    });
    li.addEventListener('dragover', (event) => {
      if (dragged === null) return;
      event.preventDefault();
      li.classList.add('drop-target');
    });
    li.addEventListener('dragleave', () => li.classList.remove('drop-target'));
    li.addEventListener('drop', (event) => {
      event.preventDefault();
      if (dragged !== null) moveButton(dragged, index);
    });
    return li;
  }));
}

// `from` and `to` count the buttons of the screen that is shown.
function moveButton(from, to) {
  const panel = currentPanel();
  const shown = screenButtons(panel);
  if (from === to || to < 0 || to >= shown.length) return;
  panel.buttons.splice(panel.buttons.indexOf(shown[from]), 1);
  const target = panel.buttons.indexOf(shown[to]);
  panel.buttons.splice(from < to ? target + 1 : target, 0, shown[from]);
  renderButtons();
  renderPreview();
  changed();
}

function selectButton(id) {
  if (id !== selectedId) stopCapture();
  selectedId = id;
  renderButtons();
  fillButtonForm();
  renderPreview();
}

function addButton() {
  const panel = currentPanel();
  const button = {
    id: newButtonId(panel), label: '', keys: '', type: 'tap', color: null, image: null,
    screen: currentScreen(),
  };
  panel.buttons.push(button);
  selectButton(button.id);
  renderGames();
  el['button-label'].focus();
  // Nothing to save yet: the button gets into the file once it has keys.
}

function duplicateButton() {
  const panel = currentPanel();
  const button = selectedButton();
  const copy = { ...button, id: newButtonId(panel) };
  panel.buttons.splice(panel.buttons.indexOf(button) + 1, 0, copy);
  selectButton(copy.id);
  renderGames();
  changed();
}

function deleteButton() {
  const panel = currentPanel();
  const index = panel.buttons.indexOf(selectedButton());
  if (index < 0) return;
  stopCapture();
  panel.buttons.splice(index, 1);
  selectedId = null;
  renderAll();
  changed();
}

// ---- one button ------------------------------------------------------------

function fillButtonForm() {
  const button = selectedButton();
  el['button-card'].hidden = !button;
  if (!button) return;
  if (document.activeElement !== el['button-label']) el['button-label'].value = button.label;
  showCombo();
  for (const choice of el['button-type'].children) {
    choice.setAttribute('aria-pressed', String(choice.dataset.type === button.type));
  }
  el['type-hint'].textContent = t(`${TYPE_TEXTS[button.type] || TYPE_TEXTS.tap}Hint`);
  el['toggle-on-field'].hidden = button.type !== 'toggle';
  el['toggle-on'].checked = Boolean(button.on);
  for (const swatch of el.colors.querySelectorAll('button')) {
    swatch.setAttribute('aria-pressed', String((swatch.dataset.color || null) === (button.color || null)));
  }
  el.colors.querySelector('input').value = button.color || '#2b3040';
  showThumb(el['image-thumb'], el['image-remove'], currentPanel(), button.image);
  fillManual(button);
  const names = screenNames(currentPanel());
  el['button-screen-field'].hidden = names.length < 2;
  el['button-screen'].replaceChildren(...names.map((name, index) => {
    const option = node('option', '', name);
    option.value = String(index);
    return option;
  }));
  el['button-screen'].value = String(button.screen || 0);
}

function showCombo() {
  const button = selectedButton();
  if (!button) return;
  el.combo.classList.toggle('recording', Boolean(capture));
  el.record.textContent = t(capture ? 'editor.cancel' : 'editor.record');
  if (capture) {
    el.combo.classList.remove('missing');
    el.combo.textContent = capture.all.length ? comboLabel(capture.all.join('+')) : t('editor.pressKeys');
    return;
  }
  el.combo.classList.toggle('missing', !button.keys);
  el.combo.textContent = button.keys ? comboLabel(button.keys) : t('editor.noKeys');
}

function setKeys(codes) {
  const button = selectedButton();
  const unknown = codes.find((code) => !keyLabels.has(code));
  if (unknown) {
    el['combo-error'].textContent = t('editor.unknownKey', { key: unknown });
    el['combo-error'].hidden = false;
    return;
  }
  el['combo-error'].hidden = true;
  // Modifiers first, in a fixed order, like the PC stores them.
  const ordered = [
    ...modifiers.filter((code) => codes.includes(code)),
    ...codes.filter((code) => !modifiers.includes(code)),
  ];
  const wasNew = !button.keys;
  button.keys = ordered.join('+');
  fillButtonForm();
  renderButtons();
  renderPreview();
  if (wasNew) renderGames();
  changed();
}

// Recording: every key pressed until all of them are released again.
function startCapture() {
  capture = { down: new Set(), all: [] };
  el['combo-error'].hidden = true;
  el.record.blur();
  showCombo();
}

function stopCapture() {
  if (!capture) return;
  capture = null;
  showCombo();
}

window.addEventListener('keydown', (event) => {
  if (!capture) return;
  event.preventDefault();
  event.stopPropagation();
  if (event.repeat || !event.code) return;
  capture.down.add(event.code);
  if (!capture.all.includes(event.code)) capture.all.push(event.code);
  showCombo();
}, true);

window.addEventListener('keyup', (event) => {
  if (!capture) return;
  event.preventDefault();
  event.stopPropagation();
  // A release of a key that went down before the recording began is not part of it.
  capture.down.delete(event.code);
  if (capture.down.size === 0 && capture.all.length) {
    const codes = capture.all;
    capture = null;
    setKeys(codes);
    showCombo();
  }
}, true);

window.addEventListener('blur', stopCapture);
// Whoever goes to a field means to type there: the keys are text, not a
// shortcut. This covers the fields of a dialog too.
document.addEventListener('focusin', (event) => {
  if (event.target.matches('input, select, textarea')) stopCapture();
});

function fillManual(button) {
  const codes = button.keys ? button.keys.split('+') : [];
  for (const box of el.manual.querySelectorAll('input[data-mod]')) {
    const right = box.dataset.mod.replace('Left', 'Right');
    box.checked = codes.includes(box.dataset.mod) || codes.includes(right);
  }
  el['manual-key'].value = codes.find((code) => !modifiers.includes(code)) || '';
}

function manualChanged() {
  const codes = [...el.manual.querySelectorAll('input[data-mod]:checked')].map((box) => box.dataset.mod);
  if (el['manual-key'].value) codes.push(el['manual-key'].value);
  if (codes.length) setKeys(codes);
}

function setColor(color) {
  selectedButton().color = color;
  fillButtonForm();
  renderButtons();
  renderPreview();
  changed();
}

function buildColors() {
  const none = node('button');
  none.type = 'button';
  none.title = t('editor.noColor');
  none.setAttribute('aria-label', t('editor.noColor'));
  none.addEventListener('click', () => setColor(null));
  const swatches = COLORS.map((color) => {
    const swatch = node('button');
    swatch.type = 'button';
    swatch.dataset.color = color;
    swatch.style.setProperty('--color', color);
    swatch.setAttribute('aria-label', color);
    swatch.addEventListener('click', () => setColor(color));
    return swatch;
  });
  const custom = document.createElement('input');
  custom.type = 'color';
  custom.title = t('editor.customColor');
  custom.setAttribute('aria-label', t('editor.customColor'));
  custom.addEventListener('input', () => setColor(custom.value));
  el.colors.replaceChildren(none, ...swatches, custom);
}

// ---- pictures --------------------------------------------------------------

// The address carries the time of the file, as the PC told it: a picture that
// was replaced by one of the same name is fetched again.
const filePath = (panel, name) => {
  const version = versions[panel.id]?.[name];
  return `/panel-files/${panel.id}/${encodeURIComponent(name)}${version ? `?v=${version}` : ''}`;
};
const imageUrl = (panel, name) => `url("${filePath(panel, name)}")`;

function showThumb(thumb, removeButton, panel, name) {
  thumb.style.backgroundImage = name ? imageUrl(panel, name) : '';
  thumb.classList.toggle('set', Boolean(name));
  removeButton.hidden = !name;
}

// A photo from a camera is far bigger than a button on a phone screen, so the
// page shrinks the picture and sends the small copy.
async function shrink(file, maxSide = IMAGE_MAX_SIDE) {
  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new Error(t('editor.imageError'));
  }
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  for (const type of ['image/webp', 'image/png']) {
    const blob = await new Promise((resolve) => { canvas.toBlob(resolve, type, 0.85); });
    if (blob && blob.type === type) return blob;
  }
  throw new Error(t('editor.imageError'));
}

let fileTarget = null; // 'cover', 'background' or the id of the button that gets the picture

function chooseFile(target) {
  fileTarget = target;
  el.file.value = '';
  el.file.click();
}

async function fileChosen() {
  const [file] = el.file.files;
  const panel = currentPanel();
  if (!file || !panel) return;
  const blob = await shrink(file, fileTarget === 'background' ? BACKGROUND_MAX_SIDE : IMAGE_MAX_SIDE);
  const response = await fetch(`/api/panels/${panel.id}/images`, {
    method: 'POST',
    body: blob,
    headers: { 'Content-Type': blob.type },
  });
  if (!response.ok) throw new Error(t('editor.imageError'));
  const { name } = await response.json();
  setPicture(panel, fileTarget, name);
}

function setPicture(panel, target, name) {
  if (target === 'cover' || target === 'background') {
    panel[target] = name;
  } else {
    const button = panel.buttons.find((candidate) => candidate.id === target);
    if (!button) return;
    button.image = name;
    if (!button.keys) { // a draft: nothing to save yet
      renderAll();
      return;
    }
  }
  renderAll();
  dirty.add(panel.id);
  setSaveState('pending');
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, SAVE_DELAY_MS);
}

// ---- preview ---------------------------------------------------------------

function renderPreview() {
  const panel = currentPanel();
  if (!panel) return;
  el['phone-name'].textContent = panel.name || 'Game Remote';
  el.phone.classList.toggle('wide', wide);
  showBackground(el.phone, panel.background ? filePath(panel, panel.background) : null);
  const names = screenNames(panel);
  el['preview-screens'].hidden = names.length < 2;
  renderTabs(el['preview-screens'], names, currentScreen(), showScreen);
  const buttons = screenButtons(panel);
  const shown = {
    columns: panel.columns,
    shape: panel.shape,
    buttons: buttons.map((button) => ({
      ...button,
      image: button.image ? filePath(panel, button.image) : null,
    })),
  };
  el['preview-empty'].hidden = shown.buttons.length > 0;
  el.preview.hidden = shown.buttons.length === 0;
  const nodes = renderGrid(el.preview, shown, { wide });
  nodes.forEach((buttonNode, index) => {
    const button = buttons[index];
    buttonNode.classList.toggle('selected', button.id === selectedId);
    buttonNode.classList.toggle('draft', !button.keys); // not on the phone yet
    buttonNode.addEventListener('click', () => selectButton(button.id));
  });
}

function renderAll() {
  renderGames();
  fillGameForm();
  renderScreens();
  renderButtons();
  fillButtonForm();
  renderPreview();
}

// ---- phone connection, status ----------------------------------------------

function showQr() {
  el.qr.src = `/api/qr/${el.address.value}.svg?code=${pairing}`;
  el.qr.hidden = false;
}

async function loadLinks() {
  const data = await api('/api/links');
  links = data.links;
  pairing = data.pairing;
  const chosen = el.address.value;
  el.address.replaceChildren(...links.map((link, index) => {
    const option = node('option', '', `${link.host} — ${t(link.kind === 'name' ? 'editor.addressName' : 'editor.addressIp')}`);
    option.value = String(index);
    return option;
  }));
  el['no-address'].hidden = links.length > 0;
  el['address-row'].hidden = links.length < 2;
  el['copy-link'].hidden = !links.length;
  if (!links.length) {
    el.qr.hidden = true;
    return;
  }
  if (chosen && Number(chosen) < links.length) el.address.value = chosen;
  showQr();
}

// A paired device comes back by itself, so with one in the list the QR code
// only takes space and folds away.
function renderConnect() {
  el.phones.textContent = phones ? t('editor.phones', { n: phones }) : t('editor.waiting');
  el.phones.classList.toggle('waiting', !phones);
  el['show-qr'].hidden = !devices.length;
  el['show-qr'].textContent = t(showQrAnyway ? 'editor.hideQr' : 'editor.showQr');
  el['connect-body'].hidden = devices.length > 0 && !showQrAnyway;
  renderDevices();
}

function lastSeen(device) {
  if (device.online) return t('editor.deviceOnline');
  if (!device.last_seen) return '';
  const when = new Date(device.last_seen * 1000).toLocaleString(currentLanguage(), {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
  return t('editor.deviceSeen', { when });
}

function renderDevices() {
  if (renaming) return; // do not take the field away from under the user's hands
  el['device-list'].replaceChildren(...devices.map((device) => {
    const li = node('li', device.online ? 'online' : '');
    li.dataset.device = device.id;
    const name = node('button', 'device-name', device.name);
    name.type = 'button';
    name.title = t('editor.renameDevice');
    name.addEventListener('click', () => startRename(device, name));
    const remove = node('button', 'quiet danger remove', '✕');
    remove.type = 'button';
    remove.title = t('editor.removeDevice');
    remove.setAttribute('aria-label', t('editor.removeDevice'));
    remove.addEventListener('click', report(() => removeDevice(device)));
    li.append(node('span', 'dot'), name, remove, node('span', 'seen', lastSeen(device)));
    return li;
  }));
}

function startRename(device, nameButton) {
  renaming = device.id;
  const input = document.createElement('input');
  input.type = 'text';
  input.maxLength = 40;
  input.value = device.name;
  let done = false;
  const finish = report(async (keep) => {
    if (done) return;
    done = true;
    renaming = null;
    const name = input.value.trim();
    if (keep && name && name !== device.name) {
      devices = (await api(`/api/devices/${device.id}`, { method: 'PUT', body: { name } })).devices;
    }
    renderDevices();
  });
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') finish(true);
    if (event.key === 'Escape') finish(false);
  });
  input.addEventListener('blur', () => finish(true));
  nameButton.replaceWith(input);
  input.focus();
  input.select();
}

async function removeDevice(device) {
  if (!window.confirm(t('editor.confirmRemoveDevice', { name: device.name }))) return;
  devices = (await api(`/api/devices/${device.id}`, { method: 'DELETE' })).devices;
  renderConnect();
}

async function copyLink() {
  const link = links[Number(el.address.value)] || links[0];
  if (!link) return;
  await navigator.clipboard.writeText(link.url);
  el['copy-link'].textContent = t('editor.copied');
  setTimeout(() => { el['copy-link'].textContent = t('editor.copyLink'); }, 2000);
}

function renderStatus(status) {
  el.offline.hidden = true;
  el.fake.hidden = !status.fake_input;
  el.version.textContent = `Game Remote ${status.version}`;
  el.update.hidden = !status.update;
  el['update-text'].textContent = status.update ? t('editor.update', { version: status.update }) : '';
  // The box follows the PC: the setting may have been changed in another window.
  if (!savingCheck) el['check-updates'].checked = status.check_updates;
  phones = status.phones;
  devices = status.devices;
  renderConnect();
  // The code inside the QR link was used or grew old: draw the new one.
  if (status.pairing !== pairing) loadLinks().catch(() => {});

  el.recent.replaceChildren(...status.recent.slice(0, 6).map((press) => {
    const what = node('span', '', `${press.panel} · ${press.button}`);
    what.append(node('span', 'keys', press.keys));
    const result = press.ok ? t('editor.sent') : `${t('editor.rejected')}: ${t(`reason.${press.reason}`)}`;
    const li = node('li', press.ok ? '' : 'rejected');
    li.append(what, node('span', 'result', result));
    return li;
  }));
  if (!status.recent.length) el.recent.append(node('li', 'empty', t('editor.noRecent')));

  // The panel files changed without this page: someone edited them by hand.
  if (status.revision !== revision && !dirty.size && !saving) loadPanels().catch(() => {});
}

async function refresh() {
  try {
    renderStatus(await api('/api/status'));
  } catch {
    el.offline.hidden = false;
  }
}

// ---- wiring ----------------------------------------------------------------

// What an action could not do is said where the state of the save is, in its
// own words: "not saved" would be untrue, the edits are on the PC.
function report(action) {
  return (...args) => Promise.resolve(action(...args)).catch((error) => {
    el['save-state'].className = 'error';
    el['save-state'].textContent = error.message;
  });
}

el['add-game'].addEventListener('click', report(addGame));
el['delete-game'].addEventListener('click', report(deleteGame));
el['export-set'].addEventListener('click', askExportLanguage);
el['export-dialog'].addEventListener('close', report(exportSet));
el['import-set'].addEventListener('click', () => {
  el['set-file'].value = '';
  el['set-file'].click();
});
el['set-file'].addEventListener('change', report(() => importSet()));
el['same-dialog'].addEventListener('close', report(() => {
  const answer = el['same-dialog'].returnValue;
  return answer === 'add' || answer === 'replace' ? importSet(answer) : null;
}));
el['game-name'].addEventListener('input', () => {
  currentPanel().name = el['game-name'].value;
  renderGames();
  renderPreview();
  changed();
});
el['columns-less'].addEventListener('click', () => changeColumns(-1));
el['columns-more'].addEventListener('click', () => changeColumns(1));
el['add-button'].addEventListener('click', addButton);
el['add-screen'].addEventListener('click', addScreen);
el['delete-screen'].addEventListener('click', deleteScreen);
el['screen-name'].addEventListener('input', () => {
  currentPanel().screens[currentScreen()] = el['screen-name'].value;
  renderScreens();
  fillButtonForm();
  renderPreview();
  changed();
});
el['button-screen'].addEventListener('change', () => {
  const button = selectedButton();
  button.screen = Number(el['button-screen'].value);
  screen = button.screen; // follow the button to its new screen
  renderAll();
  if (button.keys) changed();
});
el['button-label'].addEventListener('input', () => {
  const button = selectedButton();
  button.label = el['button-label'].value;
  renderButtons();
  renderPreview();
  if (button.keys) changed();
});
el.record.addEventListener('click', () => (capture ? stopCapture() : startCapture()));
for (const choice of el['button-type'].children) {
  choice.addEventListener('click', () => {
    const button = selectedButton();
    button.type = choice.dataset.type;
    fillButtonForm();
    renderButtons();
    renderPreview();
    if (button.keys) changed();
  });
}
el['toggle-on'].addEventListener('change', () => {
  const button = selectedButton();
  button.on = el['toggle-on'].checked;
  renderPreview();
  if (button.keys) changed();
});
for (const box of el.manual.querySelectorAll('input[data-mod]')) box.addEventListener('change', manualChanged);
el['manual-key'].addEventListener('change', manualChanged);
el['duplicate-button'].addEventListener('click', duplicateButton);
el['delete-button'].addEventListener('click', deleteButton);
el['cover-choose'].addEventListener('click', () => chooseFile('cover'));
el['cover-remove'].addEventListener('click', () => setPicture(currentPanel(), 'cover', null));
el['background-choose'].addEventListener('click', () => chooseFile('background'));
el['background-remove'].addEventListener('click', () => setPicture(currentPanel(), 'background', null));
for (const choice of el.shape.children) {
  choice.addEventListener('click', () => {
    currentPanel().shape = choice.dataset.shape;
    fillGameForm();
    renderPreview();
    changed();
  });
}
el['image-choose'].addEventListener('click', () => chooseFile(selectedId));
el['image-remove'].addEventListener('click', () => setPicture(currentPanel(), selectedId, null));
el.file.addEventListener('change', report(fileChosen));
el.language.addEventListener('change', report(async () => {
  const saved = await api('/api/settings', { method: 'PUT', body: { language: el.language.value } });
  useLanguage(saved.language);
}));
el['check-updates'].addEventListener('change', report(async () => {
  const body = { check_updates: el['check-updates'].checked };
  savingCheck = true; // an answer of the PC from before the click does not undo it
  try {
    el['check-updates'].checked = (await api('/api/settings', { method: 'PUT', body })).check_updates;
  } catch (error) {
    el['check-updates'].checked = !body.check_updates; // not saved: the box shows what the PC has
    throw error;
  } finally {
    savingCheck = false;
  }
  refresh();
}));
el['window-choose'].addEventListener('click', report(chooseWindow));
el['window-remove'].addEventListener('click', () => setWindow(null));
el['copy-link'].addEventListener('click', report(copyLink));
el.rotate.addEventListener('click', () => { wide = !wide; renderPreview(); });
el.address.addEventListener('change', showQr);
el['show-qr'].addEventListener('click', () => { showQrAnyway = !showQrAnyway; renderConnect(); });
el['open-folder'].addEventListener('click', report(() => api('/api/open-panels-folder', { method: 'POST' })));
el.release.addEventListener('click', report(() => api('/api/release-keys', { method: 'POST' }).then(refresh)));
el.quit.addEventListener('click', () => api('/api/quit', { method: 'POST' }).then(refresh, refresh));
// Do not lose the last edit when the tab is closed right after typing.
window.addEventListener('pagehide', () => {
  for (const id of dirty) {
    const panel = panels.find((candidate) => candidate.id === id);
    if (panel?.name.trim()) {
      fetch(`/api/panels/${id}`, {
        method: 'PUT',
        keepalive: true,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(forFile(panel)),
      });
    }
  }
});

function useLanguage(language) {
  setLanguage(language);
  el.language.value = language;
  applyTexts();
  buildColors();
  if (panels.length || Object.keys(panelErrors).length) renderAll();
  renderConnect();
  loadLinks().catch(() => {});
  refresh();
}

async function start() {
  try {
    const chosen = await api('/api/settings');
    setLanguage(chosen.language);
    el.language.value = chosen.language;
    el['check-updates'].checked = chosen.check_updates;
  } catch { /* keep the browser's language */ }
  applyTexts();
  buildColors();
  const keys = await api('/api/keys');
  keyLabels = new Map(keys.keys.map((key) => [key.code, key.label]));
  modifiers = keys.modifiers;
  const empty = node('option', '', '—');
  empty.value = '';
  el['manual-key'].replaceChildren(empty, ...keys.keys.filter((key) => !key.modifier).map((key) => {
    const option = node('option', '', key.label);
    option.value = key.code;
    return option;
  }));
  await loadPanels();
  loadLinks().catch(() => {});
  refresh();
  setInterval(refresh, 1500);
  setInterval(() => loadLinks().catch(() => {}), 15000);
}

start().catch(() => { el.offline.hidden = false; });
