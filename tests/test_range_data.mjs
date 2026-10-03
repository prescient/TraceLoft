import test from 'node:test';
import assert from 'node:assert/strict';
import {cohort,point,summarize,rangeCsv,equipment,clubColors,clubKey,robustSummary,clubSummaries,sourceValue,scatterCohort,dispersionCircles} from '../web/range-data.js';
const shots=[{key:'a',vals:{carry:0,total:8,offline:0},club_id:'pw',club_label:'PW',bag_id:'a',bag_name:'Bag',flight:{shape:'Straight',carry_point_yd:{forward:40,right:2},total_point_yd:{forward:50,right:4}}},
 {key:'b',vals:{carry:100,total:110,offline:null},club_id:'pw',bag_id:'a',excluded:true},
 {key:'c',vals:{carry:200},removed:true,corrected_equipment:{bag_id:'b',club_id:'9i',club_label:'9 iron'}},
 {key:'d',vals:{carry:null},club_id:'pw',bag_id:'a'}];
test('filter counts and analysis exclusions preserve missing values and valid zero',()=>{
  assert.deepEqual(cohort(shots,{status:'included'}).map(s=>s.key),['a','d']);
  assert.deepEqual(cohort(shots,{status:'removed',club:'9i'}).map(s=>s.key),['c']);
  assert.equal(summarize(shots).count,1);assert.equal(summarize(shots).mean,0);
  assert.equal(equipment(shots[2]).club_label,'9 iron');
  assert.deepEqual(cohort([...shots,{key:'e',vals:{}}],{status:'included',club:'__untagged__'}).map(s=>s.key),['e']);
});
test('carry and total use distinct model lateral coordinates, reported missing stays absent',()=>{
  assert.equal(point(shots[0],'carry','model').right,2);assert.equal(point(shots[0],'total','model').right,4);
  assert.deepEqual(point(shots[0],'carry','reported'),{forward:0,right:0});
  assert.equal(point(shots[1],'carry','reported'),null);
});
test('filtered CSV retains original/corrected tags, flags and formula-safe text',()=>{
  const csv=rangeCsv([{...shots[0],simulated:true,club_label:'=SUM(A1)',corrected_equipment:{club_label:'9 iron',bag_name:'Travel'}}]);
  assert.match(csv,/original_club/);assert.match(csv,/modeled_total_offline/);assert.match(csv,/'=SUM\(A1\)/);
  assert.match(csv,/9 iron/);assert.match(csv,/"true"/);assert.equal(csv.split('\r\n').length,2);
});

test('club colors distinguish bags and stay fixed through filtering, new shots and corrections',()=>{
  const a={bag_id:'bag',club_id:'7i',club_label:'7 iron'}, b={bag_id:'bag',club_id:'pw',club_label:'PW'};
  const c={bag_id:'other',club_id:'7i',club_label:'7 iron'};
  const base=[a,b,a,c,{}], colors=clubColors(base);
  assert.notEqual(colors.get(clubKey(a)),colors.get(clubKey(b)));
  assert.notEqual(colors.get(clubKey(a)),colors.get(clubKey(c)));
  const edited=base.map((s,i)=>i===0?{...s,removed:true,corrected_equipment:b}:s);
  const next=clubColors([...edited,{bag_id:'bag',club_id:'driver'}]);
  for(const s of base)assert.equal(next.get(clubKey(s)),colors.get(clubKey(s)));
  assert.equal(next.get(clubKey(equipment(edited[0]))),colors.get(clubKey(b)));
  assert.equal(clubKey({bag_id:'x'}),'untagged');
  assert.deepEqual([...clubColors(JSON.parse(JSON.stringify(base)))],[...colors]);
});

test('median and inclusive IQR resist one extreme reading and handle even sample sizes',()=>{
  const make=values=>values.map(carry=>({vals:{carry}}));
  assert.deepEqual(robustSummary(make([4,1,5,3,2]),'carry'),{count:5,median:3,q1:2,q3:4,iqr:2});
  assert.deepEqual(robustSummary(make([4,1,10000,3,2]),'carry'),{count:5,median:3,q1:2,q3:4,iqr:2});
  assert.deepEqual(robustSummary(make([10,20,30,40]),'carry'),{count:4,median:25,q1:17.5,q3:32.5,iqr:15});
});
test('robust metrics retain zero, omit missing/invalid/excluded values and mark single-shot spread unavailable',()=>{
  const records=[{vals:{offline:-20}},{vals:{offline:0}},{vals:{offline:10}},{vals:{offline:null}},
    {vals:{}},{vals:{offline:Infinity}},{vals:{offline:'8'}},{vals:{offline:999},excluded:true},{vals:{offline:999},removed:true}];
  assert.deepEqual(robustSummary(records,'offline',{absolute:true}),{count:3,median:10,q1:5,q3:15,iqr:10});
  assert.equal(robustSummary(records,'offline').median,0);
  assert.deepEqual(robustSummary([{vals:{launch_ang:0}}],'launch_ang'),{count:1,median:0,q1:null,q3:null,iqr:null});
  assert.equal(robustSummary(records,'descent_ang').median,null);
  assert.equal(robustSummary(records,'descent_ang').count,0);
});
test('club snapshot honors corrected membership and metric-specific counts without modeled fallbacks',()=>{
  const rows=clubSummaries([
    {bag_id:'b',bag_name:'Bag',club_id:'7',club_label:'7 iron',vals:{carry:100,offline:-8,launch_ang:20,descent_ang:40}},
    {bag_id:'b',club_id:'pw',corrected_equipment:{bag_id:'b',bag_name:'Bag',club_id:'7',club_label:'7 iron'},vals:{carry:120,offline:4,launch_ang:22},flight:{metrics:{descent_deg:80}}},
    {bag_id:'b',club_id:'7',vals:{carry:999},excluded:true},
    {bag_id:'b',club_id:'7',vals:{carry:999},removed:true},
  ]);
  assert.equal(rows.length,1);assert.equal(rows[0].count,2);assert.equal(rows[0].metrics[0].median,110);
  assert.equal(rows[0].metrics[2].median,6);assert.equal(rows[0].metrics[3].median,21);
  assert.equal(rows[0].metrics[4].count,1);assert.equal(rows[0].metrics[4].median,40);
  assert.equal(robustSummary([{simulated:true,vals:{descent:48}}],'descent_ang').median,48);
  assert.equal(robustSummary([{vals:{descent:48}}],'descent_ang').count,0);
  assert.equal(robustSummary([{simulated:true,vals:{descent_ang:0,descent:48}}],'descent_ang').median,0);
});

test('shot readings preserve zero and legacy demo descent without replacing missing source data',()=>{
  assert.equal(sourceValue(undefined,'total_spin'),undefined);
  assert.equal(sourceValue({vals:{total_spin:0}},'total_spin'),0);
  assert.equal(sourceValue({vals:{launch_ang:25}},'launch_ang'),25);
  assert.equal(sourceValue({vals:{},flight:{metrics:{descent_deg:48}}},'descent_ang'),undefined);
  assert.equal(sourceValue({vals:{descent:48}},'descent_ang'),undefined);
  assert.equal(sourceValue({simulated:true,vals:{descent:48}},'descent_ang'),48);
  assert.equal(sourceValue({simulated:true,vals:{descent_ang:0,descent:48}},'descent_ang'),0);
});

test('dispersion uses median centers and empirical 80% radii, ignoring exclusions and removals',()=>{
  const shots=[-2,-1,0,1,100].map((offline,i)=>({bag_id:'b',club_id:'7',vals:{carry:100,total:110,offline}}));
  const key=clubKey(shots[0]);
  const expected={count:5,forward:100,right:0,radius:2};
  assert.deepEqual(dispersionCircles(shots,'carry','reported').get(key),expected);
  assert.deepEqual(dispersionCircles([...shots,{...shots[0],excluded:true,vals:{carry:999,offline:999}},
    {...shots[0],removed:true,vals:{carry:999,offline:999}}],'carry','reported').get(key),expected);
  assert.deepEqual(dispersionCircles(shots.slice(0,4),'carry','reported').get(key),{count:4,radius:null});
  assert.equal(dispersionCircles(shots.map(s=>({...s,vals:{carry:0,offline:0}})),'carry','reported').get(key).radius,0);
});
test('dispersion separates bags, corrected tags and coordinate sources without imputing missing values',()=>{
  const a=Array.from({length:5},()=>({bag_id:'a',club_id:'7',vals:{carry:100,total:120,offline:2},
    flight:{carry_point_yd:{forward:90,right:-1},total_point_yd:{forward:105,right:3}}}));
  const b=a.map(s=>({...s,corrected_equipment:{bag_id:'b',club_id:'7'}}));
  const data=[...a,...b,{...a[0],vals:{carry:999,offline:null}},{vals:{carry:100,offline:0}}];
  const circles=dispersionCircles(data,'carry','reported');
  assert.equal(circles.size,2);assert.equal(circles.get(clubKey(a[0])).count,5);
  assert.equal(circles.get(clubKey(equipment(b[0]))).count,5);
  assert.equal(dispersionCircles(a,'total','reported').get(clubKey(a[0])).forward,120);
  assert.equal(dispersionCircles(a,'carry','model').get(clubKey(a[0])).right,-1);
  assert.equal(dispersionCircles(a,'total','model').get(clubKey(a[0])).right,3);
  assert.equal(dispersionCircles(a.map(s=>({...s,flight:null})),'carry','model').size,0);
});
test('default scatter retains excluded context while cleanup table and analysis remain included-only',()=>{
  const data=[{key:'a',bag_id:'b',club_id:'7'},{key:'b',bag_id:'b',club_id:'7',excluded:true},
    {key:'c',bag_id:'b',club_id:'7',removed:true},{key:'d',bag_id:'other',club_id:'7',excluded:true}];
  const filter={status:'included',bag:'b'};
  assert.deepEqual(cohort(data,filter).map(s=>s.key),['a']);
  assert.deepEqual(scatterCohort(data,filter).map(s=>s.key),['a','b']);
  assert.deepEqual(scatterCohort(data,{...filter,status:'excluded'}).map(s=>s.key),['b']);
  assert.deepEqual(scatterCohort(data,{...filter,status:'removed'}).map(s=>s.key),['c']);
  assert.deepEqual(scatterCohort(data,{...filter,status:'all'}).map(s=>s.key),['a','b','c']);
});
