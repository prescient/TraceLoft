import test from 'node:test';
import assert from 'node:assert/strict';
import {recordingWarnings} from '../web/recording.js';

const healthy={running:true,stopping:false,mode:'run',status:'waiting for shot',error:''};
test('healthy run needs no duplicate capture banner',()=>{
  assert.equal(recordingWarnings(healthy),'');
  assert.equal(recordingWarnings({...healthy,status:'Shot saved successfully'}),'');
});
test('stopped, preview and stopping keep recording warnings',()=>{
  assert.match(recordingWarnings({...healthy,running:false}),/shots are not being recorded/);
  assert.match(recordingWarnings({...healthy,mode:'preview'},'putts'),/Preview only/);
  assert.match(recordingWarnings({...healthy,stopping:true}),/Capture is stopping/);
});
test('unreadable distance, blocked table and signal loss are visible while running',()=>{
  for(const status of ['Waiting for a confident carry distance reading; target unchanged','Table dimmed — waiting for pop-up to close','Capture unavailable — waiting for signal','newest row unreadable for 5 s']) {
    const html=recordingWarnings({...healthy,status});assert.ok(html.includes(status));assert.match(html,/Check Capture diagnostics/);
  }
});
test('failure text is escaped and clears on a subsequent healthy snapshot',()=>{
  const failure=recordingWarnings({...healthy,error:'Disk <full> & retrying'});
  assert.match(failure,/role="alert"/);assert.match(failure,/&lt;full&gt;/);assert.match(failure,/&amp;/);
  assert.equal(recordingWarnings(healthy),'');
});
