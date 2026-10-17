import { html } from './charts.js';
import { mountCalculations } from './calculations.js';
import { keepOrder, makeSortable, moveItem } from './sortable.js';
import {
  finite,
  robust,
  enriched,
  cohorts,
  cohortKey,
  rowKey,
  timeline,
  histogram,
  matchesRanges,
  comparison,
  configureColors
} from './analysis-data.js';

const defaults = () => ({
  filters: {
    mode: 'real',
    kind: 'full_swing',
    metric: 'carry',
    inclusion: 'included',
    basis: 'source',
    clubs: '',
    ranges: '{}'
  },
  view: 'trends',
  metrics: ['carry', 'absolute_offline', 'launch_ang'],
  resolution: 'session',
  grid: false,
  x: 'launch_ang',
  y: 'carry',
  distribution: 'absolute_offline',
  open: false,
  inspect: '',
  highlight: '',
  compare: null
});
let state = defaults(),
  owner = '',
  ticket = 0,
  observer;
const fmt = v => (finite(v) ? (Math.abs(v) >= 1000 ? v.toFixed(0) : v.toFixed(1)) : '—');
const options = (items, selected, empty = 'All') =>
  html`${empty == null ? '' : html`<option value="">${empty}</option>`}${items.map(
    ([id, label]) => html`<option value="${id}" ${id === selected ? 'selected' : ''}>${label}</option>`
  )}`;
const metricOptions = (r, value) =>
  options(
    Object.entries(r.metrics).map(([id, m]) => [id, m.label + ' · ' + m.unit]),
    value,
    null
  );
const ranges = () => JSON.parse(state.filters.ranges || '{}');
const storeKey = () => `traceloft.analyze.workspace.v1:${owner}`;
function remember() {
  try {
    sessionStorage.setItem(storeKey(), JSON.stringify(state));
  } catch {}
}
function restore(id) {
  if (owner === id) return;
  owner = id;
  state = defaults();
  try {
    const s = JSON.parse(sessionStorage.getItem(storeKey()));
    if (s && ['trends', 'explore', 'compare'].includes(s.view) && Array.isArray(s.metrics))
      state = { ...state, ...s, filters: { ...state.filters, ...s.filters } };
  } catch {}
}
function views() {
  try {
    return JSON.parse(localStorage.getItem(storeKey() + ':views')) ?? [];
  } catch {
    return [];
  }
}
function setViews(v) {
  localStorage.setItem(storeKey() + ':views', JSON.stringify(v.slice(-12)));
}
const requestFilters = () => ({ ...state.filters, metric: state.metrics[0] || 'carry', workspace: '1' });

