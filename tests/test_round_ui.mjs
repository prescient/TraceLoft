import test from 'node:test';
import assert from 'node:assert/strict';
import { holeShots, reviewHoleData, roundScorecard as roundScorecardMarkup } from '../web/round-ui.js';
import { gameScoreboard as gameScoreboardMarkup, courseMap as courseMapMarkup } from '../web/golf-sim.js';
import { roundLabel } from '../web/round-ui.js';
// Markup helpers return SafeHtml (a String object); compare their text.
const roundScorecard = (...args) => String(roundScorecardMarkup(...args));
const gameScoreboard = (...args) => String(gameScoreboardMarkup(...args));
const courseMap = (...args) => String(courseMapMarkup(...args));
const holes = Array.from({ length: 18 }, (_, i) => ({
  id: `h${i}`,
  hole_number: i + 1,
  name: `Hole ${i + 1}`,
  par: 4,
  yards: 350,
  tee: [0, 0],
  pin: [0, 350],
  fairway: [],
  sand: [],
  water: []
}));
const game = {
  position: [0, 350],
  aim: [0, 350],
  lie: 'green',
  strokes: 5,
  penalties: 1,
  concessions: 1,
  holed: true
};
const data = () => ({
  id: 'r',
  course: holes[1],
  round: {
    holes,
    index: 1,
    results: [{ hole_id: 'h0', hole_number: 1, par: 4, game }],
    name: 'Pebble Boulder',
    tee_label: 'Blue',
    yards: 6300,
    par: 72
  },
  game: { ...game, strokes: 2, holed: false },
  shots: [
    { hole_id: 'h0', game_outcome: { applied: true } },
    { hole_id: 'h1', game_outcome: { applied: true } },
    { hole_id: 'h1', game_outcome: { applied: false } }
  ]
});
test('round score adds current partial without claiming holes or par completed', () => {
  const html = roundScorecard(data());
  assert.match(html, /<strong>7<\/strong>/);
  assert.match(html, /1\/18 holes complete/);
  assert.match(html, /\+1 on completed holes/);
  assert.match(html, /2\*/);
});
test('review switches frozen holes without mutating current state; unplayed holes stay empty', () => {
  const d = data(),
    before = structuredClone(d),
    first = reviewHoleData(d, 0);
  assert.equal(first.course.id, 'h0');
  assert.equal(first.game.strokes, 5);
  assert.equal(holeShots(first).length, 1);
  assert.equal(reviewHoleData(d, 2).game.strokes, 0);
  assert.deepEqual(d, before);
  assert.match(roundScorecard(d, true, 0), /value="0" selected/);
  assert.match(gameScoreboard(d), /Shots played<\/dt><dd>1/);
  assert.equal(holeShots({ ...d, round: undefined }).length, 3);
});

test('compact scorecard keeps reviewed-hole counts separate from the original round total', () => {
  const d = data(),
    reviewed = reviewHoleData(d, 0),
    before = structuredClone(d);
  // holeScore is markup: pass the html`` value, not its text.
  const html = roundScorecard(d, true, 0, true, gameScoreboardMarkup(reviewed, true));
  assert.match(html, /Hole 1 · Par 4/);
  assert.match(html, /Total strokes<\/dt><dd>5/);
  assert.match(html, /<strong>7<\/strong>/);
  assert.match(html, /value="0" selected/);
  assert.deepEqual(d, before);
});

test('nine-hole scorecards use original hole numbers and the correct nine total', () => {
  for (const [selection, start, label, other] of [
    ['front', 0, 'Front nine', 'Back nine'],
    ['back', 9, 'Back nine', 'Front nine']
  ]) {
    const d = data();
    d.round.holes = holes.slice(start, start + 9);
    d.round.index = 1;
    d.round.selection = selection;
    d.course = d.round.holes[1];
    d.round.results = [{ hole_id: d.round.holes[0].id, hole_number: start + 1, par: 4, game }];
    const html = roundScorecard(d, true, 0);
    assert.match(html, new RegExp(`<caption>${label}</caption>`));
    assert.ok(!html.includes(`<caption>${other}</caption>`));
    assert.match(html, /<strong>7<\/strong>/);
    assert.match(html, /1\/9 holes complete/);
    assert.match(html, new RegExp(`<th scope="col">${start + 1}</th>`));
    assert.equal(reviewHoleData(d, 0).course.hole_number, start + 1);
    assert.equal(reviewHoleData(d, 0).game.strokes, 5);
    assert.equal(roundLabel(d.round), selection === 'front' ? 'Front 9' : 'Back 9');
  }
});
