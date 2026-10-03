import {escape as esc} from './charts.js';

export function equipmentControls(catalog, selected, setup=false) {
  const bags=catalog?.bags??[], bag=bags.find(b=>b.id===selected?.bag_id)??bags[0];
  const club=bag?.clubs.find(c=>c.id===selected?.club_id), quick=bags.slice(0,3);
  if(bag&&!quick.includes(bag))quick[2]=bag;
  const abbreviations=(bag?.clubs??[]).map(c=>shortClubLabel(c.label));
  return `<div class="equipment-controls" data-setup="${setup}"><input name="range_bag_id" type="hidden" value="${esc(bag?.id??'')}"><input name="range_club_id" type="hidden" value="${esc(club?.id??'')}">
    <div class="equipment-fields"><div class="bag-column"><div class="bag-column-head"><span class="eyebrow">BAGS</span></div><div class="bag-tabs" role="group" aria-label="Bags">${quick.map(b=>`<button type="button" class="bag-tab ${b===bag?'selected':''}" data-bag-tab="${esc(b.id)}" aria-pressed="${b===bag}" title="${esc(b.name)}"><span>${esc(b.name)}</span>${b===bag?'<span aria-hidden="true">✓</span>':''}</button>`).join('')}${Array.from({length:Math.max(0,3-quick.length)},(_,i)=>`<button type="button" class="bag-tab add-bag" data-add-bag aria-label="Add bag to slot ${quick.length+i+1}">＋ Add bag</button>`).join('')}</div>${bags.length>3?'<button type="button" class="btn quiet small more-bags" data-more-bags>More bags…</button>':''}<button type="button" class="btn quiet bag-manage" data-manage-bags>Manage bags</button></div>
    <div class="club-column"><div class="eyebrow">CLUB FOR NEXT SHOT</div><div class="club-buttons" role="group" aria-label="Club for next shot">${(bag?.clubs??[]).map((c,i)=>{const chosen=c.id===club?.id, short=abbreviations[i], duplicate=abbreviations.filter(s=>s===short).length>1;return `<button type="button" class="club-button ${chosen?'selected':''}" data-club-pick="${esc(c.id)}" aria-label="Select ${esc(c.label)}" aria-pressed="${chosen}" title="${esc(c.label)}"><span class="club-short ${short.length>4?'long':''}">${esc(short)}</span>${duplicate?`<small class="club-ordinal" aria-hidden="true">${abbreviations.slice(0,i+1).filter(s=>s===short).length}</small>`:''}${chosen?'<span class="club-check" aria-hidden="true">✓</span>':''}</button>`;}).join('')}</div><div class="equipment-foot"><p class="form-hint equipment-status" role="status">${club?`${setup?'Starting club':'Next shot'}: <strong>${esc(bag.name)} / ${esc(club.label)}</strong>`:'Choose a club before hitting · untagged'}<span>${setup?'You can switch clubs during the drill.':'Earlier shots keep their tags.'}</span></p>${club?'<button type="button" class="btn quiet small" data-clear-club>Clear club</button>':''}</div></div></div></div>`;
}

function shortClubLabel(label) {
  const s=label.trim(), degree=s.match(/(\d{1,2}(?:\.\d)?)\s*°/);
  if(degree)return degree[1]+'°';
  const numbered=s.match(/\b(\d{1,2})\s*(iron|wood|hybrid|i|w|h)\b/i);
  if(numbered)return numbered[1]+({iron:'i',wood:'W',hybrid:'H',i:'i',w:'W',h:'H'}[numbered[2].toLowerCase()]);
  const standard={driver:'D',putter:'PT','pitching wedge':'PW','gap wedge':'GW','sand wedge':'SW','lob wedge':'LW'};
  return standard[s.toLowerCase()]??(s.length<=5?s:s.slice(0,4)+'…');
}

const element=html=>{const t=document.createElement('template');t.innerHTML=html;return t.content.firstElementChild;};