export async function renderAnalyze(app, api, notice, isCurrent, golferId = 'local') {
  restore(golferId);
  observer?.disconnect();
  const request = ++ticket;
  state.open = app.querySelector('.analysis-selection')?.open ?? state.open;
  app.innerHTML =
    '<div class="page-head"><h1>Analyze</h1><button class="btn quiet" data-action="home">← Practice</button></div><p role="status">Loading saved shots…</p>';
  try {
    const r = await api('/api/analysis?' + new URLSearchParams(requestFilters()));
    if (request !== ticket || !isCurrent()) return;
    state.filters = r.filters;
    state.metrics = state.metrics.filter(m => r.metrics[m]);
    if (!state.metrics.length) state.metrics = ['carry'];
    remember();
    draw(app, r, api, notice, isCurrent, golferId);
  } catch (e) {
    if (request !== ticket || !isCurrent()) return;
    app.innerHTML = html`<div class="page-head"><h1>Analyze</h1><button class="btn quiet" data-action="home">← Practice</button></div><section class="card"><p role="alert">Could not load this selection. ${e.message}</p><button class="btn primary" data-retry>Retry</button><button class="btn quiet" data-reset>Reset filters</button></section>`;
    app.querySelector('[data-retry]').onclick = () => renderAnalyze(app, api, notice, isCurrent, golferId);
    app.querySelector('[data-reset]').onclick = () => {
      state = defaults();
      remember();
      renderAnalyze(app, api, notice, isCurrent, golferId);
    };
  }
}
function scopeSummary(r) {
  const f = state.filters,
    clubs = f.clubs?.split(',').filter(Boolean) ?? [];
  return [
    f.mode === 'demo' ? 'Demo only' : 'Real only',
    f.kind.replace('_', ' '),
    f.bag ? (r.options.bags[f.bag] ?? 'Selected bag') : 'All bags',
    clubs.length ? clubs.map(c => r.options.clubs[c]?.label ?? c.slice(0, 6)).join(' + ') : 'All clubs',
    `${f.date_from || 'First session'} → ${f.date_to || 'Latest session'}`,
    f.sessions ? f.sessions.split(',').length + ' sessions' : 'All sessions',
    f.inclusion === 'all' ? 'Including excluded' : 'Included shots',
    f.configuration ? 'Config ' + f.configuration.slice(0, 6) : '',
    f.swing ? f.swing.replace('__unspecified', 'General practice') : '',
    f.tags ? 'Tags: ' + f.tags : ''
  ]
    .filter(Boolean)
    .join(' · ');
}
function draw(app, r, api, notice, isCurrent, golferId) {
  let colors = {};
  try {
    colors = JSON.parse(localStorage.getItem(storeKey() + ':colors')) ?? {};
  } catch {}
  colors = configureColors(r.options.clubs, colors);
  try {
    localStorage.setItem(storeKey() + ':colors', JSON.stringify(colors));
  } catch {}
  const f = state.filters,
    rs = enriched(r),
    context = enriched(r, r.context_rows ?? r.rows),
    selectedClubs = f.clubs?.split(',') ?? [],
    refresh = () => renderAnalyze(app, api, notice, isCurrent, golferId),
    label = m => r.metrics[m]?.label ?? m;
  const sessionPicks = r.options.sessions.map(
    s =>
      html`<label class="collection-option"><input type="checkbox" name="sessions" value="${s.id}" ${(f.sessions ?? '').split(',').includes(s.id) ? 'checked' : ''}>${s.started.slice(0, 10)} · ${s.drill} · ${s.id.slice(0, 6)}</label>`
  );
  const coverageRows = r.trend.map(
    t =>
      html`<tr><th>${t.started.slice(0, 10)}<small class="range-stat-detail">${t.drill}</small></th><td>${t.count}</td>${state.metrics.map(m => html`<td>${fmt(t.metrics[m].median)} / ${fmt(t.metrics[m].iqr)}<small class="range-stat-detail">n=${t.metrics[m].count}</small></td>`)}<td><a class="btn" href="#sessions/${t.id}">Review session</a></td></tr>`
  );
  app.innerHTML = html`<div class="analysis-workspace"><div class="page-head"><div><p class="eyebrow">YOUR SHOTS / YOUR QUESTIONS</p><h1>Analyze</h1></div><button class="btn quiet" data-action="home">← Practice</button></div>
    <div class="analysis-view-tabs" role="group" aria-label="Analysis view">${['trends', 'explore', 'compare'].map(v => html`<button class="btn quiet" data-view="${v}" aria-pressed="${state.view === v}">${v[0].toUpperCase() + v.slice(1)}</button>`)}</div>
    <div class="analysis-identity" role="status"><strong>${f.mode === 'demo' ? 'SIMULATED DATA · Demo sessions only' : 'Recorded sessions'}</strong><span>${f.basis === 'flight' ? 'ESTIMATED · Selected analytical calculations; launch/club fields are source inputs' : 'Source-reported metrics'}</span><span>${r.count} selected / ${r.context_count ?? r.count} before numeric filters</span></div>
    <details class="analysis-selection details" ${state.open ? 'open' : ''}><summary><strong>Selections & filters</strong><span class="analysis-scope">${scopeSummary(r)}</span><span class="analysis-scope">${state.metrics.map(label).join(' · ')}</span></summary>
    <form id="analysis-filters"><div class="analysis-filters">
      <label class="field">Data<select name="mode">${options(
        [
          ['real', 'Real sessions'],
          ['demo', 'Demo sessions only']
        ],
        f.mode,
        null
      )}</select></label>
      <label class="field">Practice type<select name="kind">${options(
        [
          ['full_swing', 'Full swing'],
          ['putting', 'Putting'],
          ['game', 'Simulator rounds'],
          ['all', 'All types']
        ],
        f.kind,
        null
      )}</select></label>
      <label class="field">From session date<input type="date" name="date_from" value="${f.date_from}"></label><label class="field">Through session date<input type="date" name="date_to" value="${f.date_to}"></label>
      <label class="field">Bag<select name="bag">${options(Object.entries(r.options.bags), f.bag)}</select></label><label class="field">Swing intent<select name="swing">${options([['__unspecified', 'Unspecified / general practice'], ...r.options.swings.map(s => [s, s])], f.swing)}</select></label>
      <label class="field">Analysis scope<select name="inclusion">${options(
        [
          ['included', 'Included shots'],
          ['all', 'All non-removed shots']
        ],
        f.inclusion,
        null
      )}</select></label>
      <label class="field">Metric values<select name="basis">${options(
        [
          ['source', 'Source-reported metrics'],
          ['flight', 'Selected analytical calculations']
        ],
        f.basis,
        null
      )}</select></label>
    </div><fieldset class="analysis-picks"><legend>Clubs · any selected (none means all)</legend><div class="analysis-club-picks">${clubPicks(r, f.bag, selectedClubs)}</div></fieldset>
    <fieldset class="analysis-picks"><legend>Metrics to display</legend><div class="analysis-metric-picks">${Object.entries(
      r.metrics
    ).map(
      ([id, m]) =>
        html`<label class="collection-option"><input type="checkbox" data-metric="${id}" ${state.metrics.includes(id) ? 'checked' : ''}>${m.label} · ${m.unit}</label>`
    )}</div></fieldset>
    <details class="details section-space"><summary>Sessions, configurations and tags</summary><div class="analysis-filters section-space"><label class="field">Configuration<select name="configuration">${options(Object.entries(r.options.configurations ?? {}), f.configuration)}</select></label><label class="field">Tags · comma separated<input name="tags" value="${f.tags}" placeholder="e.g. New grip, Wind"></label><label class="field">Tag matching<select name="tag_match">${options(
      [
        ['any', 'Any selected tag'],
        ['all', 'Every selected tag']
      ],
      f.tag_match,
      null
    )}</select></label></div><div class="analysis-session-picks">${sessionPicks.length ? sessionPicks : html`<p>No sessions in this data/type scope.</p>`}</div><p class="form-hint">No checked sessions means all matching sessions. Available tags: ${(r.options.tags ?? []).join(', ') || 'None'}.</p></details>
    <div class="form-foot"><button type="submit" class="btn primary">Apply / refresh</button><button type="button" class="btn quiet" data-reset>Reset filters</button></div></form>
    <div class="analysis-filters section-space"><label class="field">Trend resolution<select data-resolution>${options(
      [
        ['shot', 'Shot · capture time'],
        ['session', 'Session · start date'],
        ['week', 'Week · Monday'],
        ['month', 'Month']
      ],
      state.resolution,
      null
    )}</select></label><label class="collection-option"><input type="checkbox" data-grid ${state.grid ? 'checked' : ''}>Grid layout</label></div>
    <details class="details section-space"><summary>Saved views · dynamic queries on this browser</summary><div class="form-foot"><label class="field">View name<input data-save-name maxlength="60" placeholder="e.g. Iron progress"></label><button class="btn" data-save-view>Save current view</button><label class="field">Saved view<select data-saved>${options(
      views().map((v, i) => ['' + i, v.name]),
      '',
      'Choose a view'
    )}</select></label><button class="btn" data-load-view>Load</button><button class="btn quiet" data-delete-view>Remove saved view</button></div><p class="form-hint">Saves applied filters and layout for this golfer/browser. Reopening includes current matching shots; it is not a frozen analysis publication.</p></details></details>
    <div class="analysis-active-ranges" aria-live="polite">${Object.entries(ranges()).map(
      ([m, b]) =>
        html`<button class="btn small" data-clear-range="${m}" aria-label="Clear ${label(m)} filter">${label(m)}: ${b.min == null ? '' : '>= ' + fmt(b.min)} ${b.max == null ? '' : '≤ ' + fmt(b.max)} ${r.metrics[m].unit} ×</button>`
    )}<button class="btn quiet" data-clear-numeric ${Object.keys(ranges()).length ? '' : 'hidden'}>Clear chart filters</button><a class="btn" href="/api/analysis?${new URLSearchParams({ ...requestFilters(), format: 'csv' }).toString()}" download>Export selected shots CSV</a></div>
    <p class="form-hint analysis-coverage">${r.excluded}/${r.eligible} excluded attempts in numeric selection · ${r.removed} removed in base scope. Manual exclusions are not automatic outliers.</p>
    <div data-analysis-body></div><details class="card details section-space" data-shot-panel><summary>Shot workspace · ${r.count} selected attempts</summary><div data-shot-workspace></div></details><details class="card details section-space"><summary>Session review and metric coverage</summary><div class="table-wrap"><table><thead><tr><th>Session</th><th>Selected</th>${state.metrics.map(m => html`<th>${label(m)} · ${r.metrics[m].unit}</th>`)}<th>Review</th></tr></thead><tbody>${coverageRows.length ? coverageRows : html`<tr><td>No matching sessions.</td></tr>`}</tbody></table></div><p class="form-hint">${r.method}</p></details></div>`;
  const root = app.querySelector('.analysis-workspace'),
    form = root.querySelector('#analysis-filters'),
    body = root.querySelector('[data-analysis-body]'),
    save = () => {
      if (root.isConnected) state.open = root.querySelector('.analysis-selection').open;
      remember();
    };
  form.onsubmit = e => {
    e.preventDefault();
    const d = new FormData(form);
    state.filters = {
      ...state.filters,
      ...Object.fromEntries(d),
      club: '',
      clubs: d.getAll('clubs').join(','),
      sessions: d.getAll('sessions').join(',')
    };
    state.inspect = '';
    state.highlight = '';
    save();
    refresh();
  };
  root.querySelector('.analysis-selection').ontoggle = e => {
    if (!root.isConnected) return;
    state.open = e.target.open;
    save();
  };
  root.querySelector('[data-reset]').onclick = () => {
    const mode = state.filters.mode;
    state = defaults();
    state.filters.mode = mode;
    save();
    refresh();
  };
  for (const k of ['mode', 'kind'])
    form.elements[k].onchange = () => {
      state.filters = {
        ...defaults().filters,
        mode: form.elements.mode.value,
        kind: form.elements.kind.value
      };
      state.compare = null;
      state.inspect = '';
      save();
      refresh();
    };
  form.elements.bag.onchange = () => {
    root.querySelector('.analysis-club-picks').innerHTML = clubPicks(r, form.elements.bag.value, []);
  };
  root.querySelectorAll('[data-metric]').forEach(
    c =>
      (c.onchange = () => {
        const checked = [...root.querySelectorAll('[data-metric]:checked')].map(c => c.dataset.metric);
        if (!checked.length) {
          c.checked = true;
          notice('Keep at least one metric selected.');
          return;
        }
        state.metrics = keepOrder(state.metrics, checked); // the golfer's tile order survives
        const d = new FormData(form);
        state.filters = {
          ...state.filters,
          ...Object.fromEntries(d),
          club: '',
          clubs: d.getAll('clubs').join(','),
          sessions: d.getAll('sessions').join(','),
          metric: checked[0]
        };
        save();
        refresh();
      })
  );
  root.querySelectorAll('[data-view]').forEach(
    b =>
      (b.onclick = () => {
        state.view = b.dataset.view;
        save();
        draw(app, r, api, notice, isCurrent, golferId);
      })
  );
  root.querySelector('[data-resolution]').onchange = e => {
    state.resolution = e.target.value;
    state.inspect = '';
    save();
    draw(app, r, api, notice, isCurrent, golferId);
  };
  root.querySelector('[data-grid]').onchange = e => {
    state.grid = e.target.checked;
    save();
    draw(app, r, api, notice, isCurrent, golferId);
  };
  root.querySelectorAll('[data-clear-range]').forEach(
    b =>
      (b.onclick = () => {
        const next = ranges();
        delete next[b.dataset.clearRange];
        state.filters.ranges = JSON.stringify(next);
        save();
        refresh();
      })
  );
  root.querySelector('[data-clear-numeric]').onclick = () => {
    state.filters.ranges = '{}';
    save();
    refresh();
  };
  root.querySelector('[data-save-view]').onclick = () => {
    const name = root.querySelector('[data-save-name]').value.trim();
    if (!name) {
      notice('Name this view first.');
      return;
    }
    try {
      save();
      const list = views().filter(v => v.name !== name);
      list.push({ name, state: structuredClone(state) });
      setViews(list);
      notice('Dynamic view saved on this browser.');
      draw(app, r, api, notice, isCurrent, golferId);
    } catch {
      notice('Browser storage is unavailable.');
    }
  };
  root.querySelector('[data-load-view]').onclick = () => {
    const v = views()[root.querySelector('[data-saved]').value];
    if (!v) {
      notice('Choose a saved view.');
      return;
    }
    state = { ...defaults(), ...v.state };
    save();
    refresh();
  };
  root.querySelector('[data-delete-view]').onclick = () => {
    const i = root.querySelector('[data-saved]').value;
    if (i === '') return;
    try {
      setViews(views().filter((v, j) => '' + j !== i));
      draw(app, r, api, notice, isCurrent, golferId);
    } catch {
      notice('Browser storage is unavailable.');
    }
  };
  function rowsTable(rows) {
    const shown = rows.slice(0, 100);
    const shotRows = shown.map(
      s =>
        html`<tr ${state.highlight === rowKey(s) ? html`class="analysis-highlight"` : ''}><th>${s.session_started.slice(0, 10)} · ${s.key}<small class="range-stat-detail">${s.bag_name} / ${s.club_label}${s.swing_label ? ' / ' + s.swing_label : ''} · config ${s.lineage.configuration_id?.slice(0, 6) ?? 'unknown'}${s.excluded ? ' · excluded' : ''}</small></th>${state.metrics.map(m => html`<td>${fmt(s.values[m])}</td>`)}<td>${s.lineage.report_id?.slice(0, 6) ?? '—'}<small class="range-stat-detail">${f.basis === 'flight' ? (s.lineage.flight_model_version ?? s.lineage.putting_model_version ?? 'No selected output') : 'Source reported'}</small></td><td><a class="btn" href="#sessions/${s.session_id}">Review session</a></td></tr>`
    );
    root.querySelector('[data-shot-workspace]').innerHTML =
      html`<p class="form-hint">${shown.length}/${rows.length} attempts shown; CSV includes every selected attempt. Inspection never changes inclusion.</p><div class="table-wrap"><table><thead><tr><th>Shot / equipment</th>${state.metrics.map(m => html`<th>${label(m)} · ${r.metrics[m].unit}</th>`)}<th>Source / calculation</th><th>Review</th></tr></thead><tbody>${shotRows.length ? shotRows : html`<tr><td>No matching shots.</td></tr>`}</tbody></table></div>`;
  }
  rowsTable(rs);
  observer?.disconnect();
  let renderCharts = () => {};
  const setRange = (metric, bounds) => {
    const next = ranges();
    if (Object.keys(bounds).length) next[metric] = bounds;
    else delete next[metric];
    state.filters.ranges = JSON.stringify(next);
    save();
    refresh();
  };
  if (state.view === 'trends') {
    const t = timeline(rs, state.metrics, state.resolution);
    if (!t.points.some(p => p.id === state.inspect)) state.inspect = '';
    body.innerHTML = html`<div class="analysis-inspection"><label class="field">Inspect shared interval<select data-inspect>${options(
      t.points.map(p => [p.id, p.label]),
      state.inspect,
      'All selected intervals'
    )}</select></label><span class="form-hint">Median and type-7 middle 50% · independent units · n per metric${t.missingTime ? ' · ' + t.missingTime + ' attempts lack capture timestamps' : ''}</span></div>${legend(t.series)}<div class="analysis-trends ${state.grid ? 'analysis-grid' : ''}">${state.metrics.map((m, i) => html`<section class="analysis-panel" data-sort-key="${m}"><div class="analysis-panel-head"><button type="button" class="sort-handle" data-sort-handle aria-label="Drag to reorder ${label(m)}" title="Drag to reorder">⠿</button><h2>${label(m)}</h2><span data-trend-value="${m}" class="form-hint"></span><span class="sort-buttons"><button type="button" class="btn small quiet" data-move="${m}" data-step="-1" ${i ? '' : 'disabled'} aria-label="Move ${label(m)} earlier">Earlier</button><button type="button" class="btn small quiet" data-move="${m}" data-step="1" ${i < state.metrics.length - 1 ? '' : 'disabled'} aria-label="Move ${label(m)} later">Later</button></span></div><svg class="analysis-plot" data-trend="${m}" role="img" aria-label="${label(m)} medians and middle 50 percent by ${state.resolution}"></svg></section>`)}</div>`;
    const inspect = id => {
      state.inspect = id;
      save();
      rowsTable(
        id ? rs.filter(s => t.series.some(c => c.points.find(p => p.id === id)?.rows.includes(s))) : rs
      );
      renderCharts();
    };
    body.querySelector('[data-inspect]').onchange = e => inspect(e.target.value);
    // Tile order (user, 2026-10-17): drag a handle, or use Earlier/Later. The order is state.metrics,
    // so it is kept for this golfer and travels with saved views. The first metric also drives the
    // server query, so a new first metric reloads; otherwise only the page is redrawn.
    const reorder = keys => {
      const first = state.metrics[0];
      state.metrics = keys;
      save();
      if (keys[0] !== first) refresh();
      else draw(app, r, api, notice, isCurrent, golferId);
    };
    makeSortable(body.querySelector('.analysis-trends'), reorder);
    body.querySelectorAll('[data-move]').forEach(
      b =>
        (b.onclick = () => {
          const from = state.metrics.indexOf(b.dataset.move);
          reorder(moveItem(state.metrics, from, from + Number(b.dataset.step)));
        })
    );
    renderCharts = () =>
      body
        .querySelectorAll('[data-trend]')
        .forEach(svg => drawTrend(svg, t, svg.dataset.trend, r, state.inspect));
    body.querySelectorAll('[data-trend]').forEach(
      svg =>
        (svg.onclick = e => {
          const rect = svg.getBoundingClientRect(),
            domain = chartDomain(t.points.map(p => p.time)),
            time =
              domain.min + ((e.clientX - rect.left - 72) / (rect.width - 94)) * (domain.max - domain.min);
          const p = t.points.reduce(
            (a, b) => (!a || Math.abs(b.time - time) < Math.abs(a.time - time) ? b : a),
            null
          );
          if (p) {
            body.querySelector('[data-inspect]').value = p.id;
            inspect(p.id);
          }
        })
    );
    if (state.inspect) inspect(state.inspect);
  } else if (state.view === 'explore') {
    if (!r.metrics[state.x]) state.x = 'launch_ang';
    if (!r.metrics[state.y]) state.y = 'carry';
    if (!r.metrics[state.distribution]) state.distribution = 'absolute_offline';
    const constraint = ranges()[state.distribution] ?? {};
    body.innerHTML = html`<div class="analysis-explore-controls"><label class="field">Horizontal axis<select data-axis="x">${metricOptions(r, state.x)}</select></label><label class="field">Vertical axis<select data-axis="y">${metricOptions(r, state.y)}</select></label><label class="field">Distribution / range metric<select data-distribution>${metricOptions(r, state.distribution)}</select></label><form data-range-form><label class="field">Minimum · ${r.metrics[state.distribution].unit}<input type="number" step="any" data-range-min value="${constraint.min ?? ''}"></label><label class="field">Maximum · ${r.metrics[state.distribution].unit}<input type="number" step="any" data-range-max value="${constraint.max ?? ''}"></label><button class="btn" type="submit">Apply range</button></form></div>${legend(cohorts(rs))}<div class="analysis-explore"><section class="analysis-panel"><h2>${label(state.x)} × ${label(state.y)}</h2><p class="form-hint" data-pairs></p><svg class="analysis-plot" data-scatter role="img" aria-label="${label(state.x)} versus ${label(state.y)}; faint dots are outside numeric selection"></svg><p class="form-hint" data-shot-detail aria-live="polite">Tap a selected dot to inspect; review its session in Shot workspace.</p></section><section class="analysis-panel"><h2>${label(state.distribution)} distribution</h2><p class="form-hint" data-bin-count></p><svg class="analysis-plot" data-hist role="img" aria-label="Distribution; choose a range below to cross-filter all views"></svg><div data-bins class="analysis-bins"></div></section></div>`;
    body.querySelectorAll('[data-axis]').forEach(
      s =>
        (s.onchange = () => {
          state[s.dataset.axis] = s.value;
          save();
          draw(app, r, api, notice, isCurrent, golferId);
        })
    );
    body.querySelector('[data-distribution]').onchange = e => {
      state.distribution = e.target.value;
      save();
      draw(app, r, api, notice, isCurrent, golferId);
    };
    body.querySelector('[data-range-form]').onsubmit = e => {
      e.preventDefault();
      const min = root.querySelector('[data-range-min]').value,
        max = root.querySelector('[data-range-max]').value,
        b = { ...(min !== '' ? { min: Number(min) } : {}), ...(max !== '' ? { max: Number(max) } : {}) };
      if (b.min > b.max) {
        notice('Minimum must not exceed maximum.');
        return;
      }
      setRange(state.distribution, b);
    };
    const candidates = context.filter(s => matchesRanges(s, ranges(), state.distribution)),
      bins = histogram(candidates, state.distribution);
    body.querySelector('[data-bin-count]').textContent =
      `${candidates.filter(s => finite(s.values[state.distribution])).length}/${candidates.length} available before this dimension’s range; other ranges apply. Tap a bin below.`;
    body.querySelector('[data-bins]').innerHTML = bins.length
      ? html`${bins.map(
          (b, i) =>
            html`<button class="btn" data-bin="${i}">${fmt(b.min)}–${fmt(b.max)} ${r.metrics[state.distribution].unit} · n=${b.count}</button>`
        )}`
      : html`<p>No readings for this distribution.</p>`;
    body.querySelectorAll('[data-bin]').forEach(
      b =>
        (b.onclick = () => {
          const bin = bins[Number(b.dataset.bin)];
          setRange(state.distribution, { min: bin.min, max: bin.max });
        })
    );
    renderCharts = () => {
      drawScatter(body.querySelector('[data-scatter]'), context, rs, state.x, state.y, r, state.highlight);
      drawHistogram(body.querySelector('[data-hist]'), bins, state.distribution, r);
    };
    body.querySelector('[data-scatter]').onclick = e => {
      const bounds = e.currentTarget.getBoundingClientRect(),
        point = nearestPoint(
          rs,
          state.x,
          state.y,
          bounds.width,
          bounds.height,
          e.clientX - bounds.left,
          e.clientY - bounds.top,
          context
        );
      if (!point) return;
      state.highlight = rowKey(point);
      save();
      body.querySelector('[data-shot-detail]').textContent =
        `${point.bag_name} / ${point.club_label} · ${label(state.x)} ${fmt(point.values[state.x])} ${r.metrics[state.x].unit} · ${label(state.y)} ${fmt(point.values[state.y])} ${r.metrics[state.y].unit}`;
      rowsTable([point, ...rs.filter(s => rowKey(s) !== rowKey(point))]);
      root.querySelector('[data-shot-panel]').open = true;
      renderCharts();
    };
  } else {
    const days = [...new Set(rs.map(s => s.session_started.slice(0, 10)))].sort(),
      middle = days[Math.max(0, Math.ceil(days.length / 2) - 1)];
    state.compare ??= {
      a: {
        name: 'Baseline',
        date_from: days[0] ?? '',
        date_to: middle ?? '',
        sessions: '',
        configuration: '',
        tags: ''
      },
      b: {
        name: 'Recent',
        date_from: days[Math.ceil(days.length / 2)] ?? '',
        date_to: days.at(-1) ?? '',
        sessions: '',
        configuration: '',
        tags: ''
      }
    };
    body.innerHTML = html`<form data-compare-form><div class="analysis-compare-scopes">${['a', 'b'].map(k => {
      const c = state.compare[k];
      return html`<fieldset><legend>${k === 'a' ? 'Baseline cohort' : 'Comparison cohort'}</legend><label class="field">Cohort name<input name="${k}_name" value="${c.name}" maxlength="60" required></label><label class="field">From date<input type="date" name="${k}_date_from" value="${c.date_from}"></label><label class="field">Through date<input type="date" name="${k}_date_to" value="${c.date_to}"></label><details class="details"><summary>Sessions, configuration and tags</summary><label class="field">Sessions<select name="${k}_sessions" multiple size="4">${options(
        r.options.sessions.map(s => [s.id, s.started.slice(0, 10) + ' · ' + s.drill]),
        null,
        null
      )}</select></label><label class="field">Configuration<select name="${k}_configuration">${options(Object.entries(r.options.configurations ?? {}), c.configuration, 'Use shared scope')}</select></label><label class="field">Tags · any<input name="${k}_tags" value="${c.tags}" placeholder="Use shared scope"></label></details></fieldset>`;
    })}</div><div class="form-foot"><button class="btn primary" type="submit">Compare cohorts</button><button class="btn quiet" type="button" data-reset-periods>Use first / second half</button></div></form><p class="form-hint">Cohorts inherit shared clubs, intent, inclusion and numeric ranges. Empty dates mean no date restriction. These dynamic queries describe differences, not significance or proof of improvement.</p><div data-compare-result role="status">Loading comparison…</div>`;
    const cf = body.querySelector('[data-compare-form]');
    for (const k of ['a', 'b'])
      for (const o of cf.elements[k + '_sessions'].options)
        o.selected = state.compare[k].sessions.split(',').includes(o.value);
    const loadComparison = async () => {
      const current = ++ticket,
        host = body.querySelector('[data-compare-result]');
      host.innerHTML = '<p role="status">Loading comparison…</p>';
      try {
        const reports = await Promise.all(
          ['a', 'b'].map(k => {
            const c = state.compare[k],
              q = {
                ...requestFilters(),
                date_from: c.date_from,
                date_to: c.date_to,
                sessions: c.sessions || f.sessions,
                configuration: c.configuration || f.configuration,
                tags: c.tags || f.tags,
                tag_match: c.tags ? 'any' : f.tag_match
              };
            return api('/api/analysis?' + new URLSearchParams(q));
          })
        );
        if (current !== ticket || !host.isConnected || !isCurrent()) return;
        const [a, b] = reports,
          table = comparison(enriched(a), enriched(b), state.metrics),
          overlap = new Set(a.rows.map(rowKey)),
          common = b.rows.filter(s => overlap.has(rowKey(s))).length;
        const rows = table.flatMap(c =>
          c.metrics.map(
            m =>
              html`<tr><th><svg width="14" height="12" aria-hidden="true"><circle cx="5" cy="6" r="4" fill="${c.color}"/></svg>${c.label}<small class="range-stat-detail">${label(m.metric)} · ${r.metrics[m.metric].unit}</small></th><td>${fmt(m.before.median)} / ${fmt(m.before.iqr)} · n=${m.before.count}</td><td>${fmt(m.after.median)} / ${fmt(m.after.iqr)} · n=${m.after.count}</td><td>${m.delta > 0 ? '+' : ''}${fmt(m.delta)} ${r.metrics[m.metric].unit}</td></tr>`
          )
        );
        host.innerHTML = html`<div class="analysis-comparison-counts"><strong>${state.compare.a.name} · ${a.count} attempts</strong><strong>${state.compare.b.name} · ${b.count} attempts</strong><span>${common} attempts overlap between cohorts</span></div><div class="form-foot">${[a, b].map((report, i) => html`<a class="btn" href="/api/analysis?${new URLSearchParams({ ...report.filters, format: 'csv' }).toString()}" download>Export ${state.compare[i ? 'b' : 'a'].name} CSV</a>`)}</div><div class="table-wrap"><table><thead><tr><th>Equipment / metric</th><th>${state.compare.a.name} median / IQR · n</th><th>${state.compare.b.name} median / IQR · n</th><th>Median change</th></tr></thead><tbody>${rows.length ? rows : html`<tr><td>No matching readings. Change cohort dates or shared filters.</td></tr>`}</tbody></table></div><p class="form-hint">Same configurations/intents share a row; changed equipment uses separate rows. Missing counterparts stay unavailable.</p>`;
      } catch (e) {
        if (current === ticket && host.isConnected)
          host.innerHTML = html`<p role="alert">Comparison unavailable: ${e.message}</p>`;
      }
    };
    cf.onsubmit = e => {
      e.preventDefault();
      const d = new FormData(cf);
      for (const k of ['a', 'b'])
        state.compare[k] = {
          name: d.get(k + '_name'),
          date_from: d.get(k + '_date_from'),
          date_to: d.get(k + '_date_to'),
          sessions: d.getAll(k + '_sessions').join(','),
          configuration: d.get(k + '_configuration'),
          tags: d.get(k + '_tags')
        };
      save();
      loadComparison();
    };
    body.querySelector('[data-reset-periods]').onclick = () => {
      state.compare = null;
      save();
      draw(app, r, api, notice, isCurrent, golferId);
    };
    loadComparison();
  }
  const viewControls = body.querySelector('.analysis-explore-controls, [data-compare-form]');
  if (viewControls) {
    viewControls.classList.add('section-space');
    root.querySelector('.analysis-selection').append(viewControls);
  }
  if (state.view === 'explore')
    root
      .querySelector('.analysis-selection summary')
      .insertAdjacentHTML(
        'beforeend',
        html`<span class="analysis-scope">${label(state.x)} × ${label(state.y)} · Distribution: ${label(state.distribution)}</span>`
      );
  if (state.view === 'compare') {
    const note = body.querySelector(':scope > .form-hint');
    if (note) viewControls.append(note);
    const line = document.createElement('span');
    line.className = 'analysis-scope';
    line.dataset.cohortSummary = '';
    root.querySelector('.analysis-selection summary').append(line);
    const summary = () => {
      line.textContent = ['a', 'b']
        .map(k => {
          const c = state.compare[k];
          return `${c.name}: ${c.date_from || 'First'} → ${c.date_to || 'Latest'}${c.sessions ? ' · ' + c.sessions.split(',').length + ' sessions' : ''}${c.configuration ? ' · config ' + c.configuration.slice(0, 6) : ''}${c.tags ? ' · tags ' + c.tags : ''}`;
        })
        .join(' / ');
    };
    summary();
    viewControls.addEventListener('submit', summary);
  }
  const method = document.createElement('details');
  method.className = 'details section-space';
  method.innerHTML = html`<summary>Counting, dates and analytical methods</summary><p class="form-hint">${r.counting} Date filters use recorded session start dates. Week/month groups aggregate underlying readings using those dates; weeks start Monday. Shot plots use capture time in UTC. Inspection highlights an interval/shot; CSV retains the applied query. ${r.method}</p>`;
  root.append(method);
  observer = new ResizeObserver(() => {
    if (!root.isConnected) {
      observer.disconnect();
      return;
    }
    renderCharts();
  });
  body.querySelectorAll('svg.analysis-plot').forEach(svg => observer.observe(svg));
  renderCharts();
  mountCalculations(app, requestFilters(), api, notice, isCurrent, refresh);
}
function clubPicks(r, bag, selected) {
  const picks = Object.entries(r.options.clubs)
    .filter(([, c]) => !bag || c.bag === bag)
    .map(
      ([id, c]) =>
        html`<label class="collection-option"><input type="checkbox" name="clubs" value="${id}" ${selected.includes(id) ? 'checked' : ''}>${r.options.bags[c.bag] ?? 'No bag'} / ${c.label}</label>`
    );
  return picks.length ? html`${picks}` : html`<span class="form-hint">No tagged clubs in this scope.</span>`;
}
// Dashed stroke for every series after the first, so colors are not the only distinction.
const dash = i => (i ? html`stroke-dasharray="${3 + i * 2} 3"` : '');
function legend(series) {
  const items = series.map(
    (c, i) =>
      html`<span><svg width="24" height="12" aria-hidden="true"><line x1="0" x2="24" y1="6" y2="6" stroke="${c.color}" stroke-width="2" ${dash(i)}/><circle cx="12" cy="6" r="3" fill="${c.color}"/></svg>${c.label}</span>`
  );
  return html`<div class="analysis-legend">${items.length ? items : html`<span>No matching shots. Expand Selections & filters to change scope.</span>`}</div>`;
}
function chartDomain(values) {
  const valid = values.filter(finite);
  if (!valid.length) return { min: 0, max: 1 };
  const min = valid.reduce((a, b) => Math.min(a, b), Infinity),
    max = valid.reduce((a, b) => Math.max(a, b), -Infinity),
    pad = Math.max((max - min) * 0.08, max === min ? Math.max(Math.abs(min) * 0.05, 1) : 0.000001);
  return { min: min - pad, max: max + pad };
}
function geometry(svg, xValues, yValues) {
  const W = Math.max(260, svg.getBoundingClientRect().width),
    H = 260,
    L = 72,
    R = 22,
    T = 24,
    B = 56,
    xd = chartDomain(xValues),
    yd = chartDomain(yValues);
  return {
    W,
    H,
    L,
    R,
    T,
    B,
    xd,
    yd,
    x: v => L + ((W - L - R) * (v - xd.min)) / (xd.max - xd.min),
    y: v => T + ((H - T - B) * (yd.max - v)) / (yd.max - yd.min)
  };
}
function frame(g, xLabel, yLabel, time = false) {
  const { W, H, L, R, T, B, xd, yd, x, y } = g,
    ticks = W < 550 ? 3 : 6;
  return html`${Array.from({ length: 4 }, (_, i) => {
    const v = yLabel === 'Attempts · n' ? Math.round((yd.max * i) / 3) : yd.min + ((yd.max - yd.min) * i) / 3;
    return html`<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="range-gridline"/><text x="${L - 10}" y="${y(v) + 4}" text-anchor="end">${yLabel === 'Attempts · n' ? v : fmt(v)}</text>`;
  })}${Array.from({ length: ticks }, (_, i) => {
    const v = xd.min + ((xd.max - xd.min) * i) / (ticks - 1);
    return html`<text x="${x(v)}" y="${H - B + 22}" text-anchor="${i === 0 ? 'start' : i === ticks - 1 ? 'end' : 'middle'}">${time ? new Date(v).toISOString().slice(5, 10) : fmt(v)}</text>`;
  })}<text x="${W / 2}" y="${H - 8}" text-anchor="middle">${xLabel}</text><text x="8" y="14">${yLabel}</text>`;
}
// `markup` is html`` output.
function finish(svg, g, markup) {
  svg.setAttribute('viewBox', `0 0 ${g.W} ${g.H}`);
  svg.innerHTML = markup;
}
function drawTrend(svg, t, m, r, inspect) {
  const valid = t.series
      .flatMap(c => c.points.flatMap(p => [p.metrics[m].q1, p.metrics[m].median, p.metrics[m].q3]))
      .filter(finite),
    g = geometry(
      svg,
      t.points.map(p => p.time),
      valid
    );
  svg.parentElement.querySelector('[data-trend-value]').textContent = t.series
    .map(c => {
      const s = inspect
        ? c.points.find(p => p.id === inspect)?.metrics[m]
        : robust(c.rows.map(s => s.values[m]));
      return `${c.rows[0]?.club_label ?? ''}: ${fmt(s?.median)} ${r.metrics[m].unit} · n=${s?.count ?? 0}`;
    })
    .join(' / ');
  if (!valid.length) {
    finish(svg, g, html`<text x="20" y="90">No available ${r.metrics[m].label} readings.</text>`);
    return;
  }
  const marks = [];
  t.series.forEach((c, index) => {
    let path = '',
      segment = [];
    const flush = () => {
      if (segment.length) {
        marks.push(
          html`<polygon points="${segment
            .map(p => `${g.x(p.time)},${g.y(p.metrics[m].q1 ?? p.metrics[m].median)}`)
            .concat(
              [...segment].reverse().map(p => `${g.x(p.time)},${g.y(p.metrics[m].q3 ?? p.metrics[m].median)}`)
            )
            .join(' ')}" fill="${c.color}" fill-opacity=".08"/>`
        );
        segment = [];
      }
    };
    for (let i = 0; i < c.points.length; i++) {
      const p = c.points[i],
        s = p.metrics[m];
      if (!finite(s.median)) {
        flush();
        continue;
      }
      const prior = c.points[i - 1];
      path += `${!prior || !finite(prior.metrics[m].median) ? 'M' : 'L'}${g.x(p.time)},${g.y(s.median)} `;
      segment.push(p);
      marks.push(
        html`<circle cx="${g.x(p.time)}" cy="${g.y(s.median)}" r="${p.id === inspect ? 5 : 3}" fill="${c.color}"><title>${c.label} · ${p.label} · median ${fmt(s.median)} · IQR ${fmt(s.iqr)} · n=${s.count}</title></circle>`
      );
    }
    flush();
    marks.push(html`<path d="${path}" fill="none" stroke="${c.color}" stroke-width="2" ${dash(index)}/>`);
  });
  const focused = t.points.find(p => p.id === inspect);
  const axis =
    state.resolution === 'shot'
      ? 'Capture date · UTC'
      : state.resolution === 'session'
        ? 'Session date'
        : state.resolution === 'week'
          ? 'Week starting Monday'
          : 'Month starting';
  const focusLine = focused
    ? html`<line x1="${g.x(focused.time)}" x2="${g.x(focused.time)}" y1="${g.T}" y2="${g.H - g.B}" stroke="var(--muted)" stroke-dasharray="3 4"/>`
    : '';
  finish(svg, g, html`${frame(g, axis, r.metrics[m].unit, true)}${marks}${focusLine}`);
}
function drawScatter(svg, context, selected, xm, ym, r, highlight) {
  const pairs = context.filter(s => finite(s.values[xm]) && finite(s.values[ym])),
    chosen = new Set(selected.map(rowKey)),
    plot = pairs.slice(-1500),
    g = geometry(
      svg,
      pairs.map(s => s.values[xm]),
      pairs.map(s => s.values[ym])
    ),
    colors = new Map(cohorts(context).map(c => [c.id, c.color]));
  svg.parentElement.querySelector('[data-pairs]').textContent =
    `${selected.filter(s => finite(s.values[xm]) && finite(s.values[ym])).length}/${selected.length} selected pairs available · ${plot.length}/${pairs.length} context pairs drawn (up to 1,500)`;
  const dots = plot.map(
    s =>
      html`<circle cx="${g.x(s.values[xm])}" cy="${g.y(s.values[ym])}" r="${rowKey(s) === highlight ? 7 : 4}" fill="${colors.get(cohortKey(s))}" fill-opacity="${chosen.has(rowKey(s)) ? 0.8 : 0.12}" stroke="${rowKey(s) === highlight ? 'var(--ink)' : 'none'}"><title>${s.bag_name + ' / ' + s.club_label} · ${fmt(s.values[xm])} / ${fmt(s.values[ym])}</title></circle>`
  );
  finish(
    svg,
    g,
    html`${frame(g, r.metrics[xm].label + ' · ' + r.metrics[xm].unit, r.metrics[ym].unit)}${dots}`
  );
}
function nearestPoint(rows, xm, ym, W, H, px, py, context) {
  const pairs = context.filter(s => finite(s.values[xm]) && finite(s.values[ym])),
    xd = chartDomain(pairs.map(s => s.values[xm])),
    yd = chartDomain(pairs.map(s => s.values[ym]));
  let result = null,
    best = 25;
  for (const r of rows) {
    if (!finite(r.values[xm]) || !finite(r.values[ym])) continue;
    const x = 72 + ((W - 94) * (r.values[xm] - xd.min)) / (xd.max - xd.min),
      y = 24 + ((H - 80) * (yd.max - r.values[ym])) / (yd.max - yd.min),
      d = Math.hypot(px - x, py - y);
    if (d < best) {
      best = d;
      result = r;
    }
  }
  return result;
}
function drawHistogram(svg, bins, m, r) {
  const g = geometry(
    svg,
    bins.flatMap(b => [b.min, b.max]),
    [0, ...bins.map(b => b.count)]
  );
  g.yd.min = 0;
  g.yd.max = Math.max(3, Math.ceil(g.yd.max / 3) * 3);
  const bars = bins.map(
    b =>
      html`<rect x="${g.x(b.min)}" y="${g.y(b.count)}" width="${Math.max(0, g.x(b.max) - g.x(b.min) - 2)}" height="${Math.max(0, g.y(0) - g.y(b.count))}" fill="var(--accent)" fill-opacity=".65"><title>${fmt(b.min)}–${fmt(b.max)} · n=${b.count}</title></rect>`
  );
  finish(svg, g, html`${frame(g, r.metrics[m].label + ' · ' + r.metrics[m].unit, 'Attempts · n')}${bars}`);
}
