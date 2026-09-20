/**
 * Ablation Comparison View: Side-by-side run diffs
 * Highlights metric deltas, tag discrepancies, and artifact presence.
 * Phase 6: includes code diff viewer and image side-by-side slider.
 */

import { api } from '../api.js';
import { setBreadcrumbs, showToast } from '../components.js';

// Determine file type from extension
const TEXT_EXTS = new Set(['.py', '.ipynb', '.sh', '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini', '.txt', '.md', '.tex', '.log', '.csv', '.tsv']);
const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.svg', '.gif', '.bmp', '.webp']);

function getExt(filename) {
  const dot = filename.lastIndexOf('.');
  return dot >= 0 ? filename.slice(dot).toLowerCase() : '';
}

// ─── Diff Viewer Renderer ───────────────────────────────────────────

function renderDiffViewer(diffLines) {
  if (!diffLines || diffLines.length === 0) {
    return '<div class="diff-viewer"><div style="padding: 16px; color: var(--text-muted); text-align: center;">Files are identical — no differences.</div></div>';
  }

  let lineNumA = 0, lineNumB = 0;
  const rows = diffLines.map(raw => {
    const line = raw.replace(/\n$/, '');
    if (line.startsWith('@@')) {
      // Parse hunk header for line numbers
      const match = line.match(/@@ -(\d+)/);
      if (match) lineNumA = parseInt(match[1], 10) - 1;
      const match2 = line.match(/\+(\d+)/);
      if (match2) lineNumB = parseInt(match2[1], 10) - 1;
      return `<div class="diff-line diff-hunk">${escHtml(line)}</div>`;
    } else if (line.startsWith('---') || line.startsWith('+++')) {
      return `<div class="diff-line diff-hunk">${escHtml(line)}</div>`;
    } else if (line.startsWith('-')) {
      lineNumA++;
      return `<div class="diff-line diff-del"><span class="diff-line-num">${lineNumA}</span><span class="diff-line-content">${escHtml(line)}</span></div>`;
    } else if (line.startsWith('+')) {
      lineNumB++;
      return `<div class="diff-line diff-add"><span class="diff-line-num">${lineNumB}</span><span class="diff-line-content">${escHtml(line)}</span></div>`;
    } else {
      lineNumA++;
      lineNumB++;
      return `<div class="diff-line diff-context"><span class="diff-line-num">${lineNumA}</span><span class="diff-line-content">${escHtml(line)}</span></div>`;
    }
  });

  return `<div class="diff-viewer">${rows.join('')}</div>`;
}

// ─── Image Comparison Renderer ──────────────────────────────────────

function renderImageComparison(images, runVersions) {
  const entries = Object.entries(images);
  if (entries.length < 2) {
    return '<div style="color: var(--text-muted);">Not enough images to compare.</div>';
  }

  const [idA, srcA] = entries[0];
  const [idB, srcB] = entries[1];
  const labelA = `v${runVersions[idA] || idA}`;
  const labelB = `v${runVersions[idB] || idB}`;

  return `
    <div class="image-compare-container">
      <div class="image-compare-pane">
        <span class="image-compare-label">${labelA}</span>
        <img src="${srcA}" alt="${labelA}" />
      </div>
      <div class="image-compare-pane">
        <span class="image-compare-label">${labelB}</span>
        <img src="${srcB}" alt="${labelB}" />
      </div>
    </div>
    <div style="margin-top: 12px;">
      <div class="image-slider-wrap" data-img-a="${srcA}" data-img-b="${srcB}" data-label-a="${labelA}" data-label-b="${labelB}">
        <img src="${srcB}" alt="Base image (${labelB})" />
        <div class="image-slider-clip" style="width: 50%;">
          <img src="${srcA}" alt="Overlay image (${labelA})" />
        </div>
        <div class="image-slider-handle" style="left: 50%;"></div>
      </div>
      <div style="text-align: center; margin-top: 6px; font-size: 11px; color: var(--text-muted);">← Drag slider to compare →</div>
    </div>
  `;
}

