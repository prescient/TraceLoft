import test from 'node:test';
import assert from 'node:assert/strict';
import {
  confirmationList,
  profileControl,
  replyCounts,
  statusItems,
  statusStrip,
  voicePanel,
} from '../web/relay-diagnostics.js';

test('simulator replies are counted by code in code order (D77)', () => {
  assert.equal(replyCounts({}), '');
  assert.equal(replyCounts({ reply_codes: { 202: 4, 200: 9, 201: 3 } }), 'Replies: 200 ×9 · 201 ×3 · 202 ×4');
});

test('the voice panel says when it is not installed, listening, and what it heard (D76)', () => {
  const missing = String(voicePanel({ available: false, missing: 'Needs the vosk package.' }));
  assert.match(missing, /id="voice-toggle"\s+disabled/);
  assert.match(missing, /Not installed yet. Needs the vosk package./);
  const on = String(
    voicePanel({
      available: true,
      enabled: true,
      listening: true,
      message: '"seven iron" → 7 iron for the next shot',
      phrases: ['putter', 'seven iron']
    })
  );
  assert.match(on, /checked/);
  assert.match(on, /voice-status listening/);
  assert.match(on, /→ 7 iron for the next shot/);
  assert.match(on, /Phrases it knows \(2\)/);
});

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

test('the status strip names each link with words beside the colour (D75)', () => {
  const base = {
    input: { profile: 'rela_lpi', connected: true, quick_range: true },
    capture: { running: true },
    relay: { enabled: true, destination: 'gspro', connected: true, answering: true },
    practice: { drill: 'Driving range', quick_range: true, ended: false }
  };
  assert.deepEqual(
    statusItems(base).map(i => [i.kind, i.name, i.text]),
    [
      ['ok', 'rēlā', 'Connected · ready'],
      ['ok', 'TraceLoft', 'Recording · Quick range'],
      ['ok', 'GSPro', 'Answering']
    ]
  );
  const broken = {
    ...base,
    input: { profile: 'standard', connected: false, quick_range: false, device: 'Monitor' },
    practice: null,
    relay: { enabled: true, destination: 'gspro', connected: true, answering: false }
  };
  assert.deepEqual(
    statusItems(broken).map(i => [i.kind, i.text]),
    [
      ['bad', 'Not connected'],
      ['wait', 'Recording without a session (not in Sessions or Analyze)'],
      ['bad', 'Not answering']
    ]
  );
  const off = { ...base, practice: null, relay: { enabled: false } };
  assert.deepEqual(statusItems(off).slice(1).map(i => i.text), [
    'Ready · a Quick range starts with the next shot',
    'Off · record only'
  ]);
  assert.match(String(statusStrip(base)), /<li class="status-ok"><span class="status-dot" aria-hidden="true"><\/span><strong>GSPro<\/strong><span>Answering<\/span><\/li>/);
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
