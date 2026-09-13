/**
 * Home Page: Projects Overview & Vault Stats
 */

import { api } from '../api.js';
import { setBreadcrumbs, showToast, showModal, closeModal } from '../components.js';

export async function renderHome(container) {
  setBreadcrumbs([{ label: 'Vault', href: '#/' }]);

  container.innerHTML = `
    <div style="display: flex; justify-content: center; align-items: center; min-height: 200px;">
      <span class="mono" style="color: var(--text-muted);">Loading Vault...</span>
    </div>
  `;

  try {
    const [stats, projects] = await Promise.all([
      api.getStats().catch(() => null),
      api.listProjects(),
    ]);

    // Update navbar disk usage pill
    const statusText = document.getElementById('vault-stats-text');
    if (statusText && stats) {
      statusText.textContent = `${stats.total_runs} runs • ${stats.disk_usage_formatted}`;
    }

    container.innerHTML = `
      <!-- Page Header -->
      <div class="page-header">
        <div class="page-title-group">
          <h1>🔬 LabVault Workspace</h1>
          <p class="page-desc">Local-first experiment versioning, metric tracking, and ablation workbench</p>
        </div>
        <div class="page-actions">
          <button class="btn btn-primary" id="new-project-btn">
            <span>+ New Project</span>
          </button>
        </div>
      </div>

      <!-- Vault Stats Grid -->
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-label">Total Projects</span>
          <span class="stat-value">${stats ? stats.total_projects : projects.length}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Experiments</span>
          <span class="stat-value">${stats ? stats.total_experiments : '—'}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Tracked Runs</span>
          <span class="stat-value mono" style="color: var(--cyan);">${stats ? stats.total_runs : '—'}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Artifacts Stored</span>
          <span class="stat-value">${stats ? stats.total_artifacts : '—'}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Vault Storage</span>
          <span class="stat-value mono" style="color: #A5B4FC;">${stats ? stats.disk_usage_formatted : '—'}</span>
        </div>
      </div>

      <!-- Projects Grid -->
      <div style="margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
        <h2 style="font-size: 18px; font-weight: 600;">Research Projects</h2>
        <span style="font-size: 12px; color: var(--text-muted);">${projects.length} projects active</span>
      </div>

      <div class="projects-grid" id="projects-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px;">
        <!-- Project cards injected -->
      </div>
    `;

    const projectsGrid = container.querySelector('#projects-grid');

    if (projects.length === 0) {
      projectsGrid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <div class="empty-icon">📁</div>
          <div class="empty-title">No projects yet</div>
          <p class="empty-desc">Create your first research project or run <code>labvault add &lt;files...&gt;</code> from your terminal.</p>
          <button class="btn btn-primary" id="empty-new-proj-btn">+ Create First Project</button>
        </div>
      `;
      container.querySelector('#empty-new-proj-btn')?.addEventListener('click', openNewProjectModal);
    } else {
      projects.forEach((proj) => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.style.cursor = 'pointer';
        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary);">${proj.name}</h3>
            <span class="mono" style="font-size: 11px; padding: 2px 6px; background: rgba(255,255,255,0.05); border-radius: 4px; color: var(--text-muted);">${proj.slug}</span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 14px; min-height: 36px;">
            ${proj.description || 'No description provided.'}
          </p>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 10px; font-size: 12px; color: var(--text-muted);">
            <span>View Experiments →</span>
            <button class="btn btn-ghost btn-sm delete-proj-btn" data-slug="${proj.slug}" title="Delete Project" style="color: var(--rose);">🗑</button>
          </div>
        `;

        card.onclick = (e) => {
          if (e.target.closest('.delete-proj-btn')) return;
          window.location.hash = `#/projects/${proj.slug}`;
        };

        const delBtn = card.querySelector('.delete-proj-btn');
        if (delBtn) {
          delBtn.onclick = async (e) => {
            e.stopPropagation();
            if (confirm(`Are you sure you want to delete project '${proj.name}'?`)) {
              try {
                await api.deleteProject(proj.slug);
                showToast(`Project '${proj.name}' deleted`, 'info');
                renderHome(container);
              } catch (err) {
                showToast(err.message, 'error');
              }
            }
          };
        }

        projectsGrid.appendChild(card);
      });
    }

    container.querySelector('#new-project-btn')?.addEventListener('click', openNewProjectModal);

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon" style="color: var(--rose);">✕</div>
        <div class="empty-title">Error loading workspace</div>
        <p class="empty-desc">${err.message}</p>
        <button class="btn btn-secondary" onclick="window.location.reload()">Retry</button>
      </div>
    `;
  }
}

function openNewProjectModal() {
  const form = document.createElement('div');
  form.innerHTML = `
    <div class="form-group">
      <label class="form-label" for="proj-name">Project Name</label>
      <input type="text" id="proj-name" class="form-input" placeholder="e.g. Computer Vision ResNet" autofocus />
    </div>
    <div class="form-group">
      <label class="form-label" for="proj-desc">Description (Optional)</label>
      <textarea id="proj-desc" class="form-textarea" rows="3" placeholder="Brief summary of research goals..."></textarea>
    </div>
  `;

  showModal({
    title: 'Create Research Project',
    body: form,
    footer: `
      <button class="btn btn-secondary" id="modal-cancel-btn">Cancel</button>
      <button class="btn btn-primary" id="modal-submit-btn">Create Project</button>
    `,
  });

  document.getElementById('modal-cancel-btn').onclick = closeModal;
  document.getElementById('modal-submit-btn').onclick = async () => {
    const name = document.getElementById('proj-name').value.trim();
    const desc = document.getElementById('proj-desc').value.trim();

    if (!name) {
      showToast('Project name is required', 'error');
      return;
    }

    try {
      const proj = await api.createProject(name, desc);
      closeModal();
      showToast(`Project '${proj.name}' created!`, 'success');
      window.location.hash = `#/projects/${proj.slug}`;
    } catch (err) {
      showToast(err.message, 'error');
    }
  };
}