// Attach slider interactivity after DOM insert
function attachSliderListeners(container) {
  container.querySelectorAll('.image-slider-wrap').forEach(wrap => {
    const handle = wrap.querySelector('.image-slider-handle');
    const clip = wrap.querySelector('.image-slider-clip');
    let dragging = false;

    const onMove = (e) => {
      if (!dragging) return;
      const rect = wrap.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      let pct = ((clientX - rect.left) / rect.width) * 100;
      pct = Math.max(0, Math.min(100, pct));
      clip.style.width = `${pct}%`;
      handle.style.left = `${pct}%`;
    };

    handle.addEventListener('mousedown', () => { dragging = true; });
    handle.addEventListener('touchstart', () => { dragging = true; });
    document.addEventListener('mouseup', () => { dragging = false; });
    document.addEventListener('touchend', () => { dragging = false; });
    document.addEventListener('mousemove', onMove);
    document.addEventListener('touchmove', onMove);
  });
}

// ─── Utility ────────────────────────────────────────────────────────

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function fmtSize(bytes) {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ─── Main Render ────────────────────────────────────────────────────

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
    // Build a runs array from the response for convenience
    const runs = diff.run_ids.map(id => ({ id, version: diff.run_versions[id] || diff.run_versions[String(id)] || id }));
    const runVersions = diff.run_versions;

    container.innerHTML = `
      <div class="page-header">
        <div class="page-title-group">
          <h1>
            <span>⚡ Ablation Comparison</span>
            <span class="mono" style="font-size: 13px; color: var(--cyan); background: rgba(6,182,212,0.1); padding: 2px 8px; border-radius: 9999px;">
              ${runs.length} runs
            </span>
          </h1>
          <p class="page-desc">Comparing runs: ${runs.map(r => `v${r.version}`).join(' vs ')}</p>
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
                ${runs.map(r => `<th>Run v${r.version}</th>`).join('')}
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
                    ${runs.map(r => {
                      const v = m.values[r.id] ?? m.values[String(r.id)];
                      return `<td class="mono">${v !== undefined && v !== null ? v : '—'}</td>`;
                    }).join('')}
                    <td>
                      <span class="delta-pill ${deltaVal > 0 ? 'delta-positive' : 'delta-negative'}">
                        Δ ${deltaVal.toFixed(4)}
                      </span>
                    </td>
                  </tr>
                `;
              }).join('') : `
                <tr><td colspan="${runs.length + 2}" style="text-align: center; color: var(--text-muted);">No metrics recorded in these runs.</td></tr>
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
                ${runs.map(r => `<th>Run v${r.version}</th>`).join('')}
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${diff.tag_diffs.length > 0 ? diff.tag_diffs.map(t => `
                <tr>
                  <td class="mono" style="font-weight: 600; color: var(--text-primary);">${t.key}</td>
                  ${runs.map(r => {
                    const v = t.values[r.id] ?? t.values[String(r.id)];
                    return `<td class="mono" style="color: ${v !== undefined ? 'var(--cyan)' : 'var(--text-muted)'};">${v !== undefined ? v : '—'}</td>`;
                  }).join('')}
                  <td>
                    <span class="tag-chip" style="font-size: 10px; ${!t.is_uniform ? 'border-color: var(--amber); color: #FBBF24;' : ''}">
                      ${t.is_uniform ? 'Uniform' : 'DIFF'}
                    </span>
                  </td>
                </tr>
              `).join('') : `
                <tr><td colspan="${runs.length + 2}" style="text-align: center; color: var(--text-muted);">No tags recorded in these runs.</td></tr>
              `}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Artifacts Comparison -->
      <div style="margin-bottom: 24px;">
        <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
          <span>📁 Artifact Comparison</span>
        </h2>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                ${runs.map(r => `<th>Run v${r.version}</th>`).join('')}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${diff.artifact_diffs.length > 0 ? diff.artifact_diffs.map(art => {
                const ext = getExt(art.filename);
                const sharedCount = art.present_in.length;
                const canDiff = sharedCount >= 2 && (TEXT_EXTS.has(ext) || IMAGE_EXTS.has(ext));
                const diffType = TEXT_EXTS.has(ext) ? 'text' : IMAGE_EXTS.has(ext) ? 'image' : 'binary';
                return `
                  <tr>
                    <td class="mono" style="color: var(--text-primary);">📄 ${art.filename}
                      <span style="font-size: 10px; color: var(--text-muted); margin-left: 4px;">${fmtSize(art.sizes[art.present_in[0]] ?? art.sizes[String(art.present_in[0])])}</span>
                    </td>
                    ${runs.map(r => {
                      const present = art.present_in.includes(r.id);
                      return `
                        <td>
                          ${present ? '<span style="color: var(--emerald); font-weight: bold;">✓</span>' : '<span style="color: var(--text-muted);">—</span>'}
                        </td>
                      `;
                    }).join('')}
                    <td>
                      ${canDiff
                        ? `<button class="btn btn-sm" data-diff-file="${art.filename}" data-diff-type="${diffType}" style="font-size: 11px; padding: 3px 10px;">
                            ${diffType === 'text' ? '⟨/⟩ Diff' : '🖼 Compare'}
                           </button>`
                        : '<span style="color: var(--text-muted); font-size: 11px;">—</span>'
                      }
                    </td>
                  </tr>
                `;
              }).join('') : `
                <tr><td colspan="${runs.length + 2}" style="text-align: center; color: var(--text-muted);">No artifacts found in these runs.</td></tr>
              `}
            </tbody>
          </table>
        </div>
      </div>

      <!-- File Diff Panel (rendered on-demand) -->
      <div id="file-diff-panel" style="display: none; margin-bottom: 24px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
          <h2 id="file-diff-title" style="font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px;"></h2>
          <button class="btn btn-sm btn-secondary" id="close-diff-panel">✕ Close</button>
        </div>
        <div id="file-diff-content"></div>
      </div>
    `;

    // ── Wire up diff buttons ──

    container.querySelectorAll('[data-diff-file]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const filename = btn.dataset.diffFile;
        const type = btn.dataset.diffType;
        const panel = document.getElementById('file-diff-panel');
        const title = document.getElementById('file-diff-title');
        const content = document.getElementById('file-diff-content');

        panel.style.display = 'block';
        title.innerHTML = `${type === 'text' ? '⟨/⟩' : '🖼'} ${filename}`;
        content.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Loading diff...</div>';

        // Scroll to the panel
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

        try {
          const result = await api.compareFiles(runIds, filename);
          if (result.diff_type === 'text') {
            content.innerHTML = renderDiffViewer(result.diff_lines);
          } else if (result.diff_type === 'image') {
            content.innerHTML = renderImageComparison(result.images, runVersions);
            attachSliderListeners(content);
          } else {
            // Binary
            const sizeEntries = Object.entries(result.sizes);
            const hashEntries = Object.entries(result.hashes);
            content.innerHTML = `
              <div class="card" style="padding: 16px;">
                <p style="color: var(--text-muted); margin-bottom: 8px;">Binary file — cannot display inline diff.</p>
                <table class="data-table">
                  <thead><tr><th>Run</th><th>Size</th><th>Hash</th></tr></thead>
                  <tbody>
                    ${sizeEntries.map(([rid, sz]) => `
                      <tr>
                        <td class="mono">v${runVersions[rid] || rid}</td>
                        <td class="mono">${fmtSize(sz)}</td>
                        <td class="mono" style="font-size: 10px;">${(hashEntries.find(([h]) => h === rid)?.[1] || '—').slice(0, 12)}…</td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            `;
          }
        } catch (err) {
          content.innerHTML = `<div style="padding: 16px; color: var(--rose);">Error: ${escHtml(err.message)}</div>`;
        }
      });
    });

    // Close diff panel
    document.getElementById('close-diff-panel')?.addEventListener('click', () => {
      document.getElementById('file-diff-panel').style.display = 'none';
    });

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
