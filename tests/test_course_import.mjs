import test from 'node:test';
import assert from 'node:assert/strict';
import {importMap} from '../web/course-import.js';
import {parseRoute,routeFor} from '../web/navigation.js';
test('import has stable route and explicit map boundaries',()=>{
  assert.equal(parseRoute('#play/import').view,'course-import');
  assert.equal(routeFor('course-import',{}),'#play/import');
  assert.equal(parseRoute('#play/import/extra'),null);
  const c={viewbox:[-20,-50,340,100],bounds:[-50,50,-20,320],pin:[0,300],surfaces:{green:[{outer:[[-10,290],[10,290],[10,310],[-10,310]],holes:[]}]},boundary:{outer:[[-50,-20],[50,-20],[50,320],[-50,320]],holes:[]}};
  const html=importMap(c);assert.match(html,/Imported hole preview/);assert.match(html,/course-boundaries/);assert.doesNotMatch(html,/<image|<pattern/);
});
