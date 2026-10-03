import {decorateMatrix} from './wedge-matrix.js';
import {escape as esc} from './charts.js';
import {robustSummary, equipment, included} from './range-data.js';
const n=v=>Number.isFinite(v)?v.toFixed(1):'—';

export function renderCollectionSetup(app,old,launch,notice,eq,wedge=false) {
  const catalog=eq.catalog();
  app.innerHTML=`<div class="page-head"><div><p class="eyebrow">FULL SWING / KNOW YOUR BAG</p><h1>${wedge?'Wedge matrix':'Bag mapping'}</h1><p class="subtitle">${wedge?'Know your yardages for each wedge and swing.':'Build a reliable distance map, one club at a time.'}</p></div><button class="btn quiet" data-action="home">← Practice</button></div><form id="collection-setup"><div class="setup-columns"><section class="card"><h2>Your collection plan</h2><div class="form-grid"><label class="field">Bag<select name="range_bag_id">${catalog.bags.map(b=>`<option value="${esc(b.id)}" ${b.id===old.equipment_selection?.bag_id?'selected':''}>${esc(b.name)}</option>`).join('')}</select></label><label class="field">Readings per ${wedge?'cell':'club'}<input name="collection_samples" type="number" min="2" max="100" value="${old.collection_samples??5}" required></label><label class="field">Distance<select name="range_metric"><option value="carry">Carry · yd</option><option value="total" ${old.range_metric==='total'?'selected':''}>Total · yd</option></select></label><label class="field">Handedness<select name="handedness"><option value="right_handed">Right-handed</option><option value="left_handed" ${old.handedness==='left_handed'?'selected':''}>Left-handed</option></select></label></div>${wedge?`<label class="field section-space">Swing labels · comma separated<input name="swing_labels" value="${esc((old.swing_labels??['Half','Three-quarter','Full']).join(', '))}" maxlength="328" required></label>`:''}<fieldset class="collection-clubs"><legend>Clubs to map</legend><div id="collection-clubs" class="collection-options"></div></fieldset></section><section class="card"><p class="eyebrow">${wedge?'YOUR WEDGES, YOUR SWING LABELS':'DISTANCE, NOT YOUR BEST SHOT'}</p><h2>${wedge?'A reference for scoring distances':'Find the gaps in your bag'}</h2><p>Collect a sample for each ${wedge?'wedge and swing label':'club'}. Compare median distances and the middle 50% of your shots.</p><p class="form-hint">Missing distances do not fill your sample. Excluded and removed shots stay out of your map. Genuine mishits stay included until you choose otherwise.</p><p class="form-hint">You control club changes and when to finish. Complete the sample or keep collecting for a clearer picture.</p></section></div><div class="form-foot"><button class="btn primary" type="submit" value="live">Start ${wedge?'wedge matrix':'bag mapping'} →</button><button class="btn" type="submit" value="demo">Launch demo ${wedge?'matrix':'mapping'}</button></div></form>`;
  const form=app.querySelector('form');
  const clubs=()=>{const bag=catalog.bags.find(b=>b.id===form.elements.range_bag_id.value);app.querySelector('#collection-clubs').innerHTML=bag.clubs.map(c=>`<label class="collection-option"><input type="checkbox" name="collection_clubs" value="${esc(c.id)}" ${old.collection_plan?old.collection_plan.some(p=>p.club_id===c.id)?'checked':'':(wedge?/^(PW|GW|SW|LW)$|wedge|°/i.test(c.label):c.label.toLowerCase()!=='putter')?'checked':''}>${esc(c.label)}</label>`).join('');};
  form.elements.range_bag_id.onchange=clubs;clubs();
  form.onsubmit=async e=>{e.preventDefault();const f=new FormData(form),ids=f.getAll('collection_clubs');if(!ids.length){notice('Choose at least one club.');return;}form.querySelectorAll('button').forEach(b=>b.disabled=true);try{await launch({drill:wedge?'Wedge matrix':'Bag mapping',...(wedge?{swing_labels:f.get('swing_labels').split(',').map(s=>s.trim())}:{}),range_bag_id:f.get('range_bag_id'),range_metric:f.get('range_metric'),handedness:f.get('handedness'),collection_samples:Number(f.get('collection_samples')),collection_clubs:ids,demo:e.submitter.value==='demo'});}catch(err){notice(err.message);form.querySelectorAll('button').forEach(b=>b.disabled=false);}};
}

