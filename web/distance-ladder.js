import {escape as esc, error, direction, distanceTrend, progress} from './charts.js';
import {equipmentControls, bindEquipment} from './equipment.js';
import {recordingWarnings} from './recording.js';

const button=(text,action,kind='',extra='')=>`<button class="btn ${kind}" data-action="${action}" ${extra}>${text}</button>`;
const number=v=>Number.isFinite(v)?v.toFixed(1).replace(/\.0$/,''):'—';
const field=(name,label,value,extra='')=>`<label class="field">${label}<input name="${name}" type="number" value="${value}" ${extra} required></label>`;

export function renderDistanceSetup(app, old, launch, notice, equipment) {
  app.innerHTML=`<div class="page-head"><div><h1>Distance ladder</h1><p class="subtitle">Build distance control with wedges and irons.</p></div>${button('← Back to Practice','home','quiet')}</div>
    <div class="range-presets" aria-label="Distance presets">${['wedges','irons','custom'].map(p=>`<button type="button" class="btn" data-range-preset="${p}" aria-pressed="false">${p[0].toUpperCase()+p.slice(1)}</button>`).join('')}</div>
    <form id="range-form" class="range-setup"><section class="card"><h2>Build your ladder</h2><p class="subtitle">Set your targets and how you want to run it.</p><input type="hidden" name="range_category" value="${esc(old.range_category??'wedges')}">
    <label class="field">Distance to score<select name="range_metric"><option value="carry" ${old.range_metric!=='total'?'selected':''}>Carry (yd)</option><option value="total" ${old.range_metric==='total'?'selected':''}>Total (yd)</option></select></label><div class="form-grid section-space">
    ${field('range_start','Shortest target (yd)',old.range_start??30,'min="1" max="600" step="1"')}
    ${field('range_end','Longest target (yd)',old.range_end??100,'min="1" max="600" step="1"')}
    ${field('range_step','Step (yd)',old.range_step??10,'min="1" max="600" step="1"')}
    ${field('range_shots','Shots per target',old.range_shots??1,'min="1" max="100" step="1"')}
    ${field('range_rounds','Rounds',old.range_rounds??2,'min="1" max="100" step="1"')}
    ${field('range_tolerance','Distance window (± yd)',old.range_tolerance??5,'min="0" max="100" step="0.5"')}
    <label class="field">Order<select name="range_order"><option value="ascending" ${old.range_order!=='descending'?'selected':''}>Ascending · short to long</option><option value="descending" ${old.range_order==='descending'?'selected':''}>Descending · long to short</option></select></label>
    <label class="field">Session label (optional)<input name="range_club" maxlength="80" placeholder="e.g. Wedge distance control" value="${esc(old.range_club??'')}"></label></div>${equipmentControls(equipment.catalog(),old.equipment_selection,true)}</section>
    <section class="card range-preview"><h2>Your ladder</h2><p class="subtitle">Here are your targets for this session.</p><div id="range-preview" aria-live="polite"></div><p class="model-note">Advance after the configured shots per target, including misses. Missing or invalid distance does not advance the ladder. Exclusions affect analysis, not progression.</p><p class="model-note">Uses the selected source-reported distance. Your source must supply that measurement. Bag and club tags are saved per shot.</p><button class="btn primary range-launch" type="submit">Launch ladder →</button></section></form>`;
  const form=app.querySelector('form'), controls=form.elements;
  function params() {
    return Object.fromEntries([...new FormData(form)].map(([k,v])=>[k,k.match(/^range_(start|end|step|shots|rounds|tolerance)$/)?Number(v):v]));
  }
  function preview() {
    const p=params(), intervals=(p.range_end-p.range_start)/p.range_step;
    const count=Math.round(intervals)+1, total=count*p.range_shots*p.range_rounds;
    const limit=p.range_metric==='carry'?450:600;
    const valid=Object.values(p).every(v=>typeof v!=='number'||Number.isFinite(v)) && p.range_start>=1 && p.range_end>p.range_start && p.range_end<=limit && p.range_step>=1 && intervals>=1 && Math.abs(intervals-Math.round(intervals))<1e-8 && total<=1000 && p.range_shots>=1 && Number.isInteger(p.range_shots) && p.range_rounds>=1 && Number.isInteger(p.range_rounds);
    const targets=valid?Array.from({length:count},(_,i)=>p.range_start+i*p.range_step):[];
    if(p.range_order==='descending')targets.reverse();
    app.querySelector('#range-preview').innerHTML=valid?`<div class="range-preview-grid"><ol class="preview-rungs">${targets.slice(0,12).map((t,i)=>`<li class="${i===0?'current':''}"><span class="rung-dot"></span><strong>${number(t)} <small>yd</small></strong></li>`).join('')}${count>12?`<li>+ ${count-12} more targets</li>`:''}</ol><div class="range-plan"><p>${count} targets × ${p.range_shots} shot${p.range_shots===1?'':'s'} × ${p.range_rounds} round${p.range_rounds===1?'':'s'}</p><strong>${total} shots</strong><p>Each target: ± ${number(p.range_tolerance)} yd</p><p>Needs a valid ${esc(p.range_metric)} reading.</p></div></div>`:`<p class="session-error" role="alert">Choose a range from 1–${limit} yd and a step that divides it evenly. Use whole shots/rounds with at most 1000 shots.</p>`;
    app.querySelector('.range-launch').disabled=!valid;
    app.querySelectorAll('[data-range-preset]').forEach(b=>{const selected=b.dataset.rangePreset===p.range_category;b.classList.toggle('primary',selected);b.setAttribute('aria-pressed',String(selected));});
  }
  app.querySelectorAll('[data-range-preset]').forEach(b=>b.onclick=()=>{
    controls.range_category.value=b.dataset.rangePreset;
    if(b.dataset.rangePreset!=='custom') {
      controls.range_start.value=b.dataset.rangePreset==='wedges'?30:90;
      controls.range_end.value=b.dataset.rangePreset==='wedges'?100:170;
      controls.range_step.value=10;
    }
    preview();
  });
  form.oninput=e=>{if(['range_start','range_end','range_step'].includes(e.target.name))controls.range_category.value='custom';preview();};
  form.onchange=preview;
  form.onsubmit=async e=>{e.preventDefault();const b=app.querySelector('.range-launch');b.disabled=true;try{await launch({drill:'Distance ladder',...params()});}catch(err){notice(err.message);b.disabled=false;}};
  bindEquipment(app,equipment,null);
  preview();
}

