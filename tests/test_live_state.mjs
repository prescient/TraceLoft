import test from 'node:test';
import assert from 'node:assert/strict';
import {createLiveStateController, isStaleState} from '../web/live-state.js';

const deferred = () => {let resolve, reject; const promise = new Promise((a,b)=>{resolve=a;reject=b;}); return {promise,resolve,reject};};
const flush = () => new Promise(resolve=>setImmediate(resolve));
const stamp = (revision, epoch='server-a') => ({epoch,revision});
const message = (revision, epoch) => ({type:'state_changed',...stamp(revision,epoch)});
function fixture() {
  const requests=[], applied=[], errors=[];
  const controller=createLiveStateController({fetchState:()=>{const r=deferred();requests.push(r);return r.promise;},apply:s=>applied.push(s.live),onError:e=>errors.push(e.message)});
  return {controller,requests,applied,errors};
}

test('burst notifications coalesce and superseded responses never repaint',async()=>{
  const f=fixture();f.controller.notify(message(1));f.controller.notify(message(2));f.controller.notify(message(3));
  assert.equal(f.requests.length,1);f.requests[0].resolve({live:stamp(1)});await flush();
  assert.deepEqual(f.applied,[]);assert.equal(f.requests.length,2);
  f.requests[1].resolve({live:stamp(3)});await flush();
  assert.deepEqual(f.applied,[stamp(3)]);f.controller.notify(message(2));f.controller.notify(message(3));await flush();assert.equal(f.requests.length,2);
});
test('closed socket responses and errors are ignored',async()=>{
  for (const fail of [false,true]) {const f=fixture();f.controller.notify(message(1));f.controller.dispose();if(fail)f.requests[0].reject(Error('closed'));else f.requests[0].resolve({live:stamp(1)});await flush();assert.deepEqual(f.applied,[]);assert.deepEqual(f.errors,[]);}
});
test('new server epoch supersedes the old request',async()=>{
  const f=fixture();f.controller.notify(message(50));f.controller.notify(message(1,'server-b'));f.requests[0].resolve({live:stamp(50)});await flush();
  assert.deepEqual(f.applied,[]);f.requests[1].resolve({live:stamp(1,'server-b')});await flush();assert.deepEqual(f.applied,[stamp(1,'server-b')]);
});
test('fetch errors or a mismatched epoch request reconnect; invalid notices do nothing',async()=>{
  const f=fixture();f.controller.notify({type:'state_changed',epoch:'a',revision:-1});assert.equal(f.requests.length,0);
  f.controller.notify(message(1));f.requests[0].reject(Error('network'));await flush();assert.deepEqual(f.errors,['network']);
  f.controller.notify(message(2));f.requests[1].resolve({live:stamp(1,'other')});await flush();assert.match(f.errors[1],/reconnecting/);
});
test('action responses cannot replace a newer snapshot; restarting resets revisions',()=>{
  assert.equal(isStaleState({live:stamp(8)},{live:stamp(7)}),true);
  assert.equal(isStaleState({live:stamp(8)},{live:stamp(1,'new')}),false);
  assert.equal(isStaleState({live:stamp(8)},{live:stamp(8)}),false);
  assert.equal(isStaleState({live:stamp(8)},{}),false);
});
