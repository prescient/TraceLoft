import test from 'node:test';
import assert from 'node:assert/strict';
import {shotMotion,motionFrame,MotionClock} from '../web/shot-motion.js';

const shot=()=>({key:'a:1',vals:{carry:180,total:200,offline:-12},flight:{status:'ready',metrics:{hang_time_s:5,carry_yd:190,total_yd:210},carry_point_yd:{forward:190,right:-10},total_point_yd:{forward:210,right:-12},trajectory:[{t:0,x:0,y:0,z:0},{t:2.5,x:80,y:-6,z:30},{t:5,x:170,y:-9,z:0}]}});
test('source endpoints anchor modeled airborne shape with original hang time, then roll',()=>{
  const s=shot(),before=JSON.stringify(s),p=shotMotion(s);
  assert.equal(p.airTime,5);assert.ok(p.duration>5);
  assert.equal(motionFrame(p,5).x,180);assert.equal(motionFrame(p,5).z,0);
  assert.equal(motionFrame(p,999).x,200);assert.equal(motionFrame(p,999).y,-12);
  assert.equal(motionFrame(p,2.5).z,30/.9144);
  assert.equal(JSON.stringify(s),before);
});
test('missing model uses honest endpoint-only timing; missing all distances stays unavailable',()=>{
  const s=shot();delete s.flight;const p=shotMotion(s);
  assert.equal(p.airTime,0);assert.match(p.label,/flight unavailable/);
  assert.equal(shotMotion({vals:{}}),null);
  assert.equal(shotMotion({...s,removed:true}),null);
  delete s.vals.offline;assert.equal(shotMotion(s).directionKnown,false);
});
test('invalid carry and model estimates cannot create NaN or reverse rollout',()=>{
  const s=shot();s.vals.carry=230;
  const p=shotMotion(s);assert.ok(p.points.every(p=>Object.values(p).every(Number.isFinite)));
  assert.equal(p.total,200);assert.match(p.label,/Source total/);
  assert.ok(p.carry<=p.total);
  s.flight.metrics.hang_time_s=NaN;assert.equal(shotMotion(s).airTime,0);
});
test('Play replay follows frozen game endpoint despite heading, lie reduction and penalty',()=>{
  const s=shot();s.game_outcome={applied:true,before:{position:[20,30]},endpoint:[130,19],after:{position:[20,30]},aim_heading_degrees:90,random_degrees:2,distance_factor:.8,penalty_strokes:1};
  const before=JSON.stringify(s),p=shotMotion(s,true);
  assert.deepEqual([p.points[0].y,p.points[0].x],[20,30]);
  assert.deepEqual([p.points.at(-1).y,p.points.at(-1).x],[130,19]);
  assert.equal(JSON.stringify(s),before);
  assert.equal(shotMotion({...s,game_correction:{kind:'misread'}},true),null);
  s.game_outcome.applied=false;assert.equal(shotMotion(s,true),null);
});
test('putting stays on ground, ends at scored endpoint and never adds an animated gimme',()=>{
  const s=shot();s.game_outcome={applied:true,putting:true,before:{position:[0,100]},endpoint:[1,103],conceded_strokes:1};
  const p=shotMotion(s,true);assert.equal(p.airTime,0);
  assert.ok(p.points.every(p=>p.z===0));assert.equal(p.points.at(-1).x,103);
});
test('clock baselines initial entry, plays one latest arrival, preserves redraw time, skips reduced motion',()=>{
  const c=new MotionClock(),p=shotMotion(shot());
  c.observe('range','old',p,true,0);assert.equal(c.playing(0),false);
  c.observe('range','new',p,true,100);assert.equal(c.playing(100),true);
  c.observe('range','new',p,true,2000);assert.equal(c.started,100);
  c.observe('range','batch-last',p,true,2100);assert.equal(c.started,2100);
  c.observe('range','batch-last',null,true,2200);assert.equal(c.playing(2200),false);
  c.observe('range','reduced',p,true,2300,true);assert.equal(c.playing(2300),false);
  c.reset();c.observe('range','reduced',p,true,2400);assert.equal(c.playing(2400),false);
  c.observe('other-hole','first',p,true,2500);assert.equal(c.playing(2500),false);
});
