import {
  resetShotMotion,
  shotMotion,
  observeShotMotion,
  motionControls,
  mountShotMotion,
  motionChart,
  chartProjection
} from './shot-motion.js';
import { preserveInteraction } from './interaction-state.js';
import { decorateCollection } from './collection.js';
import { html } from './charts.js';
import { equipmentControls, bindEquipment } from './equipment.js';
import { tagDialog } from './golfers.js';
import { recordingWarnings } from './recording.js';
import {
  equipment,
  valid,
  included,
  format as n,
  cohort,
  point,
  summarize,
  rangeCsv,
  clubKey,
  clubColors,
  CLUB_METRICS,
  clubSummaries,
  rangeValue,
  RANGE_FIELDS,
  estimated,
  clubReadings,
  clubEstimates,
  hasClubData,
  scatterCohort,
  dispersionCircles
} from './range-data.js';

const views = new Map();
let scatterResize = null;
const btn = (text, action, kind = 'quiet') =>
  html`<button type="button" class="btn ${kind}" data-action="${action}">${text}</button>`;
// `disabled` toggles the disabled attribute.
const local = (text, action, kind = 'quiet', disabled = false) =>
  html`<button type="button" class="btn ${kind}" data-range-action="${action}" ${disabled ? html`disabled` : ''}>${text}</button>`;
const field = (name, label, value, min, max) =>
  html`<label class="field">${label}<input name="${name}" type="number" min="${min}" max="${max}" step="1" value="${n(value)}" required></label>`;
const select = (id, label, options, value) =>
  html`<label class="field">${label}<select data-range-filter="${id}">${options.map(([v, t]) => html`<option value="${v}" ${v === value ? 'selected' : ''}>${t}</option>`)}</select></label>`;

export function renderRangeSetup(app, old, launch, notice, eq) {
  app.innerHTML = html`<div class="page-head"><div><div class="eyebrow">FULL SWING / FREE PRACTICE</div><h1>Driving range</h1><p class="subtitle">Find your pattern. Build your confidence.</p></div>${btn('← Back to Practice', 'home')}</div>
  <form id="range-form"><div class="range-intro-grid"><section class="card"><h2>Your session</h2><p class="subtitle">Hit as many shots as you like. End the session when you’re ready.</p><div class="form-grid">${field('range_target', 'Target distance · yd (0 = free practice)', old.range_target ?? 150, 0, 450)}${field('range_depth', 'Distance window · yd (full depth)', old.range_depth ?? 20, 1, 200)}${field('range_width', 'Target width · yd', old.range_width ?? 30, 1, 200)}<label class="field">Player handedness<select name="handedness"><option value="right_handed" ${old.handedness !== 'left_handed' ? 'selected' : ''}>Right-handed</option><option value="left_handed" ${old.handedness === 'left_handed' ? 'selected' : ''}>Left-handed</option></select></label></div><p class="form-hint">Target width is a visual guide. Distance-window results use OpenGolfCoach-estimated carry, so every source is scored the same way; reported distances remain stored separately.</p></section>
  <section class="card range-intro"><div class="eyebrow">YOUR PRACTICE WORKSPACE</div><h2>Every shot tells a story.</h2><p>See carry and total dispersion, explore estimated flight shape, and clean up a forgotten club change without losing your original shots.</p><div class="range-intro-features"><span>◎ Shot dispersion</span><span>↗ Flight estimates</span><span>☷ Bulk shot review</span></div><p class="model-note">OpenGolfCoach estimates are independent of Foresight. Source measurements and modeled results remain clearly identified.</p></section></div>
  <section class="card section-space">${equipmentControls(eq.catalog(), old.equipment_selection, true)}</section><div class="range-launch-actions"><button class="btn primary" type="submit" name="mode" value="live">Launch range →</button><button class="btn" type="submit" name="mode" value="demo">Launch demo range</button><span class="form-hint">Demo sessions use labeled synthetic data and do not accept live shots.</span></div></form>`;
  bindEquipment(app, eq, null);
  app.querySelector('form').onsubmit = async e => {
    e.preventDefault();
    const f = new FormData(e.target);
    const params = Object.fromEntries(f);
    for (const k of ['range_target', 'range_width', 'range_depth']) params[k] = Number(params[k]);
    const demo = e.submitter?.value === 'demo';
    e.target.querySelectorAll('button').forEach(b => (b.disabled = true));
    try {
      await launch({ drill: 'Driving range', ...params, demo });
    } catch (error) {
      notice(error.message);
      e.target.querySelectorAll('button').forEach(b => (b.disabled = false));
    }
  };
}

