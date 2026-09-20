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

// ─── Global Loading Overlay ───
function getOrCreateLoader() {
  let el = document.getElementById('global-loader');
  if (!el) {
    el = document.createElement('div');
    el.id = 'global-loader';
    el.className = 'global-loader';
    el.innerHTML = `
      <div class="loader-spinner"></div>
      <span class="mono" style="color: var(--text-muted); font-size: 12px; margin-top: 12px;">Loading...</span>
    `;
    document.body.appendChild(el);
  }
  return el;
}

window.setLoading = function(on) {
  const loader = getOrCreateLoader();
  if (on) {
    loader.classList.add('visible');
  } else {
    loader.classList.remove('visible');
  }
};

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

  window.setLoading(true);

  try {
    if (path.length === 0) {
      await renderHome(appContent);
    } else if (path[0] === 'projects' && path[1]) {
      await renderProject(appContent, path[1]);
    } else if (path[0] === 'experiments' && path[1] && path[2]) {
      await renderExperiment(appContent, path[1], path[2]);
    } else if (path[0] === 'runs' && path[1]) {
      await renderRun(appContent, parseInt(path[1], 10));
    } else if (path[0] === 'compare') {
      await renderCompare(appContent, query);
    } else if (path[0] === 'search') {
      await renderSearch(appContent, query);
    } else {
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
  } finally {
    window.setLoading(false);
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
