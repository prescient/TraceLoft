import {escape as esc} from './charts.js';
import {format as fmt} from './range-data.js';

const PREVIEW_BLUE='#35c7ff';

const preferences=new Map();
const selectedProfiles=new Map();
export const quantile=(values,p)=>{
  const v=[...values].sort((a,b)=>a-b),i=(v.length-1)*p,lo=Math.floor(i);
  return v.length?v[lo]+(i-lo)*((v[lo+1]??v[lo])-v[lo]):null;
};

// World coordinates are [right, forward]. Aim changes bearing, never club distance.
export function projectPoint(point,position,aim) {
  const dx=aim[0]-position[0],dy=aim[1]-position[1],length=Math.hypot(dx,dy);
  if(length<.001)return null;
  return [position[0]+point.forward*dx/length+point.right*dy/length,
    position[1]+point.forward*dy/length-point.right*dx/length];
}

export function envelope(points) {
  if(!points.length)return null;
  const forward=quantile(points.map(p=>p.forward),.5),right=quantile(points.map(p=>p.right),.5);
  const radii=points.map(p=>Math.hypot(p.forward-forward,p.right-right)).sort((a,b)=>a-b);
  return {forward,right,radius:points.length>=5?radii[Math.ceil(.8*points.length)-1]:null};
}

// Compact product kernels smooth observed paired endpoints; no normal-cloud assumption.
// Independent yard-space bandwidths retain lateral/distance asymmetry and correlation.
export function densityGrid(points) {
  if(points.length<5)return [];
  const bandwidth=key=>Math.max(2,Math.min(14,(quantile(points.map(p=>p[key]),.75)-quantile(points.map(p=>p[key]),.25))*.8*Math.pow(points.length,-1/6)));
  const bf=bandwidth('forward'),br=bandwidth('right');
  // Visit only each sample's kernel support. A distant miss must not coarsen
  // the entire grid and erase a tight cluster between widely spaced grid centers.
  const df=bf/4,dr=br/4,cells=new Map();let max=0;
  for(const p of points){
    const cx=Math.floor(p.forward/df),cy=Math.floor(p.right/dr);
    for(let ox=-4;ox<=4;ox++)for(let oy=-4;oy<=4;oy++){
        const x=cx+ox,y=cy+oy;
        const u=((x+.5)*df-p.forward)/bf,v=((y+.5)*dr-p.right)/br;
        if(Math.abs(u)>=1||Math.abs(v)>=1)continue;
        const key=`${x}:${y}`,cell=cells.get(key)??{forward:x*df,right:y*dr,width:df,height:dr,value:0};
        cell.value+=(1-u*u)*(1-v*v);max=Math.max(max,cell.value);cells.set(key,cell);
      }
  }
  return [...cells.values()].map(c=>({...c,intensity:c.value/max}));
}

export function previewSvg(points,position,aim,mode) {
  if(mode==='off'||!points.length||!projectPoint(points[0],position,aim))return '';
  const bearing=Math.atan2(aim[0]-position[0],aim[1]-position[1])*180/Math.PI;
  const center=envelope(points),round=v=>Number(v.toFixed(3));
  const color=PREVIEW_BLUE;
  const heat=mode==='density'?densityGrid(points).map(c=>`<rect x="${round(c.forward)}" y="${round(c.right)}" width="${round(c.width+.015)}" height="${round(c.height+.015)}" fill="${color}" opacity="${round(.92*c.intensity)}"/>`).join(''):'';
  const ringShape=`cx="${round(center.forward)}" cy="${round(center.right)}" r="${round(center.radius??0)}" fill="none" vector-effect="non-scaling-stroke"`;
  const ring=center.radius===null?'':`<circle ${ringShape} stroke="#092b45" stroke-width="5" stroke-opacity=".85"/><circle ${ringShape} stroke="${color}" stroke-width="3"/>`;
  const dots=points.map(p=>`<circle cx="${round(p.forward)}" cy="${round(p.right)}" r=".9" fill="${color}" stroke="#102431" stroke-width=".35"/>`).join('');
  return `<g transform="translate(${position[1]} ${position[0]}) rotate(${bearing})" pointer-events="none">${heat}${ring}${dots}<path d="M ${center.forward-2},${center.right} l2,-2 l2,2 l-2,2 Z" fill="#fff" stroke="#102431" stroke-width=".7"><title>Median mapped endpoint</title></path></g>`;
}

