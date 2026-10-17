import test from 'node:test';
import assert from 'node:assert/strict';
import { confirmationList, profileControl } from '../web/relay-diagnostics.js';

const entry = (overrides = {}) => ({
  id: 'a1',
  received_at: '2026-10-17T16:00:00+00:00',
  device: 'DESKTOP-00UC2B2',
  shot_number: 17,
  sender: 'standard',
  profile: 'rela_lpi',
  fields: [
    { block: 'ClubData', key: 'Path', sent: -14.95, stored: 'measurement', reason: 'sent by the source' },
    { block: 'ClubData', key: 'FaceToTarget', sent: -13.5, stored: 'estimate', reason: 'rēlā estimate' },
  ],
  stored: { ok: true, duplicate: false, receipt_id: 'r', estimates: ['face_angle', 'carry'] },
  source_reply: { code: 200, message: 'Stored in TraceLoft' },
  simulator: { status: 'acknowledged', reply: '200 Shot received successfully', ms: 42 },
  ...overrides,
});

test('a shot trail shows each hop in words and the field classification (D74)', () => {
  const markup = String(confirmationList([entry()]));
  assert.match(markup, /Shot 17/);
  assert.match(markup, /hop hop-ok"><span aria-hidden="true">✓<\/span> Received/);
  assert.match(markup, /Stored <small>2 source estimates kept apart<\/small>/);
  assert.match(markup, /Acknowledged <small>200 Shot received successfully · 42 ms<\/small>/);
  assert.match(markup, /<td>ClubData.FaceToTarget<\/td><td>-13.5<\/td><td>Source estimate<\/td>/);
  assert.doesNotMatch(markup, /<details[^>]* open/);
  assert.match(String(confirmationList([entry()], new Set(['a1']))), /<details data-trail="a1" open>/);
});

test('refusals, silence and not-sent shots read as such, and text is escaped', () => {
  const refused = entry({
    stored: { ok: false, error: '<b>Units</b> must be Yards' },
    simulator: { status: 'not_sent', reason: 'Not stored' },
  });
  const silent = entry({ id: 'a2', simulator: { status: 'no_reply', reason: 'No reply within 5 s' } });
  const markup = String(confirmationList([refused, silent]));
  assert.match(markup, /hop-bad"><span aria-hidden="true">✕<\/span> Not stored/);
  assert.ok(markup.includes('&lt;b&gt;Units&lt;/b&gt;'));
  assert.match(markup, /Not sent <small>Not stored<\/small>/);
  assert.match(markup, /No reply <small>No reply within 5 s<\/small>/);
  assert.match(String(confirmationList([])), /No shots yet this run/);
});

test('the profile control marks the saved profile and explains it', () => {
  const profiles = [
    { id: 'standard', title: 'Standard Open Connect', description: 'All measured.' },
    { id: 'rela_lpi', title: 'rēlā · Foresight LPi', description: 'rēlā estimates kept apart.' },
  ];
  const markup = String(profileControl(profiles, 'rela_lpi'));
  assert.match(markup, /<option value="rela_lpi" selected>rēlā · Foresight LPi<\/option>/);
  assert.match(markup, /rēlā estimates kept apart/);
});
