// Presentation-only grouping; the service owns selection and CSV membership.
export const finite = v => typeof v === 'number' && Number.isFinite(v);
export function robust(values) {
  const a = values.filter(finite).sort((a, b) => a - b),
    n = a.length;
  const q = p => {
    const i = (n - 1) * p,
      l = Math.floor(i);
    return a[l] + (i - l) * (a[Math.min(l + 1, n - 1)] - a[l]);
  };
  return {
    count: n,
    median: n ? q(0.5) : null,
    q1: n > 1 ? q(0.25) : null,
    q3: n > 1 ? q(0.75) : null,
    iqr: n > 1 ? q(0.75) - q(0.25) : null
  };
}
const palette = [
  '#1455ed',
  '#087b69',
  '#b76006',
  '#853fbe',
  '#ba3276',
  '#496d89',
  '#8b6a04',
  '#c14326',
  '#28663c',
  '#5062ab',
  '#9b4261',
  '#576d13'
];
let identityColors = {};
export function configureColors(clubs, existing = {}) {
  identityColors = { ...existing };
  for (const [id, c] of Object.entries(clubs).sort(
    (a, b) =>
      a[1].bag.localeCompare(b[1].bag) || a[1].label.localeCompare(b[1].label) || a[0].localeCompare(b[0])
  )) {
    const key = c.bag + id;
    if (!identityColors[key]) {
      const i = Object.keys(identityColors).length;
      identityColors[key] = palette[i] ?? `hsl(${(i * 137.508) % 360} 65% 36%)`;
    }
  }
  return identityColors;
}
export const color = id =>
  identityColors[id] ??
  palette[([...id].reduce((h, c) => h * 31 + c.charCodeAt(0), 0) >>> 0) % palette.length];
export const rowKey = r => JSON.stringify([r.session_id, r.key]);
export function enriched(report, rows = report.rows) {
  const pins = new Map((report.lineage ?? []).map(r => [JSON.stringify([r.session_id, r.legacy_key]), r]));
  return rows.map(r => ({ ...r, basis: report.filters.basis, lineage: pins.get(rowKey(r)) ?? {} }));
}
function versions(r) {
  return r.basis === 'flight'
    ? [r.lineage?.flight_model_version, r.lineage?.putting_model_version].filter(Boolean).join(' / ')
    : '';
}
export function cohortKey(r) {
  return JSON.stringify([r.bag_id, r.club_id, r.lineage?.configuration_id ?? '', r.swing_label, versions(r)]);
}
export function cohortLabel(r) {
  return `${r.bag_name} / ${r.club_label}${r.swing_label ? ' / ' + r.swing_label : ''}${r.lineage?.configuration_id ? ' · config ' + r.lineage.configuration_id.slice(0, 6) : ''}${versions(r) ? ' · ' + versions(r) : ''}`;
}
export function cohorts(rows) {
  const result = new Map();
  for (const r of rows) {
    const id = cohortKey(r);
    if (!result.has(id))
      result.set(id, { id, label: cohortLabel(r), color: color(r.bag_id + r.club_id), rows: [] });
    result.get(id).rows.push(r);
  }
  return [...result.values()].sort((a, b) => a.label.localeCompare(b.label));
}
export function bucket(r, resolution) {
  if (resolution === 'shot') {
    const time = Date.parse(r.captured);
    return Number.isFinite(time)
      ? { id: rowKey(r), time, label: new Date(time).toISOString().replace('T', ' ').slice(0, 19) }
      : null;
  }
  const day = r.session_started?.slice(0, 10),
    time = Date.parse(day + 'T00:00:00Z');
  if (!Number.isFinite(time)) return null;
  if (resolution === 'session')
    return { id: r.session_id, time, label: day + ' · ' + r.drill + ' · ' + r.session_id.slice(0, 6) };
  const date = new Date(time);
  if (resolution === 'week') date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7));
  else date.setUTCDate(1);
  const key = date.toISOString().slice(0, 10);
  return { id: key, time: date.getTime(), label: resolution === 'week' ? 'Week of ' + key : key.slice(0, 7) };
}
export function timeline(rows, metrics, resolution) {
  const buckets = new Map();
  for (const r of rows) {
    const b = bucket(r, resolution);
    if (b) buckets.set(b.id, b);
  }
  const points = [...buckets.values()].sort((a, b) => a.time - b.time || a.id.localeCompare(b.id));
  const series = cohorts(rows).map(c => {
    const grouped = new Map();
    for (const r of c.rows) {
      const b = bucket(r, resolution);
      if (b) {
        if (!grouped.has(b.id)) grouped.set(b.id, []);
        grouped.get(b.id).push(r);
      }
    }
    return {
      ...c,
      points: points.map(b => ({
        ...b,
        rows: grouped.get(b.id) ?? [],
        metrics: Object.fromEntries(
          metrics.map(m => [m, robust((grouped.get(b.id) ?? []).map(r => r.values[m]))])
        )
      }))
    };
  });
  return { points, series, missingTime: rows.filter(r => !bucket(r, resolution)).length };
}
export function matchesRanges(row, ranges, omit = '') {
  return Object.entries(ranges).every(
    ([m, b]) =>
      m === omit ||
      (finite(row.values[m]) &&
        (b.min == null || row.values[m] >= b.min) &&
        (b.max == null || row.values[m] <= b.max))
  );
}
// Exact preceding float lets histogram bins use half-open intervals with the inclusive API.
export function previousFloat(x) {
  if (x === 0) return -Number.MIN_VALUE;
  const v = new DataView(new ArrayBuffer(8));
  v.setFloat64(0, x);
  let bits = v.getBigUint64(0);
  bits += x > 0 ? -1n : 1n;
  v.setBigUint64(0, bits);
  return v.getFloat64(0);
}
export function histogram(rows, metric, count = 8) {
  const values = rows.map(r => r.values[metric]).filter(finite);
  if (!values.length) return [];
  const min = values.reduce((a, b) => Math.min(a, b), Infinity),
    max = values.reduce((a, b) => Math.max(a, b), -Infinity),
    pad = max === min ? Math.max(Math.abs(min) * 0.05, 1) : 0;
  const lo = min - pad,
    hi = max + pad,
    step = (hi - lo) / count;
  return Array.from({ length: count }, (_, i) => {
    const min = lo + i * step,
      max = i === count - 1 ? hi : previousFloat(lo + (i + 1) * step);
    return { min, max, count: values.filter(v => v >= min && v <= max).length };
  });
}
export function comparison(a, b, metrics) {
  const left = new Map(cohorts(a).map(c => [c.id, c])),
    right = new Map(cohorts(b).map(c => [c.id, c]));
  return [...new Set([...left.keys(), ...right.keys()])].map(id => {
    const c = left.get(id) ?? right.get(id);
    return {
      ...c,
      metrics: metrics.map(m => {
        const before = robust((left.get(id)?.rows ?? []).map(r => r.values[m])),
          after = robust((right.get(id)?.rows ?? []).map(r => r.values[m]));
        return {
          metric: m,
          before,
          after,
          delta: finite(before.median) && finite(after.median) ? after.median - before.median : null
        };
      })
    };
  });
}
