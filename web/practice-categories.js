import {escape as esc} from './charts.js';

export const categories = [
  ['full','Full swing','Explore your whole game.',['driving-range','distance-ladder','bag-mapping']],
  ['irons','Irons','Build reliable approach distances.',['iron-ladder']],
  ['wedges','Wedges','Dial in scoring distances.',['wedge-ladder','wedge-matrix']],
  ['putting','Putting','Train pace, start line and touch.',['pace','line','combined','random','ladder']],
];
export function categorizedDrills(drills) {
  const ladder=drills.find(d=>d.id==='distance-ladder');
  return [...drills,...(ladder?['iron','wedge'].map(kind=>({...ladder,id:`${kind}-ladder`,
    title:`${kind==='iron'?'Iron':'Wedge'} distance ladder`,defaults:{range_category:kind==='iron'?'irons':'wedges',
      range_start:kind==='iron'?90:30,range_end:kind==='iron'?170:100,range_step:10}})):[])];
}
export function categoryMarkup(drills) {
  return categories.map(([id,title,description,ids])=>{
    const available=ids.map(id=>drills.find(d=>d.id===id)).filter(Boolean);
    return `<section class="card practice-category"><h2><button class="category-toggle" data-category="${id}" aria-expanded="false" aria-controls="category-${id}"><span><strong>${title}</strong><small>${description}</small></span><span class="category-count">${available.length} ${available.length===1?'activity':'activities'} <span aria-hidden="true">＋</span></span></button></h2><div class="drill-grid category-content" id="category-${id}" hidden>${available.map(d=>`<section class="drill-card"><h3>${esc(d.title)}</h3><p>${esc(d.description)}</p><button class="btn primary" data-action="choose" data-drill="${d.id}">Set up →</button></section>`).join('')}</div></section>`;
  }).join('');
}
export function bindCategories(app) {
  let expanded=[];
  try {expanded=JSON.parse(sessionStorage.getItem('practice-categories')||'[]');}catch{}
  if(!Array.isArray(expanded))expanded=[];
  const set=(button,open)=>{button.setAttribute('aria-expanded',String(open));app.querySelector(`#category-${button.dataset.category}`).hidden=!open;button.querySelector('[aria-hidden]').textContent=open?'−':'＋';};
  app.querySelectorAll('[data-category]').forEach(button=>{
    set(button,expanded.includes(button.dataset.category));
    button.onclick=()=>{const open=button.getAttribute('aria-expanded')!=='true';set(button,open);
      expanded=[...app.querySelectorAll('[data-category][aria-expanded="true"]')].map(b=>b.dataset.category);
      try{sessionStorage.setItem('practice-categories',JSON.stringify(expanded));}catch{}
    };
  });
}
