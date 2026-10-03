// Cosmetic materials only. Every shape comes from the round's saved course geometry.
const atlas='/assets/art/course-materials-v1.png';
const surfaces=[['rough',0,0,22,'#295448'],['fairway',1,0,36,'#51876b'],
  ['green',2,0,14,'#80ad78'],['sand',0,1,10,'#ddc590'],
  ['water',1,1,28,'#377c95'],['nature',2,1,42,'#183c32']];

export function courseLayers(c,{detailed=true,boundaries=false}={}) {
  if(c.surfaces)return polygonCourse(c,{detailed,boundaries});
  const [left,right,near,far]=c.bounds,xy=p=>`${p[1]},${p[0]}`;
  const rect=`x="${near}" y="${left}" width="${far-near}" height="${right-left}"`;
  const fill=name=>detailed?`url(#terrain-${name})`:surfaces.find(s=>s[0]===name)[4];
  const natureRects=[ [left,Math.min(right,-60)], [Math.max(left,60),right] ]
    .filter(([a,b])=>b>a).map(([a,b])=>`<rect x="${near}" y="${a}" width="${far-near}" height="${b-a}"/>`).join('');
  const shapes={
    fairway:`<polygon points="${c.fairway.map(xy).join(' ')}"/>`,
    green:`<circle cx="${c.pin[1]}" cy="${c.pin[0]}" r="${c.green_radius}"/>`,
    tee:`<circle cx="${c.tee[1]}" cy="${c.tee[0]}" r="4"/>`,
    water:c.water.map(h=>`<circle cx="${h.center[1]}" cy="${h.center[0]}" r="${h.radius}"/>`).join(''),
    sand:c.sand.map(h=>`<circle cx="${h.center[1]}" cy="${h.center[0]}" r="${h.radius}"/>`).join(''),
  };
  // Paint in classifier priority: water > sand > green > tee > fairway > nature/rough.
  return `<defs>${detailed?surfaces.map(([name,col,row,size,color])=>`<pattern id="terrain-${name}" patternUnits="userSpaceOnUse" width="${size}" height="${size}" viewBox="${col*512} ${row*512} 512 512"><rect x="${col*512}" y="${row*512}" width="512" height="512" fill="${color}"/><image href="${atlas}" x="0" y="0" width="1536" height="1024"/></pattern>`).join(''):''}
    <pattern id="terrain-mowing" patternUnits="userSpaceOnUse" width="18" height="18"><rect width="9" height="18" fill="#ffffff" opacity=".065"/></pattern>
    <clipPath id="terrain-fairway">${shapes.fairway}</clipPath>
    </defs><g class="course-terrain" aria-hidden="true" pointer-events="none">
    <rect x="${near-5}" y="${left-5}" width="${far-near+10}" height="${right-left+10}" fill="#132820"/>
    <rect ${rect} fill="${fill('rough')}"/>
    <g fill="${fill('nature')}">${natureRects}</g>
    <g fill="${fill('fairway')}">${shapes.fairway}</g>
    ${detailed?`<rect ${rect} fill="url(#terrain-mowing)" clip-path="url(#terrain-fairway)"/>`:''}
    <g fill="${fill('green')}">${shapes.tee}${shapes.green}</g>
    <g fill="${fill('sand')}" stroke="#ddc590" stroke-width=".35">${shapes.sand}</g>
    <g fill="${fill('water')}" stroke="#649899" stroke-width=".35">${shapes.water}</g>
    </g>${boundaries?`<g class="course-boundaries" aria-hidden="true" pointer-events="none" fill="none" stroke-width=".7" stroke-linejoin="round">
      <rect ${rect} stroke="#ff739c" stroke-dasharray="3 2"/>
      <g stroke="#dbbbff" stroke-dasharray="2 2">${natureRects}</g>
      <g stroke="#ffffff">${shapes.fairway}</g><g stroke="#e3ff6a">${shapes.green}${shapes.tee}</g>
      <g stroke="#ffcf70">${shapes.sand}</g><g stroke="#7cecff">${shapes.water}</g>
    </g>`:''}`;
}

export function polygonPath(p) {
  return [p.outer,...(p.holes??[])].map(r=>r.map((v,i)=>`${i?'L':'M'}${v[1]},${v[0]}`).join(' ')+' Z').join(' ');
}

function polygonCourse(c,{detailed,boundaries}) {
  const [left,right,near,far]=c.bounds;
  const order=['nature','fairway','tee','green','sand','water'];
  const colors={nature:'#193d2e',fairway:'#56834a',tee:'#91ae61',green:'#91ae61',sand:'#dfc799',water:'#155683'};
  const outlines={nature:'#dbbbff',fairway:'#fff',tee:'#e3ff6a',green:'#e3ff6a',sand:'#ffcf70',water:'#7cecff'};
  const paths=(name,extra)=>c.surfaces[name]?.map(p=>`<path d="${polygonPath(p)}" fill-rule="evenodd" ${extra}/>`).join('')??'';
  // A single registered aerial image; no repetition, rescaling of regions, or decorative hazards.
  const art=detailed&&c.image&&/^\/assets\/art\/[a-z0-9._-]+$/i.test(c.image.href)?
    `<image class="course-aerial" href="${c.image.href}" width="${c.image.width}" height="${c.image.height}" transform="matrix(${c.image.transform.join(' ')})"/>`:'';
  return `<g class="course-terrain" aria-hidden="true" pointer-events="none"><rect x="${near}" y="${left}" width="${far-near}" height="${right-left}" fill="#35543b"/>
    ${order.map(name=>paths(name,`fill="${colors[name]}"`)).join('')}${art}</g>
    ${boundaries?`<g class="course-boundaries" aria-hidden="true" pointer-events="none" fill="none" stroke-width=".65" stroke-linejoin="round">
    ${c.boundary?`<path d="${polygonPath(c.boundary)}" stroke="#ff739c" stroke-dasharray="3 2"/>`:''}
    ${order.map(name=>paths(name,`stroke="${outlines[name]}"`)).join('')}</g>`:''}`;
}
