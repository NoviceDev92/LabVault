/**
 * Ablation Comparison View: Side-by-side run diffs
 * Highlights metric deltas, tag discrepancies, and artifact presence.
 */

import { api } from '../api.js';
import { setBreadcrumbs, showToast } from '../components.js';

export async function renderCompare(container, queryParams = {}) {
  const idsStr = queryParams.ids || '';
  const runIds = idsStr.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));

  setBreadcrumbs([
    { label: 'Vault', href: '#/' },
    { label: `Compare (${runIds.length} Runs)`, href: `#/compare?ids=${idsStr}` },
  ]);

  if (runIds.length < 2) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚡</div>
        <div class="empty-title">Select at least 2 runs to compare</div>
        <p class="empty-desc">Go to an experiment dashboard and check the boxes next to runs you wish to ablate.</p>
        <button class="btn btn-primary" onclick="window.location.hash='#/'">Browse Experiments</button>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div style="display: flex; justify-content: center; align-items: center; min-height: 200px;">
      <span class="mono" style="color: var(--text-muted);">Computing Ablation Matrix...</span>
    </div>
  `;

  try {
    const diff = await api.compareRuns(runIds);
    const runVersions = diff.runs.map(r => `v${r.version}`);

    container.innerHTML = `
      <div class="page-header">
        <div class="page-title-group">
          <h1>
            <span>⚡ Ablation Comparison</span>
            <span class="mono" style="font-size: 13px; color: var(--cyan); background: rgba(6,182,212,0.1); padding: 2px 8px; border-radius: 9999px;">
              ${diff.runs.length} runs
            </span>
          </h1>
          <p class="page-desc">Comparing runs: ${runVersions.join(' vs ')}</p>
        </div>

        <div class="page-actions">
          <button class="btn btn-secondary" onclick="window.history.back()">← Back to Experiment</button>
        </div>
      </div>

      <!-- Metric Deltas Matrix -->
      <div style="margin-bottom: 24px;">
        <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
          <span>📊 Metric Deltas</span>
        </h2>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Metric Key</th>
                ${diff.runs.map(r => `<th>Run v${r.version}</th>`).join('')}
                <th>Spread / Delta</th>
              </tr>
            </thead>
            <tbody>
              ${diff.metric_deltas.length > 0 ? diff.metric_deltas.map(m => {
                const isLoss = m.key.toLowerCase().includes('loss');
                const deltaVal = m.spread;
                return `
                  <tr>
                    <td class="mono" style="font-weight: 600; color: var(--text-primary);">${m.key}</td>
                    ${diff.runs.map(r => {
                      const v = m.values[r.id];
                      return `<td class="mono">${v !== undefined && v !== null ? v : '—'}</td>`;
                    }).join('')}
                    <td>
                      <span class="delta-pill ${isLoss ? (deltaVal > 0 ? 'delta-positive' : 'delta-negative') : (deltaVal > 0 ? 'delta-positive' : 'delta-negative')}">
                        Δ ${deltaVal.toFixed(4)}
                      </span>
                    </td>
                  </tr>
                `;
              }).join('') : `
                <tr><td colspan="${diff.runs.length + 2}" style="text-align: center; color: var(--text-muted);">No metrics recorded in these runs.</td></tr>
              `}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tag Discrepancies -->
      <div style="margin-bottom: 24px;">
        <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
          <span>🏷 Hyperparameter & Tag Differences</span>
        </h2>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Tag Key</th>
                ${diff.runs.map(r => `<th>Run v${r.version}</th>`).join('')}
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${diff.tag_diffs.length > 0 ? diff.tag_diffs.map(t => `
                <tr>
                  <td class="mono" style="font-weight: 600; color: var(--text-primary);">${t.key}</td>
                  ${diff.runs.map(r => {
                    const v = t.values[r.id];
                    return `<td class="mono" style="color: ${v !== undefined ? 'var(--cyan)' : 'var(--text-muted)'};">${v !== undefined ? v : '—'}</td>`;
                  }).join('')}
                  <td>
                    <span class="tag-chip" style="font-size: 10px; ${!t.all_equal ? 'border-color: var(--amber); color: #FBBF24;' : ''}">
                      ${t.all_equal ? 'Uniform' : 'DIFF'}
                    </span>
                  </td>
                </tr>
              `).join('') : `
                <tr><td colspan="${diff.runs.length + 2}" style="text-align: center; color: var(--text-muted);">No tags recorded in these runs.</td></tr>
              `}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Artifacts Comparison -->
      <div style="margin-bottom: 24px;">
        <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
          <span>📁 Artifact Presence</span>
        </h2>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                ${diff.runs.map(r => `<th>Run v${r.version}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${diff.artifact_diffs.length > 0 ? diff.artifact_diffs.map(art => `
                <tr>
                  <td class="mono" style="color: var(--text-primary);">📄 ${art.filename}</td>
                  ${diff.runs.map(r => {
                    const present = art.present_in.includes(r.id);
                    return `
                      <td>
                        ${present ? '<span style="color: var(--emerald); font-weight: bold;">✓ Present</span>' : '<span style="color: var(--text-muted);">— Missing</span>'}
                      </td>
                    `;
                  }).join('')}
                </tr>
              `).join('') : `
                <tr><td colspan="${diff.runs.length + 1}" style="text-align: center; color: var(--text-muted);">No artifacts found in these runs.</td></tr>
              `}
            </tbody>
          </table>
        </div>
      </div>
    `;

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon" style="color: var(--rose);">✕</div>
        <div class="empty-title">Comparison Error</div>
        <p class="empty-desc">${err.message}</p>
        <button class="btn btn-secondary" onclick="window.history.back()">Back</button>
      </div>
    `;
  }
}
