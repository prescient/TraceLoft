import test from 'node:test';
import assert from 'node:assert/strict';
import {projectPoint,envelope,densityGrid,previewSvg} from '../web/club-preview.js';

test('rotation preserves short-club distance, lateral bias and ball translation',()=>{
  const p={forward:100,right:10};
  assert.deepEqual(projectPoint(p,[20,30],[20,350]),[30,130]);
  assert.deepEqual(projectPoint(p,[20,30],[350,30]),[120,20]);
  assert.deepEqual(projectPoint(p,[20,30],[20,40]),[30,130]);
  assert.equal(projectPoint(p,[20,30],[20,30]),null);
});
test('empirical outline resists one long miss but dots retain it',()=>{
  const p=[98,99,100,101,900].map(forward=>({forward,right:0}));
  assert.deepEqual(envelope(p),{forward:100,right:0,radius:2});
  assert.match(previewSvg(p,[0,0],[0,350],'outline'),/cx="900"/);
  assert.equal(previewSvg(p,[0,0],[0,350],'off'),'');
});
test('sparse and identical samples have honest finite renderings',()=>{
  const p=Array.from({length:5},()=>({forward:100,right:0}));
  assert.deepEqual(densityGrid(p.slice(0,4)),[]);
  assert.equal(envelope(p.slice(0,4)).radius,null);
  assert.equal(envelope(p).radius,0);
  const grid=densityGrid(p);
  assert.ok(grid.length>0&&grid.length<=96*96);
  assert.ok(grid.every(c=>Number.isFinite(c.intensity)&&c.intensity>0&&c.intensity<=1));
  assert.doesNotMatch(previewSvg(p,[0,0],[30,300],'density'),/NaN|Infinity/);
});
test('separated modes keep the empty gap instead of fitting one normal ellipse',()=>{
  const p=[98,99,100,101,102,198,199,200,201,202].map(forward=>({forward,right:forward<150?-10:10}));
  const grid=densityGrid(p);
  assert.ok(grid.some(c=>c.forward<110));assert.ok(grid.some(c=>c.forward>190));
  assert.ok(grid.every(c=>c.forward<130||c.forward>170));
});
test('one extreme miss cannot erase a compact central density',()=>{
  const p=[100,100,100,100,10000].map(forward=>({forward,right:0}));
  const grid=densityGrid(p);
  assert.ok(grid.some(c=>c.forward>98&&c.forward<102&&c.intensity>.8));
  assert.ok(grid.some(c=>c.forward>9998));
});
