/**
 * LabVault Client-Side SPA Router & Application Bootstrap
 */

import { api } from './api.js';
import { renderHome } from './pages/home.js';
import { renderProject } from './pages/project.js';
import { renderExperiment } from './pages/experiment.js';
import { renderRun } from './pages/run.js';
import { renderCompare } from './pages/compare.js';
import { renderSearch } from './pages/search.js';
import { closeInspectorDrawer } from './components.js';

const appContent = document.getElementById('app-content');

// Simple parse for query params from hash: #/route?key=val&key2=val2
function parseHash(hash) {
  const clean = hash.replace(/^#\/?/, '');
  const [pathPart, queryPart] = clean.split('?');
  const path = pathPart ? pathPart.split('/').filter(Boolean) : [];
  const query = {};

  if (queryPart) {
    const params = new URLSearchParams(queryPart);
    for (const [k, v] of params.entries()) {
      query[k] = v;
    }
  }

  return { path, query };
}

async function router() {
  closeInspectorDrawer();
  window.scrollTo(0, 0);

  const hash = window.location.hash || '#/';
  const { path, query } = parseHash(hash);

  try {
    if (path.length === 0) {
      // #/ (Home)
      await renderHome(appContent);
    } else if (path[0] === 'projects' && path[1]) {
      // #/projects/:slug
      await renderProject(appContent, path[1]);
    } else if (path[0] === 'experiments' && path[1] && path[2]) {
      // #/experiments/:projectSlug/:expSlug
      await renderExperiment(appContent, path[1], path[2]);
    } else if (path[0] === 'runs' && path[1]) {
      // #/runs/:id
      await renderRun(appContent, parseInt(path[1], 10));
    } else if (path[0] === 'compare') {
      // #/compare?ids=1,2
      await renderCompare(appContent, query);
    } else if (path[0] === 'search') {
      // #/search?q=...
      await renderSearch(appContent, query);
    } else {
      // Fallback
      await renderHome(appContent);
    }
  } catch (err) {
    appContent.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon" style="color: var(--rose);">✕</div>
        <div class="empty-title">Page Routing Error</div>
        <p class="empty-desc">${err.message}</p>
        <button class="btn btn-secondary" onclick="window.location.hash='#/'">Return to Vault</button>
      </div>
    `;
  }
}

// Global Search bar & shortcuts
function setupGlobalSearch() {
  const searchInput = document.getElementById('global-search-input');
  if (!searchInput) return;

  // Keyboard shortcut Ctrl+K / Cmd+K
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = searchInput.value.trim();
      if (q) {
        window.location.hash = `#/search?q=${encodeURIComponent(q)}`;
      }
    }
  });
}

// Load global vault stats into header
async function loadVaultStats() {
  try {
    const stats = await api.getStats();
    const statsText = document.getElementById('vault-stats-text');
    if (statsText && stats) {
      statsText.textContent = `${stats.total_runs} runs • ${stats.disk_usage_formatted}`;
    }
  } catch (_) {
    const statsText = document.getElementById('vault-stats-text');
    if (statsText) statsText.textContent = 'Vault Active';
  }
}

// Initialize Application
window.addEventListener('hashchange', router);
window.addEventListener('DOMContentLoaded', () => {
  setupGlobalSearch();
  loadVaultStats();
  router();
});