export function distanceRunner(data, summary, state, isReview, selectedShot, sessionNotice) {
  const active=!isReview&&!data.ended;
  const shots=data.shots, latest=shots.at(-1), shown=shots.find(s=>s.key===selectedShot)??latest;
  const shownIndex=shown?shots.indexOf(shown)+1:null, metric=data.range_metric==='carry'?'Carry':'Total';
  const targets=data.ladder_targets_yd, position=active?data.completed_shots:Math.max(0,data.completed_shots-1);
  const rung=Math.floor(position/data.range_shots)%targets.length+1;
  const round=Math.min(data.range_rounds,Math.floor(position/(targets.length*data.range_shots))+1);
  const target=active?data.target:latest?.target_distance_yd??data.target;
  const result=!shown?'Waiting':shown.excluded?'Excluded':!shown.scored?'Unscored':shown.success?'In window':'Outside window';
  const miss=shown&&!shown.excluded&&(!shown.scored||!shown.success);
  const err=shown?.distance_error_yd;
  return `<div class="page-head"><div><h1>${isReview?'Session review':'Distance ladder'}</h1><p class="subtitle">${esc(data.range_category[0].toUpperCase()+data.range_category.slice(1))}${data.range_club?' · '+esc(data.range_club):''} · ${metric} · ${data.range_order==='ascending'?'Ascending':'Descending'}${isReview?' · Saved session':data.ended?' · Complete':''}</p></div><div class="head-actions">${active?button('Relay','relay','quiet')+button('End session','finish','danger'):''}${isReview?button('Practice selector','home','quiet'):''}${button(isReview?'Exit review':'Exit session','exit-session',active?'quiet':'primary')}${!active?button('⚙ Edit targets','edit','quiet'):''}</div></div>
  ${!active?sessionNotice(data,isReview):''}${state.practice_error&&!isReview?`<div class="session-error" role="alert">${esc(state.practice_error)}</div>`:''}
  ${active?`<div id="recording-feedback">${recordingWarnings(state.capture)}</div>`:''}
  ${active?`<section class="card equipment-card" aria-label="Tag upcoming shots">${equipmentControls(state.equipment,data.equipment_selection)}</section>`:''}
  ${latest&&!latest.scored?`<div class="session-capture capture-warning" role="status"><strong>${esc(latest.unscored_reason)}</strong><span>Shot retained in the log; check the selected distance measurement in Relay.</span></div>`:''}
  <div class="distance-heroes"><section class="card"><div class="eyebrow">${shown===latest?'LATEST SHOT':`SHOT ${shownIndex}`}</div><div class="range-latest"><div><div class="range-value">${number(shown?.distance_yd)}</div><p>${metric} · yd</p></div><div><div class="range-value">${err==null?'—':error(err)}</div><p>yd${err==null?'':err< -1e-9?' · short':err>1e-9?' · long':' · on target'}</p></div><div><div class="range-outcome ${miss?'miss-text':shown?.excluded?'':'success-text'}">${result}</div><p>Ball speed ${number(shown?.vals.ball_speed)} mph</p><p>${shown?.scored?`Target ${number(shown.target_distance_yd)} yd`:'Distance unavailable until captured'}</p></div></div><div class="metric-foot">${shown?`Shot ${shownIndex}${shown.club_label?' · '+esc(shown.bag_name?shown.bag_name+' / '+shown.club_label:shown.club_label):''} · ${shown.excluded?'Excluded from analysis':'Saved automatically'}`:'Waiting for a new shot with a valid distance reading.'}</div></section>
  <section class="card"><div class="eyebrow">${active?'NEXT TARGET':data.abandoned?'SESSION ABANDONED':'LAST TARGET'}</div><div class="range-next"><div class="range-value">${number(target)} <small>yd</small></div><div><strong>${number(Math.max(0,target-data.range_tolerance))}–${number(target+data.range_tolerance)} yd window</strong><p>${active?'Rung':'Last scored rung'} ${rung} / ${targets.length} · Round ${round} / ${data.range_rounds}</p><div class="progress-row">${progress(data.completed_shots,data.repetitions,'shots')}</div><p>${data.completed_shots} / ${data.repetitions} scored shots · ${summary.successes} / ${summary.count} in window</p></div></div></section></div>
  <div class="range-rungs" aria-label="Ladder progress for round ${round}">${targets.map((t,i)=>{
    const attempts=shots.filter(s=>s.ladder_round===round&&s.ladder_rung===i+1&&s.scored), included=attempts.filter(s=>!s.excluded), failed=included.some(s=>!s.success), complete=attempts.length>=data.range_shots;
    const current=active&&i+1===rung, label=current?'In progress':!attempts.length?'Not started':!included.length?'Excluded':failed?`${included.filter(s=>!s.success).length} miss${included.filter(s=>!s.success).length===1?'':'es'}`:complete?'In window':'Recorded';
    return `<div class="range-rung ${current?'current':''} ${failed?'miss':complete&&included.length?'done':''}"><strong>${i+1} · ${number(t)} yd</strong><span class="rung-state">${complete?failed?'×':included.length?'✓':'—':'○'}</span><span>${attempts.length} / ${data.range_shots}</span><span>${label}</span></div>`;
  }).join('')}</div>
  <div class="graphs"><section class="card"><div class="eyebrow">${metric.toUpperCase()} VS TARGET</div><p class="graph-subtitle">source-reported ${metric.toLowerCase()} (yd) · per-shot target window</p><div class="legend"><span><i class="swatch"></i>± ${data.range_tolerance} yd</span><span><i class="line-swatch"></i>Target</span></div>${distanceTrend(data)}</section><section class="card"><div class="eyebrow">DISTANCE ERROR</div><p class="graph-subtitle">Short is negative · long is positive · yd</p><div class="legend"><span><i class="swatch"></i>± ${data.range_tolerance} yd tolerance</span></div>${distanceTrend(data,true)}</section></div>
  <section class="card"><div class="table-head"><div class="eyebrow">SHOT LOG</div><span class="top-hint">Latest first · select a shot to review or exclude</span></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Bag</th><th>Club</th><th>Target (yd)</th><th>${metric} (yd)</th><th>Error (yd)</th><th>Ball speed (mph)</th><th>Start line</th><th>Result</th></tr></thead><tbody>${shots.length?shots.map((s,i)=>({s,i})).reverse().map(({s,i})=>`<tr data-key="${esc(s.key)}" tabindex="0" aria-label="Select shot ${i+1}" class="${i===shots.length-1?'latest-row':''} ${s.excluded?'excluded':''} ${selectedShot===s.key?'selected':''}"><td>${i+1}</td><td>${esc(s.bag_name)||'—'}</td><td>${esc(s.club_label)||'—'}</td><td>${number(s.target_distance_yd)}</td><td>${number(s.distance_yd)}</td><td>${s.distance_error_yd==null?'—':error(s.distance_error_yd)}</td><td>${number(s.vals.ball_speed)}</td><td>${direction(s.vals.launch_dir)}</td><td class="${s.excluded?'':s.success?'success-text':'miss-text'}">${s.excluded?'Excluded':!s.scored?'Unscored':s.success?'● In window':'● Outside window'}</td></tr>`).join(''):'<tr><td colspan="9" class="empty">No recorded shots yet.</td></tr>'}</tbody></table></div><div class="table-actions">${button('Exclude / include selected','exclude','small',!selectedShot?'disabled':'')}${active?button('Abandon session','abandon','danger quiet small'):button('Delete session','delete-review','danger quiet small')}${isReview?button('Practice selector','home','quiet small'):''}${button(isReview?'Exit review':'Exit session','exit-session','quiet small')}</div><details class="details"><summary>Session statistics</summary><p>${summary.count} included scored shots · ${summary.successes} in window · ${summary.unscored} unscored<br>${summary.distance_error_yd.count?`Distance error ${summary.distance_error_yd.mean.toFixed(2)} ± ${summary.distance_error_yd.sd.toFixed(2)} yd · ${summary.distance_error_yd.short} short / ${summary.distance_error_yd.long} long`:'No scored distance readings yet.'}<br>Mean ± population standard deviation. Exclusion does not rewind the ladder.</p></details></section>
  <p class="model-note">Scored using source-reported ${metric.toLowerCase()}. Offline and launch data are context, not scored. Missing distance is unavailable, not zero. Bag and club are manually selected for upcoming shots.</p>`;
}
