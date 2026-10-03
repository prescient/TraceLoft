import test from 'node:test';
import assert from 'node:assert/strict';
import {gameScoreboard,aimReadout} from '../web/golf-sim.js';

const round=()=>({course:{par:4,pin:[0,350]},game:{strokes:5,penalties:1,concessions:1,holed:true,position:[0,349.5],aim:[0,350],lie:'green'},ended:'saved',shots:[
  {game_outcome:{applied:true}}, {game_outcome:{applied:true},excluded:true},
  {game_outcome:{applied:false}}, {game_outcome:{applied:true}},
]});

test('score explains three played shots plus penalty plus gimme; excluded strokes still count',()=>{
  const html=gameScoreboard(round());
  assert.match(html,/Hole 1 · Par 4/);
  assert.match(html,/Bogey · \+1/);
  assert.match(html,/3 played \+ 1 penalty \+ 1 gimme = 5 strokes/);
  assert.match(html,/Shots played<\/dt><dd>3/);
});

test('active and partial rounds do not imply a completed par result',()=>{
  const data=round();Object.assign(data.game,{strokes:2,penalties:0,concessions:0,holed:false});
  data.ended=null;
  assert.match(gameScoreboard(data),/In progress/);
  assert.doesNotMatch(gameScoreboard(data),/Eagle|final, unplayed/);
  data.ended='saved';assert.match(gameScoreboard(data),/Partial score/);
  Object.assign(data.game,{strokes:4,holed:true});assert.match(gameScoreboard(data),/Par · E/);
});

test('map distances measure both legs in world coordinates and switch to feet on the green',()=>{
  const data=round();
  Object.assign(data.game,{position:[0,200],aim:[30,240],lie:'fairway'});
  const html=aimReadout(data);
  assert.match(html,/Ball → aim<\/span><strong>50\.0 <small>yd/);
  assert.match(html,/Aim → pin<\/span><strong>114\.0 <small>yd/);
  Object.assign(data.game,{position:[0,345],aim:[3,349],lie:'green'});
  const green=aimReadout(data);
  assert.match(green,/Ball → aim<\/span><strong>15\.0 <small>ft/);
  assert.match(green,/Aim → pin<\/span><strong>9\.5 <small>ft/);
  data.game.aim=data.course.pin;
  assert.match(aimReadout(data),/Aim → pin<\/span><strong>0\.0 <small>ft/);
});
