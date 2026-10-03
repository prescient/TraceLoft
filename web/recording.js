import {escape as esc} from './charts.js';
export function recordingWarnings(source, noun='shots') {
  const title=!source.running?`Waiting for source — new ${noun} are not arriving.`:'';
  return `${title?`<div class="session-capture capture-warning" role="status"><strong>${esc(title)}</strong><span>Connect your shot source and check Relay before hitting.</span></div>`:''}${source.error?`<div class="session-error" role="alert">${esc(source.error)}</div>`:''}`;
}
