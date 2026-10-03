import test from 'node:test';
import assert from 'node:assert/strict';
import {changeGeometry,editsFrom,editorMarkup} from '../web/course-editor.js';
const course=()=>({tee:[0,0],pin:[0,300],boundary:{outer:[[-80,-20],[80,-20],[80,350],[-80,350]],holes:[]},surfaces:{fairway:[{outer:[[-10,0],[10,0],[10,280],[-10,280]],holes:[[[0,20],[5,20],[5,30],[0,30]]]}],green:[],tee:[],sand:[],water:[],nature:[]}});
test('edits preserve source and interior rings through move/insert/delete',()=>{
  const c=course(),original=structuredClone(c),e=editsFrom(c);
  const moved=changeGeometry(e,{action:'move',kind:'fairway',index:0,ring:1,vertex:0,point:[1,21]});
  assert.deepEqual(c,original);assert.deepEqual(e,original);
  assert.deepEqual(moved.surfaces.fairway[0].holes[0][0],[1,21]);
  const inserted=changeGeometry(moved,{action:'insert',kind:'fairway',index:0,ring:1,vertex:0,point:[2,21]});
  assert.equal(inserted.surfaces.fairway[0].holes[0].length,5);
  const deleted=changeGeometry(inserted,{action:'delete',kind:'fairway',index:0,ring:1,vertex:1});
  assert.deepEqual(deleted,moved);
});
test('drawing and removal are isolated from tee/pin and keyboard controls exist',()=>{
  const e=editsFrom(course()),points=[[1,2],[3,4],[5,6]];
  const added=changeGeometry(e,{action:'add',kind:'water',points});
  assert.equal(added.surfaces.water.length,1);assert.equal(e.surfaces.water.length,0);
  const removed=changeGeometry(added,{action:'remove',kind:'water',index:0});assert.deepEqual(removed,e);
  assert.deepEqual(changeGeometry(e,{action:'pin',point:[3,300]}).pin,[3,300]);
  assert.match(editorMarkup(course()),/Precise coordinates/);assert.match(editorMarkup(course()),/Undo map edit/);
});
