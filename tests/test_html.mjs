import test from 'node:test';
import assert from 'node:assert/strict';
import { html, raw, escape } from '../web/charts.js';

test('html escapes every interpolated value by default', () => {
  const name = `<img src=x onerror="alert('x')">&`;
  assert.equal(
    String(html`<b>${name}</b>`),
    '<b>&lt;img src=x onerror=&quot;alert(&#39;x&#39;)&quot;&gt;&amp;</b>'
  );
  assert.equal(String(html`<i>${42}</i>`), '<i>42</i>');
});

test('nested html and raw are not escaped twice', () => {
  const inner = html`<em>${'a<b'}</em>`;
  assert.equal(String(html`<p>${inner}</p>`), '<p><em>a&lt;b</em></p>');
  assert.equal(String(html`<p>${raw('<br>')}</p>`), '<p><br></p>');
});

test('arrays join, null/undefined render nothing, booleans render like template literals', () => {
  const items = ['x<', 'y'].map(item => html`<li>${item}</li>`);
  assert.equal(String(html`<ul>${items}</ul>`), '<ul><li>x&lt;</li><li>y</li></ul>');
  assert.equal(String(html`${null}${undefined}${''}`), '');
  assert.equal(String(html`${0}`), '0');
  // aria-pressed="${selected}" must keep rendering "false", exactly as before the migration.
  assert.equal(
    String(html`<b aria-pressed="${false}" hidden-state="${true}">`),
    '<b aria-pressed="false" hidden-state="true">'
  );
  assert.equal(`<b aria-pressed="${false}">`, String(html`<b aria-pressed="${false}">`));
});

test('an empty SafeHtml is truthy, so optional markup uses a ternary returning ""', () => {
  assert.ok(html``);
  assert.equal(String(html`${false ? html`<i>x</i>` : ''}`), '');
});

test('results work wherever a string is expected', () => {
  assert.equal(`${html`<b>${'&'}</b>`}`, '<b>&amp;</b>');
  assert.equal(escape(null), '');
});
