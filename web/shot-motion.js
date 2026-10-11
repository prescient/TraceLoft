// Presentation only. None of these paths or clocks participate in scoring.
const finite = Number.isFinite;
const clamp = x => Math.max(0, Math.min(1, x));
const lerp = (a, b, t) => a + (b - a) * t;
const vector = p => Array.isArray(p) && p.length === 2 && p.every(finite);

export function shotMotion(shot, game = false) {
  if (!shot || shot.removed || shot.game_correction) return null;
  const v = shot.vals ?? {},
    o = shot.game_outcome;
  if (game && (!o?.applied || !vector(o.before?.position) || !vector(o.endpoint))) return null;
  if (game && o.putting)
    return {
      points: [
        { t: 0, x: o.before.position[1], y: o.before.position[0], z: 0 },
        { t: 1.5, x: o.endpoint[1], y: o.endpoint[0], z: 0 }
      ],
      duration: 1.5,
      airTime: 0,
      label: 'Putting estimate · illustrative roll timing'
    };
  const f = shot.flight?.status === 'ready' ? shot.flight : null;
  const trajectory = (f?.trajectory ?? []).filter(p => ['t', 'x', 'y', 'z'].every(k => finite(p[k])));
  const model =
    f && trajectory.length > 1 && trajectory.at(-1).t > trajectory[0].t && trajectory.at(-1).x > 0;
  const measured = finite(v.total) && v.total >= 0 && finite(v.carry) && v.carry >= 0 && v.carry <= v.total;
  let total, carry, right, label;
  if (measured) {
    total = v.total;
    carry = v.carry;
    right = finite(v.offline) ? v.offline : null;
    label = 'Source carry / total';
  } else if (finite(v.total) && v.total >= 0) {
    total = v.total;
    carry = null;
    right = finite(v.offline) ? v.offline : null;
    label = 'Source total';
  } else if (
    !game &&
    vector(f?.total_point_yd && [f.total_point_yd.forward, f.total_point_yd.right]) &&
    finite(f.carry_point_yd?.forward)
  ) {
    total = f.total_point_yd.forward;
    carry = f.carry_point_yd.forward;
    right = f.total_point_yd.right;
    label = 'OpenGolfCoach endpoints';
  } else return null;
  if (right === null) {
    if (
      finite(f?.total_point_yd?.right) &&
      finite(f?.total_point_yd?.forward) &&
      f.total_point_yd.forward > 0
    ) {
      right = (f.total_point_yd.right * total) / f.total_point_yd.forward;
      label += ' · estimated offline';
    } else {
      right = 0;
      label += ' · direction unavailable (side view only)';
    }
  }
  const directionKnown = finite(v.offline) || finite(f?.total_point_yd?.right);
  if (carry === null && model && f.metrics?.total_yd > 0) {
    carry = total * clamp(f.metrics.carry_yd / f.metrics.total_yd);
    label += ' · estimated carry';
  }
  const hang = f?.metrics?.hang_time_s;
  const airTime = model && finite(hang) && hang > 0 && hang <= 30 && finite(carry) && carry > 0 ? hang : 0;
  let points;
  if (airTime) {
    const end = trajectory.at(-1),
      start = trajectory[0],
      landingRight = total > 0 ? (right * carry) / total : 0;
    // Fit modeled shape to distance anchors. Landing lateral position is an estimate,
    // not a claimed carry-offline measurement. Height and flight clock remain modeled.
    points = trajectory.map(p => {
      const u = clamp((p.t - start.t) / (end.t - start.t)),
        progress = p.x / end.x;
      return {
        t: u * airTime,
        x: progress * carry,
        y: progress * landingRight + (p.y - progress * end.y) / 0.9144,
        z: Math.max(0, p.z / 0.9144)
      };
    });
    points[0] = { t: 0, x: 0, y: 0, z: 0 };
    points[points.length - 1] = { t: airTime, x: carry, y: landingRight, z: 0 };
    label += ' · OpenGolfCoach shape & hang time';
    if (total > carry + 0.01) {
      const rollTime = Math.max(0.6, Math.min(2.5, Math.sqrt(total - carry) * 0.3));
      for (let i = 1; i <= 20; i++) {
        const u = i / 20,
          e = 1 - (1 - u) ** 2;
        points.push({
          t: airTime + u * rollTime,
          x: lerp(carry, total, e),
          y: lerp(landingRight, right, e),
          z: 0
        });
      }
    }
  } else {
    points = [
      { t: 0, x: 0, y: 0, z: 0 },
      { t: 1.2, x: total, y: right, z: 0 }
    ];
    label += ' · endpoint replay (flight unavailable)';
  }
  if (game) {
    const heading = (((o.aim_heading_degrees ?? 0) + (o.random_degrees ?? 0)) * Math.PI) / 180;
    const cs = Math.cos(heading),
      sn = Math.sin(heading),
      start = o.before.position;
    // Fit to the frozen game endpoint, including radial geometry and saved lie effects.
    const end = points.at(-1),
      factor = o.distance_factor ?? 1;
    const rule = o.landing_rollout,
      land = rule?.applied && vector(rule.landing_point) && airTime > 0 ? rule : null;
    const base = land && vector(land.base_endpoint) ? land.base_endpoint : o.endpoint;
    const dx = base[1] - start[1],
      dy = base[0] - start[0],
      originalDuration = points.at(-1).t;
    if (land && land.adjusted_rollout_yd <= 0.01) points = points.filter(p => p.t <= airTime);
    points = points.map(p => {
      const u = total > 0 ? p.x / total : 0,
        curve = p.y - (total > 0 ? (p.x / total) * end.y : 0);
      if (land && p.t >= airTime) {
        const progress = total > carry ? clamp((p.x - carry) / (total - carry)) : 0;
        const rollTime = Math.max(0.6, Math.min(2.5, Math.sqrt(land.adjusted_rollout_yd) * 0.3));
        return {
          ...p,
          t:
            originalDuration > airTime
              ? airTime + ((p.t - airTime) / (originalDuration - airTime)) * rollTime
              : airTime,
          x: lerp(land.landing_point[1], o.endpoint[1], progress),
          y: lerp(land.landing_point[0], o.endpoint[0], progress),
          z: 0
        };
      }
      return { ...p, x: start[1] + u * dx - curve * factor * sn, y: start[0] + u * dy + curve * factor * cs };
    });
    points[points.length - 1] = { ...points.at(-1), x: o.endpoint[1], y: o.endpoint[0], z: 0 };
    label += ' · saved lie adjustments';
  }
  if (points.some(p => !Object.values(p).every(finite))) return null;
  return { points, airTime, duration: points.at(-1).t, label, directionKnown, carry, total };
}

