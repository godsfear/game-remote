// Takes the pictures for README: the editor on the PC and the remote on a phone.
//
//   npm install --no-save playwright && npx playwright install chromium
//   node tools/make_screenshots.js            (writes docs/img/*.png)
//
// It starts its own Game Remote in test mode with a temporary data folder.
// PYTHON chooses the interpreter (default: python).

const { chromium } = require('playwright');
const { execFileSync, spawn } = require('child_process');
const fs = require('fs');
const net = require('net');
const os = require('os');
const path = require('path');

const out = path.join(__dirname, '..', 'docs', 'img');
const python = process.env.PYTHON || 'python';
const LANGUAGES = ['ru', 'en'];
// Puts the ready-made panel into a data folder in the language of the picture.
// A first start would take the language of this PC for it.
const SEED = `import sys
from pathlib import Path
from game_remote.panels import SAMPLE_ID, PanelStore, read_set, sample_dir
store = PanelStore(Path(sys.argv[1]) / 'panels')
store.root.mkdir()
store.install_set(read_set(sample_dir(SAMPLE_ID)), SAMPLE_ID, sys.argv[2])
`;

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

// Takes a temporary folder away. The program was stopped a moment ago and
// holds its files for a second yet: Windows refuses then, so the removal is
// tried again after a pause. (The retries of fs.rmSync itself did not help:
// in Node 24 they were over before the files were let go.) A folder that
// stays is left in the temporary folder of the system and is no failure.
async function removeFolder(folder) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      fs.rmSync(folder, { recursive: true, force: true });
      return;
    } catch {
      await sleep(250);
    }
  }
  console.warn(`could not remove ${folder}`);
}

// One language: the program with the ready-made panel alone, as a new user sees it.
async function shoot(browser, language) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'game-remote-shots-'));
  const editor = `http://127.0.0.1:${await freePort()}`;
  const remote = `http://127.0.0.1:${await freePort()}`;
  execFileSync(python, ['-c', SEED, dataDir, language]);
  fs.writeFileSync(path.join(dataDir, 'settings.json'), JSON.stringify({ samples: ['star-citizen'] }));
  const env = {
    ...process.env,
    GAME_REMOTE_DATA_DIR: dataDir,
    GAME_REMOTE_EDITOR_PORT: new URL(editor).port,
    GAME_REMOTE_REMOTE_PORT: new URL(remote).port,
  };
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
    await fetch(`${editor}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Origin: editor },
      body: JSON.stringify({ language }),
    });

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
    // The tile under the buttons and their signs are there before the picture is taken.
    const loaded = async () => {
      const shapes = [...document.querySelectorAll('.btn .sign-shape')];
      const urls = [
        getComputedStyle(document.querySelector('.btn')).backgroundImage,
        ...shapes.map((shape) => shape.style.getPropertyValue('--sign')),
      ];
      await Promise.all(urls.map((url) => {
        const picture = new Image();
        picture.src = url.slice(5, -2);
        return picture.decode();
      }));
      return shapes.length > 0;
    };
    await page.waitForFunction(loaded);
    await page.waitForFunction(async () => {
      const picture = new Image();
      picture.src = getComputedStyle(document.body).backgroundImage.slice(5, -2);
      await picture.decode();
      return true;
    });
    await page.screenshot({ path: path.join(out, `phone-${language}.png`) });

    const pc = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const desk = await pc.newPage();
    await desk.goto(editor);
    // The yellow line only says that this run records presses instead of sending them.
    await desk.addStyleTag({ content: '#fake { display: none !important; }' });
    await desk.waitForSelector('#preview .btn');
    await desk.waitForFunction(loaded);
    await desk.waitForSelector('#device-list li.online');
    await desk.screenshot({ path: path.join(out, `editor-${language}.png`) });
    await phone.close();
    await pc.close();
  } finally {
    server.kill('SIGKILL');
    await removeFolder(dataDir);
  }
}

async function main() {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  try {
    for (const language of LANGUAGES) await shoot(browser, language);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