function scatter(shots, v, target, width, depth, colors, size = null) {
  const pairs = shots.map(s => ({ s, p: point(s, v.metric, v.source) })).filter(x => x.p);
  const circles = dispersionCircles(shots, v.metric, v.source),
    rings = [...circles].filter(([, c]) => c.radius !== null);
  const groups = new Map();
  pairs.forEach(({ s }) => {
    const e = equipment(s),
      key = clubKey(e);
    if (!groups.has(key))
      groups.set(key, {
        label: e.club_id ? `${e.bag_name || 'No bag'} / ${e.club_label || 'Unnamed club'}` : 'Untagged'
      });
  });
  const legend = html`<ul class="range-club-legend" aria-label="Plotted shots by club">${[...groups].map(([key, g]) => html`<li><svg class="range-club-swatch" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="${colors.get(key)}"/></svg><span>${g.label}</span></li>`)}</ul>`;
  const far =
    Math.ceil(
      Math.max(
        100,
        target + 40,
        ...pairs.map(x => x.p.forward + 20),
        ...rings.map(([, c]) => c.forward + c.radius + 10)
      ) / 25
    ) * 25;
  const near =
    Math.floor(
      Math.min(0, ...pairs.map(x => x.p.forward), ...rings.map(([, c]) => c.forward - c.radius)) / 25
    ) * 25;
  const side =
    Math.ceil(
      Math.max(
        30,
        width,
        ...pairs.map(x => Math.abs(x.p.right) + 8),
        ...rings.map(([, c]) => Math.abs(c.right) + c.radius + 5)
      ) / 10
    ) * 10;
  const compact = window.matchMedia('(max-width:600px)').matches;
  const W = compact ? 500 : 740,
    H = size ? (W * size.height) / size.width : compact ? 440 : 500,
    L = compact ? 85 : 62,
    R = 25,
    T = 25,
    B = compact ? 62 : 52,
    pw = W - L - R,
    ph = H - T - B;
  const x = r => L + ((r + side) / (side * 2)) * pw,
    y = f => H - B - ((f - near) / (far - near)) * ph;
  const marks = [];
  for (let i = 0; i <= 5; i++) {
    const d = near + ((far - near) * i) / 5;
    marks.push(
      html`<line x1="${L}" y1="${y(d)}" x2="${W - R}" y2="${y(d)}" class="range-gridline"/><text x="${L - 10}" y="${y(d) + 4}" text-anchor="end">${Math.round(d)}</text>`
    );
  }
  for (const d of [-side, -side / 2, 0, side / 2, side])
    marks.push(
      html`<text x="${x(d)}" y="${H - B + 25}" text-anchor="middle">${Math.round(Math.abs(d))}${d < 0 ? 'L' : d > 0 ? 'R' : ''}</text>`
    );
  const targetMark =
    target > 0
      ? html`<rect x="${x(-width / 2)}" y="${y(target + depth / 2)}" width="${(width / (side * 2)) * pw}" height="${(depth / (far - near)) * ph}" class="range-target-zone"/><line x1="${x(0) - 13}" x2="${x(0) + 13}" y1="${y(target)}" y2="${y(target)}" class="range-target-line"/>`
      : '';
  const overlays = rings.map(
    ([key, c]) =>
      html`<g class="range-dispersion-circle" role="img" aria-label="${groups.get(key).label}: 80% dispersion radius ${n(c.radius)} yards, ${c.count} included shots"><ellipse cx="${x(c.right)}" cy="${y(c.forward)}" rx="${(c.radius / (side * 2)) * pw}" ry="${(c.radius / (far - near)) * ph}" fill="${colors.get(key)}" fill-opacity=".07" stroke="${colors.get(key)}" stroke-width="2"/><path d="M${x(c.right) - 4},${y(c.forward)}h8 M${x(c.right)},${y(c.forward) - 4}v8" stroke="${colors.get(key)}" stroke-width="1.5"/></g>`
  );
  const points = pairs.map(({ s, p }) => {
    const radius = s.key === v.focus ? 8 : 5,
      state = s.removed ? 'Removed' : s.excluded ? 'Excluded' : 'Included';
    return html`<g class="range-point ${s.removed ? 'muted' : ''} ${s.excluded ? 'analysis-excluded' : ''} ${s.key === v.focus ? 'focused' : ''}" data-inspect-shot="${s.key}" tabindex="0" role="button" aria-label="Inspect shot ${s.ordinal}, ${equipment(s).bag_name || 'No bag'}, ${equipment(s).club_label || 'Untagged'}, ${n(p.forward)} yards, ${n(p.right)} offline, ${state}"><circle cx="${x(p.right)}" cy="${y(p.forward)}" r="14" fill="transparent"/><circle cx="${x(p.right)}" cy="${y(p.forward)}" r="${radius}" fill="${colors.get(clubKey(equipment(s)))}"/>${s.excluded ? html`<circle cx="${x(p.right)}" cy="${y(p.forward)}" r="${radius}" fill="white" fill-opacity=".6"/>` : ''}<circle class="range-shot-dot" cx="${x(p.right)}" cy="${y(p.forward)}" r="${radius}" fill="none"/><title>Shot ${s.ordinal} · ${equipment(s).club_label || 'Untagged'} · ${state} · ${n(p.forward)} yd / ${n(p.right)} yd</title></g>`;
  });
  return {
    svg: html`<svg viewBox="0 0 ${W} ${H}" class="range-scatter" aria-label="${v.source === 'model' ? 'Estimated' : 'Reported'} ${v.metric} dispersion in yards" role="group">${marks}${targetMark}<line x1="${x(0)}" y1="${T}" x2="${x(0)}" y2="${H - B}" class="range-centerline"/>${overlays}${points}<text x="${W / 2}" y="${H - 5}" text-anchor="middle">${v.source === 'model' ? 'Estimated lateral position' : 'Reported offline'} · yd</text><text transform="translate(17 ${H / 2}) rotate(-90)" text-anchor="middle">${v.source === 'model' ? 'Downrange' : v.metric === 'carry' ? 'Carry' : 'Total'} · yd</text>${pairs.length ? '' : html`<text x="${W / 2}" y="${H / 2}" text-anchor="middle">No plottable shots in this view</text>`}</svg>`,
    legend
  };
}

