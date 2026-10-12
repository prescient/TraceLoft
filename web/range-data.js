// Pure range view calculations. Measurements and predictions stay in separate namespaces.
export const equipment = s => s.corrected_equipment ?? s;
export const valid = n => typeof n === 'number' && Number.isFinite(n);
export const included = s => !s.excluded && !s.removed;
export const format = (n, d = 1) => (valid(n) ? n.toFixed(d).replace(/\.0$/, '') : '—');
const CLUB_COLORS = [
  '#1455ed',
  '#087b69',
  '#b76006',
  '#853fbe',
  '#ba3276',
  '#707915',
  '#087894',
  '#be4634',
  '#427a20',
  '#5146bb',
  '#96653b',
  '#257f72',
  '#975697',
  '#536aaa',
  '#9a7626'
];
export const clubKey = e => (e.club_id ? JSON.stringify([e.bag_id || '', e.club_id]) : 'untagged');
// Use the complete session, never the filtered/sorted plot. Reserve original tags so
// retagging or removing a club's shots does not renumber the other recorded clubs.
export function clubColors(shots) {
  const colors = new Map([['untagged', '#637084']]);
  const add = e => {
    const key = clubKey(e);
    if (!colors.has(key)) {
      const i = colors.size - 1;
      colors.set(key, CLUB_COLORS[i] ?? `hsl(${(i * 137.508) % 360} 65% 40%)`);
    }
  };
  shots.forEach(add);
  shots.forEach(s => add(equipment(s)));
  return colors;
}
export function cohort(shots, filter) {
  return shots.filter(s => {
    const e = equipment(s),
      shape = s.flight?.shape ?? 'Unavailable';
    return (
      (!filter.bag || e.bag_id === filter.bag) &&
      (!filter.club || (filter.club === '__untagged__' ? !e.club_id : e.club_id === filter.club)) &&
      (!filter.shape || shape === filter.shape) &&
      (filter.status === 'all' || filter.status === 'removed'
        ? filter.status === 'all' || s.removed
        : filter.status === 'excluded'
          ? s.excluded && !s.removed
          : included(s)) &&
      (!filter.search ||
        `${e.bag_name} ${e.club_label} ${shape} ${s.cleanup_reason ?? ''}`
          .toLowerCase()
          .includes(filter.search.toLowerCase()))
    );
  });
}
// The default included table keeps excluded context on the chart, but not removed shots.
export function scatterCohort(shots, filter) {
  return filter.status === 'included'
    ? cohort(shots, { ...filter, status: 'all' }).filter(s => !s.removed)
    : cohort(shots, filter);
}
// Empirical 80% radial coverage around coordinate medians, not a confidence interval.
export function dispersionCircles(shots, metric, source) {
  const groups = new Map();
  for (const s of shots.filter(included)) {
    const e = equipment(s),
      p = point(s, metric, source);
    if (!e.club_id || !p) continue;
    const key = clubKey(e);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(p);
  }
  const median = values => {
    values.sort((a, b) => a - b);
    const i = Math.floor(values.length / 2);
    return values.length % 2 ? values[i] : (values[i - 1] + values[i]) / 2;
  };
  return new Map(
    [...groups].map(([key, points]) => {
      const count = points.length;
      if (count < 5) return [key, { count, radius: null }];
      const forward = median(points.map(p => p.forward)),
        right = median(points.map(p => p.right));
      const distances = points
        .map(p => Math.hypot(p.forward - forward, p.right - right))
        .sort((a, b) => a - b);
      return [key, { count, forward, right, radius: distances[Math.ceil(0.8 * count) - 1] }];
    })
  );
}
export function point(s, metric, source) {
  if (source === 'model') {
    const p = s.flight?.[`${metric}_point_yd`];
    return p && valid(p.forward) && valid(p.right) ? { forward: p.forward, right: p.right } : null;
  }
  return valid(s.vals[metric]) && valid(s.vals.offline)
    ? { forward: s.vals[metric], right: s.vals.offline }
    : null;
}
export function summarize(shots, metric = 'carry') {
  const values = shots
    .filter(included)
    .map(s => rangeValue(s, metric))
    .filter(valid);
  const mean = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
  return {
    count: values.length,
    mean,
    sd: values.length ? Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length) : null
  };
}
export const CLUB_METRICS = [
  { key: 'carry', label: 'Carry', unit: 'yd' },
  { key: 'total', label: 'Total', unit: 'yd' },
  { key: 'offline', label: 'Absolute offline', unit: 'yd', absolute: true },
  { key: 'launch_ang', label: 'Launch angle', unit: '°' },
  { key: 'descent_ang', label: 'Descent angle', unit: '°' }
];
// Early demo generator used 'descent'; real captures always use descent_ang.
export const sourceValue = (shot, metric) =>
  shot?.vals?.[metric] ?? (shot?.simulated && metric === 'descent_ang' ? shot.vals?.descent : undefined);
