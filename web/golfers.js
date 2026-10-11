import {escape as esc} from './charts.js';

export function bindGolferPicker(state,save,notice) {
  const button=document.querySelector('#golfer-picker');if(!button)return;
  const golfer=state.golfers?.find(g=>g.user_id===state.golfer_id);
  button.textContent=golfer?.display_name??'My golfer';
  button.onclick=()=>{
    if(document.querySelector('#golfer-dialog'))return;
    const dialog=document.createElement('dialog');dialog.id='golfer-dialog';dialog.className='confirm-dialog';dialog.setAttribute('aria-labelledby','golfer-title');
    const active=state.practice&&!state.practice.ended;
    dialog.innerHTML=`<h2 id="golfer-title">Golfer</h2><p>${active?'Finish or abandon the active session before changing golfer.':'Bags, sessions and analysis belong to the selected golfer.'}</p><form id="golfer-select"><label class="field">Current golfer<select name="user_id" ${active?'disabled':''}>${(state.golfers??[]).map(g=>`<option value="${esc(g.user_id)}" ${g===golfer?'selected':''}>${esc(g.display_name)}</option>`).join('')}</select></label><button class="btn primary" ${active?'disabled':''}>Switch golfer</button></form><details class="section-space"><summary>Add golfer</summary><form id="golfer-create"><label class="field">Name<input name="name" maxlength="80" required ${active?'disabled':''}></label><label class="field">Handedness<select name="handedness"><option value="right_handed">Right handed</option><option value="left_handed">Left handed</option></select></label><button class="btn" ${active?'disabled':''}>Create and select</button></form></details><p role="alert" class="session-error" hidden></p><div class="confirm-actions"><button class="btn quiet" data-close>Close</button></div>`;
    dialog.querySelector('[data-close]').onclick=()=>dialog.close();
    for(const form of dialog.querySelectorAll('form'))form.onsubmit=async e=>{
      e.preventDefault();const b=form.querySelector('button');b.disabled=true;
      try{await save(Object.fromEntries(new FormData(form)));dialog.close();notice('Golfer selected.');}
      catch(err){const p=dialog.querySelector('[role=alert]');p.hidden=false;p.textContent=err.message;b.disabled=false;}
    };
    dialog.addEventListener('close',()=>dialog.remove(),{once:true});document.body.append(dialog);dialog.showModal();
  };
}

export async function tagDialog(sessionId,keys,request,notice) {
  if(!keys.length||document.querySelector('#tag-dialog'))return;
  const dialog=document.createElement('dialog');dialog.id='tag-dialog';dialog.className='confirm-dialog';dialog.setAttribute('aria-labelledby','tag-title');
  dialog.innerHTML=`<h2 id="tag-title">Tags · ${keys.length} selected shots</h2><p>Tags describe shots. They do not exclude shots or change measurements.</p><form><label class="field">Tag name<input name="name" maxlength="80" placeholder="e.g. New grip" required></label><label class="field">Apply to<select name="scope"><option value="attempt">These attempts in this session</option><option value="shot">Physical shots across all sessions</option></select></label><label class="field">Action<select name="action"><option value="add">Add tag</option><option value="remove">Remove tag</option></select></label><p role="alert" class="session-error" hidden></p><div class="confirm-actions"><button class="btn quiet" type="button" data-close>Cancel</button><button class="btn primary">Apply tags</button></div></form><details class="section-space"><summary>Current tags for selected shots</summary><div data-current-tags>Loading…</div></details>`;
  dialog.querySelector('[data-close]').onclick=()=>dialog.close();
  dialog.querySelector('form').onsubmit=async e=>{
    e.preventDefault();const b=e.target.querySelector('button:not([type="button"])');b.disabled=true;
    try{const result=await request(`/api/sessions/${sessionId}/tags`,{...Object.fromEntries(new FormData(e.target)),keys});dialog.close();notice('Tags saved.',async()=>{await request(`/api/sessions/${sessionId}/tags`,{action:'undo',batch_id:result.batch_id});notice('Tag change undone.');});}
    catch(err){const p=dialog.querySelector('[role=alert]');p.hidden=false;p.textContent=err.message;b.disabled=false;}
  };
  dialog.addEventListener('close',()=>dialog.remove(),{once:true});document.body.append(dialog);dialog.showModal();
  try{const tags=await request(`/api/sessions/${sessionId}/tags`);dialog.querySelector('[data-current-tags]').innerHTML=keys.map(k=>`<p>${esc(k)}: ${(tags[k]??[]).map(t=>`${esc(t.name)} (${esc(t.scope)})`).join(', ')||'None'}</p>`).join('');}
  catch(e){dialog.querySelector('[data-current-tags]').textContent=e.message;}
}
