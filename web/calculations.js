import { escape as esc } from './charts.js';
const number = v => (Number.isFinite(v) ? v.toFixed(2) : '—');

export function mountCalculations(app, filters, api, notice, isCurrent, refresh) {
  const panel = document.createElement('details');
  panel.className = 'card details section-space';
  panel.innerHTML = `<summary>Calculation methods and version history</summary><p class="form-hint section-space">Preview calculations for shots matching the applied filters. Publication changes analytical versions and future planning. Saved outcomes and scores keep their original results.</p><div class="analysis-filters"><label class="field">Calculation family<select data-calc-family><option value="flight">OpenGolfCoach flight</option><option value="putting">Putting distance</option><option value="source_features">Source comparisons · rollout, smash, absolute offline</option></select></label><label class="field">Putting method<select data-calc-putting><option value="saved">Saved method and Stimp</option><option value="stimp-constant-deceleration-v1">Constant Stimp · square law</option><option value="fuse-flat-braking-v1">Fuse flat braking</option></select></label></div><div class="form-foot"><button class="btn" data-calc-stage>Preview recalculation</button><a class="btn quiet" href="/api/calculations/history.csv" download>Export calculation history CSV</a></div><div class="form-foot"><label class="field">Saved batches<select data-calc-history><option value="">Choose a batch</option></select></label><button class="btn quiet" data-calc-view>Review selected batch</button></div><div data-calc-preview aria-live="polite"></div>`;
  app.append(panel);
  const host = panel.querySelector('[data-calc-preview]');
  let busy = false;
  async function history() {
    const rows = await api('/api/calculations');
    if (!panel.isConnected || !isCurrent()) return;
    panel.querySelector('[data-calc-history]').innerHTML =
      '<option value="">Choose a batch</option>' +
      rows
        .map(
          b =>
            `<option value="${esc(b.batch_id)}">${esc(b.created_at.slice(0, 16))} · ${esc(b.model_family)} · ${esc(b.status)} · ${b.batch_id.slice(0, 6)}</option>`
        )
        .join('');
  }
  function preview(b) {
    if (!panel.isConnected || !isCurrent()) return;
    const changed = b.differences.filter(d => Object.keys(d.changes).length);
    host.innerHTML = `<div class="section-space"><h3>${esc(b.model_family)} · ${esc(b.status)}</h3><p class="form-hint">${esc(b.model_version)} · implementation ${esc(b.code_hash.slice(0, 12))} · batch ${esc(b.batch_id.slice(0, 8))}</p><p><strong>${b.coverage.ready}/${b.expected} ready</strong> · ${b.coverage.unavailable} unavailable · ${b.coverage.error} errors · ${b.expected - b.processed} pending · ${b.stale} stale inputs</p><p class="form-hint">${changed.length} results have changed scalar values. Complete ready coverage and unchanged source, tagging and inclusion are required to publish. Missing inputs stay unavailable.</p><div class="table-wrap calculation-preview-table" tabindex="0" role="region" aria-label="Calculation result preview"><table><thead><tr><th>Shot / session</th><th>Status</th><th>Changed metric</th><th>Current → proposed</th></tr></thead><tbody>${b.differences
      .slice(0, 50)
      .map(
        d =>
          `<tr><th>${esc(d.shot_id.slice(0, 8))}<small class="range-stat-detail">${esc(d.session_id.slice(0, 8))}</small></th><td>${esc(d.status)}<small class="range-stat-detail">${esc(d.reason ?? '')}</small></td><td>${Object.keys(d.changes).map(esc).join('<br>') || 'Same scalar values'}</td><td>${
            Object.values(d.changes)
              .map(v => number(v.before) + ' → ' + number(v.after))
              .join('<br>') || '—'
          }</td></tr>`
      )
      .join(
        ''
      )}</tbody></table></div><p class="form-hint">First ${Math.min(50, b.expected)} results shown. Full versions and lineage are available in the history export.</p><div class="form-foot"><button class="btn primary" data-calc-publish ${!b.publishable ? 'disabled' : ''}>Publish this analytical version</button>${b.status === 'staging' ? '<button class="btn" data-calc-resume>Resume interrupted batch</button>' : ''}<button class="btn quiet" data-calc-refresh>Refresh preview</button></div></div>`;
    host.querySelector('[data-calc-publish]').onclick = () =>
      run(async () => {
        await api(`/api/calculations/${b.batch_id}/publish`, { selection_token: b.selection_token });
        notice('Analytical version published. Saved shot outcomes remain intact.');
        refresh();
      });
    host.querySelector('[data-calc-refresh]').onclick = () =>
      run(async () => preview(await api('/api/calculations/' + b.batch_id)));
    const resume = host.querySelector('[data-calc-resume]');
    if (resume)
      resume.onclick = () =>
        run(async () => {
          preview(await api(`/api/calculations/${b.batch_id}/resume`, {}));
          await history();
        });
  }
  async function run(fn) {
    if (busy) return;
    busy = true;
    panel.querySelectorAll('button').forEach(b => (b.disabled = true));
    try {
      await fn();
    } catch (e) {
      notice(e.message);
      const status = host.querySelector('[role=status]');
      if (status) status.textContent = 'Preview unavailable: ' + e.message;
    } finally {
      busy = false;
      if (panel.isConnected) {
        panel.querySelectorAll(':scope > .form-foot button').forEach(b => (b.disabled = false));
        host.querySelector('[data-calc-refresh]')?.removeAttribute('disabled');
        host.querySelector('[data-calc-resume]')?.removeAttribute('disabled');
      }
    }
  }
  panel.querySelector('[data-calc-stage]').onclick = () =>
    run(async () => {
      host.innerHTML = '<p role="status">Calculating preview…</p>';
      preview(
        await api('/api/calculations', {
          family: panel.querySelector('[data-calc-family]').value,
          filters,
          putting_model: panel.querySelector('[data-calc-putting]').value
        })
      );
      await history();
    });
  panel.querySelector('[data-calc-view]').onclick = () =>
    run(async () => {
      const id = panel.querySelector('[data-calc-history]').value;
      if (id) preview(await api('/api/calculations/' + id));
      else notice('Choose a saved batch.');
    });
  history().catch(e => notice(e.message));
}
