import { renderGameSetup, renderGame } from './golf-sim.js';
import { renderCollectionSetup } from './collection.js';
import { renderRangeSetup, renderRange, disposeRange } from './driving-range.js';
import { renderRandomSetup } from './random-distances.js';
import { renderDistanceSetup, distanceRunner } from './distance-ladder.js';
import { renderPuttingSetup, puttingRunner } from './putting.js';
import { bindEquipment } from './equipment.js';
import { stopShotMotion } from './shot-motion.js';
import { disposeCourseCamera } from './course-camera.js';

/*
 * The browser half of the drill registry (drills.py). A feature owns the setup screens for its
 * catalog ids and the runner for the sessions it `runs`; app.js routes to features and never
 * branches on a drill.
 *
 * setup(app, drill, host): render drill.parameters as a form; host.launch(params) starts it.
 * mount(app, host) → { update(view), dispose() }: the runner lifecycle.
 *   - mount runs when a runner opens, or when its session, golfer or live/review mode changes.
 *     The host is bound to that session.
 *   - update(view) renders view = { data, summary, state, review, selectedShot }, once after mount
 *     and again whenever that state changes while the runner stays open.
 *   - dispose() releases observers and animation frames when the runner closes. View choices that
 *     a feature remembers per session (filters, open panels, zoom) intentionally outlive it.
 * Capabilities: `section` is the navigation home (highlighted and returned to on exit), `unit`
 * names a session in prompts, `result(summary)` is its outcome in the Sessions list, and
 * `sessionsRevision` re-renders the runner when saved sessions change (the golf scorecard lists
 * other rounds).
 *
 * Host: { api, notice, equipment, sessionNotice, launch, apply(state), redraw(), rerender(),
 *   selection(), replaceSession(saved), openLive(state) }. See runnerHost() in app.js.
 */

const DEFAULTS = {
  section: 'practice',
  unit: 'drill',
  sessionsRevision: false,
  result: summary => `${summary.successes} in window`
};

function golfRunner(app, host) {
  return {
    update({ data, summary, state, review }) {
      const change = async (path, params) => {
        host.apply(await host.api(path, params));
        host.redraw();
      };
      renderGame(app, data, summary, state, review, host.sessionNotice, {
        equipment: host.equipment,
        notice: host.notice,
        redraw: host.redraw,
        current: host.selection,
        select: selection => change(`/api/practice/${data.id}/equipment`, selection),
        aim: params => change(`/api/game/${data.id}/aim`, params),
        simulate: params => change(`/api/game/${data.id}/simulate`, params),
        next: params => change(`/api/game/${data.id}/next`, params),
        correct: async params => host.openLive(await host.api(`/api/game/${data.id}/correct`, params)),
        preview: () => host.api(`/api/game/${data.id}/preview`),
        recommendations: () => host.api(`/api/game/${data.id}/recommendations`),
        exclude: async key => {
          if (review) host.replaceSession(await host.api(`/api/sessions/${data.id}/exclude`, { key }));
          else host.apply(await host.api(`/api/practice/${data.id}/exclude`, { key }));
          host.redraw();
        }
      });
    },
    dispose() {
      stopShotMotion();
      disposeCourseCamera();
    }
  };
}

function rangeRunner(app, host) {
  return {
    update({ data, summary, state, review }) {
      const change = async (path, params) => {
        host.apply(await host.api(path, params));
        host.redraw();
      };
      renderRange(app, data, state, review, host.sessionNotice, {
        summary,
        collectionAnalysis: () => host.api(`/api/collection/${data.id}/analysis`),
        publishProfile: () => host.api(`/api/collection/${data.id}/profile`, {}),
        cell: params => change(`/api/collection/${data.id}/cell`, params),
        equipment: host.equipment,
        notice: host.notice,
        current: host.selection,
        redraw: host.redraw,
        select: selection => change(`/api/practice/${data.id}/equipment`, selection),
        simulate: count => change(`/api/range/${data.id}/simulate`, { count }),
        target: params => change(`/api/range/${data.id}/target`, params),
        cleanup: async params => {
          host.replaceSession(await host.api(`/api/range/${data.id}/cleanup`, params));
          host.redraw();
        }
      });
    },
    dispose() {
      stopShotMotion();
      disposeRange();
    }
  };
}

function distanceLadderRunner(app, host) {
  return {
    update({ data, summary, state, review, selectedShot }) {
      app.innerHTML = distanceRunner(data, summary, state, review, selectedShot, host.sessionNotice);
      bindEquipment(
        app,
        host.equipment,
        async selection => {
          host.apply(await host.api(`/api/practice/${data.id}/equipment`, selection));
          host.rerender();
        },
        host.selection
      );
    },
    dispose() {}
  };
}

function puttingRunnerFeature(app, host) {
  return {
    update({ data, summary, state, review, selectedShot }) {
      app.innerHTML = puttingRunner(data, summary, state, review, selectedShot, host.sessionNotice);
    },
    dispose() {}
  };
}

const old = drill => drill.parameters ?? {};

// Order matters: a session runs on the first feature whose `runs` accepts it.
export const FEATURES = [
  {
    id: 'golf',
    setupIds: ['golf-sim'],
    section: 'play',
    unit: 'round',
    sessionsRevision: true,
    result: summary =>
      `${summary.strokes} strokes · ${summary.hole_count ? `${summary.holes_completed}/${summary.hole_count} holes complete` : summary.holed ? 'hole complete' : 'partial round'}`,
    runs: data => data.session_kind === 'golf_sim',
    setup: (app, drill, host) =>
      renderGameSetup(app, old(drill), host.launch, host.notice, host.equipment, host.courses),
    mount: golfRunner
  },
  {
    id: 'collection',
    setupIds: ['bag-mapping', 'wedge-matrix'],
    runs: data => data.session_kind === 'driving_range' && !!data.collection_kind,
    setup: (app, drill, host) =>
      renderCollectionSetup(
        app,
        old(drill),
        host.launch,
        host.notice,
        host.equipment,
        drill.id === 'wedge-matrix'
      ),
    mount: rangeRunner
  },
  {
    id: 'random-distances',
    setupIds: ['random-distances'],
    runs: data => data.session_kind === 'driving_range' && data.target_plan === 'random',
    setup: (app, drill, host) => renderRandomSetup(app, old(drill), host.launch, host.notice, host.equipment),
    mount: rangeRunner
  },
  {
    id: 'range',
    setupIds: ['driving-range'],
    runs: data => data.session_kind === 'driving_range',
    setup: (app, drill, host) => renderRangeSetup(app, old(drill), host.launch, host.notice, host.equipment),
    mount: rangeRunner
  },
  {
    id: 'distance-ladder',
    setupIds: ['distance-ladder', 'iron-ladder', 'wedge-ladder'],
    runs: data => data.practice_type === 'full_swing',
    setup: (app, drill, host) =>
      renderDistanceSetup(app, old(drill), host.launch, host.notice, host.equipment),
    mount: distanceLadderRunner
  },
  {
    id: 'putting',
    setupIds: ['pace', 'line', 'combined', 'random', 'ladder'],
    runs: () => true,
    setup: (app, drill, host) => renderPuttingSetup(app, drill, host.launch, host.notice),
    mount: puttingRunnerFeature
  }
].map(feature => ({ ...DEFAULTS, ...feature }));

export const featureForDrill = id => FEATURES.find(feature => feature.setupIds.includes(id));
export const featureForSession = data => FEATURES.find(feature => feature.runs(data));