function dispersionHelp(v) {
  return html`<div class="range-dispersion-title"><h2>Shot dispersion</h2><div class="range-info"><button type="button" class="range-info-button" aria-label="About shot dispersion" aria-expanded="${!!v.infoOpen}" aria-controls="dispersion-help"><span aria-hidden="true">i</span></button><div class="range-info-panel" id="dispersion-help" tabindex="0" role="region" aria-label="About shot dispersion" ${v.infoOpen ? '' : 'hidden'}>
  <strong>Reading the dispersion chart</strong>
  <p>Each color is a bag/club combination. The chart follows Carry/Total, the selected source and workspace filters. Missing coordinates cannot be plotted.</p>
  <p>Circles cover at least 80% of included positions around the median center (+). They need five usable shots per club. Excluded and removed shots never affect them; untagged shots have no circle.</p>
  <p>Lighter dots are excluded; faded dots are removed. A dark outline marks the selected shot. The default chart retains excluded dots while the table shows included shots.</p>
  <p>Circles use the nearest-rank 80th-percentile radius. They describe this sample, not a confidence interval or future-shot probability. Separately scaled axes make them appear oval.</p>
  <p>${v.source === 'model' ? 'OpenGolfCoach positions are estimates, independent of source-reported outcomes.' : 'Reported offline has an unverified endpoint definition; this is not a verified landing map.'}</p>
  </div></div></div>`;
}

function bindDispersionHelp(app, v) {
  const host = app.querySelector('.range-info'),
    button = host.querySelector('button'),
    panel = host.querySelector('.range-info-panel');
  const show = open => {
    v.infoOpen = open;
    panel.hidden = !open;
    button.setAttribute('aria-expanded', String(open));
  };
  const close = () => {
    v.infoPinned = false;
    show(false);
  };
  host.onpointerenter = e => {
    if (e.pointerType === 'mouse') show(true);
  };
  host.onpointerleave = e => {
    if (e.pointerType === 'mouse' && !v.infoPinned) show(false);
  };
  button.onfocus = () => show(true);
  host.onfocusout = e => {
    if (!host.contains(e.relatedTarget)) close();
  };
  button.onclick = () => {
    v.infoPinned = !v.infoPinned;
    show(v.infoPinned);
  };
  app.onpointerdown = e => {
    if (!host.contains(e.target)) close();
  };
  app.onkeydown = e => {
    if (e.key === 'Escape' && v.infoOpen) {
      close();
      e.preventDefault();
    }
  };
}

function cleanupDialog(data, keys, action, catalog, apply, notice) {
  const shots = data.shots.filter(s => keys.includes(s.key));
  const dialog = document.createElement('dialog');
  dialog.className = 'confirm-dialog range-cleanup';
  dialog.id = 'range-cleanup';
  dialog.setAttribute('aria-labelledby', 'cleanup-title');
  const beforeCount = shots.filter(included).length;
  const afterCount = shots.filter(s =>
    included({
      ...s,
      ...({
        exclude: { excluded: true },
        include: { excluded: false },
        remove: { removed: true },
        restore: { removed: false }
      }[action] ?? {})
    })
  ).length;
  const originalGroups = [
    ...new Set(
      shots.map(s => {
        const e = equipment(s);
        return `${e.bag_name || 'No bag'} / ${e.club_label || 'Untagged'}`;
      })
    )
  ];
  dialog.innerHTML = html`<h2 id="cleanup-title">${action === 'retag' ? 'Retag' : action[0].toUpperCase() + action.slice(1)} ${keys.length} shot${keys.length === 1 ? '' : 's'}?</h2><p>Only these ${keys.length} selected shots in this session will change. New arrivals are not included.</p><div class="cleanup-preview"><strong>Current assignment</strong><p>${originalGroups.join(' · ')}</p><strong>${action === 'retag' ? 'New assignment below' : action === 'remove' ? 'Move to Removed; omit from plots and analysis' : action === 'restore' ? 'Restore to shot workspace; retain any prior exclusion' : action === 'exclude' ? 'Exclude from session statistics; retain the shot' : 'Include in session statistics (removed shots still require Restore)'}</strong><p>Selected shots included in analysis: ${beforeCount} → ${afterCount}.</p><p>Original measurements and capture tags remain preserved. Undo is available.</p></div><form id="cleanup-form">${action === 'retag' ? html`<div class="form-grid"><label class="field">Correction bag<select name="bag">${catalog.bags.map(b => html`<option value="${b.id}">${b.name}</option>`)}</select></label><label class="field">Correction club<select name="club"></select></label></div><p class="form-hint">This records a correction to the selected catalog club; the original capture assignment stays in history.</p>` : ''}<label class="field">Reason<input name="reason" maxlength="240" placeholder="e.g. Forgot to switch from PW to 9 iron" required></label><p class="session-error" role="alert" hidden></p><div class="confirm-actions"><button class="btn quiet" type="button" data-cancel>Cancel</button><button class="btn ${action === 'remove' ? 'danger' : 'primary'}" type="submit">Apply to ${keys.length} shots</button></div></form>`;
  document.body.append(dialog);
  dialog.showModal();
  const form = dialog.querySelector('form');
  if (action === 'retag') {
    const clubs = () => {
      const b = catalog.bags.find(b => b.id === form.elements.bag.value);
      form.elements.club.innerHTML = html`<option value="">Untagged</option>${b.clubs.map(c => html`<option value="${c.id}">${c.label}</option>`)}`;
    };
    form.elements.bag.onchange = clubs;
    clubs();
  }
  dialog.querySelector('[data-cancel]').onclick = () => dialog.close();
  dialog.onclose = () => dialog.remove();
  form.onsubmit = async e => {
    e.preventDefault();
    const submit = form.querySelector('[type=submit]');
    submit.disabled = true;
    try {
      await apply({
        action,
        keys,
        revision: data.cleanup_revision,
        reason: form.elements.reason.value,
        ...(action === 'retag' ? { bag_id: form.elements.bag.value, club_id: form.elements.club.value } : {})
      });
      dialog.close();
      notice(`${keys.length} shots updated. Original data is preserved.`);
    } catch (error) {
      const p = form.querySelector('[role=alert]');
      p.hidden = false;
      p.textContent = error.message;
      submit.disabled = false;
    }
  };
}

