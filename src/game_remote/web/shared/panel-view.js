// Draws a panel. The phone and the preview in the editor both use this code,
// so what the editor shows is what the phone gets.

// button: { id, label, type: 'tap' | 'hold', color, image (a URL or null) }
export function buttonNode(button) {
  const node = document.createElement('button');
  node.type = 'button';
  node.className = `btn ${button.type === 'hold' ? 'hold' : 'tap'}`;
  node.dataset.button = button.id;
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
  const columns = wide ? Math.min(panel.buttons.length, panel.columns * 2) : panel.columns;
  return Math.max(1, columns);
}

// Fills `grid` with the panel's buttons and returns the nodes in order.
export function renderGrid(grid, panel, { wide = false } = {}) {
  grid.classList.add('panel-grid');
  grid.style.setProperty('--cols', String(columnsFor(panel, wide)));
  const nodes = panel.buttons.map(buttonNode);
  grid.replaceChildren(...nodes);
  return nodes;
}
