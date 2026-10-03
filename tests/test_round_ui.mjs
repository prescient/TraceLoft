import test from 'node:test';
import assert from 'node:assert/strict';
import {holeShots,reviewHoleData,roundScorecard} from '../web/round-ui.js';
import {gameScoreboard,courseMap} from '../web/golf-sim.js';
const holes=Array.from({length:18},(_,i)=>({id:`h${i}`,hole_number:i+1,name:`Hole ${i+1}`,par:4,yards:350,tee:[0,0],pin:[0,350],fairway:[],sand:[],water:[]}));
const game={position:[0,350],aim:[0,350],lie:'green',strokes:5,penalties:1,concessions:1,holed:true};
const data=()=>({id:'r',course:holes[1],round:{holes,index:1,results:[{hole_id:'h0',hole_number:1,par:4,game}],name:'Pebble Boulder',tee_label:'Blue',yards:6300,par:72},game:{...game,strokes:2,holed:false},shots:[{hole_id:'h0',game_outcome:{applied:true}},{hole_id:'h1',game_outcome:{applied:true}},{hole_id:'h1',game_outcome:{applied:false}}]});
test('round score adds current partial without claiming holes or par completed',()=>{
 const html=roundScorecard(data());
 assert.match(html,/<strong>7<\/strong>/);assert.match(html,/1\/18 holes complete/);assert.match(html,/\+1 on completed holes/);assert.match(html,/2\*/);
});
test('review switches frozen holes without mutating current state; unplayed holes stay empty',()=>{
 const d=data(),before=structuredClone(d),first=reviewHoleData(d,0);
 assert.equal(first.course.id,'h0');assert.equal(first.game.strokes,5);assert.equal(holeShots(first).length,1);
 assert.equal(reviewHoleData(d,2).game.strokes,0);assert.deepEqual(d,before);
 assert.match(roundScorecard(d,true,0),/value="0" selected/);
 assert.match(gameScoreboard(d),/Shots played<\/dt><dd>1/);
 assert.equal(holeShots({...d,round:undefined}).length,3);
});
