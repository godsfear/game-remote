import { applyTexts, setLanguage, t } from '/shared/i18n.js';
import { columnsFor, renderGrid } from '/shared/panel-view.js';

const KEY_STORE = 'gameRemote.deviceKey';
const OLD_KEY_STORE = 'gameRemote.key'; // the shared key of the first prototype
const PANEL_STORE = 'gameRemote.panel';
const PING_EVERY_MS = 1000;
const PONG_TIMEOUT_MS = 3000;
const CLOSE_BAD_KEY = 4401;
const CLOSE_BAD_CODE = 4403;

const el = {
  name: document.getElementById('panel-name'),
  status: document.getElementById('status'),
  statusText: document.getElementById('status-text'),
  grid: document.getElementById('grid'),
  message: document.getElementById('message'),
  list: document.getElementById('panel-list'),
  items: document.getElementById('panel-items'),
  toast: document.getElementById('toast'),
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
let nextId = 1;
let lastPong = 0;
let retryMs = 500;
let toastTimer = 0;
// button id -> { pointerId, node } for every button a finger is on right now
const pressed = new Map();
// message id -> button node, to mark the button when the PC rejects a press
const waiting = new Map();

// The code comes after "#", so it never reaches a server log. Take it out of
// the address bar too: a copied link must not carry it.
function takeCodeFromLink() {
  const match = /(?:^#|&)pair=([^&]+)/.exec(location.hash);
  if (location.hash) history.replaceState(null, '', location.pathname + location.search);
  return match ? decodeURIComponent(match[1]) : null;
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
  el.status.className = state;
  el.statusText.textContent = t(`remote.${state}`);
  document.body.classList.toggle('offline', !online);
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

function send(message) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
}

// ---- connection ------------------------------------------------------------

function connect() {
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
    setTimeout(connect, retryMs);
    retryMs = Math.min(retryMs * 2, 3000);
  };
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
    render();
  } else if (message.type === 'released') {
    dropAllPresses(); // the game lost focus and the PC let go of the held keys
  } else if (message.type === 'pong') {
    lastPong = performance.now();
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
    }
  }
}

setInterval(() => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (performance.now() - lastPong > PONG_TIMEOUT_MS) {
    ws.close(); // the PC is silent: reconnect; it releases our keys by itself
    return;
  }
  send({ type: 'ping', t: performance.now() });
}, PING_EVERY_MS);

// ---- buttons ---------------------------------------------------------------

function press(button, node, pointerId) {
  if (pressed.has(button.id) || !online) return;
  pressed.set(button.id, { pointerId, node });
  node.classList.add('down');
  const id = nextId++;
  waiting.set(id, node);
  if (waiting.size > 50) waiting.delete(waiting.keys().next().value);
  send({ type: 'down', id, panel: currentPanel().id, button: button.id });
  if (navigator.vibrate) navigator.vibrate(12);
}

function release(button, pointerId) {
  const entry = pressed.get(button.id);
  if (!entry || entry.pointerId !== pointerId) return;
  pressed.delete(button.id);
  entry.node.classList.remove('down');
  send({ type: 'up', id: nextId++, panel: currentPanel().id, button: button.id });
}

// Forget every press without telling the PC: used when the connection is gone
// or the panel changed, where the PC has already released the keys.
function dropAllPresses() {
  for (const { node } of pressed.values()) node.classList.remove('down');
  pressed.clear();
  waiting.clear();
}

function releaseAll() {
  const panel = currentPanel();
  for (const [buttonId, { node }] of pressed) {
    node.classList.remove('down');
    if (panel) send({ type: 'up', id: nextId++, panel: panel.id, button: buttonId });
  }
  pressed.clear();
}

// Act on touch, not on release, and follow each finger separately so that
// one button can be held while another is tapped.
function listen(node, button) {
  node.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    try { node.setPointerCapture(event.pointerId); } catch { /* pointer already gone */ }
    press(button, node, event.pointerId);
  });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    node.addEventListener(type, (event) => release(button, event.pointerId));
  }
}

function render() {
  const panel = currentPanel();
  el.name.textContent = panel ? panel.name : 'Game Remote';
  el.name.classList.toggle('many', panels.length > 1);
  document.title = panel ? `${panel.name} · Game Remote` : 'Game Remote';
  el.grid.replaceChildren();
  if (!panel) {
    if (key && online) showMessage(t('remote.noPanels'));
    return;
  }
  if (!panel.buttons.length) {
    showMessage(t('remote.emptyPanel'));
    return;
  }
  showMessage('');
  const nodes = renderGrid(el.grid, panel, { wide: isWide() });
  el.grid.classList.toggle('wide', isWide());
  nodes.forEach((node, index) => listen(node, panel.buttons[index]));
}

function isWide() {
  return window.innerWidth > window.innerHeight * 1.2;
}

// On rotation only the column count changes; the buttons and held fingers stay.
function layout() {
  const panel = currentPanel();
  if (!panel) return;
  el.grid.style.setProperty('--cols', String(columnsFor(panel, isWide())));
  el.grid.classList.toggle('wide', isWide());
}

// ---- panel list ------------------------------------------------------------

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
    button.addEventListener('click', () => {
      panelId = panel.id;
      store.set(PANEL_STORE, panelId);
      el.list.hidden = true;
      render();
    });
    item.append(button);
    return item;
  }));
  el.list.hidden = false;
}

el.name.addEventListener('click', openList);
el.list.addEventListener('click', (event) => { if (event.target === el.list) el.list.hidden = true; });

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
window.addEventListener('pagehide', releaseAll);
window.addEventListener('blur', releaseAll);

applyTexts();
render();
connect();
keepAwake();
