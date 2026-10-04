import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {courseCamera} from '../web/course-camera.js';

test('all current and legacy holes fill landscape cameras without changing scale or cropping the playing line',()=>{
  for(const id of ['pebble-boulder-blue-v1','sheboygan-straits-blue-v1','pebble-boulder-blue-v2','sheboygan-straits-blue-v2','pebble-boulder-blue-v3']){
    const packageData=JSON.parse(readFileSync(new URL(`../courses/${id}.json`,import.meta.url)));
    for(const c of packageData.holes){
      const before=JSON.stringify(c),[bx,by,bw,bh]=c.viewbox;
      for(const aspect of [2,2.35,2.6]){
        const [x,y,w,h]=courseCamera(c,{position:c.tee},false,aspect);
        assert.ok(Math.abs(w/h-aspect)<1e-8);
        assert.ok(x>=bx-1e-8&&y>=by-1e-8&&x+w<=bx+bw+1e-8&&y+h<=by+bh+1e-8);
        for(const p of [c.tee,c.pin,...c.playing_line])assert.ok(p[1]>=x&&p[1]<=x+w&&p[0]>=y&&p[0]<=y+h,`${id} hole ${c.hole_number}: overview point clipped`);
        const [gx,gy,gw,gh]=courseCamera(c,{position:c.pin},true,aspect);
        assert.ok(Math.abs(gw/gh-aspect)<1e-8);
        assert.ok(gx>=bx-1e-8&&gy>=by-1e-8&&gx+gw<=bx+bw+1e-8&&gy+gh<=by+bh+1e-8);
        assert.ok(c.pin[1]>gx&&c.pin[1]<gx+gw&&c.pin[0]>gy&&c.pin[0]<gy+gh);
      }
      assert.equal(JSON.stringify(c),before);
    }
  }
});

test('narrow overview keeps the whole saved course and legacy view remains supported',()=>{
  const c={tee:[0,0],pin:[0,350]};
  assert.deepEqual(courseCamera(c,{position:c.tee},false,1),[-20,-85,410,170]);
  assert.ok(courseCamera(c,{position:c.pin},true,1).every(Number.isFinite));
});