export function motionFrame(plan, seconds) {
  const p = plan.points,
    t = Math.max(0, Math.min(plan.duration, seconds));
  const i = p.findIndex(v => v.t >= t);
  if (i <= 0) return { ...(i === 0 ? p[0] : p.at(-1)), phase: t < plan.airTime ? 'Flight' : 'Roll' };
  const a = p[i - 1],
    b = p[i],
    u = b.t === a.t ? 1 : (t - a.t) / (b.t - a.t);
  return {
    x: lerp(a.x, b.x, u),
    y: lerp(a.y, b.y, u),
    z: lerp(a.z, b.z, u),
    phase: t < plan.airTime ? 'Flight' : 'Roll'
  };
}

// A new page/session establishes a baseline; redraws and tag/filter edits never replay.
export class MotionClock {
  constructor() {
    this.reset();
  }
  reset() {
    this.scope = null;
    this.key = null;
    this.started = null;
    this.plan = null;
  }
  observe(scope, key, plan, live, now, reduced = false) {
    if (this.scope !== scope) {
      this.scope = scope;
      this.key = key;
      this.started = null;
      this.plan = null;
      return;
    }
    if (this.key !== key) {
      this.key = key;
      this.started = live && !reduced && plan ? now : null;
      this.plan = plan;
    }
    if (!plan || reduced) {
      this.started = null;
      this.plan = null;
    }
  }
  playing(now) {
    return this.started !== null && this.plan && now - this.started < this.plan.duration * 1000;
  }
}
const clock = new MotionClock();
let frameId = null;
export function resetShotMotion() {
  clock.reset();
  if (frameId !== null) cancelAnimationFrame(frameId);
}
export function observeShotMotion(scope, shot, plan, live) {
  clock.observe(
    scope,
    shot?.key ?? null,
    plan,
    live,
    performance.now(),
    matchMedia('(prefers-reduced-motion: reduce)').matches || document.hidden
  );
  return !!clock.playing(performance.now());
}
export function motionControls(plan) {
  return `<div class="shot-motion-controls"><span class="form-hint" data-motion-status>${plan ? 'Illustrative replay · roll timing estimated' : 'Flight unavailable · waiting for usable shot data'}</span><button class="btn small quiet" type="button" data-motion-replay ${plan ? '' : 'disabled'}>Replay ball</button><button class="btn small quiet" type="button" data-motion-skip hidden>Skip</button></div>`;
}
export function mountShotMotion(root, svg, plan, project, onFinish = () => {}) {
  if (frameId !== null) cancelAnimationFrame(frameId);
  const replay = root.querySelector('[data-motion-replay]'),
    skip = root.querySelector('[data-motion-skip]'),
    status = root.querySelector('[data-motion-status]');
  if (!svg || !plan) {
    if (replay) replay.disabled = true;
    return;
  }
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  replay.disabled = reduced.matches;
  replay.title = reduced.matches ? 'Animation disabled by your reduced-motion preference' : '';
  const ns = 'http://www.w3.org/2000/svg',
    group = document.createElementNS(ns, 'g'),
    ball = document.createElementNS(ns, 'circle');
  group.setAttribute('pointer-events', 'none');
  group.setAttribute('aria-hidden', 'true');
  group.classList.add('shot-motion-layer');
  const trails = svg.classList.contains('game-map')
    ? ['#fff', '#1265ff'].map((color, i) => {
        const path = document.createElementNS(ns, 'path');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', color);
        path.setAttribute('stroke-width', i ? '2' : '4');
        path.setAttribute('vector-effect', 'non-scaling-stroke');
        group.append(path);
        return path;
      })
    : [];
  ball.setAttribute('fill', '#fff');
  ball.setAttribute('stroke', '#1265ff');
  ball.setAttribute('stroke-width', '2');
  ball.setAttribute('vector-effect', 'non-scaling-stroke');
  group.append(ball);
  svg.append(group);
  const current = svg.querySelector('.game-current-ball');
  const finish = () => {
    clock.started = null;
    group.remove();
    if (current) current.style.visibility = '';
    skip.hidden = true;
    replay.hidden = false;
    status.textContent = reduced.matches
      ? 'Reduced motion · saved result shown'
      : 'Saved result · illustrative path; roll timing estimated';
    onFinish();
  };
  const tick = now => {
    if (!svg.isConnected) return;
    if (document.hidden || reduced.matches || !clock.playing(now)) {
      finish();
      return;
    }
    const sample = motionFrame(plan, (now - clock.started) / 1000),
      [x, y] = project(sample);
    const trace = [...plan.points.filter(p => p.t < (now - clock.started) / 1000), sample]
      .map((p, i) => `${i ? 'L' : 'M'}${project(p).join(',')}`)
      .join(' ');
    trails.forEach(path => path.setAttribute('d', trace));
    const scale = svg.viewBox.baseVal.width / Math.max(1, svg.getBoundingClientRect().width);
    ball.setAttribute('cx', x);
    ball.setAttribute('cy', y);
    ball.setAttribute('r', scale * (5 + Math.min(4, sample.z / 10)));
    skip.hidden = false;
    replay.hidden = true;
    if (current) current.style.visibility = 'hidden';
    status.textContent = `${sample.phase === 'Flight' ? 'Flight · OpenGolfCoach ' + plan.airTime.toFixed(1) + ' s' : plan.airTime ? 'Roll · illustrative timing' : 'Endpoint replay · illustrative timing'} · shot already saved`;
    frameId = requestAnimationFrame(tick);
  };
  replay.onclick = () => {
    clock.plan = plan;
    clock.started = performance.now();
    onFinish();
  };
  skip.onclick = finish;
  if (clock.playing(performance.now())) tick(performance.now());
  else {
    group.remove();
    if (reduced.matches) status.textContent = 'Reduced motion · saved result shown';
  }
}

