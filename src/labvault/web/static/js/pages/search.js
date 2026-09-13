/**
 * Global Search View: FTS5 query, tag filters, and metric ranges
 */

import { api } from '../api.js';
import { setBreadcrumbs, formatDate } from '../components.js';

export async function renderSearch(container, queryParams = {}) {
  const initialQ = queryParams.q || '';
  const initialTag = queryParams.tag || '';
  const initialMetric = queryParams.metric || '';

  setBreadcrumbs([
    { label: 'Vault', href: '#/' },
    { label: `Search`, href: `#/search` },
  ]);

  container.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <h1>🔍 Search Vault</h1>
        <p class="page-desc">Search full-text notes, filter by tags (<code>env=colab</code>), or evaluate metric ranges (<code>f1 > 0.9</code>)</p>
      </div>
    </div>

    <!-- Search Controls -->
    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 20px; margin-bottom: 24px;">
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)) 120px; gap: 14px; align-items: flex-end;">
        <div class="form-group" style="margin-bottom: 0;">
          <label class="form-label">Full-Text Query</label>
          <input type="text" id="search-q" class="form-input" placeholder="e.g. baseline, resnet, sweep..." value="${escapeHtml(initialQ)}" />
        </div>
        <div class="form-group" style="margin-bottom: 0;">
          <label class="form-label">Tag Filter</label>
          <input type="text" id="search-tag" class="form-input mono" placeholder="e.g. env=local, model=bert" value="${escapeHtml(initialTag)}" />
        </div>
        <div class="form-group" style="margin-bottom: 0;">
          <label class="form-label">Metric Condition</label>
          <input type="text" id="search-metric" class="form-input mono" placeholder="e.g. val_loss < 0.3" value="${escapeHtml(initialMetric)}" />
        </div>
        <button class="btn btn-primary" id="do-search-btn" style="height: 38px;">
          <span>Search</span>
        </button>
      </div>
    </div>

    <!-- Results Area -->
    <div id="search-results-container">
      <div class="empty-state">
        <div class="empty-icon">⌕</div>
        <div class="empty-title">Enter search criteria above</div>
        <p class="empty-desc">You can combine text search, tag filters, and numeric metric thresholds.</p>
      </div>
    </div>
  `;

  const resultsContainer = container.querySelector('#search-results-container');
  const qInput = container.querySelector('#search-q');
  const tagInput = container.querySelector('#search-tag');
  const metricInput = container.querySelector('#search-metric');
  const searchBtn = container.querySelector('#do-search-btn');

  async function executeSearch() {
    const q = qInput.value.trim();
    const tag = tagInput.value.trim();
    const metric = metricInput.value.trim();

    resultsContainer.innerHTML = `
      <div style="display: flex; justify-content: center; padding: 40px;">
        <span class="mono" style="color: var(--text-muted);">Searching Vault index...</span>
      </div>
    `;

    try {
      const results = await api.search({ q, tag, metric });

      if (!results || results.length === 0) {
        resultsContainer.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">📭</div>
            <div class="empty-title">No matching runs found</div>
            <p class="empty-desc">Try relaxing your query or checking your tag/metric filter syntax.</p>
          </div>
        `;
        return;
      }

      resultsContainer.innerHTML = `
        <div style="margin-bottom: 14px; font-size: 13px; color: var(--text-muted);">
          Found <span class="mono" style="color: var(--text-primary); font-weight: 600;">${results.length}</span> matching runs
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Experiment</th>
                <th>Version</th>
                <th>Status</th>
                <th>Notes</th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody>
              ${results.map(r => `
                <tr>
                  <td>
                    <span style="font-weight: 500; color: var(--text-primary);">${r.project_name || '—'}</span>
                  </td>
                  <td>
                    <span class="mono" style="color: #818CF8;">${r.experiment_name || '—'}</span>
                  </td>
                  <td>
                    <span class="mono" style="font-weight: 700; color: var(--cyan);">v${r.version}</span>
                  </td>
                  <td>
                    <span class="status-badge ${r.status || 'draft'}">${r.status || 'draft'}</span>
                  </td>
                  <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary);">
                    ${r.notes || '—'}
                  </td>
                  <td style="text-align: right;">
                    <a href="#/runs/${r.run_id}" class="btn btn-secondary btn-sm">Inspect Run →</a>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (err) {
      resultsContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon" style="color: var(--rose);">✕</div>
          <div class="empty-title">Search Error</div>
          <p class="empty-desc">${err.message}</p>
        </div>
      `;
    }
  }

  searchBtn.onclick = executeSearch;
  [qInput, tagInput, metricInput].forEach(inp => {
    inp.onkeydown = (e) => {
      if (e.key === 'Enter') executeSearch();
    };
  });

  if (initialQ || initialTag || initialMetric) {
    executeSearch();
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
