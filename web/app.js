import { resetShotMotion } from './shot-motion.js';
import { courseLabel } from './round-ui.js';
import { renderPlay } from './golf-sim.js';
import { renderCourseImport } from './course-import.js';
import { renderAnalyze } from './analyze.js';
import { categorizedDrills, categoryMarkup, bindCategories } from './practice-categories.js';
import { html } from './charts.js';
import { parseRoute, routeFor } from './navigation.js';
import { refreshSetupEquipment } from './equipment.js';
import { recordingWarnings } from './recording.js';
import { featureForDrill, featureForSession } from './features.js';
import { bindGolferPicker } from './golfers.js';
import { createLiveStateController, isStaleState } from './live-state.js';
import { preserveInteraction } from './interaction-state.js';

const app = document.querySelector('#app'),
  connection = document.querySelector('#connection');
let state = null,
  drills = [],
  view = 'choose',
  selectedDrill = null,
  review = null,
  selectedShot = null,
  socket = null,
  renderKey = '',
  online = false;
let sessionList = [],
  sessionListRequest = 0,
  sessionMode = 'all';
let abandonedSession = null;
let navigationRequest = 0;
let courses = [];
let runner = null; // { context, feature, handle } for the mounted runner; see features.js.
let reviewRequest = 0;

function notice(message, undo = null) {
  const box = document.querySelector('#notice');
  box.hidden = false;
  const undoButton = undo ? html`<button class="btn small" data-undo>Undo</button>` : '';
  box.innerHTML = html`<span>${message}</span>${undoButton}<button class="dismiss" aria-label="Dismiss message">×</button>`;
  box.querySelector('.dismiss').onclick = () => (box.hidden = true);
  if (undo)
    box.querySelector('[data-undo]').onclick = async event => {
      event.target.disabled = true;
      try {
        await undo();
      } catch (e) {
        notice(e.message);
      }
    };
}
function confirmAction(title, message, label) {
  if (document.querySelector('#session-confirm')) return Promise.resolve(false);
  return new Promise(resolve => {
    const dialog = document.createElement('dialog');
    dialog.id = 'session-confirm';
    dialog.className = 'confirm-dialog';
    dialog.setAttribute('aria-labelledby', 'confirm-title');
    dialog.setAttribute('aria-describedby', 'confirm-description');
    dialog.innerHTML = html`<form method="dialog"><h2 id="confirm-title">${title}</h2><p id="confirm-description">${message}</p><div class="confirm-actions"><button class="btn quiet" value="cancel" autofocus>Cancel</button><button class="btn danger" value="confirm">${label}</button></div></form>`;
    dialog.addEventListener(
      'close',
      () => {
        const confirmed = dialog.returnValue === 'confirm';
        dialog.remove();
        resolve(confirmed);
      },
      { once: true }
    );
    document.body.append(dialog);
    dialog.showModal();
  });
}
async function deleteSession(data) {
  if (
    !(await confirmAction(
      'Delete session?',
      `${data.drill} · ${date(data.started)} · ${data.captured ?? data.shots.length} recorded ${shotWord(data)}. Remove this session from your list? You can restore it from Recently deleted.`,
      'Delete session'
    ))
  )
    return;
  state = await api(`/api/sessions/${data.id}`, null, 'DELETE');
  review = null;
  setView('sessions');
  notice('Session deleted.', async () => {
    state = await api(`/api/sessions/${data.id}/restore`, {});
    setView('sessions');
    notice('Session restored.');
  });
}
async function api(path, body, method) {
  const response = await fetch(path, {
    method: method ?? (body ? 'POST' : 'GET'),
    credentials: 'same-origin',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(
      Array.isArray(data.detail)
        ? data.detail.map(d => `${d.loc.at(-1)}: ${d.msg}`).join('; ')
        : (data.detail ?? 'Request failed')
    );
    error.status = response.status;
    throw error;
  }
  return data;
}
// `extra` is attribute markup: html`` or ''.
const button = (text, action, kind = '', extra = '') =>
  html`<button class="btn ${kind}" data-action="${action}" ${extra}>${text}</button>`;
const date = value => new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
const shotWord = data => (data?.practice_type === 'full_swing' ? 'shots' : 'putts');
const equipmentContext = {
  catalog: () => state.equipment,
  notice,
  save: async (path, body, method) => update(await api(path, body, method))
};

function setView(next, { replace = false } = {}) {
  resetShotMotion();
  closeRunner();
  navigationRequest++;
  const route = routeFor(next, { practice: state?.practice, review, drill: selectedDrill });
  if (location.hash !== route) history[replace ? 'replaceState' : 'pushState'](null, '', route);
  view = next;
  selectedShot = null;
  renderKey = '';
  render();
  window.scrollTo({ top: 0, behavior: 'instant' });
}
async function openRoute(hash) {
  resetShotMotion();
  const ticket = ++navigationRequest,
    route = parseRoute(hash);
  let nextReview = null;
  try {
    if (!route) {
      review = null;
      setView('choose', { replace: true });
      return;
    }
    if (route.view === 'runner') {
      if (route.review || state.practice?.id !== route.sessionId) {
        const saved = await api(`/api/sessions/${route.sessionId}`);
        if (ticket !== navigationRequest) return;
        nextReview = saved;
      }
    } else if (route.view === 'setup') {
      if (state.practice && !state.practice.ended) {
        review = null;
        setView('choose', { replace: true });
        notice('End or abandon the active session before setting up another drill.');
        return;
      }
      const drill = drills.find(d => d.id === route.drillId);
      let parameters;
      if (route.sessionId) {
        parameters = (await api(`/api/sessions/${route.sessionId}`)).practice;
        if (ticket !== navigationRequest) return;
      }
      selectedDrill = { ...drill, parameters: parameters ?? drill.defaults };
    }
    // An old live-session link becomes a saved review once a different drill owns capture.
    review = nextReview;
    setView(route.view, { replace: true });
  } catch (e) {
    if (ticket !== navigationRequest) return;
    review = null;
    setView(route?.view === 'runner' ? 'sessions' : 'choose', { replace: true });
    notice(e.status === 404 ? 'This session is no longer available. Choose another session.' : e.message);
  }
}
function navigation() {
  const section =
    view === 'course-import'
      ? 'play'
      : ['relay', 'play', 'analyze', 'sessions'].includes(view)
        ? view
        : view === 'runner' && review
          ? 'sessions'
          : view === 'runner' && state.practice
            ? featureForSession(state.practice).section
            : view === 'setup'
              ? (featureForDrill(selectedDrill?.id)?.section ?? 'practice')
              : 'practice';
  document.querySelectorAll('[data-nav]').forEach(b => {
    const active = b.dataset.nav === section;
    b.classList.toggle('active', active);
    if (active) b.setAttribute('aria-current', 'page');
    else b.removeAttribute('aria-current');
  });
  connection.classList.toggle('offline', !online || !state?.capture.running);
  connection.querySelector('span:last-child').textContent = !online
    ? 'Reconnecting'
    : state?.capture.running
      ? 'Source ready'
      : 'Waiting for source';
}
function update(next) {
  if (isStaleState(state, next)) return;
  const previousSession = JSON.stringify([state?.practice?.id, state?.practice?.ended]);
  const sessionsChanged = state?.sessions_revision !== next.sessions_revision;
  const golferChanged = state?.golfer_id !== next.golfer_id;
  const equipmentChanged = golferChanged || state?.equipment?.revision !== next.equipment?.revision;
  state = next;
  navigation();
  bindGolferPicker(
    state,
    async body => {
      review = null;
      update(await api('/api/golfers/select', body));
      setView('choose');
    },
    notice
  );
  if (golferChanged) {
    review = null;
    renderKey = '';
  }
  if (view === 'relay') updateRelay();
  else if (view === 'sessions' && sessionsChanged) renderSessions();
  else if (view === 'play' && previousSession !== JSON.stringify([state.practice?.id, state.practice?.ended]))
    renderPlay(app, state, courses);
  else if (
    view === 'choose' &&
    previousSession !== JSON.stringify([state.practice?.id, state.practice?.ended])
  )
    renderChoose();
  else if (view === 'setup' && equipmentChanged) refreshSetupEquipment(app, equipmentContext);
  else if (view === 'runner') {
    if (review && sessionsChanged) refreshReview();
    const key = runnerKey();
    if (key !== renderKey) {
      renderKey = key;
      renderRunner(true);
    }
    const feedback = app.querySelector('#recording-feedback');
    if (feedback) {
      const markup = String(recordingWarnings(state.capture, shotWord(review?.practice ?? state.practice)));
      if (feedback.innerHTML !== markup) feedback.innerHTML = markup;
    }
  }
}
async function refreshReview() {
  const id = review.practice.id;
  const ticket = ++reviewRequest;
  try {
    const next = await api(`/api/sessions/${id}`);
    if (ticket === reviewRequest && view === 'runner' && review?.practice.id === id) {
      review = next;
      renderRunner(true);
    }
  } catch (e) {
    if (ticket === reviewRequest && view === 'runner' && review?.practice.id === id && e.status === 404) {
      review = null;
      setView('sessions');
      notice('This session was deleted on another device.');
    }
  }
}
function connect() {
  const current = new WebSocket(
    `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws?protocol=2`
  );
  socket = current;
  const live = createLiveStateController({
    fetchState: () => api('/api/state'),
    apply: next => {
      if (socket === current) update(next);
    },
    onError: () => current.close()
  });
  current.onopen = () => {
    if (socket === current) {
      online = true;
      navigation();
    }
  };
  current.onmessage = event => {
    if (socket !== current) return;
    const message = JSON.parse(event.data);
    if (message.type === 'state_changed') live.notify(message);
    else if (message.capture) update(message); // Already-open older servers during a rolling restart.
  };
  current.onclose = () => {
    live.dispose();
    if (socket !== current) return;
    online = false;
    if (view !== 'offline') {
      navigation();
      setTimeout(() => {
        if (socket === current && view !== 'offline') connect();
      }, 1800);
    }
  };
}

async function boot() {
  try {
    const fragment = new URLSearchParams(location.hash.slice(1));
    if (fragment.has('pair')) history.replaceState(null, '', location.pathname);
    state = await api('/api/state');
    drills = categorizedDrills(await api('/api/drills'));
    courses = await api('/api/courses');
    document.querySelector('nav').hidden = false;
    connection.hidden = false;
    review = null;
    online = true;
    if (location.hash) await openRoute(location.hash);
    else setView(state.practice && !state.practice.ended ? 'runner' : 'choose', { replace: true });
    connect();
  } catch (e) {
    view = 'offline';
    online = false;
    navigation();
    app.innerHTML =
      '<section class="card pair-card"><h1>Could not open TraceLoft</h1><p>Start the TraceLoft server, then try again.</p><button class="btn primary" data-action="retry">Try again</button></section>';
    notice(e.message);
  }
}

function render() {
  navigation();
  if (view === 'choose') renderChoose();
  else if (view === 'setup') renderSetup();
  else if (view === 'runner') renderRunner();
  else if (view === 'relay') renderRelay();
  else if (view === 'sessions') renderSessions();
  else if (view === 'analyze') renderAnalyze(app, api, notice, () => view === 'analyze', state?.golfer_id);
  else if (view === 'play') renderPlay(app, state, courses);
  else if (view === 'course-import')
    renderCourseImport(
      app,
      api,
      notice,
      async () => {
        courses = await api('/api/courses');
      },
      () => view === 'course-import'
    );
}
function renderChoose() {
  const ended = state.practice?.ended ? state.practice : !state.practice ? abandonedSession : null;
  app.innerHTML = html`<div class="page-head"><div><h1>Practice</h1><p class="subtitle">Choose your focus. Set your targets. Start practicing.</p></div>${state.practice && !state.practice.ended ? button('Return to active drill', 'return', 'primary') : ''}</div>${ended ? sessionNotice(ended) : ''}<div class="practice-categories">${categoryMarkup(drills)}</div><div class="section-space top-hint">Practice sessions save automatically. Review your results in Sessions.</div>`;
  bindCategories(app);
}
function renderSetup() {
  featureForDrill(selectedDrill.id).setup(app, selectedDrill, {
    launch,
    notice,
    equipment: equipmentContext,
    courses
  });
}
async function launch(params) {
  state = await api('/api/practice', params);
  review = null;
  abandonedSession = null;
  setView('runner');
}

function sessionNotice(data, isReview = false) {
  const title = data.abandoned ? 'Session abandoned' : data.ended ? 'Session over' : 'Review only';
  const detail = data.ended
    ? `No more ${shotWord(data)} will be saved to this session.`
    : 'You are reviewing saved results. Return to Practice for the active drill.';
  return html`<section class="session-ended" role="alert" aria-label="${title}"><span class="ended-icon" aria-hidden="true">!</span><div><h2>${title}</h2><p>${detail}</p><span>${data.abandoned ? `Recorded ${shotWord(data)} are saved.` : `${data.shots.length} recorded ${shotWord(data)} saved.`}${isReview ? ' Exit review to return to your sessions.' : ` Start a new ${featureForSession(data).unit} to record more.`}</span></div></section>`;
}
// Where a session's runner returns when it closes: its feature's navigation section.
const home = data =>
  data && featureForSession(data).section === 'play'
    ? { view: 'play', label: 'Play' }
    : { view: 'choose', label: 'Practice' };
async function exitSession() {
  if (review) {
    review = null;
    setView('sessions');
    return;
  }
  const data = state.practice;
  if (data && !data.ended) {
    if (
      !(await confirmAction(
        'End session and exit?',
        `Save your recorded ${shotWord(data)} and return to ${home(data).label}? This session will stop accepting ${shotWord(data)}. Relay keeps listening.`,
        'End session & exit'
      ))
    )
      return;
    state = await api(`/api/practice/${data.id}/finish`, {});
  }
  review = null;
  setView(home(data).view);
}
function runnerKey() {
  const data = review?.practice ?? state.practice;
  return JSON.stringify([
    review ?? state.practice,
    review?.summary ?? state.summary,
    state.equipment?.revision,
    data && featureForSession(data).sessionsRevision ? state.sessions_revision : null,
    state.practice_error,
    state.capture.running,
    state.capture.stopping
  ]);
}
function closeRunner() {
  runner?.handle.dispose();
  runner = null;
}
function renderRunner(preserveEdits = false) {
  const data = review?.practice ?? state.practice;
  if (!data) {
    setView('choose');
    return;
  }
  renderKey = runnerKey();
  const feature = featureForSession(data),
    context = JSON.stringify([state.golfer_id, data.id, data.ended, !!review]);
  if (runner?.context !== context || runner.feature !== feature) {
    closeRunner();
    runner = { context, feature, handle: feature.mount(app, runnerHost(data.id)) };
    preserveEdits = false;
  }
  const show = () =>
    runner.handle.update({
      data,
      summary: review?.summary ?? state.summary,
      state,
      review: !!review,
      selectedShot
    });
  if (preserveEdits) preserveInteraction(app, show);
  else show();
}
// What a mounted runner may do, bound to its session (see features.js).
function runnerHost(id) {
  const showing = () => view === 'runner' && (review?.practice ?? state.practice)?.id === id;
  return {
    api,
    notice,
    equipment: equipmentContext,
    sessionNotice,
    apply: update,
    redraw: () => {
      if (showing()) renderRunner(true);
    },
    rerender: () => renderRunner(),
    selection: () => state.practice?.equipment_selection,
    // A cleanup/exclusion response ({practice, summary}) for this session, saved or live.
    replaceSession: saved => {
      if (view === 'runner' && review?.practice.id === id) review = saved;
      else if (state.practice?.id === id) {
        state.practice = saved.practice;
        state.summary = saved.summary;
      }
    },
    // A correction reopens the session it corrected as the live runner.
    openLive: next => {
      review = null;
      update(next);
      setView('runner', { replace: true });
    }
  };
}

async function renderSessions() {
  const request = ++sessionListRequest;
  const deletedWasOpen = app.querySelector('#deleted-sessions')?.open ?? false;
  if (!app.querySelector('.session-list'))
    app.innerHTML =
      '<div class="page-head"><div><h1>Sessions</h1><p class="subtitle">Your saved practice, ready to review.</p></div></div><div class="loading">Loading sessions…</div>';
  try {
    const [sessions, deleted] = await Promise.all([api('/api/sessions'), api('/api/sessions?deleted=true')]);
    if (view !== 'sessions' || request !== sessionListRequest) return;
    sessionList = sessions;
    const active = s => s.id === state.practice?.id && !state.practice.ended;
    const visible = sessions.filter(s => sessionMode === 'all' || (sessionMode === 'demo') === !!s.demo);
    const label = s =>
      s.abandoned
        ? 'Abandoned'
        : active(s)
          ? 'Active'
          : s.ended
            ? s.summary.hole_count && !s.summary.round_complete
              ? 'Ended early'
              : 'Complete'
            : 'Unfinished';
    const entry = s =>
      html`<section class="card session-entry"><div><h2>${s.demo ? 'DEMO · ' : ''}${courseLabel(s.summary?.course_name ?? s.drill)}${s.summary?.round_selection === 'front' ? ' · Front 9' : s.summary?.round_selection === 'back' ? ' · Back 9' : ''}${s.random_pace ? ' / Random pace' : ''}</h2><p>${date(s.started)} · ${s.summary.count} included · ${featureForSession(s).result(s.summary)} · <span class="${s.abandoned ? 'miss-text' : ''}">${label(s)}</span></p>${active(s) ? html`<p class="top-hint">Finish or abandon this session before deleting.</p>` : ''}</div><div class="session-actions">${button(active(s) ? 'Return to active drill →' : 'Review session →', 'review', '', html`data-id="${s.id}"`)}${button('Delete', 'delete-session', 'danger quiet', html`data-id="${s.id}" ${active(s) ? 'disabled' : ''}`)}</div></section>`;
    const deletedEntry = s =>
      html`<section class="card session-entry"><div><h2>${s.demo ? 'DEMO · ' : ''}${s.drill}</h2><p>${date(s.started)} · ${s.captured} recorded ${shotWord(s)}</p></div>${button('Restore session', 'restore-session', '', html`data-id="${s.id}"`)}</section>`;
    app.innerHTML = html`<div class="page-head"><div><h1>Sessions</h1><p class="subtitle">Your saved practice, ready to review.</p></div></div><div class="range-session-mode"><label class="field">Session data<select id="session-mode"><option value="all" ${sessionMode === 'all' ? 'selected' : ''}>All sessions</option><option value="real" ${sessionMode === 'real' ? 'selected' : ''}>Real sessions</option><option value="demo" ${sessionMode === 'demo' ? 'selected' : ''}>Demo sessions only</option></select></label></div><div class="session-list">${visible.length ? visible.map(entry) : html`<section class="card empty">No saved sessions. Choose a drill in Practice to get started.</section>`}</div><details id="deleted-sessions" class="details deleted-sessions" ${deletedWasOpen ? 'open' : ''}><summary>Recently deleted (${deleted.length})</summary><p>Deleted sessions stay here until you restore them.</p><div class="session-list">${deleted.length ? deleted.map(deletedEntry) : html`<p>No deleted sessions.</p>`}</div></details>`;
    app.querySelector('#session-mode').onchange = e => {
      sessionMode = e.target.value;
      renderSessions();
    };
  } catch (e) {
    if (view === 'sessions' && request === sessionListRequest) notice(e.message);
  }
}

function renderRelay() {
  const relay = state.relay;
  app.innerHTML = html`<div class="page-head"><div><p class="eyebrow">CONNECT / RECORD / FORWARD</p><h1>Relay</h1><p class="subtitle">Incoming shots save automatically. Choose where they go next.</p></div><span class="chip accent">Always listening · TCP ${state.input.port}</span></div>
  <div class="capture-grid"><section class="card"><h2>Incoming shots</h2><div id="relay-source" class="section-space"></div><p class="form-hint">Point your shot source at <strong>127.0.0.1:${state.input.port}</strong> using GSPro Open Connect.</p><div class="table-wrap section-space" id="relay-read"></div></section>
  <section class="card"><h2>Send shots to</h2><label class="field section-space">Destination<select id="relay-destination"><option value="off">Off · record only</option><option value="gspro">GSPro</option><option value="infinite_tees">Infinite Tees</option></select></label><p class="form-hint">Saved automatically. Direct connection; no adapter app required.</p><div id="relay-output" class="section-space" role="status"></div><details class="details section-space"><summary>Connection details</summary><form id="relay-connection"><label class="field">Simulator port<input name="port" type="number" min="1" max="65535" value="${relay.port}" required></label><p class="form-hint">Localhost · GSPro defaults to 921; Infinite Tees to 999.</p><button class="btn" type="submit">Save port</button></form></details></section></div>
  <section class="card section-space"><h2>Data & backups</h2><p class="form-hint">Shots and sessions save to SQLite, even when forwarding is off or the simulator is disconnected.</p><div class="form-foot"><a class="btn" href="/api/exports/csv" download>Export CSV</a>${button('Back up database', 'backup-database', 'quiet')}</div><p id="database-backup-status" class="backup-status" role="status"></p></section>
  <details class="card section-space"><summary>Access & diagnostics</summary><p>${state.access.addresses.map((url, i) => [i ? ' · ' : '', html`<a href="${url}">${url}</a>`])}</p><pre id="relay-logs" class="diagnostic-log"></pre></details>`;
  const select = app.querySelector('#relay-destination');
  select.value = relay.destination;
  const save = async settings => {
    select.disabled = true;
    try {
      update(await api('/api/input/forwarding', settings));
    } catch (e) {
      notice(e.message);
      select.value = state.relay.destination;
    } finally {
      select.disabled = false;
    }
  };
  select.onchange = async () => {
    await save({ destination: select.value });
    app.querySelector('#relay-connection').elements.port.value = state.relay.port;
  };
  app.querySelector('#relay-connection').onsubmit = async e => {
    e.preventDefault();
    await save({ destination: select.value, port: Number(e.target.elements.port.value) });
  };
  updateRelay();
}
function updateRelay() {
  const source = app.querySelector('#relay-source');
  if (!source) return;
  source.innerHTML = html`<strong>${state.capture.status}</strong><p>${state.input.device || 'No source connected'} · ${state.input.received} records stored this run</p>${state.input.error ? html`<p class="session-error">${state.input.error}</p>` : ''}`;
  const relay = state.relay;
  app.querySelector('#relay-output').innerHTML =
    html`<strong>${relay.status}</strong><p>${relay.sent} shots sent this run</p>${relay.enabled && !relay.connected ? html`<p class="form-hint">Open the selected simulator. Relay reconnects automatically; earlier shots are not replayed.</p>` : ''}`;
  const select = app.querySelector('#relay-destination');
  if (!select.disabled) select.value = relay.destination;
  app.querySelector('#relay-logs').textContent = state.logs.join('\n');
  const units = {
    ball_speed: 'mph',
    launch_ang: '°',
    launch_dir: '°',
    total_spin: 'rpm',
    spin_axis: '°',
    back_spin: 'rpm',
    side_spin: 'rpm',
    carry: 'yd',
    total: 'yd',
    offline: 'yd',
    peak_height: 'ft',
    descent_ang: '°',
    curve: 'yd',
    hang_time: 's',
    club_speed: 'mph',
    attack_angle: '°',
    face_angle: '°',
    dynamic_lie: '°',
    dynamic_loft: '°',
    club_path: '°'
  };
  const vals = state.read?.vals;
  app.querySelector('#relay-read').innerHTML = vals
    ? html`<h2>Latest measurements</h2><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>${Object.entries(
        vals
      ).map(
        ([k, v]) =>
          html`<tr><td>${k.replaceAll('_', ' ')}${units[k] ? ' · ' + units[k] : ''}</td><td>${v ?? '—'}</td></tr>`
      )}</tbody></table>`
    : html`<p class="form-hint">Waiting for the first shot.</p>`;
}

document.addEventListener('click', async event => {
  const nav = event.target.closest('[data-nav]');
  if (event.target.closest('.brand')) {
    event.preventDefault();
    if (state) {
      review = null;
      setView('choose');
    }
    return;
  }
  if (nav && state) {
    review = null;
    setView(nav.dataset.nav === 'practice' ? 'choose' : nav.dataset.nav);
    return;
  }
  const row = event.target.closest('[data-key]');
  if (row) {
    selectedShot = row.dataset.key;
    renderRunner();
    return;
  }
  const action = event.target.closest('[data-action]');
  if (!action || action.disabled) return;
  const data = review?.practice ?? state?.practice;
  try {
    switch (action.dataset.action) {
      case 'retry':
        await boot();
        break;
      case 'choose':
        if (state.practice && !state.practice.ended) {
          notice('Finish or abandon the active session before setting up another drill.');
          return;
        }
        selectedDrill = { ...drills.find(d => d.id === action.dataset.drill) };
        selectedDrill.parameters = action.dataset.course
          ? { ...selectedDrill.defaults, course: { id: action.dataset.course } }
          : selectedDrill.defaults;
        setView('setup');
        break;
      case 'home':
        review = null;
        setView('choose');
        break;
      case 'play':
        review = null;
        setView('play');
        break;
      case 'tour-demo': {
        action.disabled = true;
        action.textContent = 'Building demo profiles…';
        try {
          const loaded = await api('/api/demo/tour-pack', {});
          update(loaded.state);
          notice(
            loaded.result.already_loaded
              ? 'Tour demo bag already loaded. Find its saved sessions in Sessions.'
              : `Loaded ${loaded.result.shot_count} synthetic shots in a separate Tour demo bag. Select it in demo round setup.`
          );
        } finally {
          if (action.isConnected) {
            action.disabled = false;
            action.textContent = 'Load Tour demo bag';
          }
        }
        break;
      }
      case 'exit-session':
        await exitSession();
        break;
      case 'return':
        review = null;
        setView('runner');
        break;
      case 'finish':
        update(await api(`/api/practice/${data.id}/finish`, {}));
        break;
      case 'edit':
        if (state.practice && !state.practice.ended) {
          notice('End or abandon the active session before changing targets.');
          return;
        }
        selectedDrill = {
          ...drills.find(d => d.drill === data.drill && d.random_pace === Boolean(data.random_pace)),
          parameters: data
        };
        review = null;
        setView('setup');
        break;
      case 'exclude':
        if (selectedShot) {
          if (review) {
            review = await api(`/api/sessions/${data.id}/exclude`, { key: selectedShot });
            renderRunner();
          } else update(await api(`/api/practice/${data.id}/exclude`, { key: selectedShot }));
        }
        break;
      case 'review': {
        const request = ++navigationRequest;
        const saved = await api(`/api/sessions/${action.dataset.id}`);
        if (request !== navigationRequest) return;
        review = saved;
        if (review.practice.id === state.practice?.id && !state.practice.ended) review = null;
        setView('runner');
        break;
      }
      case 'abandon':
        if (
          await confirmAction(
            'Abandon session?',
            `End this ${featureForSession(data).unit} and return to ${home(data).label}? Recorded ${shotWord(data)} will stay in Sessions as Abandoned. Relay keeps listening.`,
            'Abandon session'
          )
        ) {
          state = await api(`/api/practice/${data.id}/abandon`, {});
          abandonedSession = { ...data, abandoned: true, ended: true };
          review = null;
          setView(home(data).view);
          notice(`Session abandoned. Recorded ${shotWord(data)} are saved in Sessions.`);
        }
        break;
      case 'delete-review':
        await deleteSession(data);
        break;
      case 'delete-session': {
        const saved = sessionList.find(s => s.id === action.dataset.id);
        if (saved) await deleteSession(saved);
        break;
      }
      case 'restore-session':
        state = await api(`/api/sessions/${action.dataset.id}/restore`, {});
        setView('sessions');
        notice('Session restored.');
        break;
      case 'relay':
        review = null;
        setView('relay');
        break;
      case 'backup-database': {
        const result = await api('/api/storage/backup', {});
        const status = app.querySelector('#database-backup-status');
        if (status) status.textContent = `Verified local backup saved: ${result.path}`;
        break;
      }
    }
  } catch (e) {
    notice(e.message);
  }
});
document.addEventListener('keydown', event => {
  if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('tr[data-key]')) {
    event.preventDefault();
    selectedShot = event.target.dataset.key;
    renderRunner();
  }
});
window.addEventListener('hashchange', () => {
  document
    .querySelectorAll('dialog')
    .forEach(d => (d.id === 'session-confirm' ? d.close('cancel') : d.close()));
  if (state) openRoute(location.hash);
});
boot();
