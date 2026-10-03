import {escape as esc} from './charts.js';
export function recordingWarnings(source, noun='shots') {
  const title=!source.running?`Waiting for source — new ${noun} are not arriving.`:source.error?`Recording needs attention — new ${noun} may not be saved.`:'';
  return title?`<div class="session-capture capture-warning" role="status"><strong>${esc(title)}</strong><span>Check Relay and your shot source before hitting.</span></div>`:'';
}
