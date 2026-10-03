import {escape as esc} from './charts.js';

export const effectiveShot=s=>Boolean(s.game_outcome?.applied&&!s.game_correction);
export const latestPlayedShot=data=>data.shots.findLast(effectiveShot);

export function correctionControls(data,state) {
  const shot=latestPlayedShot(data),history=data.game_corrections??[];
  const conflict=state.practice&&!state.practice.ended&&state.practice.id!==data.id;
  const disabled=!shot||data.abandoned||conflict;
  const hint=data.abandoned?'Abandoned rounds cannot be reopened.':conflict?'Finish or abandon your active session before reopening this round.':!shot?(history.length?'No scored shots left to replay.':'Available after your first scored shot.'):`Latest scored shot · Hole ${shot.hole_number??1}, attempt ${data.shots.filter(s=>s.hole_id===shot.hole_id).indexOf(shot)+1}${data.ended?' · reopens this round':data.game.holed||shot.hole_id!==data.course.id?` · reopens hole ${shot.hole_number??1}`:''}`;
  return `<section class="card game-corrections section-space" aria-label="Shot corrections"><div><h2>Replay a shot</h2><p class="form-hint">${esc(hint)}</p><p class="form-hint">Both restore the previous position and score, including penalties and gimmes.</p></div><div class="correction-actions"><div><button class="btn" data-game-correct="mulligan" ${disabled?'disabled':''}>Mulligan</button><small>Keep shot in analysis</small></div><div><button class="btn" data-game-correct="misread" ${disabled?'disabled':''}>Misread</button><small>Exclude shot from analysis</small></div></div><details class="correction-history"><summary>Mulligans: ${history.filter(a=>a.kind==='mulligan').length} · Misreads: ${history.filter(a=>a.kind==='misread').length}</summary>${history.length?`<ol>${history.map(a=>`<li><strong>${a.kind==='misread'?'Misread':'Mulligan'}</strong> · Hole ${a.hole_number} · ${esc(new Date(a.at).toLocaleString())}</li>`).join('')}</ol>`:'<p class="form-hint">Corrections stay in the saved round. Original readings are retained.</p>'}</details></section>`;
}
