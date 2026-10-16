import { html } from './charts.js';
import { equipmentControls, bindEquipment } from './equipment.js';
import { format as n, rangeValue, valid, estimated } from './range-data.js';

// Random distances (D67): the range workspace with a server-drawn carry target after every
// scored shot. The golfer chooses the club; nothing here suggests one.

const field = (name, label, value, min, max, step = 1) =>
  html`<label class="field">${label}<input name="${name}" type="number" min="${min}" max="${max}" step="${step}" value="${value}" required></label>`;

/** The drawable targets for a setup, mirroring random_distances.target_grid (display only). */
export function targetGrid(low, high, step) {
  if (![low, high, step].every(Number.isFinite) || step <= 0 || high <= low) return [];
  return Array.from(
    { length: Math.floor((high - low) / step + 1e-9) + 1 },
    (_, i) => +(low + i * step).toFixed(6)
  );
}

/** One line describing the targets a setup draws, or what to change when it cannot work. */
export function setupPreview({ random_min, random_max, random_step, random_gap, random_count, range_depth }) {
  const grid = targetGrid(random_min, random_max, random_step);
  if (grid.length < 2)
    return { ok: false, text: 'Set the longest distance above the shortest by at least the rounding.' };
  const stuck = grid.some(t => !grid.some(o => Math.abs(o - t) >= Math.max(random_gap, 1e-6) - 1e-9));
  if (stuck)
    return {
      ok: false,
      text: `A ${n(random_gap, 0)} yd minimum change is too large for ${n(random_min, 0)}–${n(random_max, 0)} yd. Widen the range or lower the minimum change.`
    };
  return {
    ok: true,
    text: `${random_count} targets drawn from ${grid.length} distances (${n(random_min, 0)}–${n(random_max, 0)} yd, every ${n(random_step, 0)} yd). Each new target is at least ${n(Math.max(random_gap, random_step), 0)} yd from the last. In window = carry within ±${n(range_depth / 2)} yd.`
  };
}

export function renderRandomSetup(app, old, launch, notice, eq) {
  app.innerHTML = html`<div class="page-head"><div><div class="eyebrow">FULL SWING / RANDOM TARGETS</div><h1>Random distances</h1><p class="subtitle">A new carry target after every shot. Pick the club, commit to the number.</p></div><button type="button" class="btn quiet" data-action="home">← Back to Practice</button></div>
  <form id="random-form"><div class="range-intro-grid"><section class="card"><h2>Your targets</h2><p class="subtitle">TraceLoft draws each target at random. You choose the club for it.</p><div class="form-grid">${field('random_min', 'Shortest target · yd', old.random_min ?? 60, 1, 450)}${field('random_max', 'Longest target · yd', old.random_max ?? 180, 1, 450)}${field('random_step', 'Round targets to · yd', old.random_step ?? 5, 1, 50)}${field('random_gap', 'Minimum change between targets · yd', old.random_gap ?? 15, 0, 200)}${field('random_count', 'Number of targets', old.repetitions ?? 20, 1, 200)}${field('range_depth', 'Distance window · yd (full depth)', old.range_depth ?? 20, 1, 200)}${field('range_width', 'Target width · yd', old.range_width ?? 30, 1, 200)}<label class="field">Player handedness<select name="handedness"><option value="right_handed" ${old.handedness !== 'left_handed' ? 'selected' : ''}>Right-handed</option><option value="left_handed" ${old.handedness === 'left_handed' ? 'selected' : ''}>Left-handed</option></select></label></div><p id="random-preview" class="form-hint" role="status"></p></section>
  <section class="card range-intro"><div class="eyebrow">HOW IT WORKS</div><h2>Swing between clubs.</h2><p>Each scored shot ends the target and draws the next one. Tag the club you chose before you hit, so every shot keeps its club, target and result.</p><div class="range-intro-features"><span>◎ Random carry targets</span><span>⇄ Your club choice</span><span>✓ In-window score</span></div><p class="model-note">Carry is estimated by OpenGolfCoach from your launch data, the same way as the driving range. A shot without a usable carry is saved unscored and keeps the target.</p></section></div>
  <section class="card section-space">${equipmentControls(eq.catalog(), old.equipment_selection, true)}</section><div class="range-launch-actions"><button class="btn primary" type="submit" name="mode" value="live">Start random distances →</button><button class="btn" type="submit" name="mode" value="demo">Start demo</button><span class="form-hint">Demo sessions use labeled synthetic shots aimed at each target and do not accept live shots.</span></div></form>`;
  bindEquipment(app, eq, null);
  const form = app.querySelector('form');
  const numbers = () => {
    const values = Object.fromEntries(new FormData(form));
    for (const k of [
      'random_min',
      'random_max',
      'random_step',
      'random_gap',
      'random_count',
      'range_depth',
      'range_width'
    ])
      values[k] = Number(values[k]);
    return values;
  };
  const preview = () => {
    const result = setupPreview(numbers());
    const box = app.querySelector('#random-preview');
    box.textContent = result.text;
    box.classList.toggle('session-error', !result.ok);
  };
  form.oninput = preview;
  preview();
  form.onsubmit = async e => {
    e.preventDefault();
    const demo = e.submitter?.value === 'demo';
    form.querySelectorAll('button').forEach(b => (b.disabled = true));
    try {
      await launch({ drill: 'Random distances', ...numbers(), demo });
    } catch (error) {
      notice(error.message);
      form.querySelectorAll('button').forEach(b => (b.disabled = false));
    }
  };
}