export function mountClubPreview(app,data,state,ctx,active) {
  const host=app.querySelector('#club-preview'),layer=app.querySelector('#club-preview-layer');
  if(!host||!layer)return;
  if(!active||data.game.lie==='green'){
    host.innerHTML=`<p class="form-hint">${!active?'Historical review · planning overlay is available in an active round.':'Putting · full-swing preview is hidden on the green.'}</p>`;return;
  }
  const equipment=data.equipment_selection??{};
  if(!equipment.club_id){host.innerHTML='<p class="form-hint">Select a bag and club above to see its mapped dispersion.</p>';return;}
  const key=JSON.stringify([data.id,equipment.bag_id,equipment.club_id]);
  const pref=preferences.get(data.id)??{mode:'density',source:'reported',metric:'total'};
  preferences.set(data.id,pref);
  host.innerHTML='<p class="form-hint" role="status">Loading mapped dispersion…</p>';
  ctx.preview().then(payload=>{
    if(!host.isConnected)return;
    if(payload.equipment?.club_id!==equipment.club_id||payload.equipment?.bag_id!==equipment.bag_id){host.textContent='Equipment changed. Select your club again to refresh the preview.';return;}
    if(!payload.profiles.length){host.innerHTML=`<p class="form-hint">No ${data.demo?'demo':'real'} mapping for ${esc(equipment.club_label)} yet. Collect paired distance and offline readings in <a href="#setup/bag-mapping">Bag mapping</a> or <a href="#setup/wedge-matrix">Wedge matrix</a>. Your round stays active.</p>`;return;}
    const draw=()=>{
      const profile=payload.profiles.find(p=>p.id===selectedProfiles.get(key))??payload.profiles[0];selectedProfiles.set(key,profile.id);
      const view=profile.views[`${pref.source}_${pref.metric}`],points=view.points,stats=view.distance;
      const disabledCarry=pref.source==='reported',small=points.length<20;
      host.innerHTML=`<div class="preview-heading"><div><h3>Club dispersion <span class="preview-info"><button class="info-button" aria-label="About club dispersion" aria-expanded="false">i</button><span class="preview-help" role="tooltip">Historical paired endpoints from included mapping attempts, before lie reductions. Brighter shading means more nearby samples, not a future-shot probability. Dots below 5 samples; smoothing and a descriptive 80% radial outline from 5. Under 20 is a small sample. The white diamond is the median endpoint. Reused shots count once per mapping session. Aim rotates the cloud without stretching distance. Preview settings do not change shot tags or scoring.</span></span></h3><span class="form-hint">${esc(equipment.bag_name)} / ${esc(equipment.club_label)} · ${data.demo?'DEMO':'REAL'} PROFILE</span></div></div>
      <div class="preview-controls"><label class="field">Mapping / swing profile<select data-preview="profile" aria-label="Mapping / swing profile">${payload.profiles.map(p=>`<option value="${esc(p.id)}" ${p.id===profile.id?'selected':''}>${esc(p.label)}</option>`).join('')}</select></label><label class="field">Endpoint source<select data-preview="source" aria-label="Endpoint source"><option value="reported" ${pref.source==='reported'?'selected':''}>${data.demo?'Synthetic':'Reported'} total + offline</option><option value="model" ${pref.source==='model'?'selected':''}>OpenGolfCoach estimate</option></select></label></div>
      <div class="preview-switches"><div class="segmented" role="group" aria-label="Preview distance">${['total','carry'].map(m=>`<button class="btn small ${pref.metric===m?'primary':''}" data-preview-metric="${m}" aria-pressed="${pref.metric===m}" ${m==='carry'&&disabledCarry?'disabled title="Carry requires paired OpenGolfCoach endpoints"':''}>${m==='total'?'Total':'Carry'}</button>`).join('')}</div><div class="segmented" role="group" aria-label="Dispersion display">${['density','outline','off'].map(m=>`<button class="btn small ${pref.mode===m?'primary':''}" data-preview-mode="${m}" aria-pressed="${pref.mode===m}">${m[0].toUpperCase()+m.slice(1)}</button>`).join('')}</div></div>
      <div class="preview-readout" role="status"><strong>${fmt(stats.median)} yd <small>median down aim</small></strong><span>Middle 50%: ${fmt(stats.q1)}–${fmt(stats.q3)} yd</span><span>${points.length} plotted · ${profile.excluded} excluded · ${profile.removed} removed${view.missing?' · '+view.missing+' missing paired data':''}</span></div>
      <p class="form-hint preview-context">${pref.mode==='off'?'Overlay off. ':points.length===0?'No compatible paired endpoints. ':points.length<5?'Dots only · collect 5 paired endpoints for a heatmap. ':small?'Small sample · descriptive spread only. ':''}Unadjusted mapped spread · lie reduction and extra variation are not applied.${pref.source==='reported'?` ${esc(payload.geometry)} geometry; Carry needs OpenGolfCoach endpoints.`:' OpenGolfCoach 0.3.0 · flat, no wind; uncalibrated.'}${view.date_from?` ${esc(view.date_from)} to ${esc(view.date_to)}.`:''}</p>`;
      layer.innerHTML=previewSvg(points,data.game.position,data.game.aim,pref.mode);
      if(!projectPoint({forward:0,right:0},data.game.position,data.game.aim))host.querySelector('.preview-context').textContent='Aim away from the ball to display dispersion.';
      // Report off-screen endpoints instead of squeezing club distance to the viewport.
      const bounds=app.querySelector('.game-map').viewBox.baseVal;
      const outside=points.map(p=>projectPoint(p,data.game.position,data.game.aim)).filter(p=>p&&(p[1]<bounds.x||p[1]>bounds.x+bounds.width||p[0]<bounds.y||p[0]>bounds.y+bounds.height)).length;
      if(outside&&pref.mode!=='off')host.querySelector('.preview-context').append(` ${outside} endpoints outside this map view; use Hole view or change aim.`);
      host.querySelectorAll('[data-preview]').forEach(el=>el.onchange=()=>{if(el.dataset.preview==='profile')selectedProfiles.set(key,el.value);else pref[el.dataset.preview]=el.value;if(pref.source==='reported')pref.metric='total';draw();host.querySelector(`[data-preview="${el.dataset.preview}"]`).focus({preventScroll:true});});
      for(const type of ['metric','mode'])host.querySelectorAll(`[data-preview-${type}]`).forEach(el=>el.onclick=()=>{pref[type]=el.dataset[type==='metric'?'previewMetric':'previewMode'];draw();host.querySelector(`[data-preview-${type}="${pref[type]}"]`).focus({preventScroll:true});});
      const info=host.querySelector('.info-button');info.onclick=()=>{const open=info.getAttribute('aria-expanded')!=='true';info.setAttribute('aria-expanded',String(open));};
      info.onkeydown=e=>{if(e.key==='Escape')info.setAttribute('aria-expanded','false');};
    };draw();
  }).catch(error=>{if(host.isConnected)host.textContent=`Club preview unavailable: ${error.message}`;});
}
