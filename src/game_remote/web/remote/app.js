import { applyTexts, setLanguage, t } from '/shared/i18n.js';
import {
  layoutGrid, renderGrid, renderTabs, screenIndex, screenView, showBackground,
} from '/shared/panel-view.js';

const KEY_STORE = 'gameRemote.deviceKey';
const OLD_KEY_STORE = 'gameRemote.key'; // the shared key of the first prototype
const PANEL_STORE = 'gameRemote.panel';
const SCREEN_STORE = 'gameRemote.screen.'; // + panel id: the screen last shown
const VIBRATE_STORE = 'gameRemote.vibrate';
const NOTICE_AFTER_MS = 4000; // a short hiccup needs no explanation
const PING_EVERY_MS = 1000;
const PONG_TIMEOUT_MS = 3000;
// A toggle touched this long changes its light and sends no key. Long enough
// for a slow, firm press to stay a press.
const FLIP_AFTER_MS = 1000;
// After the PC opened another game by itself, touches are ignored this long.
const QUIET_AFTER_FOLLOW_MS = 400;
const CLOSE_BAD_KEY = 4401;
const CLOSE_BAD_CODE = 4403;

const el = {
  name: document.getElementById('panel-name'),
  status: document.getElementById('status'),
  statusText: document.getElementById('status-text'),
  grid: document.getElementById('grid'),
  screens: document.getElementById('screens'),
  message: document.getElementById('message'),
  list: document.getElementById('panel-list'),
  items: document.getElementById('panel-items'),
  toast: document.getElementById('toast'),
  notice: document.getElementById('notice'),
  menu: document.getElementById('menu'),
  menuOpen: document.getElementById('menu-open'),
  menuClose: document.getElementById('menu-close'),
  fullscreen: document.getElementById('menu-fullscreen'),
  vibration: document.getElementById('menu-vibration'),
  delay: document.getElementById('menu-delay'),
};

const store = {
  get(name) { try { return localStorage.getItem(name); } catch { return null; } },
  set(name, value) { try { localStorage.setItem(name, value); } catch { /* private mode */ } },
  remove(name) { try { localStorage.removeItem(name); } catch { /* private mode */ } },
};

// The QR link carries a one-time code. It buys this device a key of its own,
// which stays in the page's storage and opens every later visit.
let pairCode = takeCodeFromLink();
let key = store.get(KEY_STORE);
store.remove(OLD_KEY_STORE);
let ws = null;
let online = false;
let panels = [];
let panelId = store.get(PANEL_STORE);
let activeGames = '[]'; // the games of the window that is active on the PC, as the PC said last
let quietUntil = 0; // see QUIET_AFTER_FOLLOW_MS
let nextId = 1;
let lastPong = 0;
let retryMs = 500;
let retryTimer = 0;
let delayMs = null; // time of the last ping to the PC and back
let offlineSince = 0; // when the connection was lost; 0 while it is fine
let vibration = store.get(VIBRATE_STORE) !== 'off';
let toastTimer = 0;
// button id -> { pointerId, node, timer, flipped } for every button a finger is
// on right now; the last two belong to a toggle
const pressed = new Map();
// message id -> button node, to mark the button when the PC rejects a press
const waiting = new Map();

// The code comes after "#", so it never reaches a server log. Take it out of
// the address bar too: a copied link must not carry it.
function takeCodeFromLink() {
  const match = /(?:^#|&)pair=([^&]+)/.exec(location.hash);
  if (location.hash) history.replaceState(null, '', location.pathname + location.search);
  try {
    return match ? decodeURIComponent(match[1]) : null;
  } catch {
    return null; // a damaged link: the page asks to scan the code again
  }
}

// The name this device gets in the list on the PC; it can be changed there.
function deviceName() {
  const agent = navigator.userAgent || '';
  const model = /Android [^;)]+; ([^;)]+?)(?: Build\/[^)]*)?\)/.exec(agent)?.[1]?.trim();
  if (model && model.length > 1) return model; // new Chrome says "K" for every model
  if (/iPad/.test(agent)) return 'iPad';
  if (/iPhone/.test(agent)) return 'iPhone';
  if (/Android/.test(agent)) return t(/Mobile/.test(agent) ? 'device.phone' : 'device.tablet');
  return t('device.other');
}

