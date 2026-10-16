import test from 'node:test';
import assert from 'node:assert/strict';
import { recordingWarnings as recordingWarningsMarkup, sourceAlerts } from '../web/recording.js';
import { parseRoute } from '../web/navigation.js';
// Markup helpers return SafeHtml (a String object); compare their text.
const recordingWarnings = (...args) => String(recordingWarningsMarkup(...args));
test('source readiness is independent of simulator output', () => {
  assert.equal(recordingWarnings({ running: true, error: '' }), '');
  assert.match(recordingWarnings({ running: false }, 'putts'), /new putts are not arriving/);
});
test('raw diagnostics stay out of practice', () => {
  const html = recordingWarnings({ running: true, error: 'sensitive raw details' });
  assert.match(html, /Recording needs attention/);
  assert.ok(!html.includes('sensitive raw details'));
});
test('source alerts say what to do, pair colour with a word and escape the message (D73)', () => {
  assert.equal(String(sourceAlerts([])), '');
  assert.equal(String(sourceAlerts(undefined)), '');
  const markup = String(
    sourceAlerts([
      { level: 'error', message: "rēlā isn't connected to TraceCapture. Press Connect in rēlā." },
      { level: 'warning', message: "GSPro isn't answering. <b>Restart</b> GSPro Connect." },
    ])
  );
  assert.match(markup, /class="source-alert error"><strong>Not recording<\/strong>/);
  assert.match(markup, /class="source-alert warning"><strong>Attention<\/strong>/);
  assert.match(markup, /Press Connect in rēlā/);
  assert.ok(markup.includes('&lt;b&gt;Restart&lt;/b&gt;'));
  assert.ok(!markup.includes('<b>'));
});
test('old capture links resolve to Relay', () => {
  assert.equal(parseRoute('#capture').view, 'relay');
  assert.equal(parseRoute('#relay').view, 'relay');
});
