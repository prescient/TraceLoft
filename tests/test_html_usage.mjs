import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';

// Static guards for the escape-by-default rule in web/*.js (see CLAUDE.md).
const web = new URL('../web/', import.meta.url);
const sources = readdirSync(web)
  .filter(name => name.endsWith('.js'))
  .map(name => ({ name, text: readFileSync(new URL(name, web), 'utf8') }))
  // Blank out comment lines (keeping line numbers) so documentation examples are not flagged.
  .map(({ name, text }) => ({ name, text: text.replace(/^\s*(\/\/|\/?\*).*$/gm, '') }));
const line = (text, index) => text.slice(0, index).split('\n').length;
const offenders = pattern =>
  sources.flatMap(({ name, text }) => [...text.matchAll(pattern)].map(m => `${name}:${line(text, m.index)}`));

test('every markup template literal uses the html tag', () => {
  // A backtick template that starts with a tag must be html`...`, so its values are escaped.
  assert.deepEqual(offenders(/(?<!html)`\s*<[a-zA-Z/!]/g), []);
});

test('optional markup uses a ternary, not cond && html`` (false renders as text)', () => {
  assert.deepEqual(offenders(/&&\s*html`/g), []);
});

test('modules escape through html, not hand-written escape calls', () => {
  const manual = sources.filter(
    ({ name, text }) => name !== 'charts.js' && /\bescape as esc\b|\besc\(/.test(text)
  );
  assert.deepEqual(
    manual.map(s => s.name),
    []
  );
});
