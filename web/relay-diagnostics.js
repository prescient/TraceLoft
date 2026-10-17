// Relay diagnostics (D74): how a standard sender is read, and for each recent shot what was
// confirmed at every hop — received from the source, stored in TraceLoft (with how each value was
// classified), and sent to and acknowledged by the simulator.
import { html } from './charts.js';

const STORED = {
  measurement: 'Measurement',
  estimate: 'Source estimate',
  missing: 'Not measured',
  evidence: 'Raw packet only',
};

const SIMULATOR = {
  acknowledged: ['ok', 'Acknowledged'],
  awaiting_reply: ['wait', 'Sent · waiting for reply'],
  no_reply: ['bad', 'No reply'],
  rejected: ['bad', 'Rejected'],
  not_sent: ['off', 'Not sent'],
};

// The input-profile choice for standard senders.
export function profileControl(profiles, current) {
  const chosen = profiles.find(p => p.id === current) ?? profiles[0];
  return html`<label class="field section-space">Shot source<select id="input-profile">${profiles.map(
    p => html`<option value="${p.id}" ${p.id === current ? 'selected' : ''}>${p.title}</option>`
  )}</select></label><p class="form-hint">${chosen?.description ?? ''}</p>`;
}

function hop(kind, label, detail = '') {
  const icon = { ok: '✓', bad: '✕', wait: '…', off: '–' }[kind];
  return html`<span class="hop hop-${kind}"><span aria-hidden="true">${icon}</span> ${label}${detail ? html` <small>${detail}</small>` : ''}</span>`;
}

function time(iso) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString();
}

function storedHop(entry) {
  if (!entry.stored) return hop('wait', 'Storing');
  if (!entry.stored.ok) return hop('bad', 'Not stored', entry.stored.error);
  if (entry.stored.duplicate) return hop('ok', 'Already stored', 'duplicate sent again');
  const estimates = entry.stored.estimates?.length ?? 0;
  return hop('ok', 'Stored', estimates ? `${estimates} source estimates kept apart` : '');
}

function simulatorHop(entry) {
  const sim = entry.simulator;
  if (!sim) return hop('wait', 'Simulator');
  const [kind, label] = SIMULATOR[sim.status] ?? ['off', sim.status];
  const detail =
    sim.status === 'acknowledged'
      ? `${sim.reply} · ${sim.ms} ms`
      : sim.status === 'rejected'
        ? sim.reply
        : (sim.reason ?? '');
  return hop(kind, label, detail);
}

function fieldTable(entry) {
  if (!entry.fields?.length)
    return entry.sender === 'extended'
      ? html`<p class="form-hint">Classified by the sender itself (TraceLoft extension).</p>`
      : '';
  return html`<div class="table-wrap"><table><thead><tr><th>Sent</th><th>Value</th><th>Stored as</th><th>Why</th></tr></thead><tbody>${entry.fields.map(
    f =>
      html`<tr class="stored-${f.stored}"><td>${f.block}.${f.key}</td><td>${f.sent}</td><td>${STORED[f.stored] ?? f.stored}</td><td>${f.reason}</td></tr>`
  )}</tbody></table></div>`;
}

// The newest shots first; `open` holds the ids whose field table the golfer expanded.
export function confirmationList(diagnostics, open = new Set()) {
  if (!diagnostics?.length)
    return html`<p class="form-hint">No shots yet this run. Each shot's trail appears here.</p>`;
  return html`<ol class="shot-trail">${diagnostics.map(
    entry =>
      html`<li><div class="trail-head"><strong>Shot ${entry.shot_number ?? '?'}</strong><span>${time(entry.received_at)} · ${entry.device ?? 'unknown source'}${entry.profile ? html` · ${entry.profile}` : ''}</span></div><div class="trail-hops">${hop('ok', 'Received')}${storedHop(entry)}${simulatorHop(entry)}</div><details data-trail="${entry.id}" ${open.has(entry.id) ? 'open' : ''}><summary>Values and how they were stored</summary>${fieldTable(entry)}</details></li>`
  )}</ol>`;
}
