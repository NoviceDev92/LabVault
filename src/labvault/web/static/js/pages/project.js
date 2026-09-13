/**
 * Project Detail Page: Lists Experiments within a Project
 */

import { api } from '../api.js';
import { setBreadcrumbs, showToast, showModal, closeModal } from '../components.js';

export async function renderProject(container, projectSlug) {
  setBreadcrumbs([
    { label: 'Vault', href: '#/' },
    { label: projectSlug, href: `#/projects/${projectSlug}` },
  ]);

  container.innerHTML = `
    <div style="display: flex; justify-content: center; align-items: center; min-height: 200px;">
      <span class="mono" style="color: var(--text-muted);">Loading Project...</span>
    </div>
  `;

  try {
    const [project, experiments] = await Promise.all([
      api.getProject(projectSlug),
      api.listExperiments(projectSlug),
    ]);

    setBreadcrumbs([
      { label: 'Vault', href: '#/' },
      { label: project.name, href: `#/projects/${projectSlug}` },
    ]);

    container.innerHTML = `
      <div class="page-header">
        <div class="page-title-group">
          <h1>📦 ${project.name}</h1>
          <p class="page-desc">${project.description || 'No description provided.'}</p>
        </div>
        <div class="page-actions">
          <button class="btn btn-secondary" onclick="window.location.hash='#/'">← All Projects</button>
          <button class="btn btn-primary" id="new-experiment-btn">
            <span>+ New Experiment</span>
          </button>
        </div>
      </div>

      <div style="margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
        <h2 style="font-size: 18px; font-weight: 600;">Experiments</h2>
        <span style="font-size: 12px; color: var(--text-muted);">${experiments.length} experiments</span>
      </div>

      <div class="experiments-grid" id="experiments-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px;">
        <!-- Experiments injected -->
      </div>
    `;

    const grid = container.querySelector('#experiments-grid');

    if (experiments.length === 0) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <div class="empty-icon">🧪</div>
          <div class="empty-title">No experiments in this project</div>
          <p class="empty-desc">Create an experiment track (e.g. "learning-rate-sweep" or "resnet-ablation") to record runs.</p>
          <button class="btn btn-primary" id="empty-new-exp-btn">+ Create First Experiment</button>
        </div>
      `;
      container.querySelector('#empty-new-exp-btn')?.addEventListener('click', () => openNewExperimentModal(projectSlug));
    } else {
      experiments.forEach((exp) => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.style.cursor = 'pointer';
        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary);">${exp.name}</h3>
            <span class="mono" style="font-size: 11px; padding: 2px 6px; background: rgba(99,102,241,0.1); border-radius: 4px; color: #818CF8;">${exp.slug}</span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 14px; min-height: 36px;">
            ${exp.description || 'No description provided.'}
          </p>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 10px; font-size: 12px; color: var(--cyan);">
            <span>Open Results Dashboard →</span>
          </div>
        `;

        card.onclick = () => {
          window.location.hash = `#/experiments/${projectSlug}/${exp.slug}`;
        };

        grid.appendChild(card);
      });
    }

    container.querySelector('#new-experiment-btn')?.addEventListener('click', () => openNewExperimentModal(projectSlug));

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon" style="color: var(--rose);">✕</div>
        <div class="empty-title">Error loading project</div>
        <p class="empty-desc">${err.message}</p>
        <button class="btn btn-secondary" onclick="window.location.hash='#/'">Back to Home</button>
      </div>
    `;
  }
}

function openNewExperimentModal(projectSlug) {
  const form = document.createElement('div');
  form.innerHTML = `
    <div class="form-group">
      <label class="form-label" for="exp-name">Experiment Name</label>
      <input type="text" id="exp-name" class="form-input" placeholder="e.g. Learning Rate Sweep" autofocus />
    </div>
    <div class="form-group">
      <label class="form-label" for="exp-desc">Description (Optional)</label>
      <textarea id="exp-desc" class="form-textarea" rows="3" placeholder="Hypothesis or ablation scope..."></textarea>
    </div>
  `;

  showModal({
    title: 'Create Experiment Track',
    body: form,
    footer: `
      <button class="btn btn-secondary" id="modal-cancel-btn">Cancel</button>
      <button class="btn btn-primary" id="modal-submit-btn">Create Experiment</button>
    `,
  });

  document.getElementById('modal-cancel-btn').onclick = closeModal;
  document.getElementById('modal-submit-btn').onclick = async () => {
    const name = document.getElementById('exp-name').value.trim();
    const desc = document.getElementById('exp-desc').value.trim();

    if (!name) {
      showToast('Experiment name is required', 'error');
      return;
    }

    try {
      const exp = await api.createExperiment(projectSlug, name, desc);
      closeModal();
      showToast(`Experiment '${exp.name}' created!`, 'success');
      window.location.hash = `#/experiments/${projectSlug}/${exp.slug}`;
    } catch (err) {
      showToast(err.message, 'error');
    }
  };
}