export function mappingRows(data) {
  return data.collection_plan.map(eq=>{
    const shots=data.shots.filter(included).filter(s=>{const e=equipment(s);return e.bag_id===eq.bag_id&&e.club_id===eq.club_id;});
    return {...eq,...robustSummary(shots,data.range_metric)};
  }).sort((a,b)=>(b.median??-1)-(a.median??-1));
}
function intervalChart(rows) {
  const max=Math.max(50,...rows.map(r=>r.q3??r.median??0))*1.08,W=760,H=Math.max(180,rows.length*46+45),L=145;
  const x=v=>L+(W-L-65)*v/max;
  return `<svg class="mapping-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Club median distances and interquartile ranges in yards">${[0,.25,.5,.75,1].map(f=>`<line x1="${x(max*f)}" x2="${x(max*f)}" y1="10" y2="${H-30}" class="range-gridline"/><text x="${x(max*f)}" y="${H-6}" text-anchor="middle">${Math.round(max*f)}</text>`).join('')}${rows.map((r,i)=>{const y=30+i*46;return `<text x="${L-14}" y="${y+5}" text-anchor="end">${esc(r.club_label)}</text>${r.median==null?`<text x="${L+15}" y="${y+5}">No readings</text>`:`<line x1="${x(r.q1??r.median)}" x2="${x(r.q3??r.median)}" y1="${y}" y2="${y}" stroke="var(--accent)" stroke-width="12" stroke-opacity=".35"/><circle cx="${x(r.median)}" cy="${y}" r="6" fill="var(--accent)"/><text x="${x(r.q3??r.median)+12}" y="${y+5}">${n(r.median)}</text>`}`;}).join('')}</svg>`;
}
export function decorateCollection(app,data,active,context) {
  if(!data.collection_kind)return;
  if(data.demo_reference)app.querySelector('.range-demo')?.insertAdjacentHTML('afterend','<p class="form-hint section-space">Tour reference demo: full-swing averages anchor synthetic samples. Dispersion, rollout, GW/SW/LW and partial swings are illustrative, not measured Tour or player data. Hybrid is a generic reference, not a specific loft. <a href="https://www.trackman.com/blog/introducing-updated-tour-averages" target="_blank" rel="noopener">Trackman source ↗</a></p>');
  if(data.collection_kind==='wedge'){decorateMatrix(app,data,active,context);return;}
  app.querySelector('[data-range-action="target"]')?.remove();
  const rows=mappingRows(data),complete=rows.filter(r=>r.count>=data.collection_samples).length;
  app.querySelector('h1').textContent=data.drill+(active?'':' · review');
  app.querySelector('[data-action="edit"]')?.replaceChildren(document.createTextNode('New collection / edit setup'));
  const panel=document.createElement('section');panel.className='card collection-summary section-space';
  panel.innerHTML=`<div class="chart-head"><div><p class="eyebrow">${esc(data.collection_plan[0].bag_name)} / ${esc(data.range_metric)} · YD</p><h2>Bag map</h2></div><strong>${complete}/${rows.length} clubs sampled</strong></div><p class="form-hint">This map uses all included shots for the planned clubs, independent of workspace filters. Goal: ${data.collection_samples} readings per club. Dots show median; bands show Q1–Q3 (middle 50%). Gap is to the next shorter sampled club. Overlap describes these samples, not future-shot probability.</p><div class="mapping-layout"><div>${intervalChart(rows)}</div><div class="table-wrap"><table><thead><tr><th>Club</th><th>n / goal</th><th>Median / IQR · yd</th><th>Gap · yd</th>${active?'<th>Collect</th>':''}</tr></thead><tbody>${rows.map((r,i)=>{const next=rows.slice(i+1).find(x=>x.median!=null);return `<tr><th>${esc(r.club_label)}</th><td>${r.count}/${data.collection_samples}${r.count>=data.collection_samples?' ✓':''}</td><td>${n(r.median)} / ${n(r.iqr)}</td><td>${next&&r.median!=null?n(r.median-next.median):'—'}${next&&r.q1!=null&&next.q3!=null&&r.q1<=next.q3?'<small class="range-stat-detail">IQR overlap</small>':''}</td>${active?`<td><button class="btn small" data-collect-club="${esc(r.club_id)}">${r.club_id===data.equipment_selection?.club_id?'Selected':'Select'}</button></td>`:''}</tr>`;}).join('')}</tbody></table></div></div><div class="form-foot"><button class="btn quiet" data-mapping-csv>Export bag map CSV</button><span class="form-hint">${complete===rows.length?'Sample goal reached. Finish when you are ready.':'Small samples remain descriptive. Missing distance never counts as zero.'}</span></div>`;
  app.querySelector('.range-hero').insertAdjacentElement('afterend',panel);
  panel.querySelectorAll('[data-collect-club]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await context.select({bag_id:data.collection_plan[0].bag_id,club_id:b.dataset.collectClub});}catch(e){context.notice(e.message);b.disabled=false;}});
  panel.querySelector('[data-mapping-csv]').onclick=()=>{
    const csv=mappingCsv(data);
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv'})),a=document.createElement('a');a.href=url;a.download=`bag-map-${data.id}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
}

export function mappingCsv(data) {
 const rows=mappingRows(data);
    const cell=v=>'"'+String(v??'').replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';
    return [['bag','club','distance_metric','unit','n','median','q1','q3','iqr','demo'],...rows.map(r=>[r.bag_name,r.club_label,data.range_metric,'yd',r.count,r.median,r.q1,r.q3,r.iqr,data.demo])].map(r=>r.map(cell).join(',')).join('\r\n');
}