let statusState = 'offline';

function setStatus(state) {
  statusState = state;
  online = state === 'online';
  if (online) offlineSince = 0;
  else if (!offlineSince) offlineSince = performance.now();
  showNotice();
  el.status.className = state;
  el.statusText.textContent = t(`remote.${state}`);
  document.body.classList.toggle('offline', !online);
}

// Explains a lost connection once it lasts; before that the dot says enough.
function showNotice() {
  const lost = Boolean(key) && offlineSince > 0 && performance.now() - offlineSince > NOTICE_AFTER_MS;
  el.notice.hidden = !lost;
}

function buzz(pattern) {
  if (vibration && navigator.vibrate) navigator.vibrate(pattern);
}

function showMessage(text) {
  el.message.textContent = text || '';
  el.message.hidden = !text;
  el.grid.hidden = Boolean(text);
}

function showToast(text) {
  el.toast.textContent = text;
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.toast.hidden = true; }, 3500);
}

function currentPanel() {
  return panels.find((p) => p.id === panelId) || panels[0] || null;
}

// The buttons of the game can be grouped into screens; the phone remembers
// which one it showed for every game.
function currentScreen(panel) {
  return screenIndex(panel, Number(store.get(SCREEN_STORE + panel.id) || 0));
}

function showScreen(index) {
  const panel = currentPanel();
  if (!panel || index === currentScreen(panel)) return;
  releaseAll(); // a held button cannot stay down on a screen that is not shown
  store.set(SCREEN_STORE + panel.id, String(index));
  buzz(12);
  render();
}

function send(message) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
}

// ---- connection ------------------------------------------------------------

function connect() {
  clearTimeout(retryTimer);
  if (ws) return;
  if (!key && !pairCode) {
    setStatus('offline');
    showMessage(t('remote.scan'));
    return;
  }
  setStatus('connecting');
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${scheme}://${location.host}/ws`);
  ws = socket;
  socket.onopen = () => {
    lastPong = performance.now();
    const first = key ? { type: 'hello', key } : { type: 'pair', code: pairCode, name: deviceName() };
    socket.send(JSON.stringify(first));
  };
  socket.onmessage = (event) => { if (socket === ws) onMessage(JSON.parse(event.data)); };
  socket.onclose = (event) => {
    if (socket !== ws) return;
    ws = null;
    dropAllPresses();
    if (event.code === CLOSE_BAD_KEY || event.code === CLOSE_BAD_CODE) {
      const badKey = event.code === CLOSE_BAD_KEY;
      if (badKey) {
        key = null;
        store.remove(KEY_STORE);
        if (pairCode) { // removed on the PC, but the link brought a fresh code
          connect();
          return;
        }
      } else {
        pairCode = null;
      }
      panels = [];
      render();
      setStatus('offline');
      showMessage(t(badKey ? 'remote.badKey' : 'remote.badCode'));
      return;
    }
    setStatus('offline');
    retryTimer = setTimeout(connect, retryMs);
    retryMs = Math.min(retryMs * 2, 3000);
  };
}

// Gives up on a silent connection and starts a new one right away, without
// waiting for the old one to close: on a dead network that takes long.
function reconnect() {
  if (ws) {
    const old = ws;
    ws = null;
    try { old.close(); } catch { /* already gone */ }
  }
  dropAllPresses();
  setStatus('offline');
  retryMs = 500;
  connect();
}

// The PC can set one language for every device; null leaves it to the browser.
function useLanguage(code) {
  setLanguage(code);
  applyTexts();
  setStatus(statusState);
}

