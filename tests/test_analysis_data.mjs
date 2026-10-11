import {test} from 'node:test';
import assert from 'node:assert/strict';
import {robust,timeline,cohorts,histogram,matchesRanges,comparison,configureColors,color} from '../web/analysis-data.js';
const row=(key,v,date='2026-10-01',config='a')=>({key,session_id:date,session_started:date+'T12:00:00Z',captured:date+'T13:00:00Z',drill:'Range',bag_id:'bag',bag_name:'My bag',club_id:'7i',club_label:'7 iron',swing_label:'',lineage:{configuration_id:config},values:{carry:v,launch:18}});
test('calendar buckets aggregate readings, not session medians; configurations stay distinct',()=>{
  const rows=[row('1',100),row('2',200),row('3',300),row('4',900,'2026-10-02'),row('5',500,'2026-10-02','b')];
  const t=timeline(rows,['carry'],'week');assert.equal(t.points.length,1);assert.equal(t.series.length,2);
  assert.equal(t.series[0].points[0].metrics.carry.median,250);assert.equal(t.series[0].points[0].metrics.carry.count,4);
  assert.equal(cohorts(rows).length,2);
});
test('missing measurements and capture timestamps stay unavailable',()=>{
  const rows=[row('1',null),{...row('2',200),captured:null}];assert.equal(robust([null,200]).median,200);assert.equal(robust([200]).iqr,null);
  const t=timeline(rows,['carry'],'shot');assert.equal(t.missingTime,1);assert.equal(t.series[0].points[0].metrics.carry.count,0);
});
test('histogram bins partition exact boundaries and predicates preserve missingness',()=>{
  const rows=[0,1,2,3,4,5,6,7,8].map((v,i)=>row(''+i,v));const bins=histogram(rows,'carry',8);
  assert.equal(bins.reduce((s,b)=>s+b.count,0),9);
  for(const b of bins)assert.equal(rows.filter(r=>matchesRanges(r,{carry:{min:b.min,max:b.max}})).length,b.count);
  assert.equal(matchesRanges(row('n',null),{carry:{min:0}}),false);
});
test('comparison uses separate configurations, per-metric n, native delta and missing cohorts',()=>{
  const c=comparison([row('1',100),row('2',120)],[row('3',150),row('4',900,'2026-10-02','b')],['carry','missing']);
  assert.equal(c.length,2);assert.equal(c[0].metrics[0].delta,40);assert.equal(c[0].metrics[1].delta,null);assert.equal(c[1].metrics[0].before.count,0);
});
test('bag/club colors survive narrowed filters and newly discovered clubs',()=>{
  const first=configureColors({one:{bag:'b',label:'7 iron'},two:{bag:'b',label:'9 iron'}});
  assert.notEqual(color('bone'),color('btwo'));const before=color('bone');
  const narrowed=configureColors({two:{bag:'b',label:'9 iron'}},first);assert.equal(color('bone'),before);
  configureColors({new:{bag:'a',label:'Driver'},one:{bag:'b',label:'7 iron'}},narrowed);assert.equal(color('bone'),before);
});
test('selected calculation versions separate analytical cohorts while source readings remain comparable',()=>{
  const a={...row('a',100),basis:'flight',lineage:{configuration_id:'a',flight_model_version:'v1'}};
  const b={...row('b',110),basis:'flight',lineage:{configuration_id:'a',flight_model_version:'v2'}};
  assert.equal(cohorts([a,b]).length,2);
  assert.equal(cohorts([{...a,basis:'source'},{...b,basis:'source'}]).length,1);
  const result=comparison([a],[b],['carry']);
  assert.equal(result.length,2);assert.ok(result.every(c=>c.metrics[0].delta===null));
});
