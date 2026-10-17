import test from 'node:test';
import assert from 'node:assert/strict';
import { dropIndex, keepOrder, moveItem } from '../web/sortable.js';

test('moving a tile keeps every other tile in order', () => {
  const tiles = ['carry', 'ball_speed', 'launch_ang', 'total_spin'];
  assert.deepEqual(moveItem(tiles, 3, 0), ['total_spin', 'carry', 'ball_speed', 'launch_ang']);
  assert.deepEqual(moveItem(tiles, 0, 2), ['ball_speed', 'launch_ang', 'carry', 'total_spin']);
  assert.deepEqual(moveItem(tiles, 1, 99), ['carry', 'launch_ang', 'total_spin', 'ball_speed']);
  assert.deepEqual(moveItem(tiles, 9, 0), tiles); // an unknown tile changes nothing
  assert.deepEqual(tiles, ['carry', 'ball_speed', 'launch_ang', 'total_spin']); // not mutated
});

test('the drop target is the tile nearest the pointer, in one column or a grid', () => {
  const column = [0, 1, 2].map(i => ({ left: 0, top: i * 300, width: 800, height: 280 }));
  assert.equal(dropIndex(column, 400, 20), 0);
  assert.equal(dropIndex(column, 400, 610), 2);
  const grid = [0, 1, 2, 3].map(i => ({ left: (i % 2) * 400, top: Math.floor(i / 2) * 300, width: 380, height: 280 }));
  assert.equal(dropIndex(grid, 600, 100), 1);
  assert.equal(dropIndex(grid, 100, 500), 2);
  assert.equal(dropIndex([], 0, 0), -1);
});

test('ticking metrics keeps the golfer order and adds new ones at the end', () => {
  assert.deepEqual(keepOrder(['spin', 'carry', 'speed'], ['carry', 'speed', 'spin', 'apex']), [
    'spin',
    'carry',
    'speed',
    'apex'
  ]);
  assert.deepEqual(keepOrder(['spin', 'carry', 'speed'], ['carry', 'speed']), ['carry', 'speed']);
});
