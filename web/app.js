import {renderPlay,renderGameSetup,renderGame} from './golf-sim.js';
import {renderCourseImport} from './course-import.js';
import {renderAnalyze} from './analyze.js';
import {renderCollectionSetup} from './collection.js';
import {categorizedDrills,categoryMarkup,bindCategories} from './practice-categories.js';
import {escape as esc, direction, error, trend, gauge, progress} from './charts.js';
import {parseRoute, routeFor} from './navigation.js';
import {renderDistanceSetup, distanceRunner} from './distance-ladder.js';
import {bindEquipment, refreshSetupEquipment} from './equipment.js';
import {recordingWarnings} from './recording.js';
import {renderRangeSetup,renderRange} from './driving-range.js';

const app = document.querySelector('#app'), connection = document.querySelector('#connection');
let state=null, drills=[], view='choose', selectedDrill=null, review=null, selectedShot=null, socket=null, renderKey='', online=false;
let sessionList=[], sessionListRequest=0, sessionMode='all';
let abandonedSession=null;
let navigationRequest=0;
let courses=[];

function notice(message, undo=null) {
  const box=document.querySelector('#notice');
  box.hidden=false; box.innerHTML=`<span>${esc(message)}</span>${undo?'<button class="btn small" data-undo>Undo</button>':''}<button class="dismiss" aria-label="Dismiss message">×</button>`;
  box.querySelector('.dismiss').onclick=()=>box.hidden=true;
  if(undo)box.querySelector('[data-undo]').onclick=async event=>{event.target.disabled=true;try{await undo();}catch(e){notice(e.message);}};
}
function confirmAction(title,message,label) {
  if(document.querySelector('#session-confirm'))return Promise.resolve(false);
  return new Promise(resolve=>{
    const dialog=document.createElement('dialog');dialog.id='session-confirm';dialog.className='confirm-dialog';
    dialog.setAttribute('aria-labelledby','confirm-title');dialog.setAttribute('aria-describedby','confirm-description');
    dialog.innerHTML=`<form method="dialog"><h2 id="confirm-title">${esc(title)}</h2><p id="confirm-description">${esc(message)}</p><div class="confirm-actions"><button class="btn quiet" value="cancel" autofocus>Cancel</button><button class="btn danger" value="confirm">${esc(label)}</button></div></form>`;
    dialog.addEventListener('close',()=>{const confirmed=dialog.returnValue==='confirm';dialog.remove();resolve(confirmed);},{once:true});
    document.body.append(dialog);dialog.showModal();
  });
}
async function deleteSession(data) {
  if(!await confirmAction('Delete session?',`${data.drill} · ${date(data.started)} · ${data.captured??data.shots.length} recorded ${shotWord(data)}. Remove this session from your list? You can restore it from Recently deleted.`, 'Delete session'))return;
  state=await api(`/api/sessions/${data.id}`,null,'DELETE');review=null;setView('sessions');
  notice('Session deleted.',async()=>{state=await api(`/api/sessions/${data.id}/restore`,{});setView('sessions');notice('Session restored.');});
}
async function api(path, body, method) {
  const response=await fetch(path,{method:method??(body?'POST':'GET'),credentials:'same-origin',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
  const data=await response.json();
  if (!response.ok) {
    const error=new Error(Array.isArray(data.detail)?data.detail.map(d=>`${d.loc.at(-1)}: ${d.msg}`).join('; '):data.detail??'Request failed');
    error.status=response.status;throw error;
  }
  return data;
}
const button=(text,action,kind='',extra='')=>`<button class="btn ${kind}" data-action="${action}" ${extra}>${text}</button>`;
const date=value=>new Date(value).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});
const shotWord=data=>data?.practice_type==='full_swing'?'shots':'putts';
const equipmentContext={catalog:()=>state.equipment,notice,save:async(path,body,method)=>update(await api(path,body,method))};

