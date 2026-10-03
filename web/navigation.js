// Stable locations for the studio's screens, including saved-session reviews.
const drillIds = new Set(['pace', 'line', 'combined', 'random', 'ladder', 'distance-ladder', 'driving-range', 'iron-ladder', 'wedge-ladder', 'bag-mapping', 'wedge-matrix', 'golf-sim']);
const sessionId = /^[0-9a-f]{32}$/;

export function parseRoute(hash) {
  const parts = hash.replace(/^#/, '').split('/');
  if(parts.length===2&&parts[0]==='play'&&parts[1]==='import')return {view:'course-import'};
  if (parts.length === 1) {
    if (['relay', 'capture', 'practice', 'play', 'analyze', 'sessions'].includes(parts[0]))
      return {view: parts[0] === 'practice' ? 'choose' : parts[0] === 'capture' ? 'relay' : parts[0]};
    return null;
  }
  if (parts[0] === 'setup' && drillIds.has(parts[1]) &&
      (parts.length === 2 || parts.length === 3 && sessionId.test(parts[2])))
    return {view: 'setup', drillId: parts[1], sessionId: parts[2]};
  if (parts.length === 2 && sessionId.test(parts[1])) {
    if (parts[0] === 'practice') return {view: 'runner', sessionId: parts[1], review: false};
    if (parts[0] === 'sessions') return {view: 'runner', sessionId: parts[1], review: true};
  }
  return null;
}

export function routeFor(view, {practice, review, drill}) {
  if(view==='course-import')return '#play/import';
  if (view === 'runner') {
    const id = review?.practice.id ?? practice?.id;
    return id ? `#${review ? 'sessions' : 'practice'}/${id}` : '#practice';
  }
  if (view === 'setup')
    return `#setup/${drill.id}${drill.parameters?.id ? `/${drill.parameters.id}` : ''}`;
  return view === 'choose' ? '#practice' : `#${view}`;
}
