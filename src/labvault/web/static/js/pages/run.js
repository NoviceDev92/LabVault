/**
 * Run Detail View: Deep-dive inspector into metadata, metrics, tags,
 * file previews, run sealing, and ZIP packaging.
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
  createDropzone
} from '../components.js';

export async function renderRun(container, runId) {
  container.innerHTML = `
    <div style="display: flex; justify-content: center; align-items: center; min-height: 200px;">
      <span class="mono" style="color: var(--text-muted);">Loading Run details...</span>
    </div>
  `;

  try {
    const run = await api.getRun(runId);

    setBreadcrumbs([
      { label: 'Vault', href: '#/' },
      { label: `Run v${run.version}`, href: `#/runs/${run.id}` },
    ]);

    function refreshView() {
      renderRun(container, runId);
    }

    container.innerHTML = `
      <div class="page-header">
        <div class="page-title-group">
          <h1>
            <span>Run v${run.version}</span>
            <span class="status-badge ${run.status}">
              ${run.status === 'sealed' ? '🔒 Sealed' : 'Draft'}
            </span>
          </h1>
          <p class="page-desc">Created ${formatDate(run.created_at)} ${run.sealed_at ? `• Sealed ${formatDate(run.sealed_at)}` : ''}</p>
        </div>

        <div class="page-actions">
          <button class="btn btn-secondary" id="back-btn">← Back</button>
          <a href="${api.exportRunZipUrl(run.id)}" class="btn btn-secondary" download>
            <span>⭳ Download ZIP</span>
          </a>
          ${run.status !== 'sealed' ? `
            <button class="btn btn-primary" id="seal-run-btn" style="background: linear-gradient(135deg, #06B6D4, #0891B2);">
              <span>🔒 Seal Run</span>
            </button>
          ` : ''}
        </div>
      </div>

      <!-- Metadata & Metrics Row -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; margin-bottom: 24px;">
        
        <!-- Metrics Card -->
        <div class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="stat-label">Metrics</span>
            ${run.status !== 'sealed' ? '<button class="btn btn-ghost btn-sm" id="edit-metrics-btn" style="font-size: 11px;">Edit ✎</button>' : ''}
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${Object.entries(run.metrics || {}).length > 0 ? Object.entries(run.metrics).map(([k, v]) => `
              <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-subtle); padding-bottom: 4px;">
                <span style="color: var(--text-secondary); font-size: 13px;">${k}</span>
                <span class="mono" style="font-weight: 600; color: var(--text-primary); font-size: 14px;">${v}</span>
              </div>
            `).join('') : '<div style="color: var(--text-muted); font-size: 12px;">No metrics recorded.</div>'}
          </div>
        </div>

        <!-- Tags Card -->
        <div class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="stat-label">Tags</span>
            ${run.status !== 'sealed' ? '<button class="btn btn-ghost btn-sm" id="edit-tags-btn" style="font-size: 11px;">Edit ✎</button>' : ''}
          </div>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            ${Object.entries(run.tags || {}).length > 0 ? Object.entries(run.tags).map(([k, v]) => `
              <span class="tag-chip">${k}=${v}</span>
            `).join('') : '<div style="color: var(--text-muted); font-size: 12px;">No tags recorded.</div>'}
          </div>
        </div>

        <!-- Notes Card -->
        <div class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="stat-label">Notes</span>
            ${run.status !== 'sealed' ? '<button class="btn btn-ghost btn-sm" id="edit-notes-btn" style="font-size: 11px;">Edit ✎</button>' : ''}
          </div>
          <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.5; white-space: pre-wrap;">${run.notes || 'No notes provided for this run.'}</p>
        </div>

      </div>

      <!-- Artifacts Section -->
      <div style="margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
        <h2 style="font-size: 18px; font-weight: 600;">Run Artifacts (${run.artifacts?.length || 0})</h2>
      </div>

      <div class="table-container" style="margin-bottom: 24px;">
        <table class="data-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Type</th>
              <th>Size</th>
              <th>SHA-256 Hash</th>
              <th>Created</th>
              <th style="text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${(run.artifacts || []).length > 0 ? run.artifacts.map(art => `
              <tr data-art-id="${art.id}">
                <td>
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <span>📄</span>
                    <span style="font-weight: 500; color: var(--text-primary);">${art.filename}</span>
                  </div>
                </td>
                <td>
                  <span class="tag-chip" style="font-size: 10px;">${art.artifact_type}</span>
                </td>
                <td class="mono">${formatBytes(art.size_bytes)}</td>
                <td class="mono" style="font-size: 11px; color: var(--text-muted);" title="${art.content_hash}">
                  ${art.content_hash ? art.content_hash.slice(0, 10) + '...' : '—'}
                </td>
                <td class="mono" style="font-size: 12px; color: var(--text-muted);">${formatDate(art.created_at)}</td>
                <td style="text-align: right;">
                  <button class="btn btn-secondary btn-sm preview-btn" data-id="${art.id}">👁 Preview</button>
                  <a href="${api.downloadArtifactUrl(art.id)}" class="btn btn-ghost btn-sm" download>⭳ Download</a>
                </td>
              </tr>
            `).join('') : `
              <tr>
                <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No artifacts uploaded yet.</td>
              </tr>
            `}
          </tbody>
        </table>
      </div>

      <!-- Drag & Drop Upload Zone (if run is not sealed) -->
      ${run.status !== 'sealed' ? `
        <div style="margin-top: 16px;">
          <h3 style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">Add More Artifacts</h3>
          <div id="run-dropzone-container"></div>
        </div>
      ` : `
        <div style="background: rgba(99, 102, 241, 0.05); border: 1px dashed var(--primary); padding: 14px 20px; border-radius: var(--radius-md); font-size: 13px; color: #A5B4FC; text-align: center;">
          🔒 This run is sealed and immutable. Artifacts, metrics, and tags cannot be modified.
        </div>
      `}
    `;

    // Back button
    container.querySelector('#back-btn').onclick = () => window.history.back();

    // Seal button
    const sealBtn = container.querySelector('#seal-run-btn');
    if (sealBtn) {
      sealBtn.onclick = async () => {
        if (confirm(`Seal Run v${run.version}? This permanently makes the run immutable and prevents further edits.`)) {
          try {
            await api.sealRun(run.id);
            showToast(`Run v${run.version} is now sealed!`, 'success');
            refreshView();
          } catch (err) {
            showToast(err.message, 'error');
          }
        }
      };
    }

    // Edit notes
    const editNotesBtn = container.querySelector('#edit-notes-btn');
    if (editNotesBtn) {
      editNotesBtn.onclick = () => {
        const body = document.createElement('div');
        body.innerHTML = `
          <div class="form-group">
            <label class="form-label" for="edit-notes-input">Notes</label>
            <textarea id="edit-notes-input" class="form-textarea" rows="4">${run.notes || ''}</textarea>
          </div>
        `;
        showModal({
          title: `Edit Notes for v${run.version}`,
          body,
          footer: `
            <button class="btn btn-secondary" id="modal-cancel-btn">Cancel</button>
            <button class="btn btn-primary" id="modal-save-btn">Save Notes</button>
          `,
        });
        document.getElementById('modal-cancel-btn').onclick = closeModal;
        document.getElementById('modal-save-btn').onclick = async () => {
          const notes = document.getElementById('edit-notes-input').value;
          try {
            await api.updateRun(run.id, { notes });
            closeModal();
            showToast('Notes updated', 'success');
            refreshView();
          } catch (err) {
            showToast(err.message, 'error');
          }
        };
      };
    }

    // Preview buttons
    container.querySelectorAll('.preview-btn').forEach(btn => {
      btn.onclick = async () => {
        const artId = btn.dataset.id;
        const art = run.artifacts.find(a => a.id === parseInt(artId, 10));
        try {
          const preview = await api.previewArtifact(artId);
          openPreviewModal(art, preview);
        } catch (err) {
          showToast(err.message, 'error');
        }
      };
    });

    // Dropzone for adding artifacts
    const dropzoneContainer = container.querySelector('#run-dropzone-container');
    if (dropzoneContainer) {
      const dropzone = createDropzone(async (files) => {
        showToast(`Uploading ${files.length} file(s)...`, 'info');
        try {
          for (const file of files) {
            await api.uploadArtifact(run.id, file);
          }
          showToast('Files uploaded successfully!', 'success');
          refreshView();
        } catch (err) {
          showToast(err.message, 'error');
        }
      }, 'Drag & drop additional files to attach to this run');
      dropzoneContainer.appendChild(dropzone);
    }

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon" style="color: var(--rose);">✕</div>
        <div class="empty-title">Error loading run</div>
        <p class="empty-desc">${err.message}</p>
        <button class="btn btn-secondary" onclick="window.location.hash='#/'">Back to Home</button>
      </div>
    `;
  }
}

function openPreviewModal(art, preview) {
  const content = document.createElement('div');
  content.className = 'preview-container';
  content.style.maxHeight = '500px';

  if (preview.type === 'image') {
    content.innerHTML = `
      <img src="${preview.data}" alt="${art.filename}" style="max-height: 420px; margin: 0 auto; display: block;" />
      <div style="text-align: center; margin-top: 10px; font-size: 11px; color: var(--text-muted);">${preview.mime}</div>
    `;
  } else if (preview.type === 'table') {
    content.innerHTML = `
      <table class="data-table" style="font-size: 11px;">
        <thead>
          <tr>${preview.headers.map(h => `<th>${h}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${preview.rows.slice(0, 100).map(row => `
            <tr>${preview.headers.map(h => `<td>${row[h] || ''}</td>`).join('')}</tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } else if (preview.type === 'text') {
    content.innerHTML = `
      <pre class="preview-code-block"><code class="language-${preview.language}">${escapeHtml(preview.content)}</code></pre>
    `;
    if (window.hljs) {
      window.hljs.highlightElement(content.querySelector('code'));
    }
  } else {
    content.innerHTML = `
      <div style="text-align: center; padding: 24px;">
        <div style="font-size: 32px; margin-bottom: 8px;">💾</div>
        <div style="font-weight: 500; font-size: 15px; margin-bottom: 4px;">${art.filename}</div>
        <div class="mono" style="font-size: 12px; color: var(--text-muted);">${formatBytes(art.size_bytes)}</div>
        <a href="${api.downloadArtifactUrl(art.id)}" class="btn btn-primary" style="margin-top: 16px;" download>Download File</a>
      </div>
    `;
  }

  showModal({
    title: `Preview: ${art.filename}`,
    body: content,
    footer: `
      <a href="${api.downloadArtifactUrl(art.id)}" class="btn btn-secondary" download>⭳ Download File</a>
      <button class="btn btn-primary" id="modal-close-btn">Close</button>
    `,
  });

  document.getElementById('modal-close-btn').onclick = closeModal;
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