function onMessage(message) {
  if (message.type === 'paired') {
    key = message.key;
    store.set(KEY_STORE, key);
    pairCode = null;
  } else if (message.type === 'settings') {
    useLanguage(message.language);
    render();
  } else if (message.type === 'welcome' || message.type === 'panels') {
    if (message.type === 'welcome') useLanguage(message.language);
    if (message.type === 'welcome') {
      pairCode = null; // the key still works, so the code stays unused
      retryMs = 500;
      setStatus('online');
    }
    dropAllPresses();
    panels = message.panels || [];
    const game = message.type === 'welcome' ? gameToFollow(message.active) : null;
    if (game) follow(game);
    else render();
  } else if (message.type === 'active') {
    const game = gameToFollow(message.panels);
    if (!game) return;
    releaseAll(); // before the panel changes: the PC is told which buttons go up
    follow(game);
    buzz([12, 40, 12, 40, 12]); // three short pulses: the screen is another one now
  } else if (message.type === 'released') {
    dropAllPresses(); // the game lost focus and the PC let go of the held keys
  } else if (message.type === 'lit') {
    // A toggle was switched, from this phone or another one.
    const panel = panels.find((candidate) => candidate.id === message.panel);
    const button = panel?.buttons.find((candidate) => candidate.id === message.button);
    if (!button) return;
    button.on = message.on;
    if (panel !== currentPanel()) return;
    const node = [...el.grid.children].find((child) => child.dataset.button === button.id);
    if (node) node.setAttribute('aria-pressed', String(Boolean(button.on)));
  } else if (message.type === 'pong') {
    lastPong = performance.now();
    if (typeof message.t === 'number') delayMs = Math.max(0, Math.round(lastPong - message.t));
    if (!el.menu.hidden) renderMenu();
  } else if (message.type === 'ack') {
    const node = waiting.get(message.id);
    waiting.delete(message.id);
    if (!message.ok) {
      if (node) {
        node.classList.remove('rejected');
        void node.offsetWidth; // restart the animation
        node.classList.add('rejected');
      }
      showToast(t(`reason.${message.reason}`));
      buzz([30, 60, 30]);
    }
  }
}

setInterval(() => {
  showNotice();
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (performance.now() - lastPong > PONG_TIMEOUT_MS) {
    reconnect(); // the PC is silent; it releases our keys by itself
    return;
  }
  send({ type: 'ping', t: performance.now() });
}, PING_EVERY_MS);

// ---- buttons ---------------------------------------------------------------

// Tells the PC what happened to a button; the PC answers whether it took it.
function tell(type, button, node) {
  const id = nextId++;
  waiting.set(id, node);
  if (waiting.size > 50) waiting.delete(waiting.keys().next().value);
  send({ type, id, panel: currentPanel().id, button: button.id });
}

function press(button, node, pointerId) {
  if (pressed.has(button.id) || !online || performance.now() < quietUntil) return;
  const entry = { pointerId, node };
  pressed.set(button.id, entry);
  node.classList.add('down');
  if (button.type === 'toggle') {
    // A toggle acts when the finger leaves it. A long touch sends no key: it
    // only sets the light right when the light and the game went apart.
    entry.timer = setTimeout(() => {
      entry.flipped = true;
      tell('flip', button, node);
      // One long pulse. Two short ones mean a press the PC refused, three
      // that the PC opened another game.
      buzz(80);
    }, FLIP_AFTER_MS);
    return;
  }
  tell('down', button, node);
  buzz(12);
}

// `lifted` is false when the touch was taken away, not ended by the finger.
function release(button, pointerId, lifted) {
  const entry = pressed.get(button.id);
  if (!entry || entry.pointerId !== pointerId) return;
  pressed.delete(button.id);
  entry.node.classList.remove('down');
  if (button.type === 'toggle') {
    clearTimeout(entry.timer);
    if (lifted && !entry.flipped) {
      tell('down', button, entry.node);
      buzz(12);
    }
    return;
  }
  send({ type: 'up', id: nextId++, panel: currentPanel().id, button: button.id });
}

