import test from 'node:test';
import assert from 'node:assert/strict';
import { recordingWarnings as recordingWarningsMarkup } from '../web/recording.js';
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
test('old capture links resolve to Relay', () => {
  assert.equal(parseRoute('#capture').view, 'relay');
  assert.equal(parseRoute('#relay').view, 'relay');
});
