import { html } from './charts.js';
export function recordingWarnings(source, noun = 'shots') {
  const title = !source.running
    ? `Waiting for source — new ${noun} are not arriving.`
    : source.error
      ? `Recording needs attention — new ${noun} may not be saved.`
      : '';
  return title
    ? html`<div class="session-capture capture-warning" role="status"><strong>${title}</strong><span>Check Relay and your shot source before hitting.</span></div>`
    : '';
}

// The connected source's own problems, sent with its heartbeats (D73), shown under the header on
// every page. Colour is paired with a word: errors mean shots are not being recorded; warnings mean
// they are recorded but something else (the simulator) needs attention.
export function sourceAlerts(alerts) {
  if (!alerts?.length) return '';
  return html`${alerts.map(
    alert =>
      html`<p class="source-alert ${alert.level === 'error' ? 'error' : 'warning'}"><strong>${alert.level === 'error' ? 'Not recording' : 'Attention'}</strong> <span>${alert.message}</span></p>`
  )}`;
}