// Forget every press without telling the PC: used when the connection is gone
// or the panel changed, where the PC has already released the keys.
function dropAllPresses() {
  for (const { node, timer } of pressed.values()) {
    clearTimeout(timer);
    node.classList.remove('down');
  }
  pressed.clear();
  waiting.clear();
}

function releaseAll() {
  const panel = currentPanel();
  for (const [buttonId, { node, timer }] of pressed) {
    clearTimeout(timer); // a toggle under a finger is left as it was
    node.classList.remove('down');
    if (panel) send({ type: 'up', id: nextId++, panel: panel.id, button: buttonId });
  }
  pressed.clear();
}

// Act on touch, not on release, and follow each finger separately so that
// one button can be held while another is tapped. A toggle is the exception:
// it acts on release, so that a long touch can be told from a press.
function listen(node, button) {
  node.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    try { node.setPointerCapture(event.pointerId); } catch { /* pointer already gone */ }
    press(button, node, event.pointerId);
  });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    node.addEventListener(type, (event) => release(button, event.pointerId, type === 'pointerup'));
  }
}

function render() {
  const panel = currentPanel();
  el.name.textContent = panel ? panel.name : 'Game Remote';
  el.name.classList.toggle('many', panels.length > 1);
  document.title = panel ? `${panel.name} · Game Remote` : 'Game Remote';
  el.grid.replaceChildren();
  showBackground(document.body, panel ? panel.background : null);
  const screens = (panel && panel.screens) || [];
  el.screens.hidden = screens.length < 2;
  if (!panel) {
    if (key && online) showMessage(t('remote.noPanels'));
    return;
  }
  const screen = currentScreen(panel);
  if (screens.length > 1) renderTabs(el.screens, screens, screen, showScreen, 'pointerdown');
  const shown = screenView(panel, screen);
  if (!shown.buttons.length) {
    showMessage(t(panel.buttons.length ? 'remote.emptyScreen' : 'remote.emptyPanel'));
    return;
  }
  showMessage('');
  const nodes = renderGrid(el.grid, shown, { wide: isWide() });
  el.grid.classList.toggle('wide', isWide());
  nodes.forEach((node, index) => listen(node, shown.buttons[index]));
}

function isWide() {
  return window.innerWidth > window.innerHeight * 1.2;
}

// On rotation only the column count changes; the buttons and held fingers stay.
function layout() {
  const panel = currentPanel();
  if (!panel) return;
  layoutGrid(el.grid, screenView(panel, currentScreen(panel)), isWide());
  el.grid.classList.toggle('wide', isWide());
}

// ---- panel list ------------------------------------------------------------

function openPanel(id) {
  panelId = id;
  store.set(PANEL_STORE, id);
  el.list.hidden = true;
  render();
}

// The PC names the games bound to the window that is active there. When that
// changes, the phone opens such a game, unless it shows one of them already.
// The same news twice changes nothing: after a reconnect in the middle of a
// game the phone keeps the panel the player chose.
function gameToFollow(ids) {
  if (!Array.isArray(ids)) return null; // the PC cannot tell right now; it will
  const said = JSON.stringify(ids);
  if (said === activeGames) return null;
  activeGames = said;
  if (ids.includes(currentPanel()?.id)) return null;
  return panels.find((panel) => ids.includes(panel.id))?.id || null;
}

// The PC opened a game: the buttons changed under the player's fingers. A
// touch that was on its way to the old ones presses nothing.
function follow(game) {
  openPanel(game);
  quietUntil = performance.now() + QUIET_AFTER_FOLLOW_MS;
}

