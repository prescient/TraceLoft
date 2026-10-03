import test from 'node:test';
import assert from 'node:assert/strict';
import {courseLayers} from '../web/course-art.js';
import {courseMap} from '../web/golf-sim.js';
import {readFileSync} from 'node:fs';
import {renderPlay} from '../web/golf-sim.js';

test('original hole library selects each version and guards active sessions',()=>{
  const ids=['meadow-one-v2','willow-cove-155-v1','pine-bend-365-v1','meadow-reach-525-v1'];
  const courses=ids.map(id=>{const c=JSON.parse(readFileSync(new URL(`../courses/${id}.json`,import.meta.url)));return {...c,image:c.image.href};});
  const app={innerHTML:'',insertAdjacentHTML(_where,html){this.innerHTML+=html;}};
  renderPlay(app,{},courses);
  for(const id of ids)assert.ok(app.innerHTML.includes(`data-course="${id}"`));
  assert.equal((app.innerHTML.match(/class="card game-hole-card"/g)||[]).length,4);
  renderPlay(app,{practice:{id:'active',ended:null}},courses);
  assert.equal((app.innerHTML.match(/aria-label="Set up [^"]+" disabled/g)||[]).length,4);
  assert.match(app.innerHTML,/Return to active session/);
});

test('new hole overview, green zoom and fallback use identical saved registration',()=>{
  for(const id of ['willow-cove-155-v1','pine-bend-365-v1','meadow-reach-525-v1']){
    const c=JSON.parse(readFileSync(new URL(`../courses/${id}.json`,import.meta.url)));
    const data={course:c,game:{position:c.tee,aim:c.pin},shots:[],ended:null};
    const before=JSON.stringify(data);
    for(const zoom of [true,false]){
      const svg=courseMap(data,true,zoom,{boundaries:true});
      assert.ok(svg.includes(`transform="matrix(${c.image.transform.join(' ')})"`));
      assert.ok(svg.includes('class="course-boundaries"'));
      assert.doesNotMatch(svg,/>100 yd|>200 yd|>300 yd/);
      assert.doesNotMatch(courseMap(data,true,zoom,{detailed:false}),/<image/);
    }
    assert.equal(JSON.stringify(data),before);
  }
});

// Deliberately different saved geometry: artwork must follow the saved round, not a baked image.
const course={bounds:[-75,90,-10,400],tee:[2,3],pin:[4,360],green_radius:17,
  fairway:[[-12,3],[16,3],[9,355],[-18,350]],
  water:[{center:[-40,210],radius:19}],sand:[{center:[24,355],radius:9}]};
test('continuous aerial course uses one registered image and polygon outlines without tile patterns',()=>{
  const c=JSON.parse(readFileSync(new URL('../courses/meadow-one-v2.json',import.meta.url)));
  const art=courseLayers(c,{boundaries:true});
  assert.equal((art.match(/<image /g)||[]).length,1);
  assert.doesNotMatch(art,/<pattern|<circle/);
  assert.match(art,/transform="matrix\(/);
  assert.match(art,/class="course-boundaries"/);
  assert.doesNotMatch(courseLayers(c,{detailed:false}),/<image/);
});
test('terrain and diagnostic boundaries follow saved geometry and classifier priority',()=>{
  const html=courseLayers(course,{boundaries:true});
  assert.match(html,/x="-10" y="-75" width="410" height="165"/);
  assert.match(html,/points="3,-12 3,16 355,9 350,-18"/);
  for(const s of ['cx="360" cy="4" r="17"','cx="3" cy="2" r="4"',
    'cx="210" cy="-40" r="19"','cx="355" cy="24" r="9"']) assert.equal(html.split(s).length-1,2);
  const terrain=html.split('class="course-terrain"')[1].split('class="course-boundaries"')[0];
  assert.ok(terrain.indexOf('terrain-fairway')<terrain.indexOf('terrain-green'));
  assert.ok(terrain.indexOf('terrain-green')<terrain.indexOf('terrain-sand'));
  assert.ok(terrain.indexOf('terrain-sand')<terrain.indexOf('terrain-water'));
  assert.match(terrain,/y="60" width="410" height="30"/);
});
test('simple view and missing image retain surface colors; diagnostic layer is opt-in',()=>{
  const detailed=courseLayers(course),simple=courseLayers(course,{detailed:false});
  assert.doesNotMatch(detailed,/class="course-boundaries"/);
  assert.doesNotMatch(simple,/course-materials|<image/);
  for(const color of ['#295448','#51876b','#80ad78','#ddc590','#377c95','#183c32']) {
    assert.ok(simple.includes(color));assert.ok(detailed.includes(color));
  }
});
test('overview and green zoom share texture coordinates and never mutate saved state',()=>{
  const data={course,game:{position:[0,0],aim:[4,360]},shots:[],ended:null};
  const before=JSON.stringify(data);
  const hole=courseMap(data,true,false),green=courseMap(data,true,true,{boundaries:true});
  assert.match(hole,/viewBox="-20 -85 410 170"/);
  assert.match(green,/viewBox="336 -20 48 48"/);
  assert.match(hole,/cx="360" cy="4"/);assert.match(green,/cx="360" cy="4"/);
  assert.equal(JSON.stringify(data),before);
});
