import {correctionCounts,correctionHistory} from './game-corrections.js';
import {escape as esc} from './charts.js';

// Presentation alias keeps the original course IDs and frozen session records intact.
export function courseLabel(value) {
  return typeof value==='string'?value.replace(/^Pebble Boulder(?=$| ·)/,'Boulder Beach'):value;
}

export function roundLabel(round) {
  return round?.selection==='front'?'Front 9':round?.selection==='back'?'Back 9':`Full ${round?.holes?.length??18}`;
}

export function holeShots(data) {
  return data.shots.filter(s=>!data.round||s.hole_id===data.course.id);
}

export function reviewHoleData(data,index) {
  const r=data.round;
  if(!r||index===r.index)return data;
  const course=r.holes[index];if(!course)return data;
  const saved=r.results.find(v=>v.hole_id===course.id);
  const game=saved?.game??{position:course.tee,aim:course.pin,lie:'tee',turn:0,strokes:0,
    penalties:0,concessions:0,holed:false,last_message:'This hole was not played.'};
  return {...data,course,game};
}

export function roundScorecard(data,review=false,selectedIndex=null,expanded=review,holeScore='') {
  const r=data.round;if(!r)return '';
  const resultFor=c=>r.results.find(v=>v.hole_id===c.id);
  const completed=r.results.length,finished=r.results.reduce((sum,v)=>sum+v.game.strokes,0);
  const par=r.results.reduce((sum,v)=>sum+v.par,0),relative=finished-par;
  const currentDone=resultFor(r.holes[r.index]);
  const currentScore=currentDone?0:data.game.strokes;
  return `<details class="card round-scorecard section-space" aria-label="Round scorecard" ${expanded?'open':' '}><summary class="table-head">${holeScore?`<div class="scorecard-hole">${holeScore}<span class="scorecard-toggle">Scorecard</span></div>`:''}<div class="round-course-title" ${holeScore?'hidden':''}><p class="eyebrow">${esc(r.tee_label)} TEES · ${r.yards.toLocaleString()} YD · PAR ${r.par}</p><h2>${esc(courseLabel(r.name))} scorecard</h2><p class="correction-counts">${correctionCounts(data)}</p></div><div class="round-total"><strong>${finished+currentScore}</strong><span>strokes · ${completed}/${r.holes.length} holes complete</span><small ${holeScore?'class="round-relative"':''}>${relative===0?'E':relative>0?'+'+relative:relative} on completed holes${currentScore?' · current hole in progress':''}</small>${holeScore?`<p class="correction-counts">${correctionCounts(data)}</p>`:''}</div></summary>
  ${correctionHistory(data)}<div class="round-nines">${[0,9].filter(start=>r.holes.some(c=>c.hole_number>start&&c.hole_number<=start+9)).map(start=>`<div class="table-wrap"><table><caption>${start?'Back nine':'Front nine'}</caption><thead><tr><th scope="col">Hole</th>${r.holes.filter(c=>c.hole_number>start&&c.hole_number<=start+9).map(c=>`<th scope="col">${c.hole_number}</th>`).join('')}<th scope="col">${start?'In':'Out'}</th></tr></thead><tbody><tr><th scope="row">Yards</th>${r.holes.filter(c=>c.hole_number>start&&c.hole_number<=start+9).map(c=>`<td>${c.yards}</td>`).join('')}<td>${r.holes.filter(c=>c.hole_number>start&&c.hole_number<=start+9).reduce((s,c)=>s+c.yards,0)}</td></tr><tr><th scope="row">Par</th>${r.holes.filter(c=>c.hole_number>start&&c.hole_number<=start+9).map(c=>`<td>${c.par}</td>`).join('')}<td>${r.holes.filter(c=>c.hole_number>start&&c.hole_number<=start+9).reduce((s,c)=>s+c.par,0)}</td></tr><tr><th scope="row">Score</th>${r.holes.filter(c=>c.hole_number>start&&c.hole_number<=start+9).map(c=>{const v=resultFor(c),current=c.id===r.holes[r.index].id;return `<td class="${c.id===r.holes[selectedIndex??r.index].id?'current-hole':''}">${v?v.game.strokes:current&&data.game.strokes?`${data.game.strokes}*`:'—'}</td>`;}).join('')}<td>${r.results.filter(v=>v.hole_number>start&&v.hole_number<=start+9).reduce((sum,v)=>sum+v.game.strokes,0)||'—'}</td></tr></tbody></table></div>`).join('')}</div><p class="form-hint">Scores include penalties and gimme putts. * Partial hole; nine totals include completed holes only.</p>${review?`<label class="field round-review-select">Review a hole<select data-round-review>${r.holes.map((c,i)=>`<option value="${i}" ${i===(selectedIndex??r.index)?'selected':''}>Hole ${c.hole_number} · ${esc(c.name)}${resultFor(c)?' · complete':i===r.index&&data.game.strokes?' · partial':' · not played'}</option>`).join('')}</select></label>`:''}</details>`;
}
