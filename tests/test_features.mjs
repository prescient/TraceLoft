import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { FEATURES, featureForDrill, featureForSession } from '../web/features.js';
import { parseRoute } from '../web/navigation.js';
import { fitCourseCamera } from '../web/course-camera.js';

// Catalog ids are the first argument of each Drill(...) in the server registry.
const catalogIds = [
  ...readFileSync(new URL('../drills.py', import.meta.url), 'utf8').matchAll(/Drill\(\s*'([\w-]+)'/g)
].map(m => m[1]);

test('every catalog drill has exactly one setup feature with a setup route', () => {
  assert.ok(catalogIds.length >= 10, `parsed ${catalogIds.length} catalog ids`);
  const claimed = FEATURES.flatMap(f => f.setupIds);
  assert.equal(new Set(claimed).size, claimed.length, 'a setup id belongs to one feature');
  for (const id of catalogIds) assert.ok(featureForDrill(id), `no feature sets up ${id}`);
  for (const id of claimed)
    assert.deepEqual(parseRoute(`#setup/${id}`), { view: 'setup', drillId: id, sessionId: undefined });
});

test('sessions run on the feature for their persisted kind, with putting as the fallback', () => {
  const cases = [
    [{ session_kind: 'golf_sim', practice_type: 'full_swing' }, 'golf'],
    [{ session_kind: 'driving_range', practice_type: 'full_swing', collection_kind: 'wedge' }, 'collection'],
    [{ session_kind: 'driving_range', practice_type: 'full_swing' }, 'range'],
    [{ practice_type: 'full_swing', drill: 'Distance ladder' }, 'distance-ladder'],
    [{ drill: 'Pace consistency' }, 'putting'],
    [{ drill: 'Putting ladder' }, 'putting']
  ];
  for (const [data, id] of cases) assert.equal(featureForSession(data).id, id, JSON.stringify(data));
});

test('capabilities replace drill checks in the shell', () => {
  const golf = featureForSession({ session_kind: 'golf_sim' }),
    putting = featureForSession({ drill: 'Pace consistency' });
  assert.deepEqual([golf.section, golf.unit, golf.sessionsRevision], ['play', 'round', true]);
  assert.deepEqual([putting.section, putting.unit, putting.sessionsRevision], ['practice', 'drill', false]);
  assert.equal(featureForDrill('golf-sim').section, 'play');
  assert.equal(
    golf.result({ strokes: 9, hole_count: 9, holes_completed: 2 }),
    '9 strokes · 2/9 holes complete'
  );
  assert.equal(golf.result({ strokes: 4, holed: true }), '4 strokes · hole complete');
  assert.equal(putting.result({ successes: 3 }), '3 in window');
  for (const f of FEATURES)
    for (const key of ['setup', 'mount', 'runs', 'result'])
      assert.equal(typeof f[key], 'function', `${f.id}.${key}`);
});

test('a runner mounts, renders each update and disposes', () => {
  // Like an element, innerHTML stores the markup as a string.
  let markup = '';
  const app = {
    get innerHTML() {
      return markup;
    },
    set innerHTML(value) {
      markup = String(value);
    }
  };
  const host = { sessionNotice: () => '' };
  const data = {
    id: 'a'.repeat(32),
    drill: 'Pace consistency',
    shots: [],
    repetitions: 5,
    target: 4,
    speed_tolerance: 0.3,
    angle_tolerance: 1,
    ended: false
  };
  const summary = {
    count: 0,
    successes: 0,
    pace_error: { mean: null },
    launch_dir: { mean: null },
    launch_ang: { mean: null }
  };
  const state = { capture: { running: true, mode: 'run', status: 'Recording' }, practice_error: null };
  const runner = featureForSession(data).mount(app, host);
  runner.update({ data, summary, state, review: false, selectedShot: null });
  assert.match(app.innerHTML, /<h1>Putting practice<\/h1>/);
  assert.match(app.innerHTML, /No recorded putts yet/);
  runner.update({ data: { ...data, ended: true }, summary, state, review: true, selectedShot: null });
  assert.match(app.innerHTML, /<h1>Session review<\/h1>/);
  runner.dispose();
});

test('disposing the golf runner releases its camera observer and animation frame', () => {
  const disconnected = [];
  globalThis.ResizeObserver = class {
    observe() {}
    disconnect() {
      disconnected.push(this);
    }
  };
  globalThis.cancelAnimationFrame = () => {};
  try {
    const svg = { isConnected: true, getBoundingClientRect: () => ({ width: 0, height: 0 }) };
    fitCourseCamera(svg, {}, false);
    featureForSession({ session_kind: 'golf_sim' }).mount({}, {}).dispose();
    assert.equal(disconnected.length, 1);
  } finally {
    delete globalThis.ResizeObserver;
    delete globalThis.cancelAnimationFrame;
  }
});
