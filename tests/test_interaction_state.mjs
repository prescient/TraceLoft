import test from 'node:test';
import assert from 'node:assert/strict';
import {preserveInteraction} from '../web/interaction-state.js';

function input({name='',value='',initial='',type='text',tagName='INPUT'}={}) {
  return {id:'',tagName,type,value,defaultValue:initial,disabled:false,
    attributes:[],getAttribute:key=>key==='name'?name:null,
    selectionStart:3,selectionEnd:5,selectionDirection:'backward',
    focus(options){this.focused=options;},setSelectionRange(...values){this.selection=values;}};
}
function root(controls,active) {
  return {controls,details:[{open:true},{open:false}],tables:[{scrollLeft:120,scrollTop:30}],
    ownerDocument:{activeElement:active,defaultView:{scrollX:0,scrollY:900,scrollTo(value){this.restored=value;}}},
    querySelectorAll(selector){return selector==='details'?this.details:selector==='.table-wrap'?this.tables:this.controls;}};
}
test('live repaint keeps drafts, selection, focus, expansion and scroll without reverting server controls',()=>{
  const old=input({name:'search',value:'draft',initial:''}),next=input({name:'search',value:'',initial:''});
  const oldCheckbox=input({name:'selected',type:'checkbox'}),nextCheckbox=input({name:'selected',type:'checkbox'});
  oldCheckbox.checked=true;nextCheckbox.checked=false;
  const r=root([old,oldCheckbox],old);
  preserveInteraction(r,()=>{r.controls=[next,nextCheckbox];r.details=[{open:false},{open:true}];r.tables=[{scrollLeft:0,scrollTop:0}];});
  assert.equal(next.value,'draft');assert.deepEqual(next.selection,[3,5,'backward']);assert.deepEqual(next.focused,{preventScroll:true});
  assert.equal(nextCheckbox.checked,false);assert.deepEqual(r.details.map(d=>d.open),[true,false]);assert.deepEqual(r.tables,[{scrollLeft:120,scrollTop:30}]);
  assert.deepEqual(r.ownerDocument.defaultView.restored,{left:0,top:900,behavior:'instant'});
});
test('modal focus outside the runner is never stolen by a same-name field',()=>{
  const old=input({name:'target'}),outside=input({name:'target',value:'170'}),next=input({name:'target',value:'150'});
  const r=root([old],outside);preserveInteraction(r,()=>{r.controls=[next];});
  assert.equal(next.focused,undefined);assert.equal(next.value,'150');
});