export function refreshSetupEquipment(root, context) {
  const box=root.querySelector('.equipment-controls[data-setup="true"]');if(!box)return;
  const selected={bag_id:box.querySelector('[name=range_bag_id]').value,club_id:box.querySelector('[name=range_club_id]').value};
  box.replaceWith(element(equipmentControls(context.catalog(),selected,true)));
  bindEquipment(root,context,null);
}

export function bindEquipment(root, context, onSelect, current=()=>null) {
  let box=root.querySelector('.equipment-controls');if(!box)return;
  const setup=box.dataset.setup==='true';
  const draft=()=>({bag_id:box.querySelector('[name=range_bag_id]').value,club_id:box.querySelector('[name=range_club_id]').value});
  const redraw=selected=>{
    box=root.querySelector('.equipment-controls');if(!box)return;
    box.replaceWith(element(equipmentControls(context.catalog(),selected,setup)));
    bindEquipment(root,context,onSelect,current);
  };
  async function change(selected) {
    if(setup){redraw(selected);return;}
    box.querySelectorAll('button').forEach(c=>c.disabled=true);
    box.querySelector('[role=status]').textContent='Saving selection… wait before hitting.';
    try {await onSelect(selected);redraw(current());}
    catch(err){context.notice(err.message);redraw(current());}
  }
  box.querySelectorAll('[data-bag-tab]').forEach(b=>b.onclick=()=>{if(b.dataset.bagTab!==draft().bag_id)change({bag_id:b.dataset.bagTab,club_id:''});});
  box.querySelectorAll('[data-club-pick]').forEach(b=>b.onclick=()=>{if(b.dataset.clubPick!==draft().club_id)change({...draft(),club_id:b.dataset.clubPick});});
  const clear=box.querySelector('[data-clear-club]');if(clear)clear.onclick=()=>change({...draft(),club_id:''});
  async function manage(create=false) {
    const selected=draft();await manageBags(context,selected.bag_id,create);
    redraw(setup?selected:current());
  }
  box.querySelector('[data-manage-bags]').onclick=()=>manage();
  box.querySelectorAll('[data-add-bag]').forEach(b=>b.onclick=()=>manage(true));
  const more=box.querySelector('[data-more-bags]');if(more)more.onclick=async()=>{
    const selected=draft(), id=await chooseBag(context.catalog(),selected.bag_id);
    if(id&&id!==selected.bag_id)await change({bag_id:id,club_id:''});
  };
}

async function chooseBag(catalog, selected) {
  if(document.querySelector('#bag-picker'))return;
  const dialog=document.createElement('dialog');dialog.id='bag-picker';dialog.className='confirm-dialog';dialog.setAttribute('aria-labelledby','bag-picker-title');
  dialog.innerHTML=`<h2 id="bag-picker-title">Choose a bag</h2><p>Choosing another bag clears the club choice for upcoming shots.</p><div class="bag-picker-list">${catalog.bags.map(b=>`<button class="bag-tab ${b.id===selected?'selected':''}" type="button" data-choose-bag="${esc(b.id)}" aria-pressed="${b.id===selected}">${esc(b.name)}</button>`).join('')}</div><div class="confirm-actions"><button class="btn quiet" type="button" data-close-picker>Cancel</button></div>`;
  dialog.querySelectorAll('[data-choose-bag]').forEach(b=>b.onclick=()=>dialog.close(b.dataset.chooseBag));dialog.querySelector('[data-close-picker]').onclick=()=>dialog.close();
  document.body.append(dialog);dialog.showModal();
  await new Promise(resolve=>dialog.addEventListener('close',resolve,{once:true}));const id=dialog.returnValue;dialog.remove();return id;
}

