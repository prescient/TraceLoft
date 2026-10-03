import test from 'node:test';
import assert from 'node:assert/strict';
import {mappingRows,mappingCsv} from '../web/collection.js';
test('bag map uses effective equipment, included finite distances and type-7 quartiles',()=>{
 const plan=[{bag_id:'a',club_id:'6',club_label:'6 iron'},{bag_id:'a',club_id:'8',club_label:'8 iron'}];
 const s=(v,extra={})=>({vals:{carry:v},bag_id:'a',club_id:'6',...extra});
 const rows=mappingRows({range_metric:'carry',collection_plan:plan,shots:[s(100),s(110),s(120),s(1000,{excluded:true}),s(null),s(200,{removed:true}),s(0,{corrected_equipment:plan[1]}),s(999,{bag_id:'other'})]});
 assert.equal(rows[0].count,3);assert.equal(rows[0].median,110);assert.equal(rows[0].iqr,10);
 assert.equal(rows[1].count,1);assert.equal(rows[1].median,0);assert.equal(rows[1].iqr,null);
});

test('mapping CSV preserves missing fields and synthetic identity',()=>{
 const data={range_metric:'carry',demo:true,collection_plan:[{bag_id:'a',bag_name:'=unsafe',club_id:'x',club_label:'PW'}],shots:[]};
 const csv=mappingCsv(data);assert.ok(csv.includes('"median"'));assert.ok(csv.includes("'=unsafe"));assert.ok(csv.includes('"true"'));assert.ok(!csv.includes('undefined'));
});

import {matrixCells,matrixSuggestions,matrixCsv} from '../web/wedge-matrix.js';
test('matrix separates swing labels and requires sample coverage for suggestions',()=>{
 const eq={bag_id:'a',club_id:'w',club_label:'SW'},data={collection_plan:[eq],swing_labels:['Half','Full'],collection_samples:2,range_metric:'carry',shots:[{...eq,swing_label:'Half',vals:{carry:50}},{...eq,swing_label:'Half',vals:{carry:60}},{...eq,swing_label:'Full',vals:{carry:100}},{...eq,swing_label:'Full',vals:{carry:200},excluded:true}]};
 assert.deepEqual(matrixCells(data).map(c=>c.count),[2,1]);
 assert.equal(matrixSuggestions(data,90)[0].label,'Half');assert.equal(matrixSuggestions(data,90)[0].median,55);
 assert.ok(matrixCsv(data).includes('"Half"'));assert.deepEqual(matrixSuggestions(data,NaN),[]);
});
