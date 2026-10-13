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
// Direction words for signed club values, shared by the latest-shot tiles and the club snapshot.
// Attack angle is upward-positive. Club path, face angle and face to path are target-relative (right
// positive), so in-to-out and open/closed depend on the session's handedness.
const word = (value, positive, negative) => (!valid(value) || value === 0 ? '' : value > 0 ? positive : negative);
const attackWord = value => word(value, 'up', 'down');
const pathWord = (value, handedness) =>
  handedness !== 'left_handed' ? word(value, 'in-to-out', 'out-to-in') : word(value, 'out-to-in', 'in-to-out');
const faceWord = (value, handedness) =>
  handedness !== 'left_handed' ? word(value, 'open', 'closed') : word(value, 'closed', 'open');
// Smash factor as the source reported it, else ball speed / club speed (labeled as calculated).
const smash = shot => {
  const v = shot?.vals ?? {};
  if (valid(v.smash_factor)) return v.smash_factor;
  return valid(v.ball_speed) && valid(v.club_speed) && v.club_speed > 0 ? v.ball_speed / v.club_speed : null;
};
const estimate = key => shot => shot?.club_estimates?.[key];
// Club snapshot columns, in the order of the latest-shot panel: ball and flight, club delivery, then
// the D64 estimates. `club` columns appear only in sessions whose source reports club data. `value`
// overrides the default reading (rangeValue); `direction` names the sign of a signed value.
export const CLUB_METRICS = [
  { key: 'carry', label: 'Carry', unit: 'yd' },
  { key: 'total', label: 'Total', unit: 'yd' },
  { key: 'offline', label: 'Absolute offline', unit: 'yd', absolute: true },
  { key: 'ball_speed', label: 'Ball speed', unit: 'mph' },
  { key: 'total_spin', label: 'Total spin', unit: 'rpm', precision: 0 },
  { key: 'launch_ang', label: 'Launch angle', unit: '°' },
  { key: 'descent_ang', label: 'Descent angle', unit: '°' },
  { key: 'club_speed', label: 'Club speed', unit: 'mph', club: true },
  { key: 'smash_factor', label: 'Smash factor', unit: '', precision: 2, club: true, value: smash },
  { key: 'attack_angle', label: 'Angle of attack', unit: '°', club: true, direction: attackWord },
  { key: 'club_path', label: 'Club path', unit: '°', club: true, direction: pathWord },
  {
    key: 'face_angle',
    label: 'Face angle · est.',
    unit: '°',
    club: true,
    value: estimate('face_angle'),
    direction: faceWord
  },
  {
    key: 'face_to_path',
    label: 'Face to path · est.',
    unit: '°',
    club: true,
    value: estimate('face_to_path'),
    direction: faceWord
  },
  { key: 'dynamic_loft', label: 'Dynamic loft · est.', unit: '°', club: true, value: estimate('dynamic_loft') },
  { key: 'spin_loft', label: 'Spin loft · est.', unit: '°', club: true, value: estimate('spin_loft') }
];
// The snapshot's columns for these shots: club delivery only when a source reported club data.
export const snapshotMetrics = shots => (hasClubData(shots) ? CLUB_METRICS : CLUB_METRICS.filter(m => !m.club));
// A summarized value as shown: { value, unit } with a signed median as its size plus a direction word
// ("2.1° up"). The IQR is a width, so it needs no direction.
export function snapshotValue(metric, value, handedness = 'right_handed') {
  if (!metric.direction || !valid(value)) return { value, unit: metric.unit };
  return { value: Math.abs(value), unit: `${metric.unit} ${metric.direction(value, handedness)}`.trim() };
}
// Early demo generator used 'descent'; real captures always use descent_ang.
export const sourceValue = (shot, metric) =>
  shot?.vals?.[metric] ?? (shot?.simulated && metric === 'descent_ang' ? shot.vals?.descent : undefined);
// Range distances (D63): shots recorded since 2026-10-12 carry range_vals, OpenGolfCoach estimates
// (reported only as a labeled fallback when the model is unavailable). Older shots keep reported values.
export const RANGE_FIELDS = ['carry', 'total', 'offline', 'descent_ang', 'peak_height', 'hang_time'];
export const rangeValue = (shot, metric) =>
  RANGE_FIELDS.includes(metric) && shot?.range_vals && metric in shot.range_vals
    ? shot.range_vals[metric]
    : sourceValue(shot, metric);
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
  const openClosed = value => `° ${faceWord(value, handedness)}`.trim();
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
  const calculated = !valid(v.smash_factor) && valid(smash(shot));
  return [
    { label: 'Club speed', value: v.club_speed, unit: 'mph', precision: 1 },
    {
      label: calculated ? 'Smash factor · calc.' : 'Smash factor',
      value: smash(shot),
      unit: '',
      precision: 2
    },
    {
      label: 'Angle of attack',
      value: valid(v.attack_angle) ? Math.abs(v.attack_angle) : null,
      unit: `° ${attackWord(v.attack_angle)}`.trim(),
      precision: 1
    },
    {
      label: 'Club path',
      value: valid(v.club_path) ? Math.abs(v.club_path) : null,
      unit: `° ${pathWord(v.club_path, handedness)}`.trim(),
      precision: 1
    }
  ];
}
// Median and IQR of one metric over included shots. `value` reads a shot's value when it is not a
// plain reading (smash factor's calculated fallback, club estimates).
export function robustSummary(shots, metric, { absolute = false, value: read = s => rangeValue(s, metric) } = {}) {
  const values = shots
    .filter(included)
    .map(s => {
      const value = read(s);
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
export function clubSummaries(shots, metrics = CLUB_METRICS) {
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
    metrics: metrics.map(m => ({ key: m.key, ...robustSummary(g.shots, m.key, m) }))
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