function setView(next, {replace=false}={}) {
  navigationRequest++;
  const route=routeFor(next,{practice:state?.practice,review,drill:selectedDrill});
  if(location.hash!==route)history[replace?'replaceState':'pushState'](null,'',route);
  view=next; selectedShot=null;renderKey='';render();window.scrollTo({top:0,behavior:'instant'});
}
async function openRoute(hash) {
  const ticket=++navigationRequest, route=parseRoute(hash);
  let nextReview=null;
  try {
    if(!route){review=null;setView('choose',{replace:true});return;}
    if(route.view==='runner') {
      if(route.review||state.practice?.id!==route.sessionId){
        const saved=await api(`/api/sessions/${route.sessionId}`);
        if(ticket!==navigationRequest)return;
        nextReview=saved;
      }
    }else if(route.view==='setup') {
      if(state.practice&&!state.practice.ended){review=null;setView('choose',{replace:true});notice('End or abandon the active session before setting up another drill.');return;}
      const drill=drills.find(d=>d.id===route.drillId);
      let parameters;
      if(route.sessionId){
        parameters=(await api(`/api/sessions/${route.sessionId}`)).practice;
        if(ticket!==navigationRequest)return;
      }
      selectedDrill={...drill,parameters:parameters??drill.defaults};
    }
    // An old live-session link becomes a saved review once a different drill owns capture.
    review=nextReview;
    setView(route.view,{replace:true});
  }catch(e){
    if(ticket!==navigationRequest)return;
    review=null;
    setView(route?.view==='runner'?'sessions':'choose',{replace:true});
    notice(e.status===404?'This session is no longer available. Choose another session.':e.message);
  }
}
function navigation() {
  const section=view==='course-import'?'play':['relay','play','analyze','sessions'].includes(view)?view:view==='runner'&&review?'sessions':view==='runner'&&state.practice?.session_kind==='golf_sim'||view==='setup'&&selectedDrill?.id==='golf-sim'?'play':'practice';
  document.querySelectorAll('[data-nav]').forEach(b=>{const active=b.dataset.nav===section;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  connection.classList.toggle('offline',!online||!state?.capture.running);
  connection.querySelector('span:last-child').textContent=!online?'Reconnecting':state?.capture.running?'Source ready':'Waiting for source';
}
function update(next) {
  const previousSession=JSON.stringify([state?.practice?.id,state?.practice?.ended]);
  const sessionsChanged=state?.sessions_revision!==next.sessions_revision;
  const equipmentChanged=state?.equipment?.revision!==next.equipment?.revision;
  state=next; navigation();
  if (view==='relay') updateRelay();
  else if(view==='sessions'&&sessionsChanged)renderSessions();
  else if(view==='play'&&previousSession!==JSON.stringify([state.practice?.id,state.practice?.ended]))renderPlay(app,state,courses);
  else if(view==='choose'&&previousSession!==JSON.stringify([state.practice?.id,state.practice?.ended])) renderChoose();
  else if(view==='setup'&&equipmentChanged)refreshSetupEquipment(app,equipmentContext);
  else if (view==='runner') {
    if(review&&sessionsChanged)refreshReview();
    const key=JSON.stringify([review??state.practice,review?.summary??state.summary,state.equipment?.revision,(review?.practice??state.practice)?.session_kind==='golf_sim'?state.sessions_revision:null,state.practice_error,state.capture.running,state.capture.stopping]);
    if (key!==renderKey) { renderKey=key;renderRunner(); }
    const feedback=app.querySelector('#recording-feedback');
    if(feedback){const html=recordingWarnings(state.capture,shotWord(review?.practice??state.practice));if(feedback.innerHTML!==html)feedback.innerHTML=html;}
  }
}
async function refreshReview() {
  const id=review.practice.id;
  try {
    const next=await api(`/api/sessions/${id}`);
    if(view==='runner'&&review?.practice.id===id){review=next;renderRunner();}
  }catch(e){
    if(view==='runner'&&review?.practice.id===id&&e.status===404){review=null;setView('sessions');notice('This session was deleted on another device.');}
  }
}
function connect() {
  const current=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
  socket=current;
  current.onopen=()=>{if(socket===current){online=true;navigation();}};
  current.onmessage=event=>{if(socket===current)update(JSON.parse(event.data));};
  current.onclose=()=>{if(socket!==current)return;online=false;if(view!=='offline'){navigation();setTimeout(()=>{if(socket===current&&view!=='offline')connect();},1800);}};
}

async function boot() {
  try {
    const fragment=new URLSearchParams(location.hash.slice(1));
    if(fragment.has('pair'))history.replaceState(null,'',location.pathname);
    state=await api('/api/state');drills=categorizedDrills(await api('/api/drills'));
    try{courses=await api('/api/courses');}catch(e){if(e.status!==404)throw e;courses=[{id:'meadow-one-v2',name:'Meadow One',par:4,yards:350}];}
    document.querySelector('nav').hidden=false;connection.hidden=false;review=null;online=true;
    if(location.hash)await openRoute(location.hash);
    else setView(state.practice&&!state.practice.ended?'runner':'choose',{replace:true});
    connect();
  }catch(e){view='offline';online=false;navigation();app.innerHTML='<section class="card pair-card"><h1>Could not open TraceLoft</h1><p>Start the TraceLoft server, then try again.</p><button class="btn primary" data-action="retry">Try again</button></section>';notice(e.message);}
}

function render() {
  navigation();
  if(view==='choose') renderChoose();
  else if(view==='setup') renderSetup();
  else if(view==='runner') renderRunner();
  else if(view==='relay') renderRelay();
  else if(view==='sessions') renderSessions();
  else if(view==='analyze')renderAnalyze(app,api,notice,()=>view==='analyze');
  else if(view==='play') renderPlay(app,state,courses);
  else if(view==='course-import')renderCourseImport(app,api,notice,async()=>{courses=await api('/api/courses');},()=>view==='course-import');
}
function renderChoose() {
  const ended=state.practice?.ended?state.practice:!state.practice?abandonedSession:null;
  app.innerHTML=`<div class="page-head"><div><h1>Practice</h1><p class="subtitle">Choose your focus. Set your targets. Start practicing.</p></div>${state.practice&&!state.practice.ended?button('Return to active drill','return','primary'):''}</div>${ended?sessionNotice(ended):''}<div class="practice-categories">${categoryMarkup(drills)}</div><div class="section-space top-hint">Practice sessions save automatically. Review your results in Sessions.</div>`;
  bindCategories(app);
}
function renderSetup() {
  const d=selectedDrill, old=d.parameters??{};
  if(d.id==='golf-sim'){renderGameSetup(app,old,async params=>{state=await api('/api/practice',params);review=null;abandonedSession=null;setView('runner');},notice,equipmentContext,courses);return;}
  if(['bag-mapping','wedge-matrix'].includes(d.id)) {
    renderCollectionSetup(app,old,async params=>{state=await api('/api/practice',params);review=null;abandonedSession=null;setView('runner');},notice,equipmentContext,d.id==='wedge-matrix');
    return;
  }
  if(d.id==='driving-range') {
    renderRangeSetup(app,old,async params=>{state=await api('/api/practice',params);review=null;abandonedSession=null;setView('runner');},notice,equipmentContext);
    return;
  }
  if(['distance-ladder','iron-ladder','wedge-ladder'].includes(d.id)) {
    renderDistanceSetup(app, old, async params=>{state=await api('/api/practice',params);review=null;abandonedSession=null;setView('runner');}, notice, equipmentContext);
    return;
  }
  const ladder=d.id==='ladder';
  app.innerHTML=`<div class="page-head"><div><h1>${esc(d.title)}</h1><p class="subtitle">Set your parameters, then launch your practice session.</p></div>${button('← Practice','home','quiet')}</div><section class="card setup-card"><h2>Session targets</h2><form id="setup-form"><div class="form-grid">
    <label class="field">Pace targets<select name="random_pace"><option value="false" ${!old.random_pace&&!d.random_pace?'selected':''}>Fixed target</option><option value="true" ${old.random_pace??d.random_pace?'selected':''}>Random pace</option></select></label>
    <label class="field">Number of putts<input name="repetitions" type="number" min="1" max="1000" value="${old.repetitions??10}" required></label>
    <label class="field" data-param="fixed">Target speed (mph)<input name="target" type="number" step="0.1" min="1" max="15" value="${old.target??4}" required></label>
    <label class="field" data-param="pace">Speed tolerance (± mph)<input name="speed_tolerance" type="number" step="0.1" min="0" value="${old.speed_tolerance??.3}" required></label>
    <label class="field" data-param="random">Random minimum (mph)<input name="minimum" type="number" step="0.1" min="1" max="15" value="${old.minimum??3}" required></label>
    <label class="field" data-param="random">Random maximum (mph)<input name="maximum" type="number" step="0.1" min="1" max="15" value="${old.maximum??6}" required></label>
    <label class="field" data-param="line">Start-line tolerance (± degrees)<input name="angle_tolerance" type="number" step="0.1" min="0" value="${old.angle_tolerance??1}" required></label>
    <label class="field">Green speed · Stimp (ft)<input name="stimp" type="number" step="0.1" min="3" max="20" value="${old.stimp??10}" required></label>
    <label class="field">Distance model<select name="distance_model"><option value="stimp-constant-deceleration-v1" ${!old.distance_model||old.distance_model.id==='stimp-constant-deceleration-v1'?'selected':''}>Stimp constant braking · baseline</option><option value="fuse-flat-braking-v1" ${old.distance_model?.id==='fuse-flat-braking-v1'?'selected':''}>Fuse speed-dependent braking · comparison</option></select></label>
    <label class="field" data-param="mode">Score target as<select name="target_mode"><option value="speed" ${old.target_mode!=='distance'?'selected':''}>Measured speed (mph)</option><option value="distance" ${old.target_mode==='distance'?'selected':''}>Estimated distance (ft)</option></select></label>
    <label class="field" data-param="distance">Target distance (ft)<input name="target_distance" type="number" step="0.1" min="0.5" max="300" value="${old.target_distance_ft??10}" required></label>
    <label class="field" data-param="distance-tolerance">Distance tolerance (± ft)<input name="distance_tolerance" type="number" step="0.1" min="0" max="100" value="${old.distance_tolerance??2}" required></label>
    <label class="field" data-param="ladder">Shortest distance (ft)<input name="ladder_start" type="number" step="0.5" min="0.5" max="300" value="${old.ladder_start??5}" required></label>
    <label class="field" data-param="ladder">Longest distance (ft)<input name="ladder_end" type="number" step="0.5" min="0.5" max="300" value="${old.ladder_end??25}" required></label>
    <label class="field" data-param="ladder">Step between rungs (ft)<input name="ladder_step" type="number" step="0.5" min="0.5" max="300" value="${old.ladder_step??5}" required></label>
    <label class="field" data-param="ladder">Rounds through ladder<input name="ladder_rounds" type="number" min="1" max="100" value="${old.ladder_rounds??2}" required></label>
    <label class="field" data-param="ladder">Ladder direction<select name="ladder_direction"><option value="ascending" ${old.ladder_direction!=='descending'?'selected':''}>Ascending · short to long</option><option value="descending" ${old.ladder_direction==='descending'?'selected':''}>Descending · long to short</option></select></label>
    </div><p class="model-note">Estimated distance uses your selected flat-green model. Constant braking is the physics baseline; Fuse is a simulation comparison. Stimp is entered, not measured. Launch speed is treated as rolling speed; slope, skid and cup effects are omitted. Uncalibrated for your mat and GSPro.</p><p id="ladder-preview" class="form-hint" role="status"></p><div class="form-foot"><p class="form-hint">${ladder?'One putt per rung, advancing after every confirmed putt, including misses. Repeat for each round. Start line is measured, not scored.':'Fixed drills can score measured speed or estimated distance. Random pace varies speed; each putt keeps its own target and estimate.'}</p><button type="submit" class="btn primary">Launch drill →</button></div></form></section>`;
  const form=app.querySelector('form');
  function parameters() {
    const line=d.drill==='Start line', pace=d.drill==='Pace consistency', random=form.elements.random_pace.value==='true';
    const distance=ladder||!line&&!random&&form.elements.target_mode.value==='distance';
    form.elements.random_pace.disabled=line||ladder;
    form.elements.random_pace.closest('label').hidden=line||ladder;
    form.elements.repetitions.disabled=ladder;form.elements.repetitions.closest('label').hidden=ladder;
    app.querySelectorAll('[data-param]').forEach(label=>{
      const kind=label.dataset.param, show=kind==='ladder'?ladder:kind==='mode'?!line&&!random&&!ladder:kind==='distance-tolerance'?distance:kind==='distance'?distance&&!ladder:kind==='line'?!pace&&!ladder:!line&&!ladder&&!distance&&(kind==='pace'||kind==='random'&&random||kind==='fixed'&&!random);
      label.hidden=!show;label.querySelector('input,select').disabled=!show;
    });
    if(ladder){const count=(Number(form.elements.ladder_end.value)-Number(form.elements.ladder_start.value))/Number(form.elements.ladder_step.value)+1;app.querySelector('#ladder-preview').textContent=Number.isInteger(count)&&count>1?`${count} rungs × ${form.elements.ladder_rounds.value} rounds = ${count*Number(form.elements.ladder_rounds.value)} putts.`:'Choose a step that divides the distance range evenly.';}
  }
  form.oninput=parameters;form.onchange=parameters;parameters();
  form.onsubmit=async event=>{
    event.preventDefault();const data=new FormData(form), num=(key,fallback)=>data.has(key)?Number(data.get(key)):fallback;
    const params={drill:d.drill,target:num('target',4),speed_tolerance:num('speed_tolerance',0),angle_tolerance:num('angle_tolerance',1),repetitions:num('repetitions',10),random_pace:d.drill!=='Start line'&&data.get('random_pace')==='true',minimum:num('minimum',3),maximum:num('maximum',6)};
    Object.assign(params,{distance_model:data.get('distance_model'),stimp:num('stimp',10),target_mode:ladder?'distance':data.get('target_mode')??'speed',target_distance:num('target_distance',10),distance_tolerance:num('distance_tolerance',2),ladder_start:num('ladder_start',5),ladder_end:num('ladder_end',25),ladder_step:num('ladder_step',5),ladder_rounds:num('ladder_rounds',2),ladder_direction:data.get('ladder_direction')??'ascending'});
    try {state=await api('/api/practice',params);review=null;abandonedSession=null;setView('runner');}catch(e){notice(e.message);}
  };
}

function sessionNotice(data, isReview=false) {
  const title=data.abandoned?'Session abandoned':data.ended?'Session over':'Review only';
  const detail=data.ended?`No more ${shotWord(data)} will be saved to this session.`:'You are reviewing saved results. Return to Practice for the active drill.';
  return `<section class="session-ended" role="alert" aria-label="${title}"><span class="ended-icon" aria-hidden="true">!</span><div><h2>${title}</h2><p>${detail}</p><span>${data.abandoned?`Recorded ${shotWord(data)} are saved.`:`${data.shots.length} recorded ${shotWord(data)} saved.`}${isReview?' Exit review to return to your sessions.':data.session_kind==='golf_sim'?' Start a new round to record more.':' Start a new drill to record more.'}</span></div></section>`;
}
async function exitSession() {
  if(review){review=null;setView('sessions');return;}
  const data=state.practice;
  if(data&&!data.ended){
    if(!await confirmAction('End session and exit?', `Save your recorded ${shotWord(data)} and return to ${data.session_kind==='golf_sim'?'Play':'Practice'}? This session will stop accepting ${shotWord(data)}. Relay keeps listening.`, 'End session & exit'))return;
    state=await api(`/api/practice/${data.id}/finish`,{});
  }
  review=null;setView(data?.session_kind==='golf_sim'?'play':'choose');
}
function renderRunner() {
  const data=review?.practice??state.practice, summary=review?.summary??state.summary;
  if(!data){setView('choose');return;}
  renderKey=JSON.stringify([review??state.practice,review?.summary??state.summary,state.equipment?.revision,(review?.practice??state.practice)?.session_kind==='golf_sim'?state.sessions_revision:null,state.practice_error,state.capture.running,state.capture.stopping]);
  if(data.session_kind==='golf_sim') {
    const redraw=()=>{if(view==='runner'&&(review?.practice??state.practice)?.id===data.id)renderRunner();};
    const change=async(path,params)=>{update(await api(path,params));redraw();};
    renderGame(app,data,summary,state,!!review,sessionNotice,{
      equipment:equipmentContext,notice,redraw,current:()=>state.practice?.equipment_selection,
      select:selection=>change(`/api/practice/${data.id}/equipment`,selection),
      aim:params=>change(`/api/game/${data.id}/aim`,params),
      simulate:params=>change(`/api/game/${data.id}/simulate`,params),
      preview:()=>api(`/api/game/${data.id}/preview`),
      recommendations:()=>api(`/api/game/${data.id}/recommendations`),
      exclude:async key=>{if(review)review=await api(`/api/sessions/${data.id}/exclude`,{key});else update(await api(`/api/practice/${data.id}/exclude`,{key}));redraw();}
    });return;
  }
  if(data.session_kind==='driving_range') {
    const refreshRange=()=>{if(view==='runner'&&(review?.practice??state.practice)?.id===data.id)renderRunner();};
    renderRange(app,data,state,!!review,sessionNotice,{
      cell:async params=>{update(await api(`/api/collection/${data.id}/cell`,params));refreshRange();},
      equipment:equipmentContext,notice,current:()=>state.practice?.equipment_selection,redraw:refreshRange,
      select:async selection=>{update(await api(`/api/practice/${data.id}/equipment`,selection));refreshRange();},
      simulate:async count=>{update(await api(`/api/range/${data.id}/simulate`,{count}));refreshRange();},
      target:async params=>{update(await api(`/api/range/${data.id}/target`,params));refreshRange();},
      cleanup:async params=>{const result=await api(`/api/range/${data.id}/cleanup`,params);if(view==='runner'&&review?.practice.id===data.id){review=result;}else if(state.practice?.id===data.id){state.practice=result.practice;state.summary=result.summary;}refreshRange();}
    });
    return;
  }
  if(data.practice_type==='full_swing') {
    app.innerHTML=distanceRunner(data,summary,state,!!review,selectedShot,sessionNotice);
    bindEquipment(app,equipmentContext,async selection=>{update(await api(`/api/practice/${data.id}/equipment`,selection));renderRunner();},()=>state.practice?.equipment_selection);
    return;
  }
  const shots=data.shots, latest=shots.at(-1), own=!review, active=own&&!data.ended, recording=state.capture.running&&state.capture.mode==='run';
  const speed=latest?.vals.ball_speed, hla=latest?.vals.launch_dir, paceError=latest?speed-(latest.target??data.target):null;
  const excluded=latest?.excluded, good=latest?.success&&!excluded;
  const resultClass=excluded?'excluded':!latest?'waiting':good?'':'miss';
  const modeled=!!data.distance_model, distance=data.target_mode==='distance', ladder=data.drill==='Putting ladder';
  const distanceError=latest?.distance_error_ft, travel=latest?.estimated_distance_ft;
  const ladderPosition=active?shots.length:Math.max(0,shots.length-1);
  const rung=ladder?ladderPosition%data.ladder_targets_ft.length+1:null;
  const displayedDistance=ladder&&!active?(latest?.target_distance_ft??data.target_distance_ft):data.target_distance_ft;
  const displayedSpeed=ladder&&!active?(latest?.target??data.target):data.target;
  const targetLine=distance?`${displayedDistance.toFixed(1)} ft ± ${data.distance_tolerance} ft`:data.drill==='Start line'?`Start line 0° ± ${data.angle_tolerance}°`:`${data.target.toFixed(1)} mph ± ${data.speed_tolerance}`;
  const status=excluded?'Excluded':!latest?'Waiting':good?'In window':'Outside window';
  app.innerHTML=`<div class="page-head"><div><h1>${review?'Session review':'Putting practice'}</h1><p class="subtitle">${esc(data.drill)} <span class="chip ${data.random_pace?'accent':''}">${ladder?data.ladder_direction==='descending'?'Descending ladder':'Ascending ladder':data.random_pace?'Random pace':distance?'Distance target':'Speed target'}</span>${data.abandoned?' · Abandoned':review?' · Saved session':data.ended?' · Complete':''}</p></div><div class="head-actions">${active?button('Relay','relay','quiet')+button('End session','finish','danger'):''}${review?button('Practice selector','home','quiet'):''}${button(review?'Exit review':'Exit session','exit-session',active?'quiet':'primary')}${!active?button('⚙ Edit targets','edit','quiet'):''}</div></div>
    ${!active?sessionNotice(data,!!review):''}
    ${state.practice_error&&own?`<div class="session-error" role="alert">${esc(state.practice_error)}</div>`:''}
    ${active?`<div id="recording-feedback">${recordingWarnings(state.capture,'putts')}</div>`:''}
    <div class="heroes"><section class="card"><div class="eyebrow">LATEST PUTT</div><div class="latest-metrics ${modeled?'with-distance':''}">
      <div class="metric"><div class="metric-label">Ball speed</div><div class="metric-value">${latest?speed.toFixed(1):'—'}</div><div class="metric-unit">mph</div></div>
      <div class="metric"><div class="metric-label">${distance?'Distance error':'Pace error'}</div><div class="metric-value">${latest?error(distance?distanceError:paceError):'—'}</div><div class="metric-unit">${distance?'ft · estimated':'mph'}${distance&&latest?distanceError < -1e-9?' · short':distanceError > 1e-9?' · long':' · on target':''}${data.drill==='Start line'?' · not scored':''}</div></div>
      ${modeled?`<div class="metric"><div class="metric-label">Estimated travel</div><div class="metric-value">${travel==null?'—':travel.toFixed(1)}</div><div class="metric-unit">ft · Stimp ${data.stimp}</div></div>`:''}
      <div class="metric"><div class="metric-label">Start line</div><div class="metric-value">${latest?direction(hla):'—'}</div><div class="metric-unit">at launch</div></div>
      <div class="metric"><div class="metric-label">Result</div><div class="result ${resultClass}"><span class="result-icon">${good?'✓':latest&&!excluded?'!':'—'}</span>${status}</div></div>
    </div><div class="metric-foot">${latest?`Putt ${shots.length} · ${excluded?'Excluded from score':'Saved automatically'}`:data.ended?'No validated putts in this session.':recording?'Waiting for your next validated putt.':'Connect your shot source through Relay.'}</div></section>
    <section class="card progress-card"><div class="eyebrow">SESSION PROGRESS</div><div class="progress-counts"><div><strong>${shots.length} / ${data.repetitions}</strong><span>putts</span></div><div><strong>${summary.successes} / ${summary.count}</strong><span>in window</span></div></div><div class="progress-row">${progress(shots.length,data.repetitions)}</div><div class="target-tile"><small>${data.abandoned?'SESSION ABANDONED':data.ended?'SESSION COMPLETE':data.random_pace||ladder?'NEXT TARGET':'SESSION TARGET'}</small><strong>${targetLine}</strong>${distance?`<p>Required pace ≈ ${displayedSpeed.toFixed(2)} mph · estimated</p>`:''}${ladder?`<p>${active?'Rung':'Last rung'} ${rung} / ${data.ladder_targets_ft.length} · Round ${Math.min(Math.floor(ladderPosition/data.ladder_targets_ft.length)+1,data.ladder_rounds)} / ${data.ladder_rounds}</p><p>${data.ladder_targets_ft.map((t,i)=>`<span class="ladder-rung ${i+1===rung?'current':''}">${t.toFixed(1)} ft</span>`).join(' ')}</p>`:''}<p>${ladder?'Start line measured · not scored':data.drill!=='Start line'?`Start line 0° ± ${data.angle_tolerance}°${data.drill==='Pace consistency'||ladder?' · not scored':''}`:'Pace is measured, not scored.'}</p></div></section></div>
    ${modeled?`<p class="model-note">Estimated flat-green travel · Stimp ${data.stimp} · ${data.distance_model.id==='fuse-flat-braking-v1'?'Fuse speed-dependent braking v1':'Stimp constant braking v1'}. Uncalibrated; no slope, skid or cup effects. ${distance?'Scores estimate windows, not holed putts.':'Distance is shown for context; scoring uses launch measurements.'}</p>`:`<p class="model-note">Distance unavailable: this historical session has no saved Stimp/model. Edit targets to launch a new session with distance estimates.</p>`}
    <div class="graphs"><section class="card pace-card"><div class="eyebrow">${distance?'ESTIMATED DISTANCE (FT)':'PACE CHART'}</div><p class="graph-subtitle">${distance?'Travel vs target by putt · flat-green estimate':'Ball speed by putt'}${data.drill==='Start line'?' · not scored':''}</p><div class="legend"><span><i class="swatch"></i>Target zone${data.random_pace||ladder?' (varies)':''}</span><span><i class="line-swatch"></i>${distance?'Distance target per putt':data.random_pace?'Target per putt':`Target (${data.target.toFixed(1)} mph)`}</span></div>${trend(data,true,distance)}</section>
    <section class="card"><div class="eyebrow">START LINE (LATEST PUTT)</div><p class="graph-subtitle">Direction at launch relative to target</p>${gauge(data)}<div class="legend"><span><i class="swatch"></i>In window (±${data.angle_tolerance}°)${data.drill==='Pace consistency'||ladder?' · not scored':''}</span></div><div class="graph-divider"></div><div class="start-trend"><div class="eyebrow">START LINE TREND</div><p class="graph-subtitle">Direction by putt (right is positive)</p>${trend(data,false)}</div></section></div>
    <section class="card"><div class="table-head"><div class="eyebrow">SHOT LOG</div><span class="top-hint">Latest first · select a row to review</span></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Speed (mph)</th><th>Target (mph)</th><th>Pace error</th><th>Start line</th>${modeled?'<th>Est. travel (ft)</th><th>Distance target (ft)</th><th>Est. error (ft)</th>':''}<th>Result</th></tr></thead><tbody>${shots.length?shots.map((s,i)=>({s,i})).reverse().map(({s,i})=>`<tr data-key="${esc(s.key)}" tabindex="0" aria-label="Select putt ${i+1}" class="${i===shots.length-1?'latest-row':''} ${s.excluded?'excluded':''} ${selectedShot===s.key?'selected':''}"><td>${i+1}</td><td>${s.vals.ball_speed.toFixed(1)}</td><td>${(s.target??data.target).toFixed(1)}</td><td>${error(s.vals.ball_speed-(s.target??data.target))} mph</td><td>${direction(s.vals.launch_dir)}</td>${modeled?`<td>${s.estimated_distance_ft?.toFixed(1)??'—'}</td><td>${s.target_distance_ft?.toFixed(1)??'—'}</td><td>${s.distance_error_ft==null?'—':error(s.distance_error_ft)}</td>`:''}<td class="${s.excluded?'':s.success?'success-text':'miss-text'}">${s.excluded?'Excluded':s.success?'● In window':'● Outside window'}</td></tr>`).join(''):'<tr><td colspan="${modeled?9:6}" class="empty">No recorded putts yet.</td></tr>'}</tbody></table></div><div class="table-actions">${button('Exclude / include selected','exclude','small',!selectedShot?'disabled':'')}${active?button('Abandon session','abandon','danger quiet small'):button('Delete session','delete-review','danger quiet small')}${review?button('Practice selector','home','quiet small'):''}${button(review?'Exit review':'Exit session','exit-session','quiet small')}</div><details class="details"><summary>Session statistics</summary><p>${summary.count} included putts · ${summary.successes} in window<br>${['pace_error','launch_dir','launch_ang'].map((f,i)=>`${['Pace error','Start line','Vertical launch'][i]} ${summary[f].mean===null?'—':`${summary[f].mean.toFixed(2)} ± ${summary[f].sd.toFixed(2)}`} ${i?'°':'mph'}`).join(' · ')}${summary.distance_error_ft?.count?`<br>Estimated distance error ${summary.distance_error_ft.mean.toFixed(2)} ± ${summary.distance_error_ft.sd.toFixed(2)} ft · ${summary.distance_error_ft.short} short / ${summary.distance_error_ft.long} long`:modeled?'<br>No distance estimates yet.':''}<br>Mean ± population standard deviation. Excluded putts remain in the log.</p></details></section>`;
}

async function renderSessions() {
  const request=++sessionListRequest;
  const deletedWasOpen=app.querySelector('#deleted-sessions')?.open??false;
  if(!app.querySelector('.session-list'))app.innerHTML='<div class="page-head"><div><h1>Sessions</h1><p class="subtitle">Your saved practice, ready to review.</p></div></div><div class="loading">Loading sessions…</div>';
  try {
    const [sessions,deleted]=await Promise.all([api('/api/sessions'),api('/api/sessions?deleted=true')]);
    if(view!=='sessions'||request!==sessionListRequest)return;
    sessionList=sessions;
    const active=s=>s.id===state.practice?.id&&!state.practice.ended;
    const visible=sessions.filter(s=>sessionMode==='all'||(sessionMode==='demo')===!!s.demo);
    const label=s=>s.abandoned?'Abandoned':active(s)?'Active':s.ended?'Complete':'Unfinished';
    app.innerHTML=`<div class="page-head"><div><h1>Sessions</h1><p class="subtitle">Your saved practice, ready to review.</p></div></div><div class="range-session-mode"><label class="field">Session data<select id="session-mode"><option value="all" ${sessionMode==='all'?'selected':''}>All sessions</option><option value="real" ${sessionMode==='real'?'selected':''}>Real sessions</option><option value="demo" ${sessionMode==='demo'?'selected':''}>Demo sessions only</option></select></label></div><div class="session-list">${visible.length?visible.map(s=>`<section class="card session-entry"><div><h2>${s.demo?'DEMO · ':''}${esc(s.drill)}${s.random_pace?' / Random pace':''}</h2><p>${esc(date(s.started))} · ${s.summary.count} included · ${s.session_kind==='golf_sim'?`${s.summary.strokes} strokes · ${s.summary.holed?'hole complete':'partial round'}`:`${s.summary.successes} in window`} · <span class="${s.abandoned?'miss-text':''}">${label(s)}</span></p>${active(s)?'<p class="top-hint">Finish or abandon this session before deleting.</p>':''}</div><div class="session-actions">${button(active(s)?'Return to active drill →':'Review session →','review','',`data-id="${s.id}"`)}${button('Delete','delete-session','danger quiet',`data-id="${s.id}" ${active(s)?'disabled':''}`)}</div></section>`).join(''):'<section class="card empty">No saved sessions. Choose a drill in Practice to get started.</section>'}</div><details id="deleted-sessions" class="details deleted-sessions" ${deletedWasOpen?'open':''}><summary>Recently deleted (${deleted.length})</summary><p>Deleted sessions stay here until you restore them.</p><div class="session-list">${deleted.length?deleted.map(s=>`<section class="card session-entry"><div><h2>${s.demo?'DEMO · ':''}${esc(s.drill)}</h2><p>${esc(date(s.started))} · ${s.captured} recorded ${shotWord(s)}</p></div>${button('Restore session','restore-session','',`data-id="${s.id}"`)}</section>`).join(''):'<p>No deleted sessions.</p>'}</div></details>`;
  app.querySelector('#session-mode').onchange=e=>{sessionMode=e.target.value;renderSessions();};
  }catch(e){if(view==='sessions'&&request===sessionListRequest)notice(e.message);}
}

function renderRelay() {
  const relay=state.relay;
  app.innerHTML=`<div class="page-head"><div><p class="eyebrow">CONNECT / RECORD / FORWARD</p><h1>Relay</h1><p class="subtitle">Incoming shots save automatically. Choose where they go next.</p></div><span class="chip accent">Always listening · TCP ${state.input.port}</span></div>
  <div class="capture-grid"><section class="card"><h2>Incoming shots</h2><div id="relay-source" class="section-space"></div><p class="form-hint">Point your shot source at <strong>127.0.0.1:${state.input.port}</strong> using GSPro Open Connect.</p><div class="table-wrap section-space" id="relay-read"></div></section>
  <section class="card"><h2>Send shots to</h2><label class="field section-space">Destination<select id="relay-destination"><option value="off">Off · record only</option><option value="gspro">GSPro</option><option value="infinite_tees">Infinite Tees</option></select></label><p class="form-hint">Saved automatically. Direct connection; no adapter app required.</p><div id="relay-output" class="section-space" role="status"></div><details class="details section-space"><summary>Connection details</summary><form id="relay-connection"><label class="field">Simulator port<input name="port" type="number" min="1" max="65535" value="${relay.port}" required></label><p class="form-hint">Localhost · GSPro defaults to 921; Infinite Tees to 999.</p><button class="btn" type="submit">Save port</button></form></details></section></div>
  <section class="card section-space"><h2>Data & backups</h2><p class="form-hint">Shots and sessions save to SQLite, even when forwarding is off or the simulator is disconnected.</p><div class="form-foot"><a class="btn" href="/api/exports/csv" download>Export CSV</a>${button('Back up database','backup-database','quiet')}</div><p id="database-backup-status" class="backup-status" role="status"></p></section>
  <details class="card section-space"><summary>Access & diagnostics</summary><p>${state.access.addresses.map(url=>`<a href="${esc(url)}">${esc(url)}</a>`).join(' · ')}</p><pre id="relay-logs" class="diagnostic-log"></pre></details>`;
  const select=app.querySelector('#relay-destination');select.value=relay.destination;
  const save=async settings=>{select.disabled=true;try{update(await api('/api/input/forwarding',settings));}catch(e){notice(e.message);select.value=state.relay.destination;}finally{select.disabled=false;}};
  select.onchange=async()=>{await save({destination:select.value});app.querySelector('#relay-connection').elements.port.value=state.relay.port;};
  app.querySelector('#relay-connection').onsubmit=async e=>{e.preventDefault();await save({destination:select.value,port:Number(e.target.elements.port.value)});};
  updateRelay();
}
function updateRelay() {
  const source=app.querySelector('#relay-source');if(!source)return;
  source.innerHTML=`<strong>${esc(state.capture.status)}</strong><p>${esc(state.input.device||'No source connected')} · ${state.input.received} stored this run</p>${state.input.error?`<p class="session-error">${esc(state.input.error)}</p>`:''}`;
  const relay=state.relay;
  app.querySelector('#relay-output').innerHTML=`<strong>${esc(relay.status)}</strong><p>${relay.sent} shots sent this run</p>${relay.enabled&&!relay.connected?'<p class="form-hint">Open the selected simulator. Relay reconnects automatically; earlier shots are not replayed.</p>':''}`;
  const select=app.querySelector('#relay-destination');if(!select.disabled)select.value=relay.destination;
  app.querySelector('#relay-logs').textContent=state.logs.join('\n');
  const vals=state.read?.vals;
  app.querySelector('#relay-read').innerHTML=vals?`<h2>Latest measurements</h2><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>${Object.entries(vals).map(([k,v])=>`<tr><td>${esc(k.replaceAll('_',' '))}</td><td>${esc(v??'—')}</td></tr>`).join('')}</tbody></table>`:'<p class="form-hint">Waiting for the first shot.</p>';
}

document.addEventListener('click',async event=>{
  const nav=event.target.closest('[data-nav]');
  if(event.target.closest('.brand')){event.preventDefault();if(state){review=null;setView('choose');}return;}
  if(nav&&state){review=null;setView(nav.dataset.nav==='practice'?'choose':nav.dataset.nav);return;}
  const row=event.target.closest('[data-key]');
  if(row){selectedShot=row.dataset.key;renderRunner();return;}
  const action=event.target.closest('[data-action]');if(!action||action.disabled)return;
  const data=review?.practice??state?.practice;
  try{
    switch(action.dataset.action){
      case 'retry':await boot();break;
      case 'choose':if(state.practice&&!state.practice.ended){notice('Finish or abandon the active session before setting up another drill.');return;}selectedDrill={...drills.find(d=>d.id===action.dataset.drill)};selectedDrill.parameters=action.dataset.course?{...selectedDrill.defaults,course:{id:action.dataset.course}}:selectedDrill.defaults;setView('setup');break;
      case 'home':review=null;setView('choose');break;
      case 'play':review=null;setView('play');break;
      case 'tour-demo':{action.disabled=true;action.textContent='Building demo profiles…';try{const loaded=await api('/api/demo/tour-pack',{});update(loaded.state);notice(loaded.result.already_loaded?'Tour demo bag already loaded. Find its saved sessions in Sessions.':`Loaded ${loaded.result.shot_count} synthetic shots in a separate Tour demo bag. Select it in demo round setup.`);}finally{if(action.isConnected){action.disabled=false;action.textContent='Load Tour demo bag';}}break;}
      case 'exit-session':await exitSession();break;
      case 'return':review=null;setView('runner');break;
      case 'finish':update(await api(`/api/practice/${data.id}/finish`,{}));break;
      case 'edit':if(state.practice&&!state.practice.ended){notice('End or abandon the active session before changing targets.');return;}selectedDrill={...drills.find(d=>d.drill===data.drill&&d.random_pace===Boolean(data.random_pace)),parameters:data};review=null;setView('setup');break;
      case 'exclude':if(selectedShot){if(review){review=await api(`/api/sessions/${data.id}/exclude`,{key:selectedShot});renderRunner();}else update(await api(`/api/practice/${data.id}/exclude`,{key:selectedShot}));}break;
      case 'review':{const request=++navigationRequest;const saved=await api(`/api/sessions/${action.dataset.id}`);if(request!==navigationRequest)return;review=saved;if(review.practice.id===state.practice?.id&&!state.practice.ended)review=null;setView('runner');break;}
      case 'abandon':if(await confirmAction('Abandon session?', `End this ${data.session_kind==='golf_sim'?'round':'drill'} and return to ${data.session_kind==='golf_sim'?'Play':'Practice'}? Recorded ${shotWord(data)} will stay in Sessions as Abandoned. Relay keeps listening.`, 'Abandon session')){state=await api(`/api/practice/${data.id}/abandon`,{});abandonedSession={...data,abandoned:true,ended:true};review=null;setView(data.session_kind==='golf_sim'?'play':'choose');notice(`Session abandoned. Recorded ${shotWord(data)} are saved in Sessions.`);}break;
      case 'delete-review':await deleteSession(data);break;
      case 'delete-session':{const saved=sessionList.find(s=>s.id===action.dataset.id);if(saved)await deleteSession(saved);break;}
      case 'restore-session':state=await api(`/api/sessions/${action.dataset.id}/restore`,{});setView('sessions');notice('Session restored.');break;
      case 'relay':review=null;setView('relay');break;
      case 'backup-database':{const result=await api('/api/storage/backup',{});const status=app.querySelector('#database-backup-status');if(status)status.textContent=`Verified local backup saved: ${result.path}`;break;}
    }
  }catch(e){notice(e.message);}
});
document.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.matches('tr[data-key]')){event.preventDefault();selectedShot=event.target.dataset.key;renderRunner();}});
window.addEventListener('hashchange',()=>{document.querySelectorAll('dialog').forEach(d=>d.id==='session-confirm'?d.close('cancel'):d.close());if(state)openRoute(location.hash);});
boot();
