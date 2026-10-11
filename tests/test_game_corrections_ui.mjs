import test from 'node:test';
import assert from 'node:assert/strict';
import {
  effectiveShot,
  latestPlayedShot,
  correctionControls as correctionControlsMarkup,
  correctionCounts,
  correctionHistory as correctionHistoryMarkup
} from '../web/game-corrections.js';
import { gameScoreboard as gameScoreboardMarkup, courseMap as courseMapMarkup } from '../web/golf-sim.js';
// Markup helpers return SafeHtml (a String object); compare their text.
const gameScoreboard = (...args) => String(gameScoreboardMarkup(...args));
const courseMap = (...args) => String(courseMapMarkup(...args));
const correctionControls = (...args) => String(correctionControlsMarkup(...args));
const correctionHistory = (...args) => String(correctionHistoryMarkup(...args));
const data = () => ({
  id: 'r',
  course: {
    id: 'h',
    par: 4,
    pin: [0, 350],
    tee: [0, 0],
    bounds: [-80, 80, -15, 385],
    fairway: [],
    water: [],
    sand: [],
    green_radius: 18
  },
  game: { strokes: 1, penalties: 0, concessions: 0, holed: false, position: [0, 100], aim: [0, 350] },
  ended: null,
  shots: [
    {
      key: '1',
      hole_id: 'h',
      hole_number: 1,
      game_outcome: { applied: true, before: { position: [0, 0] }, endpoint: [0, 100], message: 'ok' }
    },
    {
      key: '2',
      hole_id: 'h',
      hole_number: 1,
      game_outcome: { applied: true },
      game_correction: { kind: 'misread' }
    },
    { key: '3', hole_id: 'h', hole_number: 1, game_outcome: { applied: false } }
  ]
});
test('corrections skip voided and unscored shots, but not analysis exclusions', () => {
  const d = data();
  d.shots[0].excluded = true;
  assert.equal(latestPlayedShot(d).key, '1');
  assert.equal(d.shots.filter(effectiveShot).length, 1);
  assert.match(gameScoreboard(d), /Shots played<\/dt><dd>1/);
  assert.match(courseMap(d), /Shot 1: ok/);
  assert.doesNotMatch(courseMap(d), /Shot 2/);
});
test('completed review exposes both actions and separate counts, with owner and abandonment guards', () => {
  const d = data();
  d.ended = '2026-10-03';
  d.game_corrections = [{ kind: 'misread', hole_number: 1, at: '2026-10-03T10:00:00Z' }];
  const html = correctionControls(d, {});
  assert.match(html, /reopens this round/);
  assert.equal(correctionCounts(d), 'Mulligans: 0 · Misreads: 1');
  assert.match(correctionHistory(d), /Hole 1/);
  assert.doesNotMatch(html, /disabled/);
  assert.match(correctionControls(d, { practice: { id: 'other', ended: null } }), /disabled/);
  d.abandoned = true;
  assert.match(correctionControls(d, {}), /Abandoned rounds cannot be reopened/);
  d.abandoned = false;
  d.shots = [];
  assert.match(correctionControls(d, {}), /No scored shots left to replay/);
});
