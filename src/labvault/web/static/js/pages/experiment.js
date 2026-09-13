/**
 * Experiment Dashboard: The Flagship Results Data Grid
 * Sortable metric columns, delta pills, multi-run comparison selection,
 * slide-out artifact inspector, and LaTeX/CSV export.
 */

import { api } from '../api.js';
import { 
  setBreadcrumbs, 
  formatDate, 
  formatBytes, 
  showToast, 
  showModal, 
  closeModal, 
  openInspectorDrawer, 
  updateFloatingDock,
  createDropzone
} from '../components.js';

let selectedRunIds = new Set();
let sortColumn = 'version';
let sortDirection = 'desc';
let activeTagFilter = null;
let pinnedRunId = null;

export async function renderExperiment(container, projectSlug, expSlug) {
  setBreadcrumbs([
    { label: 'Vault', href: '#/' },
    { label: projectSlug, href: `#/projects/${projectSlug}` },
    { label: expSlug, href: `#/experiments/${projectSlug}/${expSlug}` },
  ]);

  container.innerHTML = `
    <div style="display: flex; justify-content: center; align-items: center; min-height: 200px;">
      <span class="mono" style="color: var(--text-muted);">Loading Results Grid...</span>
    </div>
  `;

  try {
    const [project, experiment] = await Promise.all([
      api.getProject(projectSlug),
      api.getExperiment(projectSlug, expSlug),
    ]);

    const runs = await api.listRuns(experiment.id);

    // Collect all unique metric keys and tag keys
    const allMetricKeys = Array.from(new Set(runs.flatMap(r => Object.keys(r.metrics || {}))));
    const allTagKeys = Array.from(new Set(runs.flatMap(r => Object.entries(r.tags || {}).map(([k, v]) => `${k}=${v}`))));

    // Restore pinned run from local storage if available
    const storedPin = localStorage.getItem(`labvault_pin_${experiment.id}`);
    if (storedPin) pinnedRunId = parseInt(storedPin, 10);

    function refreshTable() {
      renderTableContent();
    }

    container.innerHTML = `
      <!-- Experiment Header -->
      <div class="page-header">
        <div class="page-title-group">
          <h1>
            <span>⚡ ${experiment.name}</span>
            <span class="mono" style="font-size: 13px; font-weight: normal; color: var(--cyan); background: rgba(6,182,212,0.1); padding: 2px 8px; border-radius: 9999px;">
              ${runs.length} runs recorded
            </span>
          </h1>
          <p class="page-desc">${experiment.description || 'Track metric ablations, versioned checkpoints, and research artifacts.'}</p>
          
          <!-- Tag Filter Chips -->
          <div class="tag-filter-chips" style="margin-top: 10px;" id="tag-filters-container">
            <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Filters:</span>
            <span class="tag-chip ${!activeTagFilter ? 'active' : ''}" data-filter="">All Runs</span>
            ${allTagKeys.map(tag => `
              <span class="tag-chip ${activeTagFilter === tag ? 'active' : ''}" data-filter="${tag}">${tag}</span>
            `).join('')}
          </div>
        </div>

        <div class="page-actions">
          <div style="position: relative; display: inline-block;">
            <button class="btn btn-secondary" id="export-dropdown-btn">
              <span>⭳ Export Table ▼</span>
            </button>
            <div id="export-dropdown-menu" style="display: none; position: absolute; right: 0; top: 100%; margin-top: 6px; background: var(--bg-card); border: 1px solid var(--border-medium); border-radius: var(--radius-md); box-shadow: var(--shadow-lg); z-index: 50; min-width: 170px; overflow: hidden;">
              <a href="${api.exportTableUrl(experiment.id, 'latex')}" target="_blank" class="btn btn-ghost btn-sm" style="display: block; width: 100%; text-align: left; padding: 8px 14px; border-radius: 0;">LaTeX Table (.tex)</a>
              <a href="${api.exportTableUrl(experiment.id, 'csv')}" target="_blank" class="btn btn-ghost btn-sm" style="display: block; width: 100%; text-align: left; padding: 8px 14px; border-radius: 0;">CSV Spreadsheet</a>
              <a href="${api.exportTableUrl(experiment.id, 'markdown')}" target="_blank" class="btn btn-ghost btn-sm" style="display: block; width: 100%; text-align: left; padding: 8px 14px; border-radius: 0;">Markdown Table</a>
              <a href="${api.exportTableUrl(experiment.id, 'json')}" target="_blank" class="btn btn-ghost btn-sm" style="display: block; width: 100%; text-align: left; padding: 8px 14px; border-radius: 0;">JSON Object</a>
            </div>
          </div>

          <button class="btn btn-primary" id="new-run-btn">
            <span>+ New Run</span>
          </button>
        </div>
      </div>

      <!-- Main Results Table Container -->
      <div class="table-container" id="runs-table-container">
        <!-- Table rendered dynamically -->
      </div>
    `;

    // Dropdown toggle
    const dropBtn = container.querySelector('#export-dropdown-btn');
    const dropMenu = container.querySelector('#export-dropdown-menu');
    dropBtn.onclick = (e) => {
      e.stopPropagation();
      dropMenu.style.display = dropMenu.style.display === 'none' ? 'block' : 'none';
    };
    document.addEventListener('click', () => { if (dropMenu) dropMenu.style.display = 'none'; });

    // Tag filter click
    container.querySelectorAll('.tag-chip').forEach(chip => {
      chip.onclick = () => {
        const filter = chip.dataset.filter;
        activeTagFilter = filter || null;
        renderTableContent();
      };
    });

    container.querySelector('#new-run-btn')?.addEventListener('click', () => openNewRunModal(experiment, refreshTable));

    function renderTableContent() {
      const tableContainer = container.querySelector('#runs-table-container');

      // Filter runs
      let filteredRuns = runs;
      if (activeTagFilter) {
        const [k, v] = activeTagFilter.split('=');
        filteredRuns = runs.filter(r => r.tags && r.tags[k] === v);
      }

      if (filteredRuns.length === 0) {
        tableContainer.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">📊</div>
            <div class="empty-title">No runs matching filter</div>
            <p class="empty-desc">Create your first run or reset active tag filters.</p>
            <button class="btn btn-primary" id="empty-add-run-btn">+ Add Run to Experiment</button>
          </div>
        `;
        tableContainer.querySelector('#empty-add-run-btn')?.addEventListener('click', () => openNewRunModal(experiment, refreshTable));
        return;
      }

      // Sorting
      filteredRuns.sort((a, b) => {
        let valA, valB;
        if (sortColumn === 'version') {
          valA = a.version;
          valB = b.version;
        } else if (sortColumn === 'created_at') {
          valA = new Date(a.created_at).getTime();
          valB = new Date(b.created_at).getTime();
        } else if (sortColumn === 'status') {
          valA = a.status;
          valB = b.status;
        } else {
          valA = a.metrics?.[sortColumn] ?? -Infinity;
          valB = b.metrics?.[sortColumn] ?? -Infinity;
        }

        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
      });

      // Compute baseline metrics (from earliest run or v1) for deltas
      const baselineRun = runs.slice().sort((a, b) => a.version - b.version)[0];

      tableContainer.innerHTML = `
        <div class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 38px; text-align: center;">
                  <input type="checkbox" class="custom-checkbox" id="select-all-runs" />
                </th>
                <th data-col="version" class="${sortColumn === 'version' ? 'sort-active' : ''}">
                  Version ${sortColumn === 'version' ? (sortDirection === 'asc' ? '▲' : '▼') : '↕'}
                </th>
                <th data-col="status" class="${sortColumn === 'status' ? 'sort-active' : ''}">Status</th>
                ${allMetricKeys.map(key => `
                  <th data-col="${key}" class="${sortColumn === key ? 'sort-active' : ''}">
                    ${key} ${sortColumn === key ? (sortDirection === 'asc' ? '▲' : '▼') : '↕'}
                  </th>
                `).join('')}
                <th>Tags</th>
                <th>Artifacts</th>
                <th data-col="created_at" class="${sortColumn === 'created_at' ? 'sort-active' : ''}">
                  Date ${sortColumn === 'created_at' ? (sortDirection === 'asc' ? '▲' : '▼') : '↕'}
                </th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody>
              ${filteredRuns.map(run => {
                const isPinned = pinnedRunId === run.id;
                const isSelected = selectedRunIds.has(run.id);

                return `
                  <tr class="${isSelected ? 'selected' : ''}" data-run-id="${run.id}">
                    <td style="text-align: center;">
                      <input type="checkbox" class="custom-checkbox run-row-checkbox" data-id="${run.id}" ${isSelected ? 'checked' : ''} />
                    </td>
                    <td>
                      <div style="display: flex; align-items: center; gap: 8px;">
                        <button class="star-btn ${isPinned ? 'active' : ''}" data-pin-id="${run.id}" title="${isPinned ? 'Pinned as best run' : 'Pin as best run'}">
                          ★
                        </button>
                        <span class="mono" style="font-weight: 600; color: ${isPinned ? 'var(--gold)' : 'var(--text-primary)'};">
                          v${run.version}
                        </span>
                        ${isPinned ? '<span style="font-size: 10px; color: var(--gold); font-weight: 600;">(Best)</span>' : ''}
                      </div>
                    </td>
                    <td>
                      <span class="status-badge ${run.status}">
                        ${run.status === 'sealed' ? '🔒 Sealed' : 'Draft'}
                      </span>
                    </td>
                    ${allMetricKeys.map(mKey => {
                      const val = run.metrics?.[mKey];
                      if (val === undefined || val === null) {
                        return '<td class="mono" style="color: var(--text-muted);">—</td>';
                      }

                      // Compute delta relative to baseline
                      let deltaHtml = '';
                      const baseVal = baselineRun?.metrics?.[mKey];
                      if (baseVal !== undefined && baseVal !== null && run.id !== baselineRun.id && baseVal !== 0) {
                        const diff = val - baseVal;
                        const pct = ((diff / Math.abs(baseVal)) * 100).toFixed(1);
                        const isLoss = mKey.toLowerCase().includes('loss');
                        const isGood = isLoss ? diff < 0 : diff > 0;
                        const sign = diff > 0 ? '+' : '';
                        deltaHtml = `<span class="delta-pill ${isGood ? 'delta-positive' : 'delta-negative'}">${sign}${pct}%</span>`;
                      }

                      return `
                        <td>
                          <div class="metric-cell">
                            <span>${typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(4)) : val}</span>
                            ${deltaHtml}
                          </div>
                        </td>
                      `;
                    }).join('')}
                    <td>
                      <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                        ${Object.entries(run.tags || {}).slice(0, 3).map(([k, v]) => `
                          <span class="tag-chip" style="font-size: 10px;">${k}=${v}</span>
                        `).join('')}
                        ${Object.keys(run.tags || {}).length > 3 ? `<span class="tag-chip" style="font-size: 10px;">+${Object.keys(run.tags).length - 3}</span>` : ''}
                      </div>
                    </td>
                    <td>
                      <button class="btn btn-ghost btn-sm inspect-artifacts-btn" data-run-id="${run.id}" style="font-family: var(--font-mono); font-size: 11px; color: var(--cyan);">
                        📄 ${run.artifacts?.length || 0} files
                      </button>
                    </td>
                    <td class="mono" style="font-size: 12px; color: var(--text-muted);">
                      ${formatDate(run.created_at)}
                    </td>
                    <td style="text-align: right;">
                      <a href="#/runs/${run.id}" class="btn btn-ghost btn-sm" style="color: var(--primary);">View →</a>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;

      // Sort column click handlers
      tableContainer.querySelectorAll('th[data-col]').forEach(th => {
        th.onclick = () => {
          const col = th.dataset.col;
          if (sortColumn === col) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
          } else {
            sortColumn = col;
            sortDirection = 'desc';
          }
          renderTableContent();
        };
      });

      // Row checkbox change handlers
      tableContainer.querySelectorAll('.run-row-checkbox').forEach(cb => {
        cb.onchange = (e) => {
          const rId = parseInt(cb.dataset.id, 10);
          if (cb.checked) {
            selectedRunIds.add(rId);
          } else {
            selectedRunIds.delete(rId);
          }
          cb.closest('tr').classList.toggle('selected', cb.checked);
          syncFloatingDock();
        };
      });

      // Select All checkbox
      const selectAllCb = tableContainer.querySelector('#select-all-runs');
      if (selectAllCb) {
        selectAllCb.checked = filteredRuns.length > 0 && filteredRuns.every(r => selectedRunIds.has(r.id));
        selectAllCb.onchange = (e) => {
          filteredRuns.forEach(r => {
            if (e.target.checked) selectedRunIds.add(r.id);
            else selectedRunIds.delete(r.id);
          });
          renderTableContent();
          syncFloatingDock();
        };
      }

      // Star pin handlers
      tableContainer.querySelectorAll('.star-btn').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const rId = parseInt(btn.dataset.pinId, 10);
          if (pinnedRunId === rId) {
            pinnedRunId = null;
            localStorage.removeItem(`labvault_pin_${experiment.id}`);
          } else {
            pinnedRunId = rId;
            localStorage.setItem(`labvault_pin_${experiment.id}`, rId.toString());
          }
          renderTableContent();
        };
      });

      // Inspect Artifacts click handler
      tableContainer.querySelectorAll('.inspect-artifacts-btn').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const rId = parseInt(btn.dataset.runId, 10);
          const run = runs.find(r => r.id === rId);
          if (run) showArtifactInspector(run);
        };
      });
    }

    function syncFloatingDock() {
      const ids = Array.from(selectedRunIds);
      updateFloatingDock(ids, {
        onCompare: (selIds) => {
          window.location.hash = `#/compare?ids=${selIds.join(',')}`;
        },
        onExport: (selIds) => {
          window.open(api.exportTableUrl(experiment.id, 'latex'), '_blank');
        },
        onClear: () => {
          selectedRunIds.clear();
          renderTableContent();
          syncFloatingDock();
        },
      });
    }

    renderTableContent();

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon" style="color: var(--rose);">✕</div>
        <div class="empty-title">Error loading experiment</div>
        <p class="empty-desc">${err.message}</p>
        <button class="btn btn-secondary" onclick="window.location.hash='#/'">Back to Home</button>
      </div>
    `;
  }
}

function showArtifactInspector(run) {
  const content = document.createElement('div');
  content.innerHTML = `
    <div style="background: var(--bg-card); padding: 14px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span class="mono" style="font-weight: 700; color: var(--text-primary);">Run v${run.version}</span>
        <span class="status-badge ${run.status}">${run.status}</span>
      </div>
      <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">${run.notes || 'No notes for this run.'}</div>
      <a href="#/runs/${run.id}" class="btn btn-secondary btn-sm" style="width: 100%;">Open Full Run Page →</a>
    </div>

    <div class="drawer-section-title">Artifacts (${run.artifacts?.length || 0})</div>
    <div id="inspector-artifacts-list" style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px;">
      ${(run.artifacts || []).map(art => `
        <div class="stat-card" style="padding: 12px 14px; cursor: pointer; flex-direction: row; align-items: center; justify-content: space-between;" data-art-id="${art.id}">
          <div style="display: flex; align-items: center; gap: 10px; overflow: hidden;">
            <span style="font-size: 16px;">📄</span>
            <div style="overflow: hidden;">
              <div style="font-size: 13px; font-weight: 500; color: var(--text-primary); text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">${art.filename}</div>
              <div class="mono" style="font-size: 11px; color: var(--text-muted);">${formatBytes(art.size_bytes)} • ${art.artifact_type}</div>
            </div>
          </div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-ghost btn-sm preview-art-btn" data-art-id="${art.id}" title="Preview">👁</button>
            <a href="${api.downloadArtifactUrl(art.id)}" class="btn btn-ghost btn-sm" title="Download" download>⭳</a>
          </div>
        </div>
      `).join('')}
    </div>

    <div class="drawer-section-title">Preview</div>
    <div id="inspector-preview-box" class="preview-container">
      <div style="text-align: center; color: var(--text-muted); padding: 24px; font-size: 12px;">
        Click an artifact above to preview inline (images, CSV tables, source code).
      </div>
    </div>
  `;

  content.querySelectorAll('.preview-art-btn, [data-art-id]').forEach(el => {
    el.onclick = async (e) => {
      e.stopPropagation();
      const artId = el.dataset.artId || el.closest('[data-art-id]').dataset.artId;
      const previewBox = content.querySelector('#inspector-preview-box');
      previewBox.innerHTML = '<div class="mono" style="color: var(--text-muted); text-align: center; padding: 20px;">Loading preview...</div>';

      try {
        const preview = await api.previewArtifact(artId);
        if (preview.type === 'image') {
          previewBox.innerHTML = `
            <img src="${preview.data}" alt="Artifact Preview" />
            <div style="text-align: center; margin-top: 8px; font-size: 11px; color: var(--text-muted);">${preview.mime}</div>
          `;
        } else if (preview.type === 'table') {
          previewBox.innerHTML = `
            <table class="data-table" style="font-size: 11px;">
              <thead>
                <tr>${preview.headers.map(h => `<th>${h}</th>`).join('')}</tr>
              </thead>
              <tbody>
                ${preview.rows.slice(0, 50).map(row => `
                  <tr>${preview.headers.map(h => `<td>${row[h] || ''}</td>`).join('')}</tr>
                `).join('')}
              </tbody>
            </table>
            ${preview.rows.length > 50 ? `<div style="text-align: center; font-size: 11px; color: var(--text-muted); padding: 8px;">Showing 50 of ${preview.rows.length} rows</div>` : ''}
          `;
        } else if (preview.type === 'text') {
          previewBox.innerHTML = `
            <pre class="preview-code-block"><code class="language-${preview.language}">${escapeHtml(preview.content.slice(0, 10000))}</code></pre>
          `;
          if (window.hljs) {
            window.hljs.highlightElement(previewBox.querySelector('code'));
          }
        } else {
          previewBox.innerHTML = `
            <div style="text-align: center; padding: 24px;">
              <div style="font-size: 24px; margin-bottom: 8px;">💾</div>
              <div style="font-weight: 500; margin-bottom: 4px;">${preview.filename}</div>
              <div class="mono" style="font-size: 12px; color: var(--text-muted);">${formatBytes(preview.size_bytes)}</div>
              <a href="${api.downloadArtifactUrl(artId)}" class="btn btn-primary btn-sm" style="margin-top: 14px;" download>Download File</a>
            </div>
          `;
        }
      } catch (err) {
        previewBox.innerHTML = `<div style="color: var(--rose); font-size: 12px; text-align: center; padding: 20px;">${err.message}</div>`;
      }
    };
  });

  openInspectorDrawer(`Run v${run.version} Artifacts`, content);
}

function openNewRunModal(experiment, onSuccess) {
  let droppedFiles = [];

  const form = document.createElement('div');
  form.innerHTML = `
    <div class="form-group">
      <label class="form-label" for="run-metrics">Metrics (e.g. <code>val_loss=0.298, f1=0.913, accuracy=0.92</code>)</label>
      <input type="text" id="run-metrics" class="form-input mono" placeholder="key=value, key2=value2" />
    </div>

    <div class="form-group">
      <label class="form-label" for="run-tags">Tags (e.g. <code>lr=0.0001, model=resnet50, env=colab</code>)</label>
      <input type="text" id="run-tags" class="form-input mono" placeholder="key=value, key2=value2" />
    </div>

    <div class="form-group">
      <label class="form-label" for="run-notes">Run Notes</label>
      <textarea id="run-notes" class="form-textarea" rows="2" placeholder="Hypothesis, dataset changes, hardware setup..."></textarea>
    </div>

    <div class="form-group">
      <label class="form-label">Artifact Files (Drop files to store & version)</label>
      <div id="new-run-dropzone-container"></div>
      <div id="new-run-files-list" style="margin-top: 8px; display: flex; flex-direction: column; gap: 4px;"></div>
    </div>
  `;

  const dropzoneEl = createDropzone((files) => {
    droppedFiles = droppedFiles.concat(files);
    renderFileList();
  }, 'Drag & drop checkpoints (.pt, .ckpt), notebooks, CSVs, logs');

  form.querySelector('#new-run-dropzone-container').appendChild(dropzoneEl);

  function renderFileList() {
    const listEl = form.querySelector('#new-run-files-list');
    listEl.innerHTML = droppedFiles.map((f, idx) => `
      <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface); padding: 4px 10px; border-radius: 4px; font-size: 12px;">
        <span class="mono">${f.name} (${formatBytes(f.size)})</span>
        <button type="button" class="btn btn-ghost btn-sm remove-file-btn" data-idx="${idx}" style="color: var(--rose); padding: 0 4px;">✕</button>
      </div>
    `).join('');

    listEl.querySelectorAll('.remove-file-btn').forEach(btn => {
      btn.onclick = () => {
        const i = parseInt(btn.dataset.idx, 10);
        droppedFiles.splice(i, 1);
        renderFileList();
      };
    });
  }

  showModal({
    title: `Record New Run in ${experiment.name}`,
    body: form,
    footer: `
      <button class="btn btn-secondary" id="modal-cancel-btn">Cancel</button>
      <button class="btn btn-primary" id="modal-submit-btn">Save Run & Upload</button>
    `,
  });

  document.getElementById('modal-cancel-btn').onclick = closeModal;
  document.getElementById('modal-submit-btn').onclick = async () => {
    const metricsStr = document.getElementById('run-metrics').value.trim();
    const tagsStr = document.getElementById('run-tags').value.trim();
    const notes = document.getElementById('run-notes').value.trim();

    // Parse metrics
    const metrics = {};
    if (metricsStr) {
      metricsStr.split(',').forEach(part => {
        const [k, v] = part.split('=').map(s => s.trim());
        if (k && v !== undefined) {
          const num = parseFloat(v);
          metrics[k] = isNaN(num) ? v : num;
        }
      });
    }

    // Parse tags
    const tags = {};
    if (tagsStr) {
      tagsStr.split(',').forEach(part => {
        const [k, v] = part.split('=').map(s => s.trim());
        if (k && v !== undefined) tags[k] = v;
      });
    }

    try {
      const submitBtn = document.getElementById('modal-submit-btn');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Saving Run...';

      const newRun = await api.createRun(experiment.id, { metrics, tags, notes });

      // Upload dropped files
      if (droppedFiles.length > 0) {
        submitBtn.textContent = `Uploading ${droppedFiles.length} file(s)...`;
        for (const file of droppedFiles) {
          await api.uploadArtifact(newRun.id, file);
        }
      }

      closeModal();
      showToast(`Run v${newRun.version} created successfully!`, 'success');
      if (onSuccess) onSuccess();
    } catch (err) {
      showToast(err.message, 'error');
      const submitBtn = document.getElementById('modal-submit-btn');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save Run & Upload';
      }
    }
  };
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
