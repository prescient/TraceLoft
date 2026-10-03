import {escape as esc} from './charts.js';
import {polygonPath} from './course-art.js';
export const surfaceKinds=['fairway','green','tee','sand','water','nature'];
export const editsFrom=c=>structuredClone({surfaces:c.surfaces,boundary:c.boundary,tee:c.tee,pin:c.pin});
export function changeGeometry(edits,change) {
  const next=structuredClone(edits),{kind,index,ring=0,vertex,point,points}=change;
  const poly=kind==='boundary'?next.boundary:next.surfaces[kind]?.[index];
  if(change.action==='tee'||change.action==='pin')next[change.action]=point;
  else if(change.action==='add')next.surfaces[kind].push({outer:points,holes:[]});
  else if(change.action==='boundary')next.boundary={outer:points,holes:[]};
  else if(change.action==='remove')next.surfaces[kind].splice(index,1);
  else if(change.action==='hole')poly.holes.push(points);
  else if(change.action==='move')(ring?poly.holes[ring-1]:poly.outer)[vertex]=point;
  else if(change.action==='insert')(ring?poly.holes[ring-1]:poly.outer).splice(vertex+1,0,point);
  else if(change.action==='delete')(ring?poly.holes[ring-1]:poly.outer).splice(vertex,1);
  return next;
}

export function editorMarkup(c) {
  return `<section class="course-edit-controls"><h3>Correct the map</h3><p class="form-hint">Choose a shape to inspect its vertices, or draw a missing surface. Tap vertices to select; use Move vertex then tap its destination. All distances are yards in this hole’s original map frame.</p>
  <div class="form-grid"><label class="field">Shape<select id="edit-shape"><option value="">Choose a shape</option><option value="boundary:0">Game boundary</option>${surfaceKinds.flatMap(k=>c.surfaces[k].map((p,i)=>`<option value="${k}:${i}">${esc(k)} ${i+1} · ${p.outer.length} vertices</option>`)).join('')}</select></label>
  <label class="field">Map tool<select id="edit-tool"><option value="inspect">Inspect / select vertex</option><option value="move">Move selected vertex</option><option value="draw">Draw new surface</option><option value="boundary">Draw game boundary</option><option value="hole">Draw interior cutout</option><option value="tee">Place tee</option><option value="pin">Place pin</option></select></label>
  <label class="field">New surface<select id="edit-kind">${surfaceKinds.map(k=>`<option>${k}</option>`).join('')}</select></label><label class="field">Ring<select id="edit-ring"><option value="0">Outer boundary</option></select></label></div>
  <div class="form-foot"><button type="button" class="btn" id="edit-finish">Finish drawn shape</button><button type="button" class="btn quiet" id="edit-cancel">Cancel drawing</button><button type="button" class="btn quiet" id="edit-undo">Undo map edit</button><button type="button" class="btn danger" id="edit-remove">Remove selected surface</button></div>
  <details class="details"><summary>Precise coordinates / keyboard editing</summary><div class="form-grid"><label class="field">Vertex<select id="edit-vertex"><option value="">Select a shape first</option></select></label><label class="field">Lateral · yd<input id="edit-x" type="number" step=".1" min="-5000" max="5000"></label><label class="field">Forward · yd<input id="edit-y" type="number" step=".1" min="-5000" max="5000"></label></div><div class="form-foot"><button type="button" class="btn" id="edit-point">Apply coordinate / add drawing point</button><button type="button" class="btn quiet" id="edit-insert">Insert after vertex</button><button type="button" class="btn quiet" id="edit-delete">Delete vertex</button></div></details>
  <p id="edit-status" role="status">Map corrections are drafts until published. Unknown ground plays as rough.</p></section>`;
}

