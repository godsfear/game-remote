import { applyTexts, t } from '/shared/i18n.js';

const el = Object.fromEntries(
  ['qr', 'no-address', 'address', 'address-row', 'phones', 'panels', 'folder', 'open-folder',
    'recent', 'release', 'fake', 'offline', 'version', 'quit'].map((id) => [id, document.getElementById(id)]),
);

async function api(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

function item(className, ...children) {
  const li = document.createElement('li');
  if (className) li.className = className;
  li.append(...children);
  return li;
}

function span(className, text) {
  const node = document.createElement('span');
  if (className) node.className = className;
  node.textContent = text;
  return node;
}

function empty(key) {
  const li = item('empty');
  li.textContent = t(key);
  return li;
}

function showQr() {
  el.qr.src = `/api/qr/${el.address.value}.svg`;
  el.qr.hidden = false;
}

async function loadLinks() {
  const { links } = await api('/api/links');
  const chosen = el.address.value;
  el.address.replaceChildren(...links.map((link, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    const kind = t(link.kind === 'name' ? 'editor.addressName' : 'editor.addressIp');
    option.textContent = `${link.host} — ${kind}`;
    return option;
  }));
  el['no-address'].hidden = links.length > 0;
  el['address-row'].hidden = links.length < 2;
  if (!links.length) {
    el.qr.hidden = true;
    return;
  }
  if (chosen && Number(chosen) < links.length) el.address.value = chosen;
  showQr();
}

function renderStatus(status) {
  el.offline.hidden = true;
  el.fake.hidden = !status.fake_input;
  el.phones.textContent = status.phones ? t('editor.phones', { n: status.phones }) : t('editor.waiting');
  el.phones.classList.toggle('waiting', !status.phones);
  el.folder.textContent = status.panels_dir;
  el.version.textContent = `Game Remote ${status.version}`;

  const panels = status.panels.map((panel) => item('',
    span('', panel.name),
    span('count', t('editor.buttons', { n: panel.buttons }))));
  const errors = Object.entries(status.panel_errors).map(([id, error]) => {
    const small = document.createElement('small');
    small.textContent = error;
    return item('error', span('', `${id} — ${t('editor.panelError')}`), small);
  });
  el.panels.replaceChildren(...panels, ...errors);
  if (!panels.length && !errors.length) el.panels.append(empty('editor.noPanels'));

  el.recent.replaceChildren(...status.recent.slice(0, 8).map((press) => {
    const what = span('', `${press.panel} · ${press.button}`);
    what.append(span('keys', press.keys));
    const result = press.ok ? t('editor.sent') : `${t('editor.rejected')}: ${t(`reason.${press.reason}`)}`;
    return item(press.ok ? '' : 'rejected', what, span('result', result));
  }));
  if (!status.recent.length) el.recent.append(empty('editor.noRecent'));
}

async function refresh() {
  try {
    renderStatus(await api('/api/status'));
  } catch {
    el.offline.hidden = false;
  }
}

el.address.addEventListener('change', showQr);
el['open-folder'].addEventListener('click', () => api('/api/open-panels-folder', { method: 'POST' }));
el.quit.addEventListener('click', () => api('/api/quit', { method: 'POST' }).then(refresh, refresh));
el.release.addEventListener('click', () => api('/api/release-keys', { method: 'POST' }).then(refresh));

applyTexts();
loadLinks().catch(() => { el.offline.hidden = false; });
refresh();
setInterval(refresh, 1500);
setInterval(() => loadLinks().catch(() => {}), 15000);