// Range distances (D63): shots recorded since 2026-10-12 carry range_vals, OpenGolfCoach estimates
// (reported only as a labeled fallback when the model is unavailable). Older shots keep reported values.
const RANGE_FIELDS = ['carry', 'total', 'offline'];
export const rangeValue = (shot, metric) =>
  RANGE_FIELDS.includes(metric) && shot?.range_vals ? shot.range_vals[metric] : sourceValue(shot, metric);
export const estimated = shot => shot?.distance_basis === 'opengolfcoach';
// Club delivery for the latest-shot panel. Values are source-reported, except a smash factor the source
// did not report, which is calculated from ball and club speed and labeled. Attack angle is
// upward-positive; club path is target-relative (right positive), so in-to-out depends on handedness.
export const CLUB_READINGS = ['club_speed', 'smash_factor', 'attack_angle', 'club_path'];
export const hasClubData = shots => shots.some(s => CLUB_READINGS.some(k => valid(s.vals?.[k])));
// Estimated delivery (D64, club_model.py): face angle and face to path read open/closed for the
// session's handedness (values are right-positive); lofts are plain degrees.
export function clubEstimates(shot, handedness = 'right_handed') {
  const e = shot?.club_estimates ?? {};
  const right = handedness !== 'left_handed';
  const openClosed = value =>
    !valid(value) || value === 0 ? '°' : `° ${(value > 0) === right ? 'open' : 'closed'}`;
  const signed = key => (valid(e[key]) ? Math.abs(e[key]) : null);
  return [
    { label: 'Face angle · est.', value: signed('face_angle'), unit: openClosed(e.face_angle), precision: 1 },
    { label: 'Face to path · est.', value: signed('face_to_path'), unit: openClosed(e.face_to_path), precision: 1 },
    { label: 'Dynamic loft · est.', value: e.dynamic_loft, unit: '°', precision: 1 },
    { label: 'Spin loft · est.', value: e.spin_loft, unit: '°', precision: 1 }
  ];
}
export function clubReadings(shot, handedness = 'right_handed') {
  const v = shot?.vals ?? {};
  const word = (value, positive, negative) => (!valid(value) || value === 0 ? '' : value > 0 ? positive : negative);
  const right = handedness !== 'left_handed';
  const calculated =
    !valid(v.smash_factor) && valid(v.ball_speed) && valid(v.club_speed) && v.club_speed > 0
      ? v.ball_speed / v.club_speed
      : null;
  return [
    { label: 'Club speed', value: v.club_speed, unit: 'mph', precision: 1 },
    {
      label: calculated == null ? 'Smash factor' : 'Smash factor · calc.',
      value: valid(v.smash_factor) ? v.smash_factor : calculated,
      unit: '',
      precision: 2
    },
    {
      label: 'Angle of attack',
      value: valid(v.attack_angle) ? Math.abs(v.attack_angle) : null,
      unit: `° ${word(v.attack_angle, 'up', 'down')}`.trim(),
      precision: 1
    },
    {
      label: 'Club path',
      value: valid(v.club_path) ? Math.abs(v.club_path) : null,
      unit: `° ${word(v.club_path, right ? 'in-to-out' : 'out-to-in', right ? 'out-to-in' : 'in-to-out')}`.trim(),
      precision: 1
    }
  ];
}
export function robustSummary(shots, metric, { absolute = false } = {}) {
  const values = shots
    .filter(included)
    .map(s => {
      const value = rangeValue(s, metric);
      return valid(value) ? (absolute ? Math.abs(value) : value) : null;
    })
    .filter(valid)
    .sort((a, b) => a - b);
  const count = values.length;
  // Linear interpolation at (n-1)*p, the inclusive/type-7 convention.
  const quantile = p => {
    const index = (count - 1) * p,
      lo = Math.floor(index),
      f = index - lo;
    return values[lo] + f * ((values[lo + 1] ?? values[lo]) - values[lo]);
  };
  const q1 = count > 1 ? quantile(0.25) : null,
    q3 = count > 1 ? quantile(0.75) : null;
  return { count, median: count ? quantile(0.5) : null, q1, q3, iqr: count > 1 ? q3 - q1 : null };
}
export function clubSummaries(shots) {
  const groups = new Map();
  shots.filter(included).forEach(s => {
    const e = equipment(s),
      key = JSON.stringify([e.bag_id || '', e.club_id || '']);
    if (!groups.has(key))
      groups.set(key, { label: `${e.bag_name || 'No bag'} / ${e.club_label || 'Untagged'}`, shots: [] });
    groups.get(key).shots.push(s);
  });
  return [...groups.values()].map(g => ({
    label: g.label,
    count: g.shots.length,
    metrics: CLUB_METRICS.map(m => robustSummary(g.shots, m.key, m))
  }));
}
export function rangeCsv(shots) {
  const headings = [
    'shot_key',
    'captured',
    'simulated',
    'original_bag',
    'original_club',
    'effective_bag',
    'effective_club',
    'excluded',
    'removed',
    'cleanup_reason',
    'target_yd',
    'carry_yd',
    'total_yd',
    'reported_offline_yd',
    'ball_speed_mph',
    'launch_angle_deg',
    'launch_direction_deg',
    'total_spin_rpm',
    'spin_axis_deg',
    'model_id',
    'model_status',
    'modeled_shape',
    'modeled_carry_yd',
    'modeled_total_yd',
    'modeled_carry_offline_yd',
    'modeled_total_offline_yd',
    'modeled_apex_ft',
    'modeled_descent_deg',
    'modeled_hang_time_s',
    'swing_label',
    'range_distance_basis',
    'range_carry_yd',
    'range_total_yd',
    'range_offline_yd',
    'est_club_type',
    'est_face_angle_deg',
    'est_face_to_path_deg',
    'est_face_to_path_from_spin_deg',
    'est_dynamic_loft_deg',
    'est_spin_loft_deg'
  ];
  const safe = v => {
    let s = v == null ? '' : String(v);
    if (typeof v === 'string' && /^[\s]*[=+@-]/.test(s)) s = "'" + s;
    return '"' + s.replaceAll('"', '""') + '"';
  };
  const rows = shots.map(s => {
    const e = equipment(s),
      m = s.flight?.metrics ?? {};
    return [
      s.key,
      s.captured,
      !!s.simulated,
      s.bag_name,
      s.club_label,
      e.bag_name,
      e.club_label,
      !!s.excluded,
      !!s.removed,
      s.cleanup_reason,
      s.target_distance_yd,
      s.vals.carry,
      s.vals.total,
      s.vals.offline,
      s.vals.ball_speed,
      s.vals.launch_ang,
      s.vals.launch_dir,
      s.vals.total_spin,
      s.vals.spin_axis,
      s.flight?.model,
      s.flight?.status,
      s.flight?.shape,
      m.carry_yd,
      m.total_yd,
      s.flight?.carry_point_yd?.right,
      s.flight?.total_point_yd?.right,
      m.apex_ft,
      m.descent_deg,
      m.hang_time_s,
      s.swing_label,
      s.distance_basis ?? 'reported',
      rangeValue(s, 'carry'),
      rangeValue(s, 'total'),
      rangeValue(s, 'offline'),
      s.club_estimates?.club_type,
      s.club_estimates?.face_angle,
      s.club_estimates?.face_to_path,
      s.club_estimates?.face_to_path_from_spin,
      s.club_estimates?.dynamic_loft,
      s.club_estimates?.spin_loft
    ];
  });
  return '\uFEFF' + [headings, ...rows].map(r => r.map(safe).join(',')).join('\r\n');
}
