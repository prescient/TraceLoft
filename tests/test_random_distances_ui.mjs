import test from 'node:test';
import assert from 'node:assert/strict';
import { targetGrid, setupPreview, lastResult } from '../web/random-distances.js';
import { featureForDrill, featureForSession } from '../web/features.js';
import { parseRoute } from '../web/navigation.js';
import { categories } from '../web/practice-categories.js';

const setup = {
  random_min: 60,
  random_max: 180,
  random_step: 5,
  random_gap: 15,
  random_count: 20,
  range_depth: 20
};

test('the target grid matches the server grid', () => {
  assert.deepEqual(targetGrid(60, 80, 5), [60, 65, 70, 75, 80]);
  assert.deepEqual(targetGrid(60, 82, 5), [60, 65, 70, 75, 80]);
  assert.deepEqual(targetGrid(80, 60, 5), []);
});

test('the setup preview explains the draw, or what to change', () => {
  const ok = setupPreview(setup);
  assert.equal(ok.ok, true);
  assert.match(ok.text, /20 targets drawn from 25 distances \(60–180 yd, every 5 yd\)/);
  assert.match(ok.text, /at least 15 yd from the last/);
  assert.match(ok.text, /±10 yd/);
  const narrow = setupPreview({ ...setup, random_min: 100, random_max: 110 });
  assert.equal(narrow.ok, false);
  assert.match(narrow.text, /Widen the range or lower the minimum change/);
  assert.equal(setupPreview({ ...setup, random_max: 60 }).ok, false);
});

test('the latest result is described in words, with estimates labeled', () => {
  assert.equal(lastResult(undefined).kind, 'waiting');
  const unscored = lastResult({ scored: false });
  assert.equal(unscored.kind, 'miss');
  assert.match(unscored.text, /target unchanged/);
  const shot = {
    scored: true,
    success: true,
    target_distance_yd: 140,
    distance_basis: 'opengolfcoach',
    range_vals: { carry: 135.2 },
    vals: {}
  };
  const hit = lastResult(shot);
  assert.equal(hit.kind, 'hit');
  assert.equal(hit.text, 'Target 140 yd · carry 135.2 yd est. · 4.8 yd short · In window ✓');
  const long = lastResult({ ...shot, success: false, range_vals: { carry: 162 }, excluded: true });
  assert.equal(long.kind, 'miss');
  assert.equal(long.text, 'Target 140 yd · carry 162 yd est. · 22 yd long · Outside window · excluded');
});

test('random distances has a setup route, a Full swing card and its own runner feature', () => {
  assert.equal(featureForDrill('random-distances').id, 'random-distances');
  assert.deepEqual(parseRoute('#setup/random-distances'), {
    view: 'setup',
    drillId: 'random-distances',
    sessionId: undefined
  });
  assert.ok(categories.find(([id]) => id === 'full')[3].includes('random-distances'));
  const data = { session_kind: 'driving_range', practice_type: 'full_swing', target_plan: 'random' };
  assert.equal(featureForSession(data).id, 'random-distances');
  assert.equal(featureForSession({ ...data, target_plan: undefined }).id, 'range');
});
