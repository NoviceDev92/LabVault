/**
 * LabVault Web API Client
 * Clean async fetch wrapper for all backend REST endpoints.
 */

const BASE_URL = '/api';

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const headers = options.headers || {};
  
  if (!(options.body instanceof FormData) && !headers['Content-Type'] && options.method && options.method !== 'GET') {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  if (!response.ok) {
    let errorDetail = `Request failed (${response.status})`;
    try {
      if (contentType.includes('application/json')) {
        const errJson = await response.json();
        errorDetail = errJson.detail || JSON.stringify(errJson);
      } else {
        errorDetail = await response.text();
      }
    } catch (_) {}
    throw new Error(errorDetail);
  }

  if (contentType.includes('application/json')) {
    return await response.json();
  }
  return await response.text();
}

export const api = {
  // Vault Stats
  getStats: () => request('/stats'),

  // Projects
  listProjects: () => request('/projects'),
  getProject: (slug) => request(`/projects/${encodeURIComponent(slug)}`),
  createProject: (name, description = null) => 
    request('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    }),
  deleteProject: (slug) =>
    request(`/projects/${encodeURIComponent(slug)}`, {
      method: 'DELETE',
    }),

  // Experiments
  listExperiments: (projectSlug) => 
    request(`/projects/${encodeURIComponent(projectSlug)}/experiments`),
  getExperiment: (projectSlug, expSlug) => 
    request(`/projects/${encodeURIComponent(projectSlug)}/experiments/${encodeURIComponent(expSlug)}`),
  createExperiment: (projectSlug, name, description = null) =>
    request(`/projects/${encodeURIComponent(projectSlug)}/experiments`, {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    }),

  // Runs
  listRuns: (expId) => request(`/experiments/${expId}/runs`),
  getRun: (runId) => request(`/runs/${runId}`),
  createRun: (expId, { metrics = {}, tags = {}, notes = '' } = {}) =>
    request(`/experiments/${expId}/runs`, {
      method: 'POST',
      body: JSON.stringify({ metrics, tags, notes }),
    }),
  updateRun: (runId, { metrics, tags, notes }) =>
    request(`/runs/${runId}`, {
      method: 'PATCH',
      body: JSON.stringify({ metrics, tags, notes }),
    }),
  sealRun: (runId) =>
    request(`/runs/${runId}/seal`, {
      method: 'POST',
    }),

  // Artifacts
  uploadArtifact: (runId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request(`/runs/${runId}/artifacts`, {
      method: 'POST',
      body: formData,
    });
  },
  previewArtifact: (artifactId) => request(`/artifacts/${artifactId}/preview`),
  downloadArtifactUrl: (artifactId) => `${BASE_URL}/artifacts/${artifactId}/download`,

  // Search
  search: ({ q = '', tag = '', metric = '', after = '', before = '' } = {}) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (tag) params.set('tag', tag);
    if (metric) params.set('metric', metric);
    if (after) params.set('after', after);
    if (before) params.set('before', before);
    return request(`/search?${params.toString()}`);
  },

  // Comparison
  compareRuns: (runIds) =>
    request('/compare', {
      method: 'POST',
      body: JSON.stringify({ run_ids: runIds }),
    }),
  compareFiles: (runIds, filename) =>
    request('/compare/files', {
      method: 'POST',
      body: JSON.stringify({ run_ids: runIds, filename }),
    }),

  // Export
  exportTableUrl: (expId, format = 'csv') => 
    `${BASE_URL}/export/table?experiment_id=${expId}&format=${encodeURIComponent(format)}`,
  exportRunZipUrl: (runId) => `${BASE_URL}/export/run/${runId}`,
};
