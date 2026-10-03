export function escape(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
export const direction = value => `${Math.abs(value).toFixed(1)}°${value < 0 ? ' L' : value > 0 ? ' R' : ''}`;
export const error = value => `${value >= 0 ? '+' : ''}${value.toFixed(1)}`;

function range(values, target, tolerance, pace) {
  let low = Math.min(target - tolerance, target - (pace ? .5 : 2), ...values);
  let high = Math.max(target + tolerance, target + (pace ? .5 : 2), ...values);
  const padding = (high - low) * .12;
  low -= padding; high += padding;
  const raw = (high - low) / 5;
  const power = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map(n => n * power).find(n => n >= raw);
  return {low:Math.floor(low / step) * step, high:Math.ceil(high / step) * step, step};
}

export function trend(session, pace = true, distance = false) {
  const shots = session.shots, width = 600, height = pace ? 385 : 245;
  const left = 55, right = 574, top = 16, bottom = height - 45;
  const field = pace ? 'ball_speed' : 'launch_dir';
  const target = distance ? session.target_distance_ft : pace ? session.target : 0;
  const tolerance = distance ? session.distance_tolerance : pace ? session.speed_tolerance : session.angle_tolerance;
  const values = shots.map(s => distance ? s.estimated_distance_ft : s.vals[field]);
  const targets = shots.map(s => distance ? s.target_distance_ft : pace ? (s.target ?? target) : 0);
  const domain = [...values, ...targets.map(t => t - tolerance), ...targets.map(t => t + tolerance)];
  if (distance && session.ladder_targets_ft) domain.push(...session.ladder_targets_ft.flatMap(t=>[t-tolerance,t+tolerance]));
  if (pace && session.random_pace) domain.push(session.minimum - tolerance, session.maximum + tolerance);
  const bounds = range(domain, target, tolerance, pace);
  const y = v => bottom - (v - bounds.low) / (bounds.high - bounds.low) * (bottom - top);
  const x = i => left + i / Math.max(1, shots.length - 1) * (right - left);
  const random = pace && (session.random_pace || session.drill==='Putting ladder');
  let bands = '', grid = '', targetLines = '', series = '';
  const band = (l,r,t) => `<rect class="band" x="${l}" y="${y(t + tolerance)}" width="${r-l}" height="${y(t-tolerance)-y(t+tolerance)}"/>`;
  const line = (l,r,t) => `<line class="target" stroke-dasharray="5 4" x1="${l}" x2="${r}" y1="${y(t)}" y2="${y(t)}"/>`;
  if (!random || !shots.length) { bands = band(left,right,target); targetLines = line(left,right,target); }
  else targets.forEach((t,i) => {
    const l = i ? (x(i-1)+x(i))/2 : left, r = i === shots.length-1 ? right : (x(i)+x(i+1))/2;
    bands += band(l,r,t); targetLines += line(l,r,t);
  });
  for (let i=0; i<=Math.round((bounds.high-bounds.low)/bounds.step); i++) {
    const value = bounds.low + i * bounds.step;
    grid += `<line class="grid" x1="${left}" x2="${right}" y1="${y(value)}" y2="${y(value)}"/><text x="${left-12}" y="${y(value)+4}" text-anchor="end">${value.toFixed(1)}</text>`;
  }
  let previous = null;
  shots.forEach((shot,i) => {
    const px = x(i), py = y(values[i]), last = i === shots.length-1;
    const scored = pace || !['Pace consistency','Putting ladder'].includes(session.drill);
    const miss = scored && Math.abs(values[i]-targets[i]) > tolerance + 1e-9;
    if (previous && !shot.excluded) series += `<path class="series" d="M${previous[0]},${previous[1]} L${px},${py}"/>`;
    previous = shot.excluded ? null : [px,py];
    series += `<g data-key="${escape(shot.key)}"><title>Putt ${i+1}: ${values[i].toFixed(1)} ${distance?'estimated ft':pace?'mph':'degrees'}, target ${targets[i].toFixed(1)}${shot.excluded?', excluded':''}</title><circle class="point${last?' latest':''}${last&&miss?' miss':''}${shot.excluded?' excluded':''}" cx="${px}" cy="${py}" r="${last?7:4.5}"/>${shot.excluded?`<path d="M${px-4},${py-4}L${px+4},${py+4}" stroke="#fff"/>`:''}</g>`;
    if (shots.length<=15 || !i || last) series += `<text x="${px}" y="${bottom+22}" text-anchor="middle">${i+1}</text>`;
  });
  if (!shots.length) series = `<text x="${(left+right)/2}" y="${(top+bottom)/2}" text-anchor="middle">Your putts will appear here</text>`;
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${distance?'Estimated travel in feet':pace?'Ball speed in mph':'Launch direction in degrees'} by putt, with target zone and latest putt highlighted">${bands}${grid}${targetLines}${series}<text x="${(left+right)/2}" y="${height-5}" text-anchor="middle">Putt number</text></svg>`;
}

export function gauge(session) {
  const shot = session.shots.at(-1), value = shot?.vals.launch_dir ?? 0, tolerance = session.angle_tolerance;
  const limit = Math.ceil(Math.max(2,tolerance*1.5,Math.abs(value)*1.2)*2)/2;
  const left=34,right=566,cy=75,x=v=>left+(v+limit)/(limit*2)*(right-left);
  const scored = !['Pace consistency','Putting ladder'].includes(session.drill);
  const color = shot?.excluded ? '#8295aa' : !scored ? 'var(--muted)' : Math.abs(value)<=tolerance+1e-9 ? 'var(--accent)' : 'var(--amber)';
  const ticks = [...new Set([-limit,-tolerance,0,tolerance,limit])].map(v=>`<line x1="${x(v)}" x2="${x(v)}" y1="${cy-20}" y2="${cy+20}" stroke="${v===0?'var(--ink)':'var(--muted)'}"/>`).join('');
  return `<svg class="chart gauge" viewBox="0 0 600 132" role="img" aria-label="Latest start line ${shot?direction(value):'waiting'}, target plus or minus ${tolerance} degrees"><text x="34" y="18">Left ${limit.toFixed(1)}°</text><text x="566" y="18" text-anchor="end">Right ${limit.toFixed(1)}°</text><rect x="${left}" y="${cy-10}" width="${right-left}" height="20" rx="4" fill="var(--grid)"/><rect x="${x(-tolerance)}" y="${cy-10}" width="${x(tolerance)-x(-tolerance)}" height="20" fill="#c4d5ff"/>${ticks}${shot?`<text x="${x(value)}" y="${cy-29}" text-anchor="middle" fill="${color}" class="${color==='var(--amber)'?'miss-text':'latest-text'}">${direction(value)}</text><circle cx="${x(value)}" cy="${cy}" r="10" fill="${color}" stroke="var(--accent)" stroke-width="3"/>`:''}<text x="${x(0)}" y="${cy+35}" text-anchor="middle">0°</text></svg>`;
}

export function progress(count, total, noun='putts') {
  const percent = Math.min(1,count/total)*100;
  return `<svg class="progress-track" viewBox="0 0 300 14" preserveAspectRatio="none" role="img" aria-label="${count} of ${total} ${noun} captured"><rect width="300" height="14" rx="7" fill="var(--grid)"/><rect width="${3*percent}" height="14" rx="7" fill="var(--accent)"/></svg><span>${Math.round(percent)}%</span>`;
}

export function distanceTrend(session, errors=false) {
  const shots=session.shots, width=600,height=340,left=56,right=574,top=18,bottom=292;
  const tolerance=session.range_tolerance, target=errors?0:session.target;
  const values=shots.map(s=>errors?s.distance_error_yd:s.distance_yd);
  const targets=shots.map(s=>errors?0:s.target_distance_yd);
  const domain=[...values.filter(Number.isFinite),...targets.flatMap(t=>[t-tolerance,t+tolerance])];
  if(!errors)domain.push(...session.ladder_targets_yd);
  const bounds=range(domain,target,tolerance,false);
  const x=i=>left+i/Math.max(1,shots.length-1)*(right-left);
  const y=v=>bottom-(v-bounds.low)/(bounds.high-bounds.low)*(bottom-top);
  let bands='',lines='',grid='',series='',previous=null;
  const windows=shots.length?targets:[target];
  windows.forEach((t,i)=>{const l=i?(x(i-1)+x(i))/2:left,r=i===windows.length-1?right:(x(i)+x(i+1))/2;bands+=`<rect class="band" x="${l}" y="${y(t+tolerance)}" width="${r-l}" height="${y(t-tolerance)-y(t+tolerance)}"/>`;lines+=`<line class="target" x1="${l}" x2="${r}" y1="${y(t)}" y2="${y(t)}"/>`;});
  for(let i=0;i<=Math.round((bounds.high-bounds.low)/bounds.step);i++) {
    const v=bounds.low+i*bounds.step;
    grid+=`<line class="grid" x1="${left}" x2="${right}" y1="${y(v)}" y2="${y(v)}"/><text x="${left-10}" y="${y(v)+4}" text-anchor="end">${v.toFixed(0)}</text>`;
  }
  shots.forEach((s,i)=>{
    if(Number.isFinite(values[i])) {
      const px=x(i),py=y(values[i]),last=i===shots.length-1;
      if(previous&&!s.excluded)series+=`<path class="series" d="M${previous[0]},${previous[1]}L${px},${py}"/>`;
      previous=s.excluded?null:[px,py];
      series+=`<g data-key="${escape(s.key)}"><title>Shot ${i+1}: ${values[i].toFixed(1)} yd${errors?' error':`, target ${s.target_distance_yd} yd`}${s.excluded?', excluded':''}</title><circle class="point${last?' latest':''}${!s.success?' miss':''}${s.excluded?' excluded':''}" cx="${px}" cy="${py}" r="${last?7:4.5}"/></g>`;
    }else previous=null;
    if(shots.length<=15||i===0||i===shots.length-1)series+=`<text x="${x(i)}" y="${bottom+24}" text-anchor="middle">${i+1}</text>`;
  });
  if(!shots.length)series=`<text x="315" y="155" text-anchor="middle">Your shots will appear here</text>`;
  return `<svg class="chart distance-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${errors?'Distance error':session.range_metric+' versus target'} in yards by shot">${bands}${grid}${lines}${series}<text x="315" y="335" text-anchor="middle">Shot number</text></svg>`;
}
