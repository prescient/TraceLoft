import { html, direction, error, trend, gauge, progress } from './charts.js';
import { recordingWarnings } from './recording.js';

// `extra` is attribute markup: html`` or ''.
const button = (text, action, kind = '', extra = '') =>
  html`<button class="btn ${kind}" data-action="${action}" ${extra}>${text}</button>`;

export function renderPuttingSetup(app, d, launch, notice) {
  const old = d.parameters ?? {};
  const ladder = d.id === 'ladder';
  app.innerHTML = html`<div class="page-head"><div><h1>${d.title}</h1><p class="subtitle">Set your parameters, then launch your practice session.</p></div>${button('← Practice', 'home', 'quiet')}</div><section class="card setup-card"><h2>Session targets</h2><form id="setup-form"><div class="form-grid">
    <label class="field">Pace targets<select name="random_pace"><option value="false" ${!old.random_pace && !d.random_pace ? 'selected' : ''}>Fixed target</option><option value="true" ${(old.random_pace ?? d.random_pace) ? 'selected' : ''}>Random pace</option></select></label>
    <label class="field">Number of putts<input name="repetitions" type="number" min="1" max="1000" value="${old.repetitions ?? 10}" required></label>
    <label class="field" data-param="fixed">Target speed (mph)<input name="target" type="number" step="0.1" min="1" max="15" value="${old.target ?? 4}" required></label>
    <label class="field" data-param="pace">Speed tolerance (± mph)<input name="speed_tolerance" type="number" step="0.1" min="0" value="${old.speed_tolerance ?? 0.3}" required></label>
    <label class="field" data-param="random">Random minimum (mph)<input name="minimum" type="number" step="0.1" min="1" max="15" value="${old.minimum ?? 3}" required></label>
    <label class="field" data-param="random">Random maximum (mph)<input name="maximum" type="number" step="0.1" min="1" max="15" value="${old.maximum ?? 6}" required></label>
    <label class="field" data-param="line">Start-line tolerance (± degrees)<input name="angle_tolerance" type="number" step="0.1" min="0" value="${old.angle_tolerance ?? 1}" required></label>
    <label class="field">Green speed · Stimp (ft)<input name="stimp" type="number" step="0.1" min="3" max="20" value="${old.stimp ?? 10}" required></label>
    <label class="field">Distance model<select name="distance_model"><option value="stimp-constant-deceleration-v1" ${!old.distance_model || old.distance_model.id === 'stimp-constant-deceleration-v1' ? 'selected' : ''}>Stimp constant braking · baseline</option><option value="fuse-flat-braking-v1" ${old.distance_model?.id === 'fuse-flat-braking-v1' ? 'selected' : ''}>Fuse speed-dependent braking · comparison</option></select></label>
    <label class="field" data-param="mode">Score target as<select name="target_mode"><option value="speed" ${old.target_mode !== 'distance' ? 'selected' : ''}>Measured speed (mph)</option><option value="distance" ${old.target_mode === 'distance' ? 'selected' : ''}>Estimated distance (ft)</option></select></label>
    <label class="field" data-param="distance">Target distance (ft)<input name="target_distance" type="number" step="0.1" min="0.5" max="300" value="${old.target_distance_ft ?? 10}" required></label>
    <label class="field" data-param="distance-tolerance">Distance tolerance (± ft)<input name="distance_tolerance" type="number" step="0.1" min="0" max="100" value="${old.distance_tolerance ?? 2}" required></label>
    <label class="field" data-param="ladder">Shortest distance (ft)<input name="ladder_start" type="number" step="0.5" min="0.5" max="300" value="${old.ladder_start ?? 5}" required></label>
    <label class="field" data-param="ladder">Longest distance (ft)<input name="ladder_end" type="number" step="0.5" min="0.5" max="300" value="${old.ladder_end ?? 25}" required></label>
    <label class="field" data-param="ladder">Step between rungs (ft)<input name="ladder_step" type="number" step="0.5" min="0.5" max="300" value="${old.ladder_step ?? 5}" required></label>
    <label class="field" data-param="ladder">Rounds through ladder<input name="ladder_rounds" type="number" min="1" max="100" value="${old.ladder_rounds ?? 2}" required></label>
    <label class="field" data-param="ladder">Ladder direction<select name="ladder_direction"><option value="ascending" ${old.ladder_direction !== 'descending' ? 'selected' : ''}>Ascending · short to long</option><option value="descending" ${old.ladder_direction === 'descending' ? 'selected' : ''}>Descending · long to short</option></select></label>
    </div><p class="model-note">Estimated distance uses your selected flat-green model. Constant braking is the physics baseline; Fuse is a simulation comparison. Stimp is entered, not measured. Launch speed is treated as rolling speed; slope, skid and cup effects are omitted. Uncalibrated for your mat and GSPro.</p><p id="ladder-preview" class="form-hint" role="status"></p><div class="form-foot"><p class="form-hint">${ladder ? 'One putt per rung, advancing after every confirmed putt, including misses. Repeat for each round. Start line is measured, not scored.' : 'Fixed drills can score measured speed or estimated distance. Random pace varies speed; each putt keeps its own target and estimate.'}</p><button type="submit" class="btn primary">Launch drill →</button></div></form></section>`;
  const form = app.querySelector('form');
  function parameters() {
    const line = d.drill === 'Start line',
      pace = d.drill === 'Pace consistency',
      random = form.elements.random_pace.value === 'true';
    const distance = ladder || (!line && !random && form.elements.target_mode.value === 'distance');
    form.elements.random_pace.disabled = line || ladder;
    form.elements.random_pace.closest('label').hidden = line || ladder;
    form.elements.repetitions.disabled = ladder;
    form.elements.repetitions.closest('label').hidden = ladder;
    app.querySelectorAll('[data-param]').forEach(label => {
      const kind = label.dataset.param,
        show =
          kind === 'ladder'
            ? ladder
            : kind === 'mode'
              ? !line && !random && !ladder
              : kind === 'distance-tolerance'
                ? distance
                : kind === 'distance'
                  ? distance && !ladder
                  : kind === 'line'
                    ? !pace && !ladder
                    : !line &&
                      !ladder &&
                      !distance &&
                      (kind === 'pace' || (kind === 'random' && random) || (kind === 'fixed' && !random));
      label.hidden = !show;
      label.querySelector('input,select').disabled = !show;
    });
    if (ladder) {
      const count =
        (Number(form.elements.ladder_end.value) - Number(form.elements.ladder_start.value)) /
          Number(form.elements.ladder_step.value) +
        1;
      app.querySelector('#ladder-preview').textContent =
        Number.isInteger(count) && count > 1
          ? `${count} rungs × ${form.elements.ladder_rounds.value} rounds = ${count * Number(form.elements.ladder_rounds.value)} putts.`
          : 'Choose a step that divides the distance range evenly.';
    }
  }
  form.oninput = parameters;
  form.onchange = parameters;
  parameters();
  form.onsubmit = async event => {
    event.preventDefault();
    const data = new FormData(form),
      num = (key, fallback) => (data.has(key) ? Number(data.get(key)) : fallback);
    const params = {
      drill: d.drill,
      target: num('target', 4),
      speed_tolerance: num('speed_tolerance', 0),
      angle_tolerance: num('angle_tolerance', 1),
      repetitions: num('repetitions', 10),
      random_pace: d.drill !== 'Start line' && data.get('random_pace') === 'true',
      minimum: num('minimum', 3),
      maximum: num('maximum', 6)
    };
    Object.assign(params, {
      distance_model: data.get('distance_model'),
      stimp: num('stimp', 10),
      target_mode: ladder ? 'distance' : (data.get('target_mode') ?? 'speed'),
      target_distance: num('target_distance', 10),
      distance_tolerance: num('distance_tolerance', 2),
      ladder_start: num('ladder_start', 5),
      ladder_end: num('ladder_end', 25),
      ladder_step: num('ladder_step', 5),
      ladder_rounds: num('ladder_rounds', 2),
      ladder_direction: data.get('ladder_direction') ?? 'ascending'
    });
    try {
      await launch(params);
    } catch (e) {
      notice(e.message);
    }
  };
}