export function disposeRange() {
  scatterResize?.disconnect();
  scatterResize = null;
}

export function renderRange(app, data, state, isReview, sessionNotice, context) {
  disposeRange();
  if (!views.has(data.id))
    views.set(data.id, {
      metric: 'carry',
      source: 'model',
      bag: '',
      club: '',
      shape: '',
      status: 'included',
      search: '',
      sort: 'latest',
      selected: new Set(),
      focus: null,
      follow: true,
      flightView: 'side'
    });
  const v = views.get(data.id),
    active = !isReview && !data.ended,
    shots = data.shots.map((s, i) => ({ ...s, ordinal: i + 1 }));
  const shown = (v.follow ? null : shots.find(s => s.key === v.focus)) ?? shots.at(-1);
  v.focus = shown?.key ?? null;
  const motion = shotMotion(shown);
  observeShotMotion('range:' + data.id, shown, motion, active && v.follow);
  let matched = cohort(shots, v);
  matched.sort((a, b) =>
    v.sort === 'latest'
      ? b.ordinal - a.ordinal
      : v.sort === 'oldest'
        ? a.ordinal - b.ordinal
        : (rangeValue(a, v.metric) ?? Infinity) - (rangeValue(b, v.metric) ?? Infinity)
  );
  // D63: distances are OpenGolfCoach estimates for shots recorded since 2026-10-12.
  const modeledDistances = shots.some(estimated),
    distanceBasis = data.demo ? 'synthetic' : modeledDistances ? 'OpenGolfCoach-estimated' : 'reported',
    est = s => (estimated(s) ? ' · est.' : '');
  const analytical = matched.filter(included),
    summary = summarize(analytical, v.metric),
    all = summarize(
      cohort(shots, { ...v, status: 'all' }).map(s => ({ ...s, excluded: false, removed: false })),
      v.metric
    );
  const shapes = new Map();
  analytical.forEach(s => {
    const name = s.flight?.shape ?? 'Unavailable';
    shapes.set(name, (shapes.get(name) ?? 0) + 1);
  });
  const eq = shown ? equipment(shown) : {},
    last = shots.at(-1),
    flight = shown?.flight,
    fm = flight?.metrics ?? {};
  const bagOptions = [
    ...new Map(
      shots.map(s => {
        const e = equipment(s);
        return [e.bag_id || '', e.bag_name || 'No bag'];
      })
    ).entries()
  ].filter(([id]) => id);
  const clubOptions = [
    ...new Map(
      shots
        .filter(s => !v.bag || equipment(s).bag_id === v.bag)
        .map(s => {
          const e = equipment(s);
          return [e.club_id || '', `${e.club_label || 'Untagged'} · ${e.bag_name || 'No bag'}`];
        })
    ).entries()
  ].filter(([id]) => id);
  const undo = [...data.cleanup_history].reverse().find(b => b.action !== 'undo' && !b.undone);
  const redraw = () =>
    preserveInteraction(app, () => renderRange(app, data, state, isReview, sessionNotice, context));
  const plotShots = scatterCohort(shots, v),
    colors = clubColors(shots);
  const drawScatter = size =>
    scatter(plotShots, v, data.range_target, data.range_width, data.range_depth, colors, size);
  const chart = drawScatter();
  const metricTiles = [
    ['Carry', 'carry', 'yd'],
    ['Total', 'total', 'yd'],
    ['Offline', 'offline', 'yd'],
    ['Ball speed', 'ball_speed', 'mph'],
    ['Total spin', 'total_spin', 'rpm', 0],
    ['Launch angle', 'launch_ang', '°'],
    ['Descent angle', 'descent_ang', '°']
  ].map(
    ([label, key, unit, precision = 1]) =>
      html`<div><span>${label}${RANGE_FIELDS.includes(key) ? est(shown) : ''}</span><strong>${n(rangeValue(shown, key), precision)}<small>${unit}</small></strong></div>`
  );
  // Club delivery row: only in sessions whose source reports club data (iPad club table, Premier memory).
  const clubTiles = hasClubData(shots)
    ? html`<h3 class="range-club-heading">Club delivery</h3><div class="range-metrics range-club-metrics">${[
        ...clubReadings(shown, data.handedness),
        ...clubEstimates(shown, data.handedness)
      ].map(
        r =>
          html`<div><span>${r.label}</span><strong>${n(r.value, r.precision)}<small>${r.unit}</small></strong></div>`
      )}</div>`
    : '';
  const flightTiles = [
    ['Carry', fm.carry_yd, 'yd'],
    ['Total', fm.total_yd, 'yd'],
    ['Apex', fm.apex_ft, 'ft'],
    ['Descent', fm.descent_deg, '°'],
    ['Hang time', fm.hang_time_s, 's'],
    ['Spin axis', shown?.vals.spin_axis, '°']
  ].map(
    ([label, val, unit]) =>
      html`<div><strong>${n(val)} ${unit}</strong><span>${label}${label === 'Spin axis' ? ' · input' : ''}</span></div>`
  );
  const shapeBars = shapes.size
    ? [...shapes]
        .sort((a, b) => b[1] - a[1])
        .map(
          ([shape, count]) =>
            html`<div><span>${shape}</span><meter min="0" max="${Math.max(1, analytical.length)}" value="${count}">${count}</meter><strong>${count}</strong></div>`
        )
    : html`<p class="empty">Your shot patterns will appear here.</p>`;
  const shotRows = matched.length
    ? matched.map(s => {
        const e = equipment(s);
        return html`<tr class="${s.key === v.focus ? 'selected' : ''} ${included(s) ? '' : 'excluded'}"><td><input type="checkbox" data-select-shot="${s.key}" aria-label="Select shot ${s.ordinal}" ${v.selected.has(s.key) ? 'checked' : ''}></td><td><button class="btn quiet small" data-inspect-shot="${s.key}" aria-label="Inspect shot ${s.ordinal}">#${s.ordinal}</button></td><td><strong>${e.club_label || 'Untagged'}</strong><small>${e.bag_name || 'No bag'}${s.corrected_equipment ? ' · corrected' : ''}${data.collection_kind === 'wedge' ? ` · ${s.swing_label ?? 'Swing unavailable'}` : ''}</small></td><td>${n(rangeValue(s, 'carry'))}</td><td>${n(rangeValue(s, 'total'))}</td><td>${n(rangeValue(s, 'offline'))}</td><td>${n(s.vals.ball_speed)}</td><td>${n(s.vals.launch_ang)}</td><td>${n(s.vals.total_spin, 0)}</td><td>${s.flight?.shape ?? 'Unavailable'}</td><td>${s.removed ? 'Removed' : s.excluded ? 'Excluded' : 'Included'}</td></tr>`;
      })
    : html`<tr><td colspan="11" class="empty">No shots match this view. Change the filters or add a shot.</td></tr>`;
  const history = data.cleanup_history.length
    ? data.cleanup_history
        .slice()
        .reverse()
        .map(
          b =>
            html`<p><strong>${b.action} · ${b.items.length} shots${b.undone ? ' · undone' : ''}</strong> — ${b.reason}<br><span class="form-hint">${b.at}</span></p>`
        )
    : html`<p>No cleanup changes yet.</p>`;
  app.innerHTML = html`<div class="range-view"><div class="page-head"><div><div class="eyebrow">${data.demo ? 'DEMO / ' : ''}FULL SWING · ${isReview ? 'SAVED REVIEW' : active ? 'FREE PRACTICE' : 'RESULTS'}</div><h1>${isReview ? 'Range review' : 'Driving range'}</h1><p class="subtitle">${shots.length} recorded · ${shots.filter(included).length} included · ${data.handedness === 'left_handed' ? 'Left' : 'Right'}-handed</p></div><div class="head-actions">${active && !data.demo ? btn('Relay', 'relay', 'quiet') : ''}${active ? btn('End session', 'finish', 'danger') : btn('New range / edit setup', 'edit')}${isReview ? btn('Practice selector', 'home') : ''}${btn(isReview ? 'Exit review' : 'Exit session', 'exit-session', 'primary')}</div></div>
  ${data.demo ? html`<section class="range-demo" role="status"><div><strong>SIMULATED DATA · Demo range</strong><span>Generated shots only. Live capture does not enter this session.</span></div>${active ? html`<div>${local('＋ Add simulated shot', 'simulate', 'primary')}${local('Generate sample set (10)', 'sample', '')}</div>` : ''}</section>` : ''}
  ${active && !data.demo ? html`<div id="recording-feedback">${recordingWarnings(state.capture)}</div>` : ''}${!active ? sessionNotice(data, isReview) : ''}${state.practice_error && !isReview ? html`<div class="session-error" role="alert">${state.practice_error}</div>` : ''}
  ${active ? html`<section class="card equipment-card" aria-label="Tag upcoming shots">${equipmentControls(state.equipment, data.equipment_selection)}</section>` : ''}
  <section class="card range-hero"><div class="range-hero-heading"><div><span class="eyebrow">${shown === last ? 'LATEST SHOT' : `SHOT ${shown?.ordinal ?? '—'}`}</span><p>${eq.bag_name ?? ''}${eq.club_label ? ' / ' + eq.club_label : ' · Untagged'} ${shown?.corrected_equipment ? '· Corrected tag' : ''}</p></div><div>${shown && shown !== last ? local('Back to latest', 'latest') : ''}<span class="range-shape">${flight?.shape ?? (shown ? 'Model unavailable' : 'Waiting for a shot')}</span><p class="form-hint">OpenGolfCoach classification · estimated</p></div></div><div class="range-metrics">${metricTiles}</div>${clubTiles}<p class="form-hint">${data.demo_reference ? 'Synthetic Tour-reference samples; OpenGolfCoach estimates are separate' : data.demo ? 'Synthetic values generated from the flight model' : estimated(shown) ? 'Carry, total and offline: OpenGolfCoach estimates · other values source-reported' : 'source-reported values'} · ${shown ? `Shot ${shown.ordinal} · ${shown.removed ? 'Removed' : shown.excluded ? 'Excluded' : 'Saved'}${shown.target_distance_yd ? ` · Carry target ${n(shown.target_distance_yd)} yd${valid(rangeValue(shown, 'carry')) ? ` · ${shown.success ? 'In distance window' : 'Outside distance window'} · ${n(Math.abs(rangeValue(shown, 'carry') - shown.target_distance_yd))} yd ${rangeValue(shown, 'carry') < shown.target_distance_yd ? 'short' : 'long'}${est(shown)}` : ''}` : ''}` : 'Waiting for your first shot. Missing values stay unavailable.'}</p></section>
  <section class="range-analysis-controls"><div class="range-segment" aria-label="Scatter distance">${['carry', 'total'].map(m => html`<button class="btn ${v.metric === m ? 'primary' : 'quiet'}" data-distance="${m}" aria-pressed="${v.metric === m}">${m === 'carry' ? 'Carry' : 'Total'}</button>`)}</div>${select(
    'source',
    'Plot source',
    [
      ['model', 'OpenGolfCoach · estimated positions'],
      ['reported', data.demo ? 'Synthetic distance / offline' : 'Foresight · reported distance / offline']
    ],
    v.source
  )}<div class="range-target-control"><span>${data.range_target ? `Target ${n(data.range_target)} yd · ${n(data.range_width)} × ${n(data.range_depth)} yd` : 'Free practice · no target'}</span>${active ? local('Change target', 'target') : ''}</div></section>
  <div class="range-chart-grid"><section class="card range-dispersion-card"><div class="table-head">${dispersionHelp(v)}<span class="top-hint">${v.source === 'model' ? 'Estimated' : 'Reported'} · ${v.metric}</span></div><div class="range-scatter-stage">${chart.svg}</div>${chart.legend}<div class="range-summary-strip"><div><strong>${n(summary.mean)} yd</strong><span>Included mean · n=${summary.count}</span></div><div><strong>± ${n(summary.sd)} yd</strong><span>Population spread</span></div><div><strong>${n(all.mean)} yd</strong><span>All matching mean · n=${all.count}</span></div></div><p class="form-hint">Statistics use ${distanceBasis} ${v.metric}, independent of the plot source. Small samples are descriptive.</p></section>
  <div class="range-side"><section class="card"><div class="table-head"><h2>Flight profile</h2><span class="estimate-label">ESTIMATED</span></div><div class="range-segment range-flight-switch" aria-label="Flight profile view">${['side', 'top'].map(m => html`<button type="button" class="btn ${v.flightView === m ? 'primary' : 'quiet'}" data-flight-view="${m}" aria-pressed="${v.flightView === m}">${m === 'side' ? 'Side view' : 'Top view'}</button>`)}</div>${motionChart(motion, v.flightView)}${motionControls(motion)}<p class="form-hint">${motion?.label ?? 'Flight estimate unavailable'}. Path fitted to distance anchors; landing lateral position is estimated. Source and model metrics remain separate.</p><h3>OpenGolfCoach estimates</h3><div class="range-flight-metrics">${flightTiles}</div><p class="form-hint">OpenGolfCoach 0.3.0 · flat, no wind, standard atmosphere; typical fairway rollout. Uncalibrated against Foresight.</p></section><section class="card"><h2>Flight shapes</h2><p class="form-hint">${analytical.length} included shots in this filter · classification follows player handedness.</p><div class="shape-bars">${shapeBars}</div></section></div></div>
  <section class="card section-space range-club-snapshot" id="club-snapshot"><h2>Club snapshot</h2><p class="form-hint">${data.demo ? 'Synthetic values' : modeledDistances ? 'Carry, total and offline are OpenGolfCoach estimates; angles are source-reported' : 'source-reported values'} · included shots matching the workspace filters below. Median and IQR for each metric; n counts available readings.</p><div class="table-wrap" role="region" aria-label="Club snapshot statistics" tabindex="0"><table><thead><tr><th scope="col">Club</th><th scope="col">Included</th>${CLUB_METRICS.map(m => html`<th scope="col">${m.label} · ${m.unit}</th>`)}</tr></thead><tbody>${clubRows(analytical)}</tbody></table></div><p class="form-hint">IQR = Q3 − Q1, the width of the middle 50% (interpolated quartiles). At least two readings are needed for spread; small samples are descriptive. Absolute offline ignores left/right sign. Missing readings stay unavailable.</p></section>
  <section class="card section-space" id="shot-workspace"><div class="table-head"><div><h2>Shot workspace</h2><p class="form-hint">Filter, inspect and clean up this session. Original captures stay preserved.</p></div>${local('Export filtered CSV', 'csv')}</div><div class="range-filters">${select('bag', 'Bag', [['', 'All bags'], ...bagOptions], v.bag)}${select('club', 'Club', [['', 'All clubs'], ['__untagged__', 'Untagged'], ...clubOptions], v.club)}${select('shape', 'Flight shape', [['', 'All shapes'], ...[...new Set(shots.map(s => s.flight?.shape ?? 'Unavailable'))].map(s => [s, s])], v.shape)}${select(
    'status',
    'Shot state',
    [
      ['included', 'Included'],
      ['all', 'All recorded'],
      ['excluded', 'Excluded'],
      ['removed', 'Removed']
    ],
    v.status
  )}${select(
    'sort',
    'Sort',
    [
      ['latest', 'Latest first'],
      ['oldest', 'Oldest first'],
      ['distance', 'Distance · low to high']
    ],
    v.sort
  )}<label class="field">Search tags / reasons<input data-range-search value="${v.search}" placeholder="Club, shape or reason"></label></div>
  <div class="range-selection-bar"><strong>${v.selected.size} selected · ${matched.length} matching / ${shots.length} recorded</strong><div>${local('Select all matching', 'select-all', 'quiet', !matched.length)}${local('Clear selection', 'clear', 'quiet', !v.selected.size)}${local('Retag clubs', 'retag', '', !v.selected.size)}${local('Exclude', 'exclude', 'quiet', !v.selected.size)}${local('Include', 'include', 'quiet', !v.selected.size)}${local('Remove', 'remove', 'danger quiet', !v.selected.size)}${local('Restore', 'restore', 'quiet', !v.selected.size)}${local('Undo last cleanup', 'undo', 'quiet', !undo)}</div></div>
  <div class="table-wrap range-shot-table"><table><thead><tr><th>Select</th><th>Shot</th><th>Bag / club</th><th>Carry${modeledDistances ? ' (est.)' : ''} · yd</th><th>Total${modeledDistances ? ' (est.)' : ''} · yd</th><th>Offline${modeledDistances ? ' (est.)' : ''} · yd</th><th>Speed · mph</th><th>Launch · °</th><th>Spin · rpm</th><th>Est. shape</th><th>State</th></tr></thead><tbody>${shotRows}</tbody></table></div>
  <div class="range-workspace-foot"><p class="form-hint">${data.shots.filter(s => s.removed).length} removed · ${data.shots.filter(s => s.excluded && !s.removed).length} excluded. Remove hides a shot from session analysis; use Removed → Restore to recover it.</p>${local('Reset filters', 'reset')}</div>
  ${shown ? html`<details class="details"><summary>Shot ${shown.ordinal} details & provenance</summary><div class="range-detail-grid"><p>Recorded ${shown.captured}<br>Original tag: ${shown.bag_name || 'No bag'} / ${shown.club_label || 'Untagged'}<br>Effective tag: ${eq.bag_name || 'No bag'} / ${eq.club_label || 'Untagged'}<br>Cleanup reason: ${shown.cleanup_reason || 'None'}</p><p>Launch direction: ${n(shown.vals.launch_dir)}° (positive right)<br>Spin axis: ${n(shown.vals.spin_axis)}°<br>Model: ${flight?.model || 'Unavailable'}<br>Prediction uses launch inputs only; saved results are not recomputed by cleanup.</p></div></details>` : ''}
  <details class="details"><summary>Cleanup history (${data.cleanup_history.length})</summary>${history}</details>
  <div class="table-actions">${active ? btn('Abandon session', 'abandon', 'danger quiet') : btn('Delete session', 'delete-review', 'danger quiet')}${isReview ? btn('Practice selector', 'home') : ''}${btn(isReview ? 'Exit review' : 'Exit session', 'exit-session')}</div></section>
<p class="model-note">Reported and modeled flight results have different definitions. No modeled club delivery is presented as measured. <a href="/api/range-notices" target="_blank" rel="noopener">OpenGolfCoach license & model notes</a></p></div>`;
  mountShotMotion(
    app,
    app.querySelector('.shot-flight'),
    motion,
    motion ? chartProjection(motion, v.flightView) : null,
    redraw
  );
  bindDispersionHelp(app.querySelector('.range-view'), v);
  const tagButton = document.createElement('button');
  tagButton.type = 'button';
  tagButton.className = 'btn quiet';
  tagButton.textContent = 'Tags';
  tagButton.disabled = !v.selected.size;
  tagButton.onclick = () =>
    tagDialog(
      data.id,
      [...v.selected],
      async (path, body) => {
        const r = await fetch(path, {
          method: body ? 'POST' : 'GET',
          headers: body ? { 'Content-Type': 'application/json' } : {},
          body: body ? JSON.stringify(body) : undefined
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail ?? 'Tag request failed');
        return d;
      },
      context.notice
    );
  app.querySelector('.range-selection-bar>div').append(tagButton);
  if (active) bindEquipment(app, context.equipment, context.select, context.current);
  app.querySelectorAll('[data-flight-view]').forEach(
    b =>
      (b.onclick = () => {
        v.flightView = b.dataset.flightView;
        redraw();
      })
  );
  app.querySelectorAll('[data-distance]').forEach(
    b =>
      (b.onclick = () => {
        v.metric = b.dataset.distance;
        redraw();
      })
  );
  app.querySelectorAll('[data-range-filter]').forEach(
    el =>
      (el.onchange = () => {
        v[el.dataset.rangeFilter] = el.value;
        if (el.dataset.rangeFilter === 'bag') v.club = '';
        v.selected.clear();
        redraw();
      })
  );
  app.querySelector('[data-range-search]').onchange = e => {
    v.search = e.target.value;
    v.selected.clear();
    redraw();
  };
  app.querySelectorAll('[data-select-shot]').forEach(
    b =>
      (b.onchange = () => {
        if (b.checked) v.selected.add(b.dataset.selectShot);
        else v.selected.delete(b.dataset.selectShot);
        redraw();
      })
  );
  const bindInspection = root =>
    root.querySelectorAll('[data-inspect-shot]').forEach(b => {
      const inspect = () => {
        resetShotMotion();
        v.focus = b.dataset.inspectShot;
        v.follow = false;
        redraw();
        if (b.closest('table'))
          app.querySelector('.range-hero').scrollIntoView({ behavior: 'smooth', block: 'start' });
      };
      b.onclick = inspect;
      b.onkeydown = e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          inspect();
        }
      };
    });
  bindInspection(app);
  const stage = app.querySelector('.range-scatter-stage');
  // Redraw coordinates at the available aspect ratio, retaining readable SVG text and markers.
  // The SVG is positioned out of flow, so changing its viewBox cannot grow the observed stage.
  const observer = new ResizeObserver(entries => {
    if (!stage.isConnected) {
      observer.disconnect();
      return;
    }
    const { width, height } = entries[0].contentRect;
    if (width <= 0 || height <= 0) return;
    const focused = stage.contains(document.activeElement)
      ? document.activeElement.dataset.inspectShot
      : null;
    stage.innerHTML = drawScatter({ width, height }).svg;
    bindInspection(stage);
    if (focused)
      [...stage.querySelectorAll('[data-inspect-shot]')]
        .find(b => b.dataset.inspectShot === focused)
        ?.focus({ preventScroll: true });
  });
  scatterResize = observer;
  observer.observe(stage);
  app.querySelectorAll('[data-range-action]').forEach(
    b =>
      (b.onclick = async () => {
        const action = b.dataset.rangeAction;
        if (action === 'select-all') {
          v.selected = new Set(matched.map(s => s.key));
          redraw();
          return;
        }
        if (action === 'clear') {
          v.selected.clear();
          redraw();
          return;
        }
        if (action === 'latest') {
          resetShotMotion();
          v.follow = true;
          v.focus = last?.key;
          redraw();
          return;
        }
        if (action === 'reset') {
          Object.assign(v, { bag: '', club: '', shape: '', search: '', status: 'included', sort: 'latest' });
          v.selected.clear();
          redraw();
          return;
        }
        if (action === 'csv') {
          const url = URL.createObjectURL(new Blob([rangeCsv(matched)], { type: 'text/csv;charset=utf-8' }));
          const a = document.createElement('a');
          a.href = url;
          a.download = `traceloft-${data.demo ? 'DEMO-' : ''}range-${data.id}.csv`;
          a.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
          return;
        }
        if (['exclude', 'include', 'remove', 'restore', 'retag'].includes(action)) {
          cleanupDialog(
            data,
            [...v.selected],
            action,
            state.equipment,
            async params => {
              await context.cleanup(params);
              v.selected.clear();
              context.redraw();
            },
            context.notice
          );
          return;
        }
        if (action === 'target') {
          targetDialog(data, context);
          return;
        }
        b.disabled = true;
        try {
          if (action === 'simulate' || action === 'sample')
            await context.simulate(action === 'sample' ? 10 : 1);
          if (action === 'undo')
            await context.cleanup({
              action: 'undo',
              keys: [],
              revision: data.cleanup_revision,
              reason: 'Undo previous cleanup',
              batch_id: undo.id
            });
        } catch (e) {
          context.notice(e.message);
          b.disabled = false;
        }
      })
  );
  decorateCollection(app, data, active, { ...context, shown });
}

