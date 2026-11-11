// Checks the phone panel and the PC page in a real browser with touch emulation.
//
//   npm install --no-save playwright && npx playwright install chromium
//   node tests/browser/check.js [folder for screenshots]
//
// It starts its own Game Remote with fake input, a temporary data folder and
// free ports. PYTHON chooses the interpreter (default: python).

const { chromium } = require('playwright');
const { execFileSync, spawn } = require('child_process');
const fs = require('fs');
const net = require('net');
const os = require('os');
const path = require('path');
const zlib = require('zlib');

const shots = process.argv[2];
const python = process.env.PYTHON || 'python';
const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'game-remote-browser-'));
let editor;
let remote;
let server = null;
let failed = 0;

function ok(name, condition, extra = '') {
  if (!condition) failed += 1;
  console.log(`${condition ? 'ok  ' : 'FAIL'} ${name}${extra ? ` (${extra})` : ''}`);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function until(check, ms = 6000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try {
      if (await check()) return true;
    } catch { /* not ready yet */ }
    await sleep(50);
  }
  return false;
}

function freePort() {
  return new Promise((resolve) => {
    const probe = net.createServer();
    probe.listen(0, '127.0.0.1', () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
}

async function startServer(ports, folder = dataDir) {
  const env = {
    ...process.env,
    LANG: 'ru_RU.UTF-8',
    LC_ALL: '',
    GAME_REMOTE_DATA_DIR: folder,
    GAME_REMOTE_EDITOR_PORT: String(ports.editor),
    GAME_REMOTE_REMOTE_PORT: String(ports.remote),
  };
  const args = ['-m', 'game_remote', '--no-browser', '--no-tray', '--fake-input'];
  server = spawn(python, args, { env, stdio: 'ignore' });
  const started = await until(async () => (await fetch(`${remote}/api/health`)).ok, 20000);
  if (!started) throw new Error('Game Remote did not start');
}

function killServer() {
  if (server) server.kill('SIGKILL');
  server = null;
}

const status = async () => (await fetch(`${editor}/api/status`)).json();
// The link inside the QR code, pointed at this machine. Its code works once.
const pairLink = async () => {
  const { links } = await (await fetch(`${editor}/api/links`)).json();
  return `${remote}/#pair=${links[0].url.split('#pair=')[1]}`;
};
const held = async () => JSON.stringify((await status()).held_keys);
const shot = (page, name, options = {}) => (
  shots ? page.screenshot({ path: path.join(shots, `${name}.png`), ...options }) : null
);

function writePanel(id, panel) {
  const folder = path.join(dataDir, 'panels', id);
  fs.mkdirSync(folder, { recursive: true });
  const text = typeof panel === 'string' ? panel : JSON.stringify(panel, null, 2);
  fs.writeFileSync(path.join(folder, 'panel.json'), text);
}

// A plain PNG of the given size, to upload as a button picture.
function png(width, height, [red, green, blue]) {
  const chunk = (type, data) => {
    const body = Buffer.concat([Buffer.from(type), data]);
    const head = Buffer.alloc(4);
    head.writeUInt32BE(data.length);
    const tail = Buffer.alloc(4);
    tail.writeUInt32BE(zlib.crc32(body));
    return Buffer.concat([head, body, tail]);
  };
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header.set([8, 2, 0, 0, 0], 8); // 8 bits per channel, RGB
  const row = Buffer.concat([Buffer.from([0]), Buffer.alloc(width * 3, Buffer.from([red, green, blue]))]);
  const pixels = Buffer.concat(Array.from({ length: height }, () => row));
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', header),
    chunk('IDAT', zlib.deflateSync(pixels)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

// The plain panel the checks below work with, in place of the ready-made one.
function seedDemo() {
  const code = 'import json; from game_remote.panels import demo_panel; '
    + 'print(json.dumps(demo_panel(russian=True).model_dump(exclude_none=True)))';
  writePanel('demo', execFileSync(python, ['-c', code], { encoding: 'utf8' }));
  fs.writeFileSync(path.join(dataDir, 'settings.json'), JSON.stringify({ samples: ['star-citizen'] }));
}

// Where every button of the panel lies, and whether the pictures are there.
const tiles = (page, grid) => page.evaluate((selector) => {
  const box = (node) => {
    const { left, top, right, bottom, width, height } = node.getBoundingClientRect();
    return { left, top, right, bottom, width, height };
  };
  const area = document.querySelector(selector);
  const buttons = [...area.querySelectorAll('.btn')];
  return {
    grid: box(area),
    buttons: buttons.map(box),
    pictures: buttons.map((node) => node.querySelector('img')?.naturalWidth || 0),
  };
}, grid);

// Square, all of one size, inside the grid, and not on top of each other.
function squaresFit({ grid, buttons }, least) {
  const near = (a, b) => Math.abs(a - b) < 1;
  const apart = (a, b) => a.right <= b.left + 1 || b.right <= a.left + 1
    || a.bottom <= b.top + 1 || b.bottom <= a.top + 1;
  return buttons.every((b) => near(b.width, b.height) && near(b.width, buttons[0].width)
      && b.width >= least
      && b.left >= grid.left - 1 && b.right <= grid.right + 1
      && b.top >= grid.top - 1 && b.bottom <= grid.bottom + 1)
    && buttons.every((a, i) => buttons.every((b, j) => i === j || apart(a, b)));
}

// A new user's first start: the ready-made Star Citizen panel with its pictures.
async function firstRun(browser, ports, phoneOptions, watch) {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'game-remote-first-'));
  await startServer(ports, folder);
  try {
    const phone = await browser.newContext({ ...phoneOptions, locale: 'ru-RU' });
    const page = await phone.newPage();
    watch(page, 'first phone');
    await page.goto(await pairLink());
    await page.waitForSelector('#status.online');
    ok('first start shows the Star Citizen panel', (await page.locator('#panel-name').textContent()) === 'Star Citizen');
    ok(
      'it has the six buttons in the system language',
      (await page.locator('.btn .label').allTextContents()).join() === 'Flight Ready,ATC,Шасси,Фары,VTOL,Карта'
    );
    ok('every button has its picture', await until(async () => (await tiles(page, '#grid')).pictures.join() === '512,512,512,512,512,512'));
    const background = () => page.evaluate(async () => {
      const url = getComputedStyle(document.body).backgroundImage.slice(5, -2);
      const picture = new Image();
      picture.src = url;
      await picture.decode();
      return `${new URL(url).pathname} ${picture.naturalWidth}`;
    });
    ok('the background picture is behind the panel', (await background()) === '/panel-files/star-citizen/background.jpg 941');
    let layout = await tiles(page, '#grid');
    ok('upright: square buttons in two columns fill the width', squaresFit(layout, 180)
      && new Set(layout.buttons.map((b) => Math.round(b.left))).size === 2, JSON.stringify(layout.buttons[0]));
    ok('the buttons stand in the middle of the screen', Math.abs(
      (layout.buttons[0].top - layout.grid.top) - (layout.grid.bottom - layout.buttons[5].bottom)
    ) < 4);
    await shot(page, 'phone-star-citizen');

    await page.locator('.btn[data-button="flight-ready"]').tap();
    ok('Flight Ready presses right Alt + R', await until(async () => (await status()).recent[0]?.keys === 'Right Alt+R'), JSON.stringify((await status()).recent[0]));
    await page.locator('.btn[data-button="atc"]').tap();
    ok('ATC presses left Alt + N', await until(async () => (await status()).recent[0]?.keys === 'Alt+N'), JSON.stringify((await status()).recent[0]));
    ok('no key stays down after the taps', await until(async () => (await held()) === '[]'));

    await page.setViewportSize({ width: 915, height: 412 });
    await page.waitForSelector('#grid.wide');
    layout = await tiles(page, '#grid');
    ok('on its side: two even rows of three', squaresFit(layout, 120)
      && new Set(layout.buttons.map((b) => Math.round(b.top))).size === 2
      && new Set(layout.buttons.map((b) => Math.round(b.left))).size === 3, JSON.stringify(layout.buttons[0]));
    await shot(page, 'phone-star-citizen-wide');
    await page.setViewportSize({ width: 412, height: 915 });

    const pc = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'ru-RU' });
    const desk = await pc.newPage();
    watch(desk, 'first editor');
    await desk.goto(editor);
    await desk.waitForSelector('#preview .btn');
    ok('the editor opens the ready-made panel', (await desk.locator('#game-name').inputValue()) === 'Star Citizen');
    layout = await tiles(desk, '#preview');
    ok('the preview shows the same square buttons', squaresFit(layout, 60) && layout.pictures.every((side) => side === 512), JSON.stringify(layout.buttons[0]));
    ok('the preview shows the background', await desk.evaluate(() => getComputedStyle(document.getElementById('phone')).backgroundImage.includes('background.jpg')));
    ok('the editor shows the background and the shape', (await desk.locator('#background-thumb.set').count()) === 1
      && (await desk.locator('#shape [data-shape="square"]').getAttribute('aria-pressed')) === 'true');
    await shot(desk, 'editor-star-citizen');

    const saved = () => desk.waitForFunction(() => document.getElementById('save-state').textContent === 'Сохранено');
    await desk.locator('#shape [data-shape="fill"]').click();
    await saved();
    ok('"fill the screen" reaches the phone', await until(() => page.locator('#grid:not(.square)').count()));
    layout = await tiles(page, '#grid');
    ok('then the buttons take the whole grid', layout.buttons[5].bottom > layout.grid.bottom - 20
      && layout.buttons[0].top < layout.grid.top + 20);
    await desk.locator('#background-remove').click();
    await saved();
    ok('a removed background leaves the phone', await until(() => page.evaluate(() => getComputedStyle(document.body).backgroundImage === 'none')));
    ok('and the preview', await desk.evaluate(() => getComputedStyle(document.getElementById('phone')).backgroundImage === 'none'));

    const [chooser] = await Promise.all([
      desk.waitForEvent('filechooser'),
      desk.locator('#background-choose').click(),
    ]);
    await chooser.setFiles({ name: 'cockpit.png', mimeType: 'image/png', buffer: png(1200, 2400, [20, 40, 60]) });
    await saved();
    await desk.locator('#shape [data-shape="square"]').click();
    await saved();
    ok('an own background is kept large enough for a phone screen', await until(async () => (
      (await background()).endsWith(' 960')
    )), await background());
    ok('square buttons are back', squaresFit(await tiles(page, '#grid'), 180));
    await phone.close();
    await pc.close();
  } finally {
    killServer();
    fs.rmSync(folder, { recursive: true, force: true });
  }
}

const X4 = {
  name: 'X4: Foundations',
  columns: 2,
  buttons: [
    { id: 'map', label: 'Карта', keys: 'KeyM' },
    { id: 'stop', label: 'Стоп', keys: 'Backspace', color: '#c44f6a' },
    { id: 'boost', label: 'Ускорение', keys: 'Tab', type: 'hold', color: '#2f9e62' },
    { id: 'radio', label: 'Связь', keys: 'ControlLeft+KeyR' },
    { id: 'long', label: 'Очень длинная подпись кнопки, проверка', keys: 'ShiftLeft+KeyD' },
  ],
};

async function main() {
  const ports = { editor: await freePort(), remote: await freePort() };
  editor = `http://127.0.0.1:${ports.editor}`;
  remote = `http://127.0.0.1:${ports.remote}`;
  if (shots) fs.mkdirSync(shots, { recursive: true });

  const browser = await chromium.launch();
  const errors = [];
  const watch = (page, name) => {
    page.on('console', (m) => { if (m.type() === 'error') errors.push(`${name}: ${m.text()}`); });
    page.on('pageerror', (e) => errors.push(`${name}: ${e}`));
  };
  const phoneOptions = {
    viewport: { width: 412, height: 915 },
    hasTouch: true,
    isMobile: true,
    deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
  };

  await firstRun(browser, ports, phoneOptions, watch);
  seedDemo();
  await startServer(ports);

  // ---- phone: connect -------------------------------------------------------
  const phone = await browser.newContext({ ...phoneOptions, locale: 'ru-RU' });
  const page = await phone.newPage();
  watch(page, 'phone');
  const firstLink = await pairLink();
  await page.goto(firstLink);
  await page.waitForSelector('#status.online');
  ok('the code is taken out of the address bar', !page.url().includes('pair'));
  ok('the phone is in the list under its model name', (await status()).devices.map((d) => d.name).join() === 'Pixel 7');
  ok('six demo buttons are drawn', (await page.locator('.btn').count()) === 6);
  ok('interface follows the browser language', (await page.locator('#status-text').textContent()) === 'На связи');
  ok('demo panel follows the system language', (await page.locator('#panel-name').textContent()) === 'Демо');
  ok('PC counts the phone', (await status()).phones === 1);
  await shot(page, 'phone-portrait');

  // Real multi-touch through the DevTools protocol. touchStart adds fingers,
  // touchEnd lifts the listed ones.
  const cdp = await phone.newCDPSession(page);
  const touch = (type, touchPoints) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints });
  const center = async (id) => {
    const box = await page.locator(`.btn[data-button="${id}"]`).boundingBox();
    return { x: Math.round(box.x + box.width / 2), y: Math.round(box.y + box.height / 2) };
  };
  const [map, fwd, run, jump] = [
    await center('map'), await center('forward'), await center('run'), await center('jump'),
  ];

  // ---- phone: tap, hold, several fingers ------------------------------------
  await touch('touchStart', [{ ...map, id: 1 }]);
  ok('a tap acts on touch, before the finger lifts', await until(async () => (await status()).recent[0]?.keys === 'M'));
  await touch('touchEnd', [{ ...map, id: 1 }]);
  ok('a tap releases the key by itself', await until(async () => (await held()) === '[]'));

  await touch('touchStart', [{ ...fwd, id: 1 }]);
  ok('hold keeps the key down', await until(async () => (await held()) === '["KeyW"]'));
  ok('held button looks pressed', (await page.locator('.btn[data-button="forward"].down').count()) === 1);
  await touch('touchStart', [{ ...fwd, id: 1 }, { ...run, id: 2 }]);
  ok('a second finger holds a second key', await until(async () => (await held()) === '["KeyW","ShiftLeft"]'));
  await shot(page, 'phone-two-fingers');
  await touch('touchStart', [{ ...fwd, id: 1 }, { ...run, id: 2 }, { ...jump, id: 3 }]);
  await touch('touchEnd', [{ ...jump, id: 3 }]);
  ok('a third finger taps while two hold', await until(async () => {
    const now = await status();
    return now.recent[0].keys === 'Space' && now.held_keys.length === 2;
  }));
  const away = { x: fwd.x + 150, y: fwd.y + 300, id: 1 };
  await touch('touchMove', [away, { ...run, id: 2 }]);
  await sleep(200);
  ok('a finger that slides off the button keeps holding', (await held()) === '["KeyW","ShiftLeft"]');
  await touch('touchEnd', [away]);
  ok('lifting one finger releases only its key', await until(async () => (await held()) === '["ShiftLeft"]'));
  await touch('touchEnd', [{ ...run, id: 2 }]);
  ok('lifting the last finger releases everything', await until(async () => (await held()) === '[]'));

  await touch('touchStart', [{ ...fwd, id: 1 }]);
  await until(async () => (await held()) === '["KeyW"]');
  await page.evaluate(() => window.dispatchEvent(new Event('blur')));
  ok('leaving the page releases the key', await until(async () => (await held()) === '[]'));
  await touch('touchEnd', [{ ...fwd, id: 1 }]);

  ok('the keep-awake video plays', await until(() => page.evaluate(() => {
    const video = document.getElementById('awake');
    return !video.paused && video.readyState >= 2 && video.videoWidth > 0;
  })));

  // ---- phone: settings of the device -----------------------------------------
  await page.locator('#menu-open').tap();
  await page.waitForSelector('#menu:not([hidden])');
  ok('the phone menu offers full screen', await page.locator('#menu-fullscreen').isVisible());
  ok('vibration is on at first', (await page.locator('#menu-vibration').getAttribute('aria-pressed')) === 'true');
  ok('the menu shows the delay to the PC', await until(async () => /: \d+ мс$/.test(await page.locator('#menu-delay').textContent())));
  await shot(page, 'phone-menu');
  await page.locator('#menu-vibration').tap();
  ok('vibration can be switched off', (await page.locator('#menu-vibration').getAttribute('aria-pressed')) === 'false');
  ok('the choice is remembered on the device', (await page.evaluate(() => localStorage.getItem('gameRemote.vibrate'))) === 'off');
  await page.locator('#menu-vibration').tap();
  await page.locator('#menu-close').tap();
  ok('the menu closes', await page.locator('#menu').isHidden());
  const manifest = await (await fetch(`${remote}/manifest.json`)).json();
  ok('the page has a home screen icon', (await fetch(`${remote}/${manifest.icons[0].src}`)).headers.get('content-type') === 'image/png');

  // ---- phone: landscape -----------------------------------------------------
  await page.setViewportSize({ width: 915, height: 412 });
  await sleep(200);
  const columns = await page.locator('#grid').evaluate((grid) => getComputedStyle(grid).getPropertyValue('--cols').trim());
  ok('landscape puts the six buttons in one row', columns === '6');
  ok('landscape needs no scrolling', await page.evaluate(() => (
    document.documentElement.scrollHeight <= window.innerHeight
    && document.documentElement.scrollWidth <= window.innerWidth
  )));
  await shot(page, 'phone-landscape');
  await page.setViewportSize({ width: 412, height: 915 });

  // ---- panels change on the PC ----------------------------------------------
  await touch('touchStart', [{ ...fwd, id: 1 }]);
  await until(async () => (await held()) === '["KeyW"]');
  writePanel('x4', X4);
  ok('a panel edit releases held keys', await until(async () => (await held()) === '[]'));
  await touch('touchEnd', [{ ...fwd, id: 1 }]);
  ok('the panel name offers a choice', await until(() => page.locator('#panel-name.many').count()));
  await page.locator('#panel-name').tap();
  await page.waitForSelector('#panel-list:not([hidden])');
  await shot(page, 'phone-panel-list');
  await page.locator('#panel-items button', { hasText: 'X4' }).tap();
  ok('the second panel opens', await until(async () => (await page.locator('.btn').count()) === 5));
  await shot(page, 'phone-second-panel');
  const radio = await center('radio');
  await touch('touchStart', [{ ...radio, id: 1 }]);
  await touch('touchEnd', [{ ...radio, id: 1 }]);
  ok('a combo reaches the PC as Ctrl+R', await until(async () => (await status()).recent[0].keys === 'Ctrl+R'));

  writePanel('x4', '{ "name": "X4", "buttons": [ { "id": "a", "keys": "Nope" } ] }');
  ok('a broken panel file leaves the other panel working', await until(async () => (
    (await page.locator('#panel-name').textContent()) === 'Демо'
  )));

  // ---- PC page --------------------------------------------------------------
  const pc = await browser.newContext({ viewport: { width: 1280, height: 800 }, locale: 'ru-RU', deviceScaleFactor: 2 });
  const desk = await pc.newPage();
  watch(desk, 'pc');
  await desk.goto(editor);
  desk.on('dialog', (dialog) => dialog.accept());
  ok('PC page shows the connected phone', await until(async () => (await desk.locator('#phones').textContent()).includes('1')));
  ok('PC page lists the phone as connected', await until(async () => (
    (await desk.locator('#device-list li.online .device-name').allTextContents()).join() === 'Pixel 7'
  )));
  ok('the QR code folds away once a phone is paired', await desk.locator('#qr').isHidden());
  await desk.click('#show-qr');
  ok('the QR code is drawn', await until(() => desk.evaluate(() => document.getElementById('qr').naturalWidth > 0)));
  ok('the address list fits its card', await desk.evaluate(() => (
    document.getElementById('address').getBoundingClientRect().right
    <= document.getElementById('connect').getBoundingClientRect().right
  )));

  // ---- devices: a second one, a used code, rename, remove ---------------------
  await desk.locator('#device-list .device-name').click();
  await desk.keyboard.type('Мой телефон');
  await sleep(1700); // a status refresh must not take the field away
  ok('the name field survives a refresh of the page data', (await desk.locator('#device-list input').count()) === 1);
  await desk.keyboard.press('Enter');
  ok('a device can be renamed', await until(async () => (await status()).devices[0].name === 'Мой телефон'));
  await page.locator('.btn[data-button="map"]').tap();
  ok('the phone keeps working after the rename', await until(async () => (await status()).recent[0].phone === 'Мой телефон'));

  const qrBefore = await desk.locator('#qr').getAttribute('src');
  const secondLink = await pairLink();
  ok('a used code is replaced by a new one', secondLink !== firstLink);
  const tabletContext = await browser.newContext({
    viewport: { width: 800, height: 1100 }, hasTouch: true, isMobile: true, locale: 'ru-RU',
  });
  const tablet = await tabletContext.newPage();
  watch(tablet, 'tablet');
  await tablet.goto(secondLink);
  await tablet.waitForSelector('#status.online');
  ok('a second device pairs with the next code', await until(async () => (await desk.locator('#device-list li.online').count()) === 2));
  ok('the QR code on the PC is redrawn after pairing', await until(async () => (
    (await desk.locator('#qr').getAttribute('src')) !== qrBefore
  )));
  await shot(desk, 'pc-devices', { fullPage: true });

  const lateContext = await browser.newContext({ ...phoneOptions, locale: 'ru-RU' });
  const late = await lateContext.newPage();
  await late.goto(secondLink);
  await late.waitForSelector('#message:not([hidden])');
  ok('a code that was used pairs nobody else', (await late.locator('#message').textContent()).includes('уже использован'));
  ok('a refused device is not in the list', (await status()).devices.length === 2);
  await shot(late, 'phone-used-code');
  await lateContext.close();

  await desk.locator('#device-list li', { hasText: 'Браузер' }).locator('.remove').click();
  ok('a removed device leaves the list', await until(async () => (await status()).devices.length === 1));
  ok('a removed device is told to scan again', await until(async () => (
    (await tablet.locator('#message').textContent()).includes('отключили')
  )));
  ok('a removed device shows no buttons', (await tablet.locator('.btn').count()) === 0);
  await tablet.reload();
  await tablet.waitForSelector('#message:not([hidden])');
  ok('a removed device does not come back after a reload', (await status()).devices.length === 1);
  await tabletContext.close();
  await desk.click('#show-qr');
  ok('PC page shows the broken panel', await until(async () => (await desk.locator('#panel-errors li').count()) === 1));
  ok('PC page lists recent presses', (await desk.locator('#recent li').count()) > 1);

  // ---- editor: a new game with two buttons ----------------------------------
  const saved = () => desk.waitForFunction(() => document.getElementById('save-state').textContent === 'Сохранено');
  const stored = async (id) => (await (await fetch(`${editor}/api/panels`)).json()).panels.find((p) => p.id === id);
  await desk.click('#add-game');
  await desk.waitForFunction(() => document.activeElement?.id === 'game-name');
  await desk.keyboard.type('Elite');
  await desk.click('#add-button');
  await desk.keyboard.type('Связь');
  ok('a button without a key is not saved', (await stored('game')).buttons.length === 0);
  await desk.click('#record');
  await desk.keyboard.down('ControlLeft');
  await desk.keyboard.down('KeyR');
  ok('the shortcut shows while it is recorded', (await desk.locator('#combo').textContent()) === 'Ctrl+R');
  await desk.keyboard.up('KeyR');
  await desk.keyboard.up('ControlLeft');
  await desk.click('#button-type [data-type="hold"]');
  await desk.click('#colors button[data-color="#2f9e62"]');
  await desk.click('#add-button');
  await desk.keyboard.type('Карта');
  await desk.click('#record');
  await desk.keyboard.press('KeyM');
  await saved();
  let game = await stored('game');
  ok('the editor saves by itself', game.name === 'Elite' && game.buttons.length === 2);
  ok('recorded shortcut is stored with modifiers first', game.buttons[0].keys === 'ControlLeft+KeyR'
    && game.buttons[0].type === 'hold' && game.buttons[0].color === '#2f9e62' && game.buttons[1].keys === 'KeyM');
  ok('preview is drawn by the same code as the phone', (await desk.locator('#preview .btn.hold .label').textContent()) === 'Связь');

  await desk.locator('#button-list li').nth(1).locator('.move button').first().click();
  await desk.click('#columns-less');
  await saved();
  game = await stored('game');
  ok('order and columns are saved', game.buttons[0].label === 'Карта' && game.columns === 2);

  await desk.locator('#preview .btn', { hasText: 'Связь' }).click();
  await desk.click('#manual summary');
  await desk.check('#manual input[data-mod="ShiftLeft"]');
  await desk.selectOption('#manual-key', 'F5');
  await saved();
  ok('a shortcut can be chosen by hand', (await stored('game')).buttons[1].keys === 'ControlLeft+ShiftLeft+F5');

  await desk.click('#window-choose');
  ok('open windows are offered for the game', await until(async () => (await desk.locator('#window-list button').count()) === 2));
  await shot(desk, 'pc-window-choice', { fullPage: true });
  await desk.locator('#window-list button[data-exe="X4.exe"]').click();
  await saved();
  ok('the chosen window is saved with the game', (await stored('game')).window === 'X4.exe');
  ok('the game card names the program', (await desk.locator('#window-name').textContent()) === 'X4.exe');
  await shot(desk, 'pc-editor', { fullPage: true });

  // The phone got all of it without a reload.
  ok('the phone offers the new game', await until(() => page.locator('#panel-name.many').count()));
  await page.locator('#panel-name').tap();
  await page.locator('#panel-items button', { hasText: 'Elite' }).tap();
  ok('the phone shows the new buttons in the new order', await until(async () => (
    (await page.locator('.btn .label').allTextContents()).join() === 'Карта,Связь'
  )));
  ok('the phone uses the new column count', (await page.locator('#grid').evaluate((grid) => getComputedStyle(grid).getPropertyValue('--cols').trim())) === '2');
  await page.locator('.btn', { hasText: 'Карта' }).tap();
  ok('a button made in the editor presses its key', await until(async () => (await status()).recent[0].keys === 'M'));

  // ---- screens: the buttons of one game in groups -----------------------------
  const labels = (view, grid) => view.locator(`${grid} .btn .label`).allTextContents().then((all) => all.join());
  await desk.click('#add-screen');
  ok('the buttons made so far become the first screen',
    (await desk.locator('#screen-tabs button').allTextContents()).join() === 'Экран 1,Экран 2');
  await desk.keyboard.type('Бой'); // the name of the new screen is selected, ready to be replaced
  await desk.click('#add-button');
  await desk.keyboard.type('Огонь');
  await desk.click('#record');
  await desk.keyboard.press('KeyG');
  await saved();
  game = await stored('game');
  ok('a new button lands on the open screen', game.screens.join() === 'Экран 1,Бой'
    && game.buttons.map((button) => button.screen).join() === '0,0,1');
  ok('the editor shows one screen at a time', (await labels(desk, '#preview')) === 'Огонь'
    && (await desk.locator('#button-list li').count()) === 1);
  ok('the phone gets a tab for every screen', await until(async () => (
    (await page.locator('#screens button').allTextContents()).join() === 'Экран 1,Бой'
  )));
  ok('the phone stays on the first screen', (await labels(page, '#grid')) === 'Карта,Связь');

  // A second finger switches the screen while the first one holds a button.
  const link = await center(game.buttons[1].id);
  const tabBox = await page.locator('#screens button').nth(1).boundingBox();
  const tab = { x: Math.round(tabBox.x + tabBox.width / 2), y: Math.round(tabBox.y + tabBox.height / 2) };
  await touch('touchStart', [{ ...link, id: 1 }]);
  await until(async () => (await held()) !== '[]');
  await touch('touchStart', [{ ...link, id: 1 }, { ...tab, id: 2 }]);
  ok('a touch on a tab shows the other screen', await until(async () => (await labels(page, '#grid')) === 'Огонь'));
  ok('a button held on the screen that went away is released', await until(async () => (await held()) === '[]'));
  await touch('touchEnd', []);
  await page.locator('.btn', { hasText: 'Огонь' }).tap();
  ok('a button of the second screen presses its key', await until(async () => (await status()).recent[0].keys === 'G'));
  await shot(page, 'phone-screens');
  await shot(desk, 'pc-editor-screens', { fullPage: true });
  await page.reload();
  await page.waitForSelector('#status.online');
  ok('the phone remembers the screen of the game', await until(async () => (await labels(page, '#grid')) === 'Огонь'));

  await desk.selectOption('#button-screen', '0');
  await saved();
  ok('a button moves to another screen', (await stored('game')).buttons.every((button) => button.screen === 0)
    && (await labels(desk, '#preview')) === 'Карта,Связь,Огонь');
  ok('the phone says that a screen is empty', await until(async () => (
    (await page.locator('#message').textContent()).includes('На этом экране')
  )));
  await desk.locator('#screen-tabs button', { hasText: 'Бой' }).click();
  await desk.click('#delete-screen');
  await saved();
  ok('with one screen left the game has no screens again', (await stored('game')).screens.length === 0
    && await desk.locator('#screen-tabs').isHidden());
  ok('and the phone shows all the buttons without tabs', await until(async () => (
    (await labels(page, '#grid')) === 'Карта,Связь,Огонь' && await page.locator('#screens').isHidden()
  )));
  await desk.locator('#button-list li', { hasText: 'Огонь' }).click();
  await desk.click('#delete-button');
  await saved();

  // ---- editor: pictures ----------------------------------------------------
  const pick = async (buttonId, file) => {
    const [chooser] = await Promise.all([desk.waitForEvent('filechooser'), desk.click(buttonId)]);
    await chooser.setFiles(file);
  };
  await desk.locator('#button-list li', { hasText: 'Связь' }).click();
  await pick('#image-choose', { name: 'photo.png', mimeType: 'image/png', buffer: png(1200, 800, [200, 60, 60]) });
  ok('the picture is saved into the panel', await until(async () => /^img-[0-9a-f]{12}\.webp$/.test((await stored('game')).buttons[1].image || '')));
  const picture = (await stored('game')).buttons[1].image;
  const size = await desk.evaluate(async (url) => {
    const image = new Image();
    image.src = url;
    await image.decode();
    return [image.naturalWidth, image.naturalHeight];
  }, `/panel-files/game/${picture}`);
  ok('a big picture is shrunk before upload', size.join('x') === '512x341', size.join('x'));
  ok('the preview shows the picture', await until(() => desk.locator('#preview .btn.has-image img').evaluate((img) => img.naturalWidth > 0)));
  ok('the phone shows the picture', await until(() => page.locator('.btn.has-image img').evaluate((img) => img.naturalWidth > 0)));
  ok('the label stays readable over the picture', (await page.locator('.btn.has-image .label').textContent()) === 'Связь');
  await shot(page, 'phone-picture');

  await pick('#cover-choose', { name: 'cover.png', mimeType: 'image/png', buffer: png(300, 300, [40, 120, 220]) });
  ok('the cover is saved', await until(async () => Boolean((await stored('game')).cover)));
  await until(() => page.locator('#panel-name.many').count());
  await page.locator('#panel-name').tap();
  ok('the phone shows the cover in the list of games', await until(() => page.locator('#panel-items img').evaluate((img) => img.naturalWidth > 0)));
  await shot(page, 'phone-covers');
  await page.locator('#panel-items button', { hasText: 'Elite' }).tap();

  await pick('#image-choose', { name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('not a picture') });
  ok('a file that is not a picture is refused with a reason', await until(async () => (
    (await desk.locator('#save-state').textContent()).includes('PNG')
  )));
  ok('the old picture stays after a refused file', (await stored('game')).buttons[1].image === picture);
  await shot(desk, 'pc-editor-picture', { fullPage: true });

  // ---- one language for all devices -----------------------------------------
  await desk.selectOption('#language', 'en');
  ok('the editor switches language', await until(async () => (await desk.locator('#games h2').textContent()) === 'Games'));
  ok('the phone follows the language chosen on the PC', await until(async () => (await page.locator('#status-text').textContent()) === 'Connected'));
  ok('names typed by the user are not translated', (await page.locator('.btn .label').allTextContents()).join() === 'Карта,Связь');
  await desk.selectOption('#language', 'auto');
  ok('"auto" gives the language back to the browser', await until(async () => (await page.locator('#status-text').textContent()) === 'На связи'));
  await until(async () => (await desk.locator('#games h2').textContent()) === 'Игры');

  // A file edited by hand shows up in the open editor.
  const demoFile = path.join(dataDir, 'panels', 'demo', 'panel.json');
  const demo = JSON.parse(fs.readFileSync(demoFile, 'utf8'));
  fs.writeFileSync(demoFile, JSON.stringify({ ...demo, name: 'Демо из файла' }));
  ok('the editor notices a file edited by hand', await until(async () => (
    (await desk.locator('#game-list').textContent()).includes('Демо из файла')
  )));

  await desk.click('#delete-game');
  ok('a deleted game leaves the phone', await until(async () => (await page.locator('#panel-name.many').count()) === 0));
  ok('a deleted game is kept in the trash folder', fs.readdirSync(path.join(dataDir, 'trash')).length === 1);
  await shot(desk, 'pc-page', { fullPage: true });

  // ---- wrong or missing key -------------------------------------------------
  const stranger = await browser.newContext({ ...phoneOptions, locale: 'en-US' });
  const wrong = await stranger.newPage();
  await wrong.goto(`${remote}/#pair=not-the-code`);
  await wrong.waitForSelector('#message:not([hidden])');
  ok('a wrong code asks to scan again', (await wrong.locator('#message').textContent()).includes('Scan the code'));
  ok('a wrong code shows no buttons', (await wrong.locator('.btn').count()) === 0);
  await wrong.evaluate(() => localStorage.setItem('gameRemote.deviceKey', 'made-up-key'));
  await wrong.reload();
  await wrong.waitForSelector('#message:not([hidden])');
  ok('an unknown key is refused', (await wrong.locator('#message').textContent()).includes('disconnected'));
  ok('nobody was added to the list', (await status()).devices.length === 1);
  const bare = await stranger.newPage();
  await bare.goto(remote);
  await bare.waitForSelector('#message:not([hidden])');
  ok('no key asks to scan', (await bare.locator('#message').textContent()).includes('Scan the QR code'));
  await shot(bare, 'phone-no-key');

  ok('no errors in the browser console', errors.length === 0, errors.join(' | '));

  // ---- sets: a game as a file to share ---------------------------------------
  // After the console check: the refused file below is an error there by design.
  const games = async () => (await (await fetch(`${editor}/api/panels`)).json()).panels;
  // Whoever goes to a text field while a shortcut is recorded means to type there.
  const keysBefore = (await games())[0].buttons[0].keys;
  await desk.locator('#button-list li').first().click();
  const labelBefore = await desk.locator('#button-label').inputValue();
  await desk.click('#record');
  await desk.click('#button-label');
  await desk.keyboard.press('End');
  await desk.keyboard.type('x');
  ok('typing into a text field ends the recording of a shortcut',
    (await desk.locator('#button-label').inputValue()) === `${labelBefore}x`
    && (await desk.locator('#combo.recording').count()) === 0);
  await desk.fill('#button-label', labelBefore);
  await saved();
  ok('and the keys typed there are not the shortcut of the button',
    (await games())[0].buttons[0].keys === keysBefore);
  // The same when the export asks its question.
  await desk.click('#record');
  await desk.click('#export-set');
  ok('the export asks for the language of the labels and offers the one of the page',
    /^(ru|en)$/.test(await desk.locator('#export-language').inputValue()));
  await desk.fill('#export-language', '12');
  await desk.click('#export-ok');
  ok('an answer that is not two letters is not taken', await desk.locator('#export-dialog').evaluate((dialog) => dialog.open));
  await desk.locator('#export-language').selectText();
  await desk.keyboard.type('ru');
  ok('the answer is typed into the question, not into the recording of a shortcut',
    (await desk.locator('#export-language').inputValue()) === 'ru');
  const [download] = await Promise.all([desk.waitForEvent('download'), desk.click('#export-ok')]);
  ok('and the button keeps its shortcut', (await games())[0].buttons[0].keys === keysBefore);
  const [original0] = await games();
  ok('a game is exported as a zip named after its folder', download.suggestedFilename() === 'demo.zip');
  const [setChooser] = await Promise.all([desk.waitForEvent('filechooser'), desk.click('#import-set')]);
  await setChooser.setFiles(await download.path());
  await desk.waitForSelector('#same-dialog[open]');
  ok('a set called like a game of the PC changes nothing until the user says what to do',
    (await games()).length === 1 && (await desk.locator('#same-text').textContent()).includes(original0.name));
  await desk.click('#same-add');
  ok('an imported set becomes a new game', await until(async () => (await games()).length === 2));
  const [original, copy] = await games();
  ok('with the same name and buttons', copy.name === original.name
    && JSON.stringify(copy.buttons) === JSON.stringify(original.buttons));
  ok('the editor opens the imported game', await until(async () => (
    (await desk.locator('#game-list button[aria-current="true"]').getAttribute('data-panel')) === copy.id
  )));
  const [badChooser] = await Promise.all([desk.waitForEvent('filechooser'), desk.click('#import-set')]);
  await badChooser.setFiles({ name: 'notes.zip', mimeType: 'application/zip', buffer: Buffer.from('not a zip') });
  ok('a file that is not a set is refused with a reason', await until(async () => (
    (await desk.locator('#save-state.error').textContent()).includes('zip')
  )));
  ok('and the refusal does not read as a failed save',
    !/Not saved|Не сохранено/.test(await desk.locator('#save-state').textContent()));

  // A game that cannot be saved keeps what the page has when another game arrives.
  await desk.click(`#game-list button[data-panel="${original.id}"]`);
  const columnsShown = Number(await desk.locator('#columns').textContent());
  await desk.fill('#game-name', '');
  await desk.click('#columns-more');
  const [thirdChooser] = await Promise.all([desk.waitForEvent('filechooser'), desk.click('#import-set')]);
  await thirdChooser.setFiles(await download.path());
  await desk.waitForSelector('#same-dialog[open]');
  await desk.click('#same-add');
  await until(async () => (await games()).length === 3);
  ok('the save that failed is still reported after the import',
    await until(() => desk.locator('#save-state.error').count()));
  await desk.click(`#game-list button[data-panel="${original.id}"]`);
  ok('a game that could not be saved keeps its edits when a set is imported',
    Number(await desk.locator('#columns').textContent()) === columnsShown + 1
    && (await desk.locator('#game-name').inputValue()) === '');
  await desk.fill('#game-name', original.name);
  await saved();

  // "Replace": the set takes the place of the game, which goes to the trash folder.
  const trashBefore = fs.readdirSync(path.join(dataDir, 'trash')).length;
  await desk.click('#columns-more');
  await saved();
  const [fourthChooser] = await Promise.all([desk.waitForEvent('filechooser'), desk.click('#import-set')]);
  await fourthChooser.setFiles(await download.path());
  await desk.waitForSelector('#same-dialog[open]');
  await desk.click('#same-replace');
  ok('a replaced game is what the set says', await until(async () => (
    (await games()).find((game) => game.id === original.id).columns === original.columns
  )));
  ok('it keeps its place, and the old one is in the trash folder', (await games()).length === 3
    && fs.readdirSync(path.join(dataDir, 'trash')).length === trashBefore + 1);
  ok('the editor shows the game that was replaced', await until(async () => (
    (await desk.locator('#game-list button[aria-current="true"]').getAttribute('data-panel')) === original.id
    && Number(await desk.locator('#columns').textContent()) === original.columns
  )));

  // An export waits for a save that is on its way.
  const order = [];
  const noteExport = () => order.push('export'); // the download begins
  const noteSave = (response) => { if (response.request().method() === 'PUT') order.push('saved'); };
  desk.on('download', noteExport);
  desk.on('response', noteSave);
  await desk.route(`**/api/panels/${original.id}`, async (route) => {
    if (route.request().method() === 'PUT') await new Promise((resolve) => { setTimeout(resolve, 700); });
    await route.continue().catch(() => {}); // the route may be gone when the check fails
  });
  await desk.click('#columns-less');
  await desk.waitForTimeout(600); // the save was sent and is held by the route above
  await desk.click('#export-set');
  await Promise.all([desk.waitForEvent('download'), desk.click('#export-ok')]);
  ok('an export waits for the save that is on its way', order.join() === 'saved,export', order.join());
  await desk.unroute(`**/api/panels/${original.id}`);
  desk.off('download', noteExport);
  desk.off('response', noteSave);

  for (const game of (await games()).filter((candidate) => candidate.id !== original.id)) {
    await desk.click(`#game-list button[data-panel="${game.id}"]`);
    await desk.click('#delete-game');
    await until(async () => !(await games()).some((candidate) => candidate.id === game.id));
  }

  // ---- a save that fails is tried again ------------------------------------
  // Comes after the console check: the refused request is an error there by design.
  const addGame = async (name) => {
    await desk.click('#add-game');
    await desk.waitForFunction(() => document.activeElement?.id === 'game-name');
    await desk.keyboard.type(name);
    await saved();
  };
  await addGame('First');
  await addGame('Second');
  await desk.route('**/api/panels/game', (route) => (
    route.request().method() === 'PUT' ? route.fulfill({ status: 500, body: '{}' }) : route.continue()
  ));
  await desk.click('#game-list button[data-panel="game"]');
  await desk.click('#columns-more');
  ok('a failed save is reported', await until(() => desk.locator('#save-state.error').count()));
  await desk.unroute('**/api/panels/game');
  await desk.click('#game-list button[data-panel="game-2"]');
  await desk.click('#columns-more');
  await saved();
  ok('a save that failed is tried again with the next one',
    (await stored('game')).columns === 4 && (await stored('game-2')).columns === 4);
  for (const id of ['game', 'game-2']) {
    await desk.click(`#game-list button[data-panel="${id}"]`);
    await desk.click('#delete-game');
    await until(async () => !(await stored(id)));
  }

  // A link with a damaged code still opens the page.
  const damaged = await stranger.newPage();
  await damaged.goto(`${remote}/#pair=%E0%A4%A`);
  await damaged.waitForSelector('#message:not([hidden])');
  ok('a damaged link asks to scan', (await damaged.locator('#message').textContent()).includes('Scan the QR code'));
  await damaged.close();

  // ---- the PC disappears while a key is held --------------------------------
  await touch('touchStart', [{ ...fwd, id: 1 }]);
  await until(async () => (await held()) === '["KeyW"]');
  killServer();
  ok('the phone shows the lost connection', await until(() => page.locator('#status.offline').count(), 8000));
  ok('the held button is no longer shown pressed', (await page.locator('.btn.down').count()) === 0);
  ok('a short break shows no explanation yet', await page.locator('#notice').isHidden());
  ok('a lasting break explains what to check', await until(() => page.locator('#notice').isVisible(), 8000));
  await shot(page, 'phone-offline');
  await touch('touchEnd', [{ ...fwd, id: 1 }]);
  await startServer(ports);
  ok('the phone reconnects by itself', await until(() => page.locator('#status.online').count(), 15000));
  ok('nothing is held after the reconnect', (await held()) === '[]');
  ok('the explanation goes away with the connection', await page.locator('#notice').isHidden());

  // ---- a rejected press, with a fake PC -------------------------------------
  const mock = await phone.newPage();
  await mock.addInitScript(() => {
    window.buzzes = [];
    Object.defineProperty(navigator, 'vibrate', { value: (pattern) => { window.buzzes.push(pattern); return true; } });
  });
  await mock.routeWebSocket(/\/ws$/, (ws) => {
    ws.onMessage((text) => {
      const message = JSON.parse(text);
      const reply = (data) => ws.send(JSON.stringify(data));
      if (message.type === 'hello') {
        reply({
          type: 'welcome',
          panels: [{
            id: 'u',
            name: 'Undecember',
            columns: 2,
            buttons: [
              { id: 'a', label: 'Зелье', type: 'tap', color: '#c44f6a', image: null },
              { id: 'b', label: 'Навык', type: 'hold', color: null, image: null },
            ],
          }],
        });
      }
      if (message.type === 'ping') reply({ type: 'pong', t: message.t });
      if (message.type === 'down') reply({ type: 'ack', id: message.id, ok: false, reason: 'elevated' });
    });
  });
  await mock.goto(remote);
  await mock.waitForSelector('#status.online');
  await mock.locator('.btn[data-button="a"]').tap();
  await mock.waitForSelector('#toast:not([hidden])');
  ok('a rejected press says why', (await mock.locator('#toast').textContent()).includes('администратора'));
  ok('a rejected press feels different from an accepted one', (await mock.evaluate(() => JSON.stringify(window.buzzes))) === '[12,[30,60,30]]');
  await shot(mock, 'phone-rejected');

  await browser.close();
}

main()
  .catch((error) => {
    console.error(error);
    failed += 1;
  })
  .finally(() => {
    killServer();
    fs.rmSync(dataDir, { recursive: true, force: true });
    console.log(failed ? `${failed} FAILED` : 'ALL OK');
    process.exit(failed ? 1 : 0);
  });
