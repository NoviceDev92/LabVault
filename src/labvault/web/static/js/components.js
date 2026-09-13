/**
 * Reusable UI Components & Helpers for LabVault
 */

export function formatBytes(bytes) {
  if (bytes === 0 || !bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function formatDate(dateString) {
  if (!dateString) return '—';
  try {
    const d = new Date(dateString);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch (_) {
    return dateString;
  }
}

export function setBreadcrumbs(crumbs = []) {
  const container = document.getElementById('nav-breadcrumbs');
  if (!container) return;

  container.innerHTML = '';
  crumbs.forEach((crumb, idx) => {
    if (idx > 0) {
      const sep = document.createElement('span');
      sep.className = 'breadcrumb-sep';
      sep.textContent = '/';
      container.appendChild(sep);
    }

    const item = document.createElement(crumb.href ? 'a' : 'span');
    item.className = `breadcrumb-item ${!crumb.href || idx === crumbs.length - 1 ? 'active' : ''}`;
    item.textContent = crumb.label;
    if (crumb.href) {
      item.href = crumb.href;
    }
    container.appendChild(item);
  });
}

export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

export function showModal({ title, body, footer = null }) {
  const container = document.getElementById('modal-container');
  if (!container) return;

  container.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-header">
        <h3 style="font-size: 16px;">${title}</h3>
        <button class="btn btn-ghost btn-sm" id="modal-close-x" style="font-size: 16px;">✕</button>
      </div>
      <div class="modal-body">
        ${typeof body === 'string' ? body : ''}
      </div>
      <div class="modal-footer" id="modal-footer-container">
        <!-- Buttons injected -->
      </div>
    </div>
  `;

  if (typeof body !== 'string' && body instanceof HTMLElement) {
    container.querySelector('.modal-body').appendChild(body);
  }

  const footerContainer = container.querySelector('#modal-footer-container');
  if (footer) {
    if (typeof footer === 'string') {
      footerContainer.innerHTML = footer;
    } else if (footer instanceof HTMLElement) {
      footerContainer.appendChild(footer);
    }
  } else {
    footerContainer.remove();
  }

  container.classList.add('open');

  const closeBtn = container.querySelector('#modal-close-x');
  if (closeBtn) {
    closeBtn.onclick = closeModal;
  }

  container.onclick = (e) => {
    if (e.target === container) {
      closeModal();
    }
  };
}

export function closeModal() {
  const container = document.getElementById('modal-container');
  if (container) {
    container.classList.remove('open');
    container.innerHTML = '';
  }
}

export function openInspectorDrawer(title, contentElement) {
  const drawer = document.getElementById('inspector-drawer');
  const backdrop = document.getElementById('drawer-backdrop');
  const titleEl = document.getElementById('drawer-title');
  const bodyEl = document.getElementById('drawer-body');
  const closeBtn = document.getElementById('drawer-close-btn');

  if (!drawer || !backdrop) return;

  titleEl.innerHTML = title;
  bodyEl.innerHTML = '';
  if (typeof contentElement === 'string') {
    bodyEl.innerHTML = contentElement;
  } else if (contentElement instanceof HTMLElement) {
    bodyEl.appendChild(contentElement);
  }

  drawer.classList.add('open');
  backdrop.classList.add('open');

  const close = () => {
    drawer.classList.remove('open');
    backdrop.classList.remove('open');
  };

  backdrop.onclick = close;
  if (closeBtn) closeBtn.onclick = close;
}

export function closeInspectorDrawer() {
  const drawer = document.getElementById('inspector-drawer');
  const backdrop = document.getElementById('drawer-backdrop');
  if (drawer) drawer.classList.remove('open');
  if (backdrop) backdrop.classList.remove('open');
}

export function updateFloatingDock(selectedRunIds, { onCompare, onExport, onClear }) {
  const dock = document.getElementById('floating-dock');
  const countEl = document.getElementById('dock-count');
  const compareBtn = document.getElementById('dock-compare-btn');
  const exportBtn = document.getElementById('dock-export-btn');
  const clearBtn = document.getElementById('dock-clear-btn');

  if (!dock) return;

  if (selectedRunIds.length > 0) {
    countEl.textContent = selectedRunIds.length;
    dock.classList.add('show');
  } else {
    dock.classList.remove('show');
  }

  if (compareBtn) {
    compareBtn.onclick = () => onCompare && onCompare(selectedRunIds);
  }
  if (exportBtn) {
    exportBtn.onclick = () => onExport && onExport(selectedRunIds);
  }
  if (clearBtn) {
    clearBtn.onclick = () => onClear && onClear();
  }
}

export function createDropzone(onFilesSelected, label = 'Drag & drop artifact files here, or click to browse') {
  const wrap = document.createElement('div');
  wrap.className = 'dropzone';
  wrap.innerHTML = `
    <div class="dropzone-icon">⭳</div>
    <div style="font-weight: 500; font-size: 13px; color: var(--text-primary); margin-bottom: 4px;">${label}</div>
    <div style="font-size: 11px; color: var(--text-muted);">Supports model weights, scripts, notebooks, CSVs, configs, figures</div>
    <input type="file" multiple style="display: none;" />
  `;

  const input = wrap.querySelector('input');
  wrap.onclick = () => input.click();

  input.onchange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFilesSelected(Array.from(e.target.files));
    }
  };

  wrap.ondragover = (e) => {
    e.preventDefault();
    wrap.classList.add('dragover');
  };

  wrap.ondragleave = () => {
    wrap.classList.remove('dragover');
  };

  wrap.ondrop = (e) => {
    e.preventDefault();
    wrap.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelected(Array.from(e.dataTransfer.files));
    }
  };

  return wrap;
}