function clubRows(shots) {
  const groups = clubSummaries(shots);
  return groups.length
    ? groups.map(
        g =>
          html`<tr><th scope="row">${g.label}</th><td>${g.count}</td>${g.metrics.map(m => html`<td><strong>${n(m.median)}</strong><span class="range-stat-detail">IQR ${n(m.iqr)} · n=${m.count}</span></td>`)}</tr>`
      )
    : html`<tr><td colspan="7" class="empty">Included club statistics will appear here.</td></tr>`;
}

function targetDialog(data, context) {
  const d = document.createElement('dialog');
  d.className = 'confirm-dialog';
  d.id = 'range-target-dialog';
  d.setAttribute('aria-labelledby', 'target-title');
  d.innerHTML = html`<h2 id="target-title">Next-shot target</h2><p>Applies to upcoming shots. Earlier targets stay saved with their shots.</p><form>${field('target', 'Target distance · yd (0 = free practice)', data.range_target, 0, 450)}${field('width', 'Target width · yd', data.range_width, 1, 200)}${field('depth', 'Distance window · yd (full depth)', data.range_depth, 1, 200)}<p class="session-error" role="alert" hidden></p><div class="confirm-actions"><button type="button" class="btn quiet" data-cancel>Cancel</button><button type="submit" class="btn primary">Save target</button></div></form>`;
  document.body.append(d);
  d.showModal();
  d.querySelector('[data-cancel]').onclick = () => d.close();
  d.onclose = () => d.remove();
  d.querySelector('form').onsubmit = async e => {
    e.preventDefault();
    const b = d.querySelector('[type=submit]');
    b.disabled = true;
    try {
      await context.target(Object.fromEntries([...new FormData(e.target)].map(([k, v]) => [k, Number(v)])));
      d.close();
    } catch (error) {
      const p = d.querySelector('[role=alert]');
      p.hidden = false;
      p.textContent = error.message;
      b.disabled = false;
    }
  };
}
