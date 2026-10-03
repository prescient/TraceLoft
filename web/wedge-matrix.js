import {escape as esc} from './charts.js';
import {robustSummary,equipment,included} from './range-data.js';
const n=v=>Number.isFinite(v)?v.toFixed(1):'—';
export function matrixCells(data) {
  return data.collection_plan.flatMap(eq=>data.swing_labels.map(label=>{
    const shots=data.shots.filter(included).filter(s=>{const e=equipment(s);return e.bag_id===eq.bag_id&&e.club_id===eq.club_id&&s.swing_label===label;});
    return {...eq,label,...robustSummary(shots,data.range_metric),launch:robustSummary(shots,'launch_ang'),spin:robustSummary(shots,'total_spin')};
  }));
}
export function matrixSuggestions(data,target) {
  if(!Number.isFinite(target)||target<=0)return [];
  return matrixCells(data).filter(c=>c.count>=data.collection_samples).map(c=>({...c,error:c.median-target})).sort((a,b)=>Math.abs(a.error)-Math.abs(b.error)).slice(0,3);
}
export function matrixCsv(data) {
  const cell=v=>'"'+String(v??'').replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';
  return [['bag','club','swing','metric','unit','n','median','q1','q3','iqr','launch_deg','spin_rpm','demo'],...matrixCells(data).map(c=>[c.bag_name,c.club_label,c.label,data.range_metric,'yd',c.count,c.median,c.q1,c.q3,c.iqr,c.launch.median,c.spin.median,data.demo])].map(r=>r.map(cell).join(',')).join('\r\n');
}
export function decorateMatrix(app,data,active,context) {
  app.querySelector('h1').textContent='Wedge matrix'+(active?'':' · review');
  app.querySelector('[data-range-action="target"]')?.remove();
  app.querySelector('[data-action="edit"]')?.replaceChildren(document.createTextNode('New matrix / edit setup'));
  if(context.shown){const label=document.createElement('p');label.className='form-hint';label.textContent=`Recorded swing: ${context.shown.swing_label??'Unavailable'}`;app.querySelector('.range-hero').append(label);}
  const cells=matrixCells(data),full=cells.filter(c=>c.count>=data.collection_samples).length;
  const panel=document.createElement('section');panel.className='card matrix-summary section-space';
  panel.innerHTML=`<div class="chart-head"><div><p class="eyebrow">${esc(data.collection_plan[0].bag_name)} / ${esc(data.range_metric)} · YD</p><h2>Your wedge matrix</h2></div><strong>${full}/${cells.length} cells sampled</strong></div><p class="form-hint">${data.collection_samples} included readings per cell. Median / IQR · n = available readings. All included planned shots; independent of workspace filters. Swing labels describe your intent, not a fixed percentage of distance.</p><div class="table-wrap"><table class="wedge-grid"><thead><tr><th>Wedge</th>${data.swing_labels.map(l=>`<th>${esc(l)}</th>`).join('')}</tr></thead><tbody>${data.collection_plan.map(eq=>`<tr><th>${esc(eq.club_label)}</th>${data.swing_labels.map(label=>{const c=cells.find(c=>c.club_id===eq.club_id&&c.label===label),selected=active&&eq.club_id===data.equipment_selection?.club_id&&label===data.swing_label;return `<td><${active?'button':'div'} ${active?'type="button"':''} class="matrix-cell ${selected?'selected':''} ${c.count>=data.collection_samples?'sampled':''}" ${active?`data-cell-club="${esc(eq.club_id)}" data-cell-swing="${esc(label)}" aria-pressed="${selected}" aria-label="Collect ${esc(eq.club_label)} ${esc(label)}"`:''}><strong>${n(c.median)} <small>yd</small></strong><span>IQR ${n(c.iqr)} · n=${c.count}</span><small>${n(c.launch.median)}° launch · ${n(c.spin.median)} rpm</small>${selected?'<small>● Next shot</small>':''}</${active?'button':'div'}></td>`;}).join('')}</tr>`).join('')}</tbody></table></div><div class="matrix-suggest section-space"><label class="field">Find a shot for this distance · yd<input type="number" min="1" max="450" step="1" data-wedge-target placeholder="e.g. 75"></label><div data-wedge-suggestions aria-live="polite"><p class="form-hint">Suggestions use cells that meet your sample goal. They are estimates from this session, with no extrapolation.</p></div></div><div class="form-foot"><button class="btn quiet" data-matrix-export>Export matrix CSV</button><button class="btn quiet" data-matrix-print>Print reference</button><span class="form-hint">${full===cells.length?'Matrix sample goal reached. Finish when ready.':'Fill empty cells or keep collecting to improve coverage.'}</span></div>`;
  app.querySelector('.range-hero').insertAdjacentElement('afterend',panel);
  const choose=async(club_id,swing_label,b)=>{b.disabled=true;try{await context.cell({club_id,swing_label});}catch(e){context.notice(e.message);b.disabled=false;}};
  panel.querySelectorAll('[data-cell-club]').forEach(b=>b.onclick=()=>choose(b.dataset.cellClub,b.dataset.cellSwing,b));
  if(active){const tag=document.createElement('section');tag.className='card wedge-next';tag.innerHTML=`<p class="eyebrow">SWING FOR NEXT SHOT</p><div class="wedge-swings">${data.swing_labels.map(l=>`<button class="btn ${l===data.swing_label?'primary':''}" data-swing="${esc(l)}" aria-pressed="${l===data.swing_label}">${esc(l)}</button>`).join('')}</div><p class="form-hint">${esc(data.equipment_selection?.club_label||'Choose a planned wedge')} · <strong>${esc(data.swing_label)}</strong>. Previous shots keep their labels.</p>`;app.querySelector('.range-hero').insertAdjacentElement('beforebegin',tag);tag.querySelectorAll('[data-swing]').forEach(b=>b.onclick=()=>choose(data.equipment_selection?.club_id||'',b.dataset.swing,b));}
  panel.querySelector('[data-wedge-target]').oninput=e=>{
    const suggestions=matrixSuggestions(data,Number(e.target.value));
    panel.querySelector('[data-wedge-suggestions]').innerHTML=suggestions.length?`<div class="suggestion-list">${suggestions.map(c=>`<div><strong>${esc(c.club_label)} / ${esc(c.label)}</strong><span>${n(c.median)} yd · ${n(Math.abs(c.error))} yd ${c.error<0?'short':'long'} · IQR ${n(c.iqr)} · n=${c.count}</span></div>`).join('')}</div>`:'<p class="form-hint">Enter a target and complete at least one cell’s sample goal.</p>';
  };
  panel.querySelector('[data-matrix-export]').onclick=()=>{const url=URL.createObjectURL(new Blob([matrixCsv(data)],{type:'text/csv'})),a=document.createElement('a');a.href=url;a.download=`wedge-matrix-${data.id}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  panel.querySelector('[data-matrix-print]').onclick=()=>window.print();
}
