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
