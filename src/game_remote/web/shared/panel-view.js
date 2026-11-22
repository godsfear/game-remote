// Draws a panel. The phone and the preview in the editor both use this code,
// so what the editor shows is what the phone gets.

// button: { id, label, type: 'tap' | 'hold' | 'toggle' | 'macro', on, color,
//           image (a URL or null), sign (a URL or null),
//           width, height (cells of the grid; one when missing) }
export function buttonNode(button) {
  const node = document.createElement('button');
  node.type = 'button';
  node.className = `btn ${['hold', 'toggle', 'macro'].includes(button.type) ? button.type : 'tap'}`;
  node.dataset.button = button.id;
  // A toggle is lit while what it switches is on, a macro while it runs.
  if (['toggle', 'macro'].includes(button.type)) {
    node.setAttribute('aria-pressed', String(Boolean(button.on)));
  }
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
  if (button.sign) {
    // Only the shape of the sign is taken: the panel gives the colour. The
    // glow lies on a layer of its own, or the shape would cut it off.
    const sign = document.createElement('span');
    sign.className = 'sign';
    const shape = document.createElement('span');
    shape.className = 'sign-shape';
    shape.style.setProperty('--sign', `url("${button.sign}")`);
    sign.append(shape);
    node.append(sign);
    node.classList.add('has-sign');
  }
  const label = document.createElement('span');
  label.className = 'label';
  label.textContent = button.label;
  node.append(label);
  return node;
}

// The cells of the grid a button takes: across, never more than the grid has
// columns, and down.
const cellsOf = (button, columns) => [Math.min(button.width || 1, columns), button.height || 1];

// How many rows the buttons fill. The grid puts every button into the first
// free place that holds it, row by row (grid-auto-flow: dense); so does this.
function rowsFor(buttons, columns) {
  const taken = new Set();
  let rows = 0;
  let free = 0; // the first cell nothing lies in: no button finds a place before it
  for (const button of buttons) {
    const [across, down] = cellsOf(button, columns);
    const place = (at) => Array.from(
      { length: across * down }, (_, n) => at + (n % across) + Math.floor(n / across) * columns,
    );
    while (taken.has(free)) free += 1;
    let at = free;
    while ((at % columns) + across > columns || place(at).some((cell) => taken.has(cell))) at += 1;
    place(at).forEach((cell) => taken.add(cell));
    rows = Math.max(rows, Math.floor(at / columns) + down);
  }
  return rows;
}

// Portrait uses the panel's own column count; a wide screen fits twice as many.
export function columnsFor(panel, wide) {
  if (!wide) return panel.columns;
  // No more columns than the buttons fill when they stand in one row.
  const inOneRow = panel.buttons.reduce((sum, button) => sum + cellsOf(button, panel.columns * 2)[0], 0);
  let columns = Math.max(1, Math.min(inOneRow, panel.columns * 2));
  // Square buttons stand in even rows: six on a wide screen are 3 + 3, not
  // 4 + 2. That is the fewest columns that make no more rows, and never fewer
  // than the widest button takes: it would lose its width for it.
  if (panel.shape === 'square') {
    const widest = Math.max(1, ...panel.buttons.map((button) => cellsOf(button, columns)[0]));
    const rows = rowsFor(panel.buttons, columns);
    while (columns > widest && rowsFor(panel.buttons, columns - 1) === rows) columns -= 1;
  }
  return columns;
}

// Sets the grid's shape and the place its buttons take in it. The buttons
// themselves stay, so a finger that holds one keeps holding it when the phone
// is turned. The grid holds the buttons of `panel`, in their order.
export function layoutGrid(grid, panel, wide = false) {
  const columns = columnsFor(panel, wide);
  grid.classList.add('panel-grid');
  // Square buttons leave room around them, so the background shows.
  grid.classList.toggle('square', panel.shape === 'square');
  grid.style.setProperty('--cols', String(columns));
  grid.style.setProperty('--rows', String(Math.max(1, rowsFor(panel.buttons, columns))));
  panel.buttons.forEach((button, index) => {
    const [across, down] = cellsOf(button, columns);
    grid.children[index]?.style.setProperty('--w', String(across));
    grid.children[index]?.style.setProperty('--h', String(down));
  });
}

// What a panel gives to all its buttons: the tile under those that have no
// picture of their own, and the colour and the glow of their signs.
// panel: { tile (a URL or null), sign_color, sign_glow }
export function themeGrid(grid, panel) {
  const set = (name, value) => (
    value ? grid.style.setProperty(name, value) : grid.style.removeProperty(name)
  );
  grid.classList.toggle('tiled', Boolean(panel.tile));
  grid.classList.toggle('glow', Boolean(panel.sign_glow));
  set('--tile', panel.tile ? `url("${panel.tile}")` : null);
  set('--sign-color', panel.sign_color);
  set('--sign-glow', panel.sign_glow);
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
  themeGrid(grid, panel);
  const nodes = panel.buttons.map((button) => buttonNode(button));
  grid.replaceChildren(...nodes);
  layoutGrid(grid, panel, wide);
  return nodes;
}