function openList() {
  if (panels.length < 2) return;
  releaseAll();
  el.items.replaceChildren(...panels.map((panel) => {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    if (panel.cover) {
      const cover = document.createElement('img');
      cover.src = panel.cover;
      cover.alt = '';
      cover.onerror = () => cover.remove();
      button.append(cover);
    }
    const name = document.createElement('span');
    name.textContent = panel.name;
    button.append(name);
    button.setAttribute('aria-selected', String(panel.id === currentPanel().id));
    button.addEventListener('click', () => openPanel(panel.id));
    item.append(button);
    return item;
  }));
  el.list.hidden = false;
}

el.name.addEventListener('click', openList);
el.list.addEventListener('click', (event) => { if (event.target === el.list) el.list.hidden = true; });

// ---- settings of this device ----------------------------------------------

const fullscreenElement = () => document.fullscreenElement || document.webkitFullscreenElement;

function renderMenu() {
  const root = document.documentElement;
  el.fullscreen.parentElement.hidden = !(root.requestFullscreen || root.webkitRequestFullscreen);
  el.fullscreen.setAttribute('aria-pressed', String(Boolean(fullscreenElement())));
  el.vibration.parentElement.hidden = !navigator.vibrate;
  el.vibration.setAttribute('aria-pressed', String(vibration));
  el.delay.hidden = !online || delayMs === null;
  el.delay.textContent = t('remote.delay', { ms: delayMs });
}

async function toggleFullscreen() {
  const root = document.documentElement;
  try {
    if (fullscreenElement()) await (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    else await (root.requestFullscreen || root.webkitRequestFullscreen).call(root, { navigationUI: 'hide' });
  } catch { /* the browser said no; the switch shows the real state */ }
  renderMenu();
}

el.menuOpen.addEventListener('click', () => {
  releaseAll();
  renderMenu();
  el.menu.hidden = false;
});
el.menuClose.addEventListener('click', () => { el.menu.hidden = true; });
el.fullscreen.addEventListener('click', toggleFullscreen);
el.vibration.addEventListener('click', () => {
  vibration = !vibration;
  store.set(VIBRATE_STORE, vibration ? 'on' : 'off');
  renderMenu();
  buzz(12);
});
for (const type of ['fullscreenchange', 'webkitfullscreenchange']) document.addEventListener(type, renderMenu);

// ---- keep the screen on ----------------------------------------------------

// The Wake Lock API only exists on secure pages, and this page is plain HTTP.
// Browsers also keep the screen on while a video plays, so a black, silent
// video sits behind the buttons. It is page-sized because Chrome ignores
// small or hidden videos for this purpose.
const awake = document.getElementById('awake');
let wakeLock = null;

async function keepAwake() {
  if (document.hidden) return;
  if (navigator.wakeLock) {
    try {
      if (!wakeLock || wakeLock.released) wakeLock = await navigator.wakeLock.request('screen');
      return;
    } catch { /* fall back to the video */ }
  }
  if (awake.paused) awake.play().catch(() => { /* needs a touch first; the next one retries */ });
}

document.addEventListener('pointerdown', keepAwake, { capture: true, passive: true });
document.addEventListener('visibilitychange', keepAwake);

// ---- page ------------------------------------------------------------------

window.addEventListener('resize', layout);
document.addEventListener('contextmenu', (event) => event.preventDefault());
document.addEventListener('visibilitychange', () => { if (document.hidden) releaseAll(); });
// Back from a locked screen or a lost Wi-Fi: do not wait for the next retry.
document.addEventListener('visibilitychange', () => {
  if (document.hidden) return;
  const silent = ws && performance.now() - lastPong > PONG_TIMEOUT_MS;
  if (silent || (!ws && statusState === 'offline' && (key || pairCode))) reconnect();
});
window.addEventListener('online', () => { if (!ws && (key || pairCode)) reconnect(); });
window.addEventListener('pagehide', releaseAll);
window.addEventListener('blur', releaseAll);

applyTexts();
render();
connect();
keepAwake();