/** What the latest shot did against its target, in words (never color alone). */
export function lastResult(shot) {
  if (!shot) return { kind: 'waiting', text: 'Waiting for your first shot.' };
  if (shot.removed) return { kind: 'waiting', text: 'Latest shot removed from the session.' };
  if (!shot.scored) return { kind: 'miss', text: 'Carry unavailable · target unchanged. Hit it again.' };
  const carry = rangeValue(shot, 'carry'),
    error = carry - shot.target_distance_yd,
    side = error < -1e-9 ? 'short' : error > 1e-9 ? 'long' : 'on target',
    label = estimated(shot) ? ' est.' : '';
  return {
    kind: shot.success ? 'hit' : 'miss',
    text: `Target ${n(shot.target_distance_yd, 0)} yd · carry ${n(carry)} yd${label} · ${side === 'on target' ? 'on target' : `${n(Math.abs(error))} yd ${side}`} · ${shot.success ? 'In window ✓' : 'Outside window'}${shot.excluded ? ' · excluded' : ''}`
  };
}

export function decorateRandomTargets(app, data, active, context) {
  if (data.target_plan !== 'random') return;
  const targets = context.summary?.targets ?? {},
    completed = data.completed_shots,
    total = data.repetitions,
    last = lastResult(data.shots.at(-1));
  app.querySelector('h1').textContent = data.drill + (context.isReview ? ' · review' : '');
  const eyebrow = app.querySelector('.page-head .eyebrow');
  if (eyebrow) eyebrow.textContent = eyebrow.textContent.replace('FREE PRACTICE', 'RANDOM TARGETS');
  app.querySelector('[data-range-action="target"]')?.remove();
  const targetText = app.querySelector('.range-target-control > span');
  if (targetText)
    targetText.textContent = active
      ? `Next target ${n(data.range_target, 0)} yd · ${n(data.range_width)} × ${n(data.range_depth)} yd window`
      : `Random targets ${n(data.random_min, 0)}–${n(data.random_max, 0)} yd · ${n(data.range_width)} × ${n(data.range_depth)} yd window`;
  app
    .querySelector('[data-action="edit"]')
    ?.replaceChildren(document.createTextNode('New session / edit setup'));
  // The result headline already shows the in-window count.
  const score = html`<div class="random-target-score">${active ? html`<div><strong>${targets.in_window ?? 0} / ${targets.scored ?? 0}</strong><span>in window</span></div>` : ''}<div><strong>${valid(targets.mean_absolute_error) ? `${n(targets.mean_absolute_error)} yd` : '—'}</strong><span>average miss${data.demo ? '' : ' · est.'}</span></div><div><strong>${targets.short ?? 0} short · ${targets.long ?? 0} long</strong><span>included scored shots</span></div></div>`;
  const panel = document.createElement('section');
  panel.className = 'card random-target';
  panel.setAttribute('aria-label', active ? 'Next target' : 'Random distances result');
  panel.innerHTML = active
    ? html`<div class="random-target-main"><span class="eyebrow">NEXT TARGET · ${completed + 1} OF ${total}</span><strong class="random-target-yardage">${n(data.range_target, 0)}<small>yd carry</small></strong><p class="form-hint">In window: ±${n(data.range_depth / 2)} yd. Choose your club below, then hit.</p></div><div class="random-target-side"><p class="random-target-last ${last.kind}" role="status">${last.text}</p>${score}<svg class="random-target-progress" viewBox="0 0 300 10" preserveAspectRatio="none" role="img" aria-label="${completed} of ${total} targets done"><rect width="300" height="10" fill="var(--grid)"/><rect width="${(300 * completed) / total}" height="10" fill="var(--accent)"/></svg><p class="form-hint">${completed} of ${total} targets done · exclusions change the score, not the targets.</p></div>`
    : html`<div class="random-target-main"><span class="eyebrow">${data.abandoned ? 'SESSION ABANDONED' : 'SESSION RESULT'} · ${completed} OF ${total} TARGETS</span><strong class="random-target-yardage">${targets.in_window ?? 0}<small>/ ${targets.scored ?? 0} in window</small></strong><p class="form-hint">Targets ${n(data.random_min, 0)}–${n(data.random_max, 0)} yd · window ±${n(data.range_depth / 2)} yd.</p></div><div class="random-target-side"><p class="random-target-last ${last.kind}">Last shot: ${last.text}</p>${score}</div>`;
  const anchor = (active && app.querySelector('.equipment-card')) || app.querySelector('.range-hero');
  anchor.insertAdjacentElement('beforebegin', panel);
}