export function motionChart(plan, view = 'side') {
  if (!plan)
    return '<div class="range-flight-empty">Record carry / total or valid launch inputs to see the shot.</div>';
  if (view === 'top' && !plan.directionKnown)
    return '<div class="range-flight-empty">Top view needs offline or a valid flight estimate. Side view is available.</div>';
  const xmax = Math.max(1, ...plan.points.map(p => p.x)),
    zmax = Math.max(10, ...plan.points.map(p => p.z * 3)),
    side = Math.max(10, ...plan.points.map(p => Math.abs(p.y)));
  const project = p =>
    view === 'top'
      ? [265 + (p.y / side) * 205, 255 - (p.x / xmax) * 220]
      : [45 + (p.x / xmax) * 440, 185 - ((p.z * 3) / zmax) * 155];
  const path = plan.points.map((p, i) => `${i ? 'L' : 'M'}${project(p).join(',')}`).join(' ');
  const landing = project(motionFrame(plan, plan.airTime)),
    end = project(plan.points.at(-1));
  return `<svg class="range-flight shot-flight" viewBox="0 0 515 ${view === 'top' ? 300 : 225}" role="img" aria-label="Illustrative ball flight and rollout"><path d="${path}" class="range-flight-path"/>${plan.airTime ? `<circle cx="${landing[0]}" cy="${landing[1]}" r="4" fill="white" stroke="var(--accent)"><title>Estimated landing at carry distance</title></circle>` : ''}<circle cx="${end[0]}" cy="${end[1]}" r="4" fill="var(--accent)"><title>Stopping distance</title></circle><text x="45" y="${view === 'top' ? 279 : 209}">0</text><text x="490" y="${view === 'top' ? 279 : 209}" text-anchor="end">${Math.round(xmax)} yd</text>${view === 'side' ? `<text x="45" y="32">${Math.round(zmax)} ft</text>` : '<text x="265" y="299" text-anchor="middle">Forward ↑ · right → (axes scaled independently)</text>'}</svg>`;
}
export function chartProjection(plan, view) {
  const xmax = Math.max(1, ...plan.points.map(p => p.x)),
    zmax = Math.max(10, ...plan.points.map(p => p.z * 3)),
    side = Math.max(10, ...plan.points.map(p => Math.abs(p.y)));
  return p =>
    view === 'top'
      ? [265 + (p.y / side) * 205, 255 - (p.x / xmax) * 220]
      : [45 + (p.x / xmax) * 440, 185 - ((p.z * 3) / zmax) * 155];
}
