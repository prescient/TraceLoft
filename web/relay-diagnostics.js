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

// The Relay status strip (D75): the three links a golfer cares about, each with a dot and words —
// the shot source, recording in TraceLoft, and the simulator.
export function statusItems(state) {
  const input = state.input ?? {},
    relay = state.relay ?? {},
    practice = state.practice;
  const profile = (state.input_profiles ?? []).find(p => p.id === input.profile);
  const sourceName = input.profile === 'rela_lpi' ? 'rēlā' : input.device || 'Shot source';
  const source = !input.connected
    ? ['bad', sourceName, 'Not connected']
    : state.capture?.running
      ? ['ok', sourceName, 'Connected · ready']
      : ['wait', sourceName, 'Connected · not ready'];
  const active = practice && !practice.ended;
  const recording = state.practice_error
    ? ['bad', 'TraceLoft', 'Save failed — see the alert']
    : active
      ? ['ok', 'TraceLoft', `Recording · ${practice.quick_range ? 'Quick range' : practice.drill}`]
      : input.quick_range
        ? ['ok', 'TraceLoft', 'Ready · a Quick range starts with the next shot']
        : ['wait', 'TraceLoft', 'Recording without a session (not in Sessions or Analyze)'];
  const names = { gspro: 'GSPro', infinite_tees: 'Infinite Tees' };
  const sim = names[relay.destination] ?? 'Simulator';
  const simulator = !relay.enabled
    ? ['off', 'Simulator', 'Off · record only']
    : relay.delegated
      ? ['ok', sim, 'Sent directly by the shot source']
      : !relay.connected
        ? ['bad', sim, 'Not connected']
        : relay.answering === false
          ? ['bad', sim, 'Not answering']
          : relay.answering
            ? ['ok', sim, 'Answering']
            : ['ok', sim, 'Connected · answers with the next shot'];
  return [source, recording, simulator].map(([kind, name, text]) => ({ kind, name, text, profile: profile?.title }));
}

// Simulator replies this run by code (D77), e.g. "Replies: 200 ×9 · 201 ×3", or '' before any.
export function replyCounts(relay = {}) {
  const codes = Object.entries(relay.reply_codes ?? {}).sort(([a], [b]) => Number(a) - Number(b));
  return codes.length ? `Replies: ${codes.map(([code, n]) => `${code} ×${n}`).join(' · ')}` : '';
}

export function statusStrip(state) {
  return html`<ol class="relay-status" aria-label="Shot path status">${statusItems(state).map(
    item =>
      html`<li class="status-${item.kind}"><span class="status-dot" aria-hidden="true"></span><strong>${item.name}</strong><span>${item.text}</span></li>`
  )}</ol>`;
}

// Voice club selection (D76): on/off, listening state, the last thing heard, and the phrases known.
export function voicePanel(voice = {}) {
  const status = !voice.available
    ? html`<p class="form-hint">Not installed yet. ${voice.missing ?? ''}</p>`
    : voice.error
      ? html`<p class="session-error" role="alert">${voice.error}</p>`
      : voice.enabled
        ? html`<p class="voice-status ${voice.listening ? 'listening' : ''}"><span class="status-dot" aria-hidden="true"></span>${voice.listening ? 'Listening on this PC’s microphone. Say a club, e.g. “seven iron”.' : 'Starting the microphone…'}</p>`
        : html`<p class="form-hint">Off. Clubs are chosen by tapping.</p>`;
  const phrases = voice.phrases ?? [];
  return html`<label class="collection-option"><input type="checkbox" id="voice-toggle" ${voice.enabled ? 'checked' : ''} ${voice.available ? '' : 'disabled'}>Choose clubs by voice (this PC’s microphone, offline)</label>${status}${voice.message ? html`<p class="voice-heard" role="status">${voice.message}</p>` : ''}${
    phrases.length
      ? html`<details class="details"><summary>Phrases it knows (${phrases.length})</summary><p class="form-hint">${phrases.join(' · ')}</p></details>`
      : voice.available
        ? html`<p class="form-hint">Choose a bag (or keep one bag) so voice knows your clubs.</p>`
        : ''
  }`;
}

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
