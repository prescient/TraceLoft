import { escape as esc } from './charts.js';

export const effectiveShot = s => Boolean(s.game_outcome?.applied && !s.game_correction);
export const latestPlayedShot = data => data.shots.findLast(effectiveShot);

export function correctionControls(data, state) {
  const shot = latestPlayedShot(data),
    history = data.game_corrections ?? [];
  const conflict = state.practice && !state.practice.ended && state.practice.id !== data.id;
  const disabled = !shot || data.abandoned || conflict;
  const hint = data.abandoned
    ? 'Abandoned rounds cannot be reopened.'
    : conflict
      ? 'Finish or abandon your active session before reopening this round.'
      : !shot
        ? history.length
          ? 'No scored shots left to replay.'
          : 'Available after your first scored shot.'
        : `Latest scored shot · Hole ${shot.hole_number ?? 1}, attempt ${data.shots.filter(s => s.hole_id === shot.hole_id).indexOf(shot) + 1}${data.ended ? ' · reopens this round' : data.game.holed || shot.hole_id !== data.course.id ? ` · reopens hole ${shot.hole_number ?? 1}` : ''}`;
  return `<button class="btn" data-game-correct="mulligan" title="${esc(hint)} Keep shot in analysis. Restores position and score, including penalties and gimmes." ${disabled ? 'disabled' : ''}>Mulligan</button><button class="btn" data-game-correct="misread" title="${esc(hint)} Exclude shot from analysis. Restores position and score, including penalties and gimmes." ${disabled ? 'disabled' : ''}>Misread</button>`;
}

export function correctionCounts(data) {
  const history = data.game_corrections ?? [];
  return `Mulligans: ${history.filter(a => a.kind === 'mulligan').length} · Misreads: ${history.filter(a => a.kind === 'misread').length}`;
}

export function correctionHistory(data) {
  const history = data.game_corrections ?? [];
  return history.length
    ? `<details class="correction-history"><summary>Shot correction history</summary><ol>${history.map(a => `<li><strong>${a.kind === 'misread' ? 'Misread' : 'Mulligan'}</strong> · Hole ${a.hole_number} · ${esc(new Date(a.at).toLocaleString())}</li>`).join('')}</ol></details>`
    : '';
}
