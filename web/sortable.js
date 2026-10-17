// Drag-to-reorder for tiles (Analyze trends). Pointer events, so a finger on the iPad works as well as
// a mouse (Safari has no touch support for HTML drag and drop). The pure helpers are tested in Node.

// A copy of `list` with the item at `from` moved to index `to`.
export function moveItem(list, from, to) {
  const next = [...list];
  if (from < 0 || from >= next.length) return next;
  const [item] = next.splice(from, 1);
  next.splice(Math.max(0, Math.min(to, next.length)), 0, item);
  return next;
}

// The index a dragged tile should take: the tile whose centre is nearest the pointer. Works for one
// column and for grids, where tiles sit side by side.
export function dropIndex(rects, x, y) {
  let best = -1,
    distance = Infinity;
  rects.forEach((r, i) => {
    const d = Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2));
    if (d < distance) {
      distance = d;
      best = i;
    }
  });
  return best;
}

// Keep the golfer's order for metrics still checked, then add newly checked ones in the order given.
export function keepOrder(previous, checked) {
  const kept = previous.filter(m => checked.includes(m));
  return [...kept, ...checked.filter(m => !kept.includes(m))];
}

// Make the tiles in `container` (each with `data-sort-key` and a `[data-sort-handle]`) draggable.
// `onOrder(keys)` receives the new key order once the tile is dropped somewhere new.
export function makeSortable(container, onOrder) {
  const tiles = () => [...container.querySelectorAll('[data-sort-key]')];
  container.querySelectorAll('[data-sort-handle]').forEach(handle => {
    handle.onpointerdown = event => {
      const tile = handle.closest('[data-sort-key]');
      const from = tiles().indexOf(tile);
      let to = from;
      event.preventDefault();
      handle.setPointerCapture(event.pointerId);
      tile.classList.add('sort-dragging');
      handle.onpointermove = move => {
        const list = tiles();
        to = dropIndex(
          list.map(t => t.getBoundingClientRect()),
          move.clientX,
          move.clientY
        );
        list.forEach((t, i) => t.classList.toggle('sort-target', i === to && i !== from));
      };
      handle.onpointerup = handle.onpointercancel = () => {
        handle.onpointermove = handle.onpointerup = handle.onpointercancel = null;
        tiles().forEach(t => t.classList.remove('sort-dragging', 'sort-target'));
        const keys = tiles().map(t => t.dataset.sortKey);
        if (to >= 0 && to !== from) onOrder(moveItem(keys, from, to));
      };
    };
  });
}