async function manageBags(context, initial, create=false) {
  if(document.querySelector('#bag-manager'))return;
  const dialog=document.createElement('dialog');dialog.id='bag-manager';dialog.className='confirm-dialog bag-manager';
  dialog.setAttribute('aria-labelledby','bag-manager-title');document.body.append(dialog);
  let selected=initial, revision;
  const row=c=>`<div class="bag-club" data-club-id="${esc(c.id)}"><label class="field">Club name<input value="${esc(c.label)}" maxlength="80" required></label><button class="btn small quiet" type="button" data-remove-club aria-label="Remove ${esc(c.label)||'new club'}">Remove</button></div>`;
  function draw() {
    const catalog=context.catalog();revision=catalog.revision;
    const bag=catalog.bags.find(b=>b.id===selected)??catalog.bags[0];selected=bag.id;
    dialog.innerHTML=`<div class="bag-manager-head"><h2 id="bag-manager-title">Manage bags</h2><button type="button" class="btn quiet" data-close-bags aria-label="Close bag manager">Close</button></div><p class="form-hint">Changes apply to upcoming shots. Saved shot tags stay intact.</p><label class="field">Bag to edit<select data-edit-bag>${catalog.bags.map(b=>`<option value="${esc(b.id)}" ${b.id===selected?'selected':''}>${esc(b.name)}</option>`).join('')}</select></label><form id="bag-edit"><label class="field section-space">Bag name<input name="name" value="${esc(bag.name)}" maxlength="80" required></label><div class="bag-clubs">${bag.clubs.map(row).join('')}</div><button class="btn small quiet" type="button" data-add-club>Add club</button><p class="session-error" data-bag-error role="alert" hidden></p><div class="confirm-actions"><button class="btn quiet" type="button" data-close-bags>Close</button><button class="btn primary" type="submit">Save bag</button></div></form><form id="bag-create" class="new-bag"><label class="field">New bag name<input name="name" maxlength="80" placeholder="e.g. Practice bag" required></label><button class="btn" type="submit">Create bag</button><p class="form-hint">Starts with common clubs; edit them to match your equipment.</p></form>`;
    dialog.querySelector('[data-edit-bag]').onchange=e=>{selected=e.target.value;draw();};
    dialog.querySelectorAll('[data-close-bags]').forEach(b=>b.onclick=()=>dialog.close());
    dialog.querySelector('[data-add-club]').onclick=()=>{if(dialog.querySelectorAll('.bag-club').length>=50)return;dialog.querySelector('.bag-clubs').insertAdjacentHTML('beforeend',row({id:'',label:''}));dialog.querySelector('.bag-club:last-child input').focus();};
    dialog.querySelector('.bag-clubs').onclick=e=>{if(e.target.closest('[data-remove-club]'))e.target.closest('.bag-club').remove();};
    async function save(e,create) {
      e.preventDefault();const form=e.target, name=form.elements.name.value, before=context.catalog().bags.map(b=>b.id);
      const body={revision,name};if(!create)body.clubs=[...dialog.querySelectorAll('.bag-club')].map(r=>({id:r.dataset.clubId,label:r.querySelector('input').value}));
      dialog.querySelectorAll('button,input,select').forEach(c=>c.disabled=true);
      try {await context.save(create?'/api/equipment/bags':`/api/equipment/bags/${selected}`,body,create?'POST':'PUT');if(create)selected=context.catalog().bags.find(b=>!before.includes(b.id)).id;draw();context.notice(create?'Bag created.':'Bag saved. Earlier shot tags are unchanged.');}
      catch(err){const p=dialog.querySelector('[data-bag-error]');p.hidden=false;p.textContent=err.message;dialog.querySelectorAll('button,input,select').forEach(c=>c.disabled=false);}
    }
    dialog.querySelector('#bag-edit').onsubmit=e=>save(e,false);dialog.querySelector('#bag-create').onsubmit=e=>save(e,true);
  }
  draw();dialog.showModal();
  if(create)dialog.querySelector('#bag-create input').focus();
  await new Promise(resolve=>dialog.addEventListener('close',resolve,{once:true}));dialog.remove();
}
