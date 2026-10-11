/** Keep local reading/editing context across a same-session live repaint. */
export function preserveInteraction(root, repaint) {
  const controls = [...root.querySelectorAll('input,textarea,select,button,a')];
  const active = root.ownerDocument.activeElement;
  const identity = element => element.id ? `id:${element.id}` :
    element.getAttribute('name') ? `name:${element.getAttribute('name')}` :
    [...element.attributes].filter(a=>a.name.startsWith('data-')).map(a=>`${a.name}:${a.value}`).join('|');
  const focusedIndex = controls.indexOf(active);
  const key = focusedIndex >= 0 ? identity(active) : '';
  const drafts = controls.filter(el=>['INPUT','TEXTAREA'].includes(el.tagName) &&
    !['hidden','checkbox','radio','file','submit','button'].includes(el.type) && el.value !== el.defaultValue)
    .map(el=>({key:identity(el),value:el.value})).filter(item=>item.key);
  const caret = focusedIndex >= 0 && typeof active.selectionStart === 'number' ?
    [active.selectionStart,active.selectionEnd,active.selectionDirection] : null;
  const detailKey = (el,i) => el.id || el.querySelector('summary')?.textContent.trim()
    .replace(/\(\d+\)/g,'(count)').replace(/\bShot\s+\d+/g,'Shot') || `position:${i}`;
  const details = new Map([...root.querySelectorAll('details')].map((el,i)=>[detailKey(el,i),el.open]));
  const scroll = [...root.querySelectorAll('.table-wrap')].map(el=>[el.scrollLeft,el.scrollTop]);
  const win = root.ownerDocument.defaultView;
  const position = win ? [win.scrollX,win.scrollY] : null;
  repaint();
  const nextControls = [...root.querySelectorAll('input,textarea,select,button,a')];
  for (const draft of drafts) {
    const next = nextControls.find(el=>identity(el) === draft.key);
    if (next && !next.disabled) next.value = draft.value;
  }
  root.querySelectorAll('details').forEach((el,i)=>{const key=detailKey(el,i);if(details.has(key))el.open=details.get(key);});
  root.querySelectorAll('.table-wrap').forEach((el,i)=>{if(scroll[i])[el.scrollLeft,el.scrollTop]=scroll[i];});
  const focused = key ? nextControls.find(el=>identity(el) === key) :
    focusedIndex >= 0 ? nextControls[focusedIndex] : null;
  if (focused && !focused.disabled) {
    focused.focus({preventScroll:true});
    if (caret && typeof focused.setSelectionRange === 'function') focused.setSelectionRange(...caret);
  }
  if (position) win.scrollTo({left:position[0],top:position[1],behavior:'instant'});
}