export function bindEditor(panel,c,apply,undo,canUndo,notice,pendingChanged=()=>{}) {
  const svg=panel.querySelector('.import-map'),$=id=>panel.querySelector('#'+id);
  let selected=null,ring=0,vertex=0,points=[],busy=false;
  const geometry=editsFrom(c),group=document.createElementNS('http://www.w3.org/2000/svg','g');svg.append(group);
  const poly=()=>selected?(selected.kind==='boundary'?geometry.boundary:geometry.surfaces[selected.kind][selected.index]):null;
  const vertices=()=>poly()?(ring?poly().holes[ring-1]:poly().outer):[];
  const pointFields=()=>{const p=vertices()[vertex];if(p){$('edit-x').value=p[0];$('edit-y').value=p[1];}};
  function draw(){
    pendingChanged(points.length>0);
    const p=poly(),r=c.viewbox[2]/170;
    group.innerHTML=(p?`<path d="${polygonPath(p)}" fill="none" stroke="#ffdc77" stroke-width="2" vector-effect="non-scaling-stroke"/>`:'')+
      vertices().map((v,i)=>`<circle data-vertex="${i}" cx="${v[1]}" cy="${v[0]}" r="${r*2}" fill="transparent" stroke="transparent"/><circle data-vertex="${i}" cx="${v[1]}" cy="${v[0]}" r="${r*.6}" fill="${i===vertex?'#ffdc77':'#fff'}" stroke="#142638" stroke-width=".4"/>`).join('')+
      (points.length?`<polyline points="${points.map(p=>`${p[1]},${p[0]}`).join(' ')}" fill="#35c7ff22" stroke="#35c7ff" stroke-width="2" vector-effect="non-scaling-stroke"/>${points.map(p=>`<circle cx="${p[1]}" cy="${p[0]}" r="${r*.6}" fill="#35c7ff"/>`).join('')}`:'');
    $('edit-vertex').innerHTML=vertices().map((_,i)=>`<option value="${i}">Vertex ${i+1}</option>`).join('');$('edit-vertex').value=vertex;
    $('edit-status').textContent=points.length?`${points.length} drawing points · finish with at least 3. Changes are not applied until Finish drawn shape.`:selected?`${selected.kind} ${selected.index+1} · vertex ${vertex+1} of ${vertices().length}.`:'Select a shape or choose a drawing tool.';
  }
  async function commit(change){if(busy)return;busy=true;try{await apply(changeGeometry(geometry,change));}catch(e){notice(e.message);}finally{busy=false;}}
  $('edit-undo').disabled=!canUndo;$('edit-undo').onclick=()=>undo().catch(e=>notice(e.message));
  $('edit-shape').onchange=e=>{const [kind,i]=e.target.value.split(':');selected=kind?{kind,index:Number(i)}:null;ring=0;vertex=0;points=[];$('edit-ring').innerHTML='<option value="0">Outer boundary</option>'+(poly()?.holes??[]).map((_,i)=>`<option value="${i+1}">Interior cutout ${i+1}</option>`).join('');draw();pointFields();};
  $('edit-ring').onchange=e=>{ring=Number(e.target.value);vertex=0;draw();pointFields();};
  $('edit-vertex').onchange=e=>{vertex=Number(e.target.value);draw();pointFields();};
  $('edit-tool').onchange=()=>{points=[];draw();};
  $('edit-cancel').onclick=()=>{points=[];draw();};
  function usePoint(point){
    const tool=$('edit-tool').value;
    if(['draw','boundary','hole'].includes(tool)){points.push(point);draw();}
    else if(['tee','pin'].includes(tool))commit({action:tool,point});
    else if(selected&&tool==='move')commit({...selected,ring,vertex,action:'move',point});
    else notice('Choose a drawing or placement tool, or select a vertex and use Move selected vertex.');
  }
  svg.onclick=e=>{const target=e.target.closest('[data-vertex]');if(target&&$('edit-tool').value==='inspect'){vertex=Number(target.dataset.vertex);draw();pointFields();return;}
    const p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const map=p.matrixTransform(svg.getScreenCTM().inverse());usePoint([Number(map.y.toFixed(2)),Number(map.x.toFixed(2))]);};
  const inputPoint=()=>{if(!$('edit-x').value||!$('edit-y').value)throw Error('Enter both coordinate values.');const p=[Number($('edit-x').value),Number($('edit-y').value)];if(p.some(v=>!Number.isFinite(v)||Math.abs(v)>5000))throw Error('Use finite coordinates within ±5,000 yd.');return p;};
  $('edit-point').onclick=()=>{try{const p=inputPoint();if($('edit-tool').value==='inspect'&&selected)commit({...selected,ring,vertex,action:'move',point:p});else usePoint(p);}catch(e){notice(e.message);}};
  for(const action of ['insert','delete'])$('edit-'+action).onclick=()=>{if(!selected)return notice('Choose a shape first.');try{commit({...selected,ring,vertex,action,point:action==='insert'?inputPoint():null});}catch(e){notice(e.message);}};
  $('edit-finish').onclick=()=>{if(points.length<3)return notice('Draw at least three points.');const tool=$('edit-tool').value;if(tool==='hole'&&!selected)return notice('Choose the surface receiving this cutout.');if(!['draw','boundary','hole'].includes(tool))return notice('Choose a drawing tool first.');commit({...(selected??{}),action:tool==='draw'?'add':tool,kind:tool==='draw'?$('edit-kind').value:selected?.kind,points});};
  $('edit-remove').onclick=()=>{if(!selected||selected.kind==='boundary')return notice('Choose a surface. Replace the game boundary by drawing a new one.');commit({...selected,action:'remove'});};
  draw();
}