export function puttingRunner(data, summary, state, isReview, selectedShot, sessionNotice) {
  const shots = data.shots,
    latest = shots.at(-1),
    own = !isReview,
    active = own && !data.ended,
    recording = state.capture.running && state.capture.mode === 'run';
  const speed = latest?.vals.ball_speed,
    hla = latest?.vals.launch_dir,
    paceError = latest ? speed - (latest.target ?? data.target) : null;
  const excluded = latest?.excluded,
    good = latest?.success && !excluded;
  const resultClass = excluded ? 'excluded' : !latest ? 'waiting' : good ? '' : 'miss';
  const modeled = !!data.distance_model,
    distance = data.target_mode === 'distance',
    ladder = data.drill === 'Putting ladder';
  const distanceError = latest?.distance_error_ft,
    travel = latest?.estimated_distance_ft;
  const ladderPosition = active ? shots.length : Math.max(0, shots.length - 1);
  const rung = ladder ? (ladderPosition % data.ladder_targets_ft.length) + 1 : null;
  const displayedDistance =
    ladder && !active ? (latest?.target_distance_ft ?? data.target_distance_ft) : data.target_distance_ft;
  const displayedSpeed = ladder && !active ? (latest?.target ?? data.target) : data.target;
  const targetLine = distance
    ? `${displayedDistance.toFixed(1)} ft ± ${data.distance_tolerance} ft`
    : data.drill === 'Start line'
      ? `Start line 0° ± ${data.angle_tolerance}°`
      : `${data.target.toFixed(1)} mph ± ${data.speed_tolerance}`;
  const status = excluded ? 'Excluded' : !latest ? 'Waiting' : good ? 'In window' : 'Outside window';
  const logRows = shots
    .map((s, i) => ({ s, i }))
    .reverse()
    .map(
      ({ s, i }) =>
        html`<tr data-key="${s.key}" tabindex="0" aria-label="Select putt ${i + 1}" class="${i === shots.length - 1 ? 'latest-row' : ''} ${s.excluded ? 'excluded' : ''} ${selectedShot === s.key ? 'selected' : ''}"><td>${i + 1}</td><td>${s.vals.ball_speed.toFixed(1)}</td><td>${(s.target ?? data.target).toFixed(1)}</td><td>${error(s.vals.ball_speed - (s.target ?? data.target))} mph</td><td>${direction(s.vals.launch_dir)}</td>${modeled ? html`<td>${s.estimated_distance_ft?.toFixed(1) ?? '—'}</td><td>${s.target_distance_ft?.toFixed(1) ?? '—'}</td><td>${s.distance_error_ft == null ? '—' : error(s.distance_error_ft)}</td>` : ''}<td class="${s.excluded ? '' : s.success ? 'success-text' : 'miss-text'}">${s.excluded ? 'Excluded' : s.success ? '● In window' : '● Outside window'}</td></tr>`
    );
  const statistics = ['pace_error', 'launch_dir', 'launch_ang']
    .map(
      (f, i) =>
        `${['Pace error', 'Start line', 'Vertical launch'][i]} ${summary[f].mean === null ? '—' : `${summary[f].mean.toFixed(2)} ± ${summary[f].sd.toFixed(2)}`} ${i ? '°' : 'mph'}`
    )
    .join(' · ');
  return html`<div class="page-head"><div><h1>${isReview ? 'Session review' : 'Putting practice'}</h1><p class="subtitle">${data.drill} <span class="chip ${data.random_pace ? 'accent' : ''}">${ladder ? (data.ladder_direction === 'descending' ? 'Descending ladder' : 'Ascending ladder') : data.random_pace ? 'Random pace' : distance ? 'Distance target' : 'Speed target'}</span>${data.abandoned ? ' · Abandoned' : isReview ? ' · Saved session' : data.ended ? ' · Complete' : ''}</p></div><div class="head-actions">${active ? [button('Relay', 'relay', 'quiet'), button('End session', 'finish', 'danger')] : ''}${isReview ? button('Practice selector', 'home', 'quiet') : ''}${button(isReview ? 'Exit review' : 'Exit session', 'exit-session', active ? 'quiet' : 'primary')}${!active ? button('⚙ Edit targets', 'edit', 'quiet') : ''}</div></div>
    ${!active ? sessionNotice(data, isReview) : ''}
    ${state.practice_error && own ? html`<div class="session-error" role="alert">${state.practice_error}</div>` : ''}
    ${active ? html`<div id="recording-feedback">${recordingWarnings(state.capture, 'putts')}</div>` : ''}
    <div class="heroes"><section class="card"><div class="eyebrow">LATEST PUTT</div><div class="latest-metrics ${modeled ? 'with-distance' : ''}">
      <div class="metric"><div class="metric-label">Ball speed</div><div class="metric-value">${latest ? speed.toFixed(1) : '—'}</div><div class="metric-unit">mph</div></div>
      <div class="metric"><div class="metric-label">${distance ? 'Distance error' : 'Pace error'}</div><div class="metric-value">${latest ? error(distance ? distanceError : paceError) : '—'}</div><div class="metric-unit">${distance ? 'ft · estimated' : 'mph'}${distance && latest ? (distanceError < -1e-9 ? ' · short' : distanceError > 1e-9 ? ' · long' : ' · on target') : ''}${data.drill === 'Start line' ? ' · not scored' : ''}</div></div>
      ${modeled ? html`<div class="metric"><div class="metric-label">Estimated travel</div><div class="metric-value">${travel == null ? '—' : travel.toFixed(1)}</div><div class="metric-unit">ft · Stimp ${data.stimp}</div></div>` : ''}
      <div class="metric"><div class="metric-label">Start line</div><div class="metric-value">${latest ? direction(hla) : '—'}</div><div class="metric-unit">at launch</div></div>
      <div class="metric"><div class="metric-label">Result</div><div class="result ${resultClass}"><span class="result-icon">${good ? '✓' : latest && !excluded ? '!' : '—'}</span>${status}</div></div>
    </div><div class="metric-foot">${latest ? `Putt ${shots.length} · ${excluded ? 'Excluded from score' : 'Saved automatically'}` : data.ended ? 'No validated putts in this session.' : recording ? 'Waiting for your next validated putt.' : 'Connect your shot source through Relay.'}</div></section>
    <section class="card progress-card"><div class="eyebrow">SESSION PROGRESS</div><div class="progress-counts"><div><strong>${shots.length} / ${data.repetitions}</strong><span>putts</span></div><div><strong>${summary.successes} / ${summary.count}</strong><span>in window</span></div></div><div class="progress-row">${progress(shots.length, data.repetitions)}</div><div class="target-tile"><small>${data.abandoned ? 'SESSION ABANDONED' : data.ended ? 'SESSION COMPLETE' : data.random_pace || ladder ? 'NEXT TARGET' : 'SESSION TARGET'}</small><strong>${targetLine}</strong>${distance ? html`<p>Required pace ≈ ${displayedSpeed.toFixed(2)} mph · estimated</p>` : ''}${ladder ? html`<p>${active ? 'Rung' : 'Last rung'} ${rung} / ${data.ladder_targets_ft.length} · Round ${Math.min(Math.floor(ladderPosition / data.ladder_targets_ft.length) + 1, data.ladder_rounds)} / ${data.ladder_rounds}</p><p>${data.ladder_targets_ft.map((t, i) => [i ? ' ' : '', html`<span class="ladder-rung ${i + 1 === rung ? 'current' : ''}">${t.toFixed(1)} ft</span>`])}</p>` : ''}<p>${ladder ? 'Start line measured · not scored' : data.drill !== 'Start line' ? `Start line 0° ± ${data.angle_tolerance}°${data.drill === 'Pace consistency' || ladder ? ' · not scored' : ''}` : 'Pace is measured, not scored.'}</p></div></section></div>
    ${modeled ? html`<p class="model-note">Estimated flat-green travel · Stimp ${data.stimp} · ${data.distance_model.id === 'fuse-flat-braking-v1' ? 'Fuse speed-dependent braking v1' : 'Stimp constant braking v1'}. Uncalibrated; no slope, skid or cup effects. ${distance ? 'Scores estimate windows, not holed putts.' : 'Distance is shown for context; scoring uses launch measurements.'}</p>` : html`<p class="model-note">Distance unavailable: this historical session has no saved Stimp/model. Edit targets to launch a new session with distance estimates.</p>`}
    <div class="graphs"><section class="card pace-card"><div class="eyebrow">${distance ? 'ESTIMATED DISTANCE (FT)' : 'PACE CHART'}</div><p class="graph-subtitle">${distance ? 'Travel vs target by putt · flat-green estimate' : 'Ball speed by putt'}${data.drill === 'Start line' ? ' · not scored' : ''}</p><div class="legend"><span><i class="swatch"></i>Target zone${data.random_pace || ladder ? ' (varies)' : ''}</span><span><i class="line-swatch"></i>${distance ? 'Distance target per putt' : data.random_pace ? 'Target per putt' : `Target (${data.target.toFixed(1)} mph)`}</span></div>${trend(data, true, distance)}</section>
    <section class="card"><div class="eyebrow">START LINE (LATEST PUTT)</div><p class="graph-subtitle">Direction at launch relative to target</p>${gauge(data)}<div class="legend"><span><i class="swatch"></i>In window (±${data.angle_tolerance}°)${data.drill === 'Pace consistency' || ladder ? ' · not scored' : ''}</span></div><div class="graph-divider"></div><div class="start-trend"><div class="eyebrow">START LINE TREND</div><p class="graph-subtitle">Direction by putt (right is positive)</p>${trend(data, false)}</div></section></div>
    <section class="card"><div class="table-head"><div class="eyebrow">SHOT LOG</div><span class="top-hint">Latest first · select a row to review</span></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Speed (mph)</th><th>Target (mph)</th><th>Pace error</th><th>Start line</th>${modeled ? html`<th>Est. travel (ft)</th><th>Distance target (ft)</th><th>Est. error (ft)</th>` : ''}<th>Result</th></tr></thead><tbody>${shots.length ? logRows : html`<tr><td colspan="${modeled ? 9 : 6}" class="empty">No recorded putts yet.</td></tr>`}</tbody></table></div><div class="table-actions">${button('Exclude / include selected', 'exclude', 'small', !selectedShot ? html`disabled` : '')}${active ? button('Abandon session', 'abandon', 'danger quiet small') : button('Delete session', 'delete-review', 'danger quiet small')}${isReview ? button('Practice selector', 'home', 'quiet small') : ''}${button(isReview ? 'Exit review' : 'Exit session', 'exit-session', 'quiet small')}</div><details class="details"><summary>Session statistics</summary><p>${summary.count} included putts · ${summary.successes} in window<br>${statistics}${summary.distance_error_ft?.count ? html`<br>Estimated distance error ${summary.distance_error_ft.mean.toFixed(2)} ± ${summary.distance_error_ft.sd.toFixed(2)} ft · ${summary.distance_error_ft.short} short / ${summary.distance_error_ft.long} long` : modeled ? html`<br>No distance estimates yet.` : ''}<br>Mean ± population standard deviation. Excluded putts remain in the log.</p></details></section>`;
}
