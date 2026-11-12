// Draws a panel. The phone and the preview in the editor both use this code,
// so what the editor shows is what the phone gets.

// button: { id, label, type: 'tap' | 'hold' | 'toggle', on, color, image (a URL or null) }
export function buttonNode(button) {
  const node = document.createElement('button');
  node.type = 'button';
  node.className = `btn ${['hold', 'toggle'].includes(button.type) ? button.type : 'tap'}`;
  node.dataset.button = button.id;
  // A toggle is lit while what it switches is on.
  if (button.type === 'toggle') node.setAttribute('aria-pressed', String(Boolean(button.on)));
  if (button.color) node.style.setProperty('--color', button.color);
  if (button.image) {
    const img = document.createElement('img');
    img.src = button.image;
    img.alt = '';
    img.draggable = false;
    img.onerror = () => { img.remove(); node.classList.remove('has-image'); };
    node.append(img);
    node.classList.add('has-image');
  }
  const label = document.createElement('span');
  label.className = 'label';
  label.textContent = button.label;
  node.append(label);
  return node;
}

// Portrait uses the panel's own column count; a wide screen fits twice as many.
export function columnsFor(panel, wide) {
  const count = panel.buttons.length;
  let columns = wide ? Math.min(count, panel.columns * 2) : panel.columns;
  // Square buttons stand in even rows: six on a wide screen are 3 + 3, not 4 + 2.
  if (wide && panel.shape === 'square' && columns > 0) {
    columns = Math.ceil(count / Math.ceil(count / columns));
  }
  return Math.max(1, columns);
}

// Sets the grid's shape without touching its buttons, so a finger that holds
// one keeps holding it when the phone is turned.
export function layoutGrid(grid, panel, wide = false) {
  const columns = columnsFor(panel, wide);
  grid.classList.add('panel-grid');
  // Square buttons leave room around them, so the background shows.
  grid.classList.toggle('square', panel.shape === 'square');
  grid.style.setProperty('--cols', String(columns));
  grid.style.setProperty('--rows', String(Math.max(1, Math.ceil(panel.buttons.length / columns))));
}

// Puts the panel's background picture behind `node`, or takes it away.
export function showBackground(node, url) {
  node.classList.toggle('with-background', Boolean(url));
  node.style.backgroundImage = url ? `url("${url}")` : '';
}

// A panel may group its buttons into screens. This is the panel as one screen
// shows it: the same panel with only that screen's buttons.
export function screenView(panel, screen) {
  return { ...panel, buttons: panel.buttons.filter((button) => (button.screen || 0) === screen) };
}

// The screen to show: `wanted` if the panel has it, else the first one.
export function screenIndex(panel, wanted) {
  const count = Math.max(1, (panel.screens || []).length);
  return Number.isInteger(wanted) && wanted >= 0 && wanted < count ? wanted : 0;
}

// Fills `strip` with one tab per screen name; `pick(index)` runs on `event`.
// The phone listens to the touch itself, like its buttons do: a second finger
// makes no click while the first one holds a button.
export function renderTabs(strip, names, current, pick, event = 'click') {
  strip.classList.add('screen-tabs');
  strip.replaceChildren(...names.map((name, index) => {
    const tab = document.createElement('button');
    tab.type = 'button';
    tab.textContent = name;
    tab.dataset.screen = String(index);
    tab.setAttribute('aria-pressed', String(index === current));
    tab.addEventListener(event, (happened) => {
      happened.preventDefault();
      pick(index);
    });
    return tab;
  }));
}

// Fills `grid` with the panel's buttons and returns the nodes in order.
export function renderGrid(grid, panel, { wide = false } = {}) {
  layoutGrid(grid, panel, wide);
  const nodes = panel.buttons.map(buttonNode);
  grid.replaceChildren(...nodes);
  return nodes;
}
