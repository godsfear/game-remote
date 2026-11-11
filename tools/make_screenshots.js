// Takes the pictures for README: the editor on the PC and the remote on a phone.
//
//   npm install --no-save playwright && npx playwright install chromium
//   node tools/make_screenshots.js            (writes docs/img/*.png)
//
// It starts its own Game Remote in test mode with a temporary data folder.
// PYTHON chooses the interpreter (default: python).

const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const net = require('net');
const os = require('os');
const path = require('path');

const out = path.join(__dirname, '..', 'docs', 'img');
const python = process.env.PYTHON || 'python';
const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'game-remote-shots-'));

const PANELS = {
  ru: {
    name: 'X4: Foundations',
    columns: 3,
    window: 'X4.exe',
    buttons: [
      { id: 'map', label: 'Карта', keys: 'KeyM', color: '#2b5fd9' },
      { id: 'info', label: 'Свойства', keys: 'KeyI', color: '#7a4fd1' },
      { id: 'dock', label: 'Стыковка', keys: 'ShiftLeft+KeyD', color: '#1f8a8a' },
      { id: 'boost', label: 'Ускорение', keys: 'Tab', type: 'hold', color: '#2f9e62' },
      { id: 'travel', label: 'Круиз', keys: 'ShiftLeft+Digit1', color: '#c9822b' },
      { id: 'stop', label: 'Стоп', keys: 'Backspace', color: '#c44f6a' },
      { id: 'scan', label: 'Сканер', keys: 'ShiftLeft+Digit2', color: '#8a8f9c' },
      { id: 'radio', label: 'Связь', keys: 'KeyC' },
      { id: 'save', label: 'Сохранить', keys: 'F5' },
    ],
  },
  en: ['Map', 'Info', 'Dock', 'Boost', 'Travel', 'Stop', 'Scan', 'Comms', 'Save'],
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function freePort() {
  return new Promise((resolve) => {
    const probe = net.createServer();
    probe.listen(0, '127.0.0.1', () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
}

function writePanel(language) {
  const panel = structuredClone(PANELS.ru);
  if (language === 'en') panel.buttons.forEach((button, index) => { button.label = PANELS.en[index]; });
  const folder = path.join(dataDir, 'panels', 'x4');
  fs.mkdirSync(folder, { recursive: true });
  fs.writeFileSync(path.join(folder, 'panel.json'), JSON.stringify(panel, null, 2));
}

async function main() {
  const editor = `http://127.0.0.1:${await freePort()}`;
  const remote = `http://127.0.0.1:${await freePort()}`;
  const env = {
    ...process.env,
    GAME_REMOTE_DATA_DIR: dataDir,
    GAME_REMOTE_EDITOR_PORT: new URL(editor).port,
    GAME_REMOTE_REMOTE_PORT: new URL(remote).port,
  };
  writePanel('ru');
  const args = ['-m', 'game_remote', '--no-browser', '--no-tray', '--fake-input'];
  const server = spawn(python, args, { env, stdio: 'ignore' });
  try {
    for (let attempt = 0; ; attempt += 1) {
      try {
        if ((await fetch(`${remote}/api/health`)).ok) break;
      } catch { /* not started yet */ }
      if (attempt > 200) throw new Error('Game Remote did not start');
      await sleep(100);
    }
    fs.rmSync(path.join(dataDir, 'panels', 'demo'), { recursive: true, force: true });
    fs.mkdirSync(out, { recursive: true });

    const browser = await chromium.launch();
    const phone = await browser.newContext({
      viewport: { width: 412, height: 800 },
      hasTouch: true,
      isMobile: true,
      deviceScaleFactor: 2,
      userAgent: 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    });
    const page = await phone.newPage();
    const { links } = await (await fetch(`${editor}/api/links`)).json();
    await page.goto(`${remote}/#pair=${links[0].url.split('#pair=')[1]}`);
    await page.waitForSelector('#status.online');

    const pc = await browser.newContext({ viewport: { width: 1280, height: 860 } });
    const desk = await pc.newPage();

    for (const language of ['ru', 'en']) {
      writePanel(language);
      await fetch(`${editor}/api/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Origin: editor },
        body: JSON.stringify({ language }),
      });
      await desk.goto(editor);
      // The yellow line only says that this run records presses instead of sending them.
      await desk.addStyleTag({ content: '#fake { display: none !important; }' });
      const first = language === 'ru' ? PANELS.ru.buttons[0].label : PANELS.en[0];
      await desk.waitForSelector(`#preview .btn >> text=${first}`);
      await desk.waitForSelector('#device-list li.online');
      await desk.screenshot({ path: path.join(out, `editor-${language}.png`) });
      await page.waitForSelector(`.btn >> text=${first}`);
      await page.screenshot({ path: path.join(out, `phone-${language}.png`) });
    }
    await browser.close();
  } finally {
    server.kill('SIGKILL');
    fs.rmSync(dataDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
