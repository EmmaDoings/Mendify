/* ============================================================
   Mendify - Main Application Logic
   Stack: Vanilla JavaScript (ES6+)
   ============================================================ */

'use strict';

/* ============================================================
   1. HELPERS
   ============================================================ */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function slugify(text) {
  return String(text || 'mendify-app')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40) || 'mendify-app';
}

function setLoading(btnEl, isLoading) {
  if (!btnEl) return;

  if (!btnEl.dataset.label) {
    btnEl.dataset.label = btnEl.innerHTML;
  }

  if (isLoading) {
    btnEl.disabled = true;
    btnEl.innerHTML = '<span class="spinner" aria-hidden="true"></span> Working...';
  } else {
    btnEl.disabled = false;
    btnEl.innerHTML = btnEl.dataset.label;
  }
}

function showToast(msg) {
  const toast = $('#toast');
  if (!toast) return;

  toast.textContent = msg;
  toast.classList.remove('hidden');

  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toast.classList.add('hidden');
  }, 2400);
}

const ICON_SVG = {
  terminal: '<polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line>',
  'log-out': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line>',
  blocks: '<rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><path d="M14 17h7"></path><path d="M17 14v7"></path>',
  bug: '<path d="M8 2l1.5 3h5L16 2"></path><rect x="7" y="5" width="10" height="14" rx="5"></rect><path d="M3 13h4"></path><path d="M17 13h4"></path><path d="M4 19l3-2"></path><path d="M20 19l-3-2"></path><path d="M4 7l3 2"></path><path d="M20 7l-3 2"></path>',
  'shield-check': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="M9 12l2 2 4-5"></path>',
  'messages-square': '<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path><path d="M8 8h8"></path><path d="M8 12h5"></path>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>',
  'search-check': '<circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.3-4.3"></path><path d="M8 11l2 2 4-5"></path>',
  plus: '<path d="M12 5v14"></path><path d="M5 12h14"></path>',
  send: '<path d="M22 2L11 13"></path><path d="M22 2l-7 20-4-9-9-4 20-7z"></path>',
  check: '<path d="M20 6L9 17l-5-5"></path>'
};

function refreshIcons(root = document) {
  $$('i[data-lucide]', root).forEach(icon => {
    const name = icon.dataset.lucide;
    const markup = ICON_SVG[name];
    if (!markup) return;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    svg.dataset.lucide = name;
    svg.innerHTML = markup;
    icon.replaceWith(svg);
  });
}

/* ============================================================
   Theme / Density
   ============================================================ */

function loadTheme() {
  const saved = window.localStorage.getItem('mendify:theme');
  return saved || 'dark';
}

function saveTheme(theme) {
  window.localStorage.setItem('mendify:theme', theme);
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  $$('.theme-option').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.themeOption === theme);
  });
}

function loadDensity() {
  const saved = window.localStorage.getItem('mendify:density');
  return saved || 'comfortable';
}

function saveDensity(density) {
  window.localStorage.setItem('mendify:density', density);
}

function applyDensity(density) {
  document.documentElement.setAttribute('data-density', density);
  $$('.density-option').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.densityOption === density);
  });
}

/* ============================================================
   API Health
   ============================================================ */

async function checkApiHealth() {
  const indicator = $('#statusIndicator');
  if (!indicator) return;

  try {
    const res = await fetch(`${getApiBase()}/api/v1/health/`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });
    const data = await res.json().catch(() => ({}));
    const healthy = data.status === 'healthy';
    indicator.textContent = healthy ? 'Online' : 'Degraded';
    indicator.dataset.status = healthy ? 'online' : 'degraded';
    indicator.dataset.healthy = healthy ? 'true' : 'false';
  } catch {
    indicator.textContent = 'Offline';
    indicator.dataset.status = 'offline';
    indicator.dataset.healthy = 'false';
  }
}

function switchPanel(panelId) {
  $$('.panel').forEach(panel => panel.classList.remove('active'));

  const target = $(`#${panelId}`);
  if (target) target.classList.add('active');

  const panelName = String(panelId || '').replace(/^panel-/, '');
  if (panelName) saveUiStatePatch({ activePanel: panelName });
}

function normaliseFiles(filesObj) {
  return Object.entries(filesObj || {}).map(([path, content]) => ({
    path,
    content: String(content ?? '')
  }));
}

function normaliseSeverity(value) {
  // Keep severities aligned with backend/bugs.py BugSchema:
  // allowed: low | medium | high | critical
  const severity = String(value || 'low').toLowerCase();
  if (severity === 'critical') return 'critical';
  if (severity === 'medium' || severity === 'med' || severity === 'warning') return 'medium';
  if (severity === 'high') return 'high';
  if (severity === 'low') return 'low';
  return 'low';
}


function renderFolderTree(treeStr, containerEl) {
  if (!containerEl) return;
  containerEl.textContent = String(treeStr ?? '');
}

function renderPreWithLineNumbers(text, containerEl) {
  if (!containerEl) return;

  const lines = String(text ?? '').split(/\r?\n/);
  const pre = document.createElement('pre');

  lines.forEach((line, index) => {
    const span = document.createElement('span');
    span.className = 'line';
    span.dataset.line = String(index + 1);
    span.textContent = line || ' ';
    pre.appendChild(span);
  });

  containerEl.textContent = '';
  containerEl.appendChild(pre);
}

function renderAiStatus(outputEl, payload = {}) {
  const header = outputEl?.querySelector('.output-header');
  if (!header) return;

  let status = header.querySelector('.ai-status');
  if (!status) {
    status = document.createElement('span');
    try {
      header.insertAdjacentElement('afterbegin', status);
    } catch (e) {
      header.appendChild(status);
    }
  }

  const aiGenerated = Boolean(payload.ai_generated);
  status.className = `ai-status ${aiGenerated ? 'ai' : 'local'}`;
  status.textContent = aiGenerated ? 'AI' : 'Local';
  status.title = aiGenerated
    ? 'Generated by the configured AI provider.'
    : (payload.ai_error || 'Local fallback output.');
}

function buildCopyAll(files) {
  return files
    .map(file => `// ===================== ${file.path} =====================\n${file.content}`)
    .join('\n\n');
}

function copyTextFallback(text, label) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
    showToast('Copied to clipboard.');
  } catch {
    window.prompt(label || 'Copy:', text);
  }
  document.body.removeChild(ta);
}

function getApiBase() {
  if (window.MENDIFY_API_URL !== undefined) return window.MENDIFY_API_URL || '';
  return 'http://localhost:5000';
}

function getAccessToken() {
  return window.localStorage.getItem('access_token') || '';
}

function getRefreshToken() {
  return window.localStorage.getItem('refresh_token') || '';
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return '';

  const res = await fetch(`${getApiBase()}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${refreshToken}`
    }
  });

  if (!res.ok) return '';

  const payload = await res.json().catch(() => ({}));
  if (!payload.access_token) return '';

  window.localStorage.setItem('access_token', payload.access_token);
  return payload.access_token;
}

async function apiRequest(path, { method = 'GET', body, token, signal } = {}) {
  let authToken = token || getAccessToken();

  const makeRequest = currentToken => fetch(`${getApiBase()}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined,
    signal
  });

  let res = await makeRequest(authToken);

  if (res.status === 401 && authToken && !path.includes('/api/v1/auth/refresh')) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      authToken = refreshedToken;
      res = await makeRequest(authToken);
    }
  }

  const contentType = res.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await res.json().catch(() => ({}))
    : {};

  if (!res.ok) {
    const msg = payload?.error || payload?.message || `Request failed (${res.status})`;
    throw new Error(msg);
  }

  return payload;
}

const CONTROL_STATE_IDS = [
  'appIdea',
  'stackSelect',
  'backendSelect',
  'debugLang',
  'buggyCode',
  'auditLang',
  'auditCode',
  'chatInput'
];
const MAX_CHAT_SESSIONS = 20;
const MAX_CHAT_MESSAGES = 120;
const COMPILE_REQUEST_TIMEOUT_MS = 120000;

let uiState = {};
let chatSessions = [];
let activeChatId = '';
let isRestoringState = false;

function userStoragePrefix() {
  try {
    const user = JSON.parse(window.localStorage.getItem('user') || '{}');
    return String(user.id || user.email || user.username || 'local').replace(/[^a-z0-9@._-]/gi, '_');
  } catch {
    return 'local';
  }
}

function stateKey(name) {
  return `mendify:${userStoragePrefix()}:${name}:v1`;
}

function readState(name, fallback) {
  try {
    const raw = window.localStorage.getItem(stateKey(name));
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeState(name, value) {
  try {
    window.localStorage.setItem(stateKey(name), JSON.stringify(value));
  } catch (error) {
    console.warn(`Could not save ${name}:`, error);
  }
}

function loadSavedState() {
  uiState = readState('ui', {});
  chatSessions = readState('chat-history', []);
  activeChatId = readState('active-chat', '') || uiState.activeChatId || '';

  if (!Array.isArray(chatSessions)) chatSessions = [];
  chatSessions = chatSessions
    .filter(session => session && session.id)
    .slice(0, MAX_CHAT_SESSIONS);
}

function saveUiStatePatch(patch) {
  if (isRestoringState) return;
  uiState = {
    ...uiState,
    ...patch,
    updatedAt: new Date().toISOString()
  };
  writeState('ui', uiState);
}

function collectControlState() {
  return CONTROL_STATE_IDS.reduce((memo, id) => {
    const el = $(`#${id}`);
    if (el) memo[id] = el.value;
    return memo;
  }, {});
}

function saveCurrentControls() {
  saveUiStatePatch({ controls: collectControlState() });
}

function makeId(prefix) {
  const random = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${Date.now()}-${random}`;
}

function summarizeChatTitle(text) {
  const title = String(text || 'New chat').replace(/\s+/g, ' ').trim();
  return title.length > 46 ? `${title.slice(0, 43)}...` : title || 'New chat';
}

function saveChatState() {
  chatSessions = chatSessions
    .slice()
    .sort((a, b) => new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0))
    .slice(0, MAX_CHAT_SESSIONS);

  writeState('chat-history', chatSessions);
  writeState('active-chat', activeChatId);
  saveUiStatePatch({ activeChatId });
}

function createChatSession(seedMessage = '') {
  const now = new Date().toISOString();
  const session = {
    id: makeId('chat'),
    title: seedMessage ? summarizeChatTitle(seedMessage) : 'New chat',
    createdAt: now,
    updatedAt: now,
    messages: []
  };

  chatSessions = [session, ...chatSessions].slice(0, MAX_CHAT_SESSIONS);
  activeChatId = session.id;
  saveChatState();
  return session;
}

function getActiveChatSession({ create = false } = {}) {
  let session = chatSessions.find(item => item.id === activeChatId);

  if (!session && chatSessions.length) {
    session = chatSessions[0];
    activeChatId = session.id;
  }

  if (!session && create) {
    session = createChatSession();
  }

  return session || null;
}

function addMessageToActiveSession(type, text) {
  const session = getActiveChatSession({ create: true });
  if (!session) return;

  const now = new Date().toISOString();
  session.messages = Array.isArray(session.messages) ? session.messages : [];
  session.messages.push({
    id: makeId('msg'),
    type,
    text: String(text ?? ''),
    createdAt: now
  });

  if (type === 'user' && (!session.title || session.title === 'New chat')) {
    session.title = summarizeChatTitle(text);
  }

  if (session.messages.length > MAX_CHAT_MESSAGES) {
    session.messages = session.messages.slice(-MAX_CHAT_MESSAGES);
  }

  session.updatedAt = now;
  saveChatState();
  renderChatHistoryList();
}

function appendWelcomeMessage() {
  const container = $('#chatMessages');
  if (!container) return;

  const msg = document.createElement('div');
  msg.className = 'chat-msg ai';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = 'AI';

  const content = document.createElement('div');
  content.className = 'msg-content';
  content.textContent = [
    'Agent ready.',
    'Scope: files, search, edits, and project reasoning.'
  ].join('\n');

  msg.append(avatar, content);
  container.appendChild(msg);
}

function renderChatMessagesFromHistory() {
  const container = $('#chatMessages');
  if (!container) return;

  container.textContent = '';
  const session = getActiveChatSession();

  if (!session || !Array.isArray(session.messages) || session.messages.length === 0) {
    appendWelcomeMessage();
    return;
  }

  session.messages.forEach(message => {
    addChatMessage(message.text, message.type, { persist: false });
  });
}

function formatHistoryTime(value) {
  if (!value) return '';
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(new Date(value));
  } catch {
    return '';
  }
}

function renderChatHistoryList() {
  const list = $('#chatHistoryList');
  if (!list) return;

  list.textContent = '';

  if (chatSessions.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'history-empty';
    empty.textContent = 'Your conversations will appear here.';
    list.appendChild(empty);
    return;
  }

  chatSessions.forEach(session => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `history-item${session.id === activeChatId ? ' active' : ''}`;

    const title = document.createElement('span');
    title.className = 'history-title';
    title.textContent = session.title || 'New chat';

    const meta = document.createElement('span');
    meta.className = 'history-meta';
    const count = Array.isArray(session.messages) ? session.messages.length : 0;
    meta.textContent = `${count} message${count === 1 ? '' : 's'} · ${formatHistoryTime(session.updatedAt)}`;

    btn.append(title, meta);
    btn.addEventListener('click', () => {
      activeChatId = session.id;
      saveChatState();
      renderChatHistoryList();
      renderChatMessagesFromHistory();
    });

    list.appendChild(btn);
  });
}

function restoreUiState() {
  isRestoringState = true;

  Object.entries(uiState.controls || {}).forEach(([id, value]) => {
    const el = $(`#${id}`);
    if (el && typeof value === 'string') el.value = value;
  });

  if (uiState.lastCompiledProject) {
    renderCompiledProject(uiState.lastCompiledProject, {
      selectedPath: uiState.selectedCompiledFile,
      persist: false
    });
  }

  if (uiState.debugResult) {
    renderDebugResults(uiState.debugResult, { persist: false });
  }

  if (uiState.auditResult) {
    renderAuditResults(uiState.auditResult, { persist: false });
  }

  if (Array.isArray(uiState.pendingEdits) && uiState.pendingEdits.length) {
    pendingEdits = uiState.pendingEdits;
    const editText = pendingEdits
      .map((edit, index) => `${index + 1}. ${edit.file}\n- ${edit.search}\n+ ${edit.replace}`)
      .join('\n\n');

    $('#chatEditPreview')?.classList.remove('hidden');
    const editContent = $('#chatEditContent');
    if (editContent) editContent.textContent = editText;
  }

  const panel = uiState.activePanel || 'compiler';
  const navBtn = $$('.nav-btn').find(btn => btn.dataset.panel === panel);
  $$('.nav-btn').forEach(btn => btn.classList.remove('active'));
  navBtn?.classList.add('active');
  switchPanel(`panel-${panel}`);

  isRestoringState = false;

  window.setTimeout(() => {
    if (Number.isFinite(uiState.scrollY)) {
      window.scrollTo({ top: uiState.scrollY, behavior: 'auto' });
    }
  }, 0);
}

function wireStatePersistence() {
  CONTROL_STATE_IDS.forEach(id => {
    const el = $(`#${id}`);
    if (!el) return;

    const eventName = el.tagName === 'SELECT' ? 'change' : 'input';
    el.addEventListener(eventName, saveCurrentControls);
  });

  let scrollTimer = 0;
  window.addEventListener('scroll', () => {
    window.clearTimeout(scrollTimer);
    scrollTimer = window.setTimeout(() => {
      saveUiStatePatch({ scrollY: window.scrollY });
    }, 180);
  }, { passive: true });

  window.addEventListener('beforeunload', saveCurrentControls);
}

// Visibility is restored by checkAuth() after token verification.
// auth-gate.js hides the page on load to prevent FOUC.

/* ============================================================
   3. PROJECT COMPILER
   ============================================================ */

let currentCompiledFiles = [];
let currentProjectId = null;

// ── Projects CRUD ──

async function saveCurrentProject({ silent } = {}) {
  const idea = ($('#appIdea')?.value || '').trim();
  if (!idea) { if (!silent) showToast('Compile a project first.'); return; }
  const token = window.localStorage.getItem('access_token');
  if (!token) { if (!silent) showToast('Please log in to save projects.'); return; }

  try {
    const body = {
      name: idea.slice(0, 200),
      description: idea,
      language: $('#stackSelect')?.value || 'vanilla',
      framework: $('#backendSelect')?.value || 'flask'
    };
    const res = await apiRequest('/api/v1/projects/', {
      method: 'POST', token, body
    });
    currentProjectId = res.project?.id;
    if (!silent) showToast('Project saved.');
    loadSavedProjects();
  } catch (e) {
    if (!silent) showToast(e.message || 'Failed to save project.');
  }
}

async function loadSavedProjects() {
  const token = window.localStorage.getItem('access_token');
  const list = $('#savedProjectsList');
  if (!list) return;
  if (!token) { list.innerHTML = '<span class="saved-projects-empty">Log in to save projects</span>'; return; }

  try {
    const res = await apiRequest('/api/v1/projects/', { token });
    const projects = res.projects || [];
    if (projects.length === 0) {
      list.innerHTML = '<span class="saved-projects-empty">No saved projects</span>';
      return;
    }
    list.innerHTML = '';
    projects.forEach(p => {
      const item = document.createElement('button');
      item.className = 'saved-project-item';
      item.innerHTML = `
        <div>
          <div class="saved-project-name">${escapeHtml(p.name)}</div>
          <div class="saved-project-meta">${p.language} · ${new Date(p.created_at).toLocaleDateString()}</div>
        </div>
        <div class="saved-project-actions">
          <button data-load="${p.id}" title="Load into compiler">&#9654;</button>
          <button data-delete="${p.id}" title="Delete">&#10005;</button>
        </div>`;
      item.querySelector('[data-load]')?.addEventListener('click', (e) => {
        e.stopPropagation();
        // Load project by populating the compile form
        $('#appIdea').value = p.description || p.name;
        if (p.framework === 'flask') $('#backendSelect').value = 'flask';
        if (p.framework === 'express') $('#backendSelect').value = 'express';
        if (p.framework === 'go') $('#backendSelect').value = 'go';
        if (p.language === 'react') $('#stackSelect').value = 'react';
        if (p.language === 'vanilla') $('#stackSelect').value = 'vanilla';
        currentProjectId = p.id;
        showToast('Project loaded. Click Compile to regenerate.');
        switchPanel('compiler');
      });
      item.querySelector('[data-delete]')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        try {
          await apiRequest(`/api/v1/projects/${p.id}`, { method: 'DELETE', token });
          showToast('Project deleted.');
          loadSavedProjects();
        } catch (err) {
          showToast(err.message || 'Delete failed.');
        }
      });
      list.appendChild(item);
    });
  } catch {
    list.innerHTML = '<span class="saved-projects-empty">Failed to load</span>';
  }
}

async function saveBugsFromAnalysis(projectId, results) {
  const token = window.localStorage.getItem('access_token');
  if (!token || !projectId || !results?.length) return;
  for (const result of results) {
    for (const bug of (result.bugs || [])) {
      try {
        await apiRequest(`/api/v1/bugs/project/${projectId}`, {
          method: 'POST', token,
          body: {
            title: bug.title || 'Unknown issue',
            description: bug.description || '',
            severity: normaliseSeverity(bug.severity || 'medium'),

            file_path: result.path || '',
            line_number: bug.line || null,
            fix_snippet: bug.fix || ''
          }
        });
      } catch { /* best-effort */ }
    }
  }
  if (results.some(r => r.bugs?.length)) showToast('Bugs saved to project.');
}

function buildLocalBackendFiles(backend) {
  if (backend === 'flask') {
    return {
      'backend/app.py': `from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

items = [
    {"id": 1, "text": "Plan the first release", "done": False},
    {"id": 2, "text": "Invite an early tester", "done": False},
]


def next_id():
    return max((item["id"] for item in items), default=0) + 1


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok"})


@app.get("/api/items")
def list_items():
    return jsonify({"items": items})


@app.post("/api/items")
def create_item():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()

    if not text:
        return jsonify({"error": "Text is required"}), 400

    item = {"id": next_id(), "text": text, "done": False}
    items.append(item)
    return jsonify(item), 201


@app.patch("/api/items/<int:item_id>")
def update_item(item_id):
    data = request.get_json(silent=True) or {}

    for item in items:
        if item["id"] == item_id:
            if "text" in data:
                item["text"] = str(data["text"]).strip()
            if "done" in data:
                item["done"] = bool(data["done"])
            return jsonify(item)

    return jsonify({"error": "Item not found"}), 404


@app.delete("/api/items/<int:item_id>")
def delete_item(item_id):
    for index, item in enumerate(items):
        if item["id"] == item_id:
            deleted = items.pop(index)
            return jsonify(deleted)

    return jsonify({"error": "Item not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
`,
      'backend/requirements.txt': `Flask==3.0.0
flask-cors==4.0.0
`
    };
  }

  return {};
}

function fullStarterCss(appSelector = '#app') {
  return `*,
*::before,
*::after {
  box-sizing: border-box;
}

:root {
  color-scheme: dark;
  --bg: #10131a;
  --panel: #171c26;
  --panel-strong: #202837;
  --text: #eef2ff;
  --muted: #9aa7bd;
  --accent: #8dd3c7;
  --border: #2b3548;
  --danger: #ff7b8a;
}

body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: radial-gradient(circle at top left, rgba(141, 211, 199, 0.13), transparent 34%), var(--bg);
  color: var(--text);
  line-height: 1.6;
}

button,
input {
  font: inherit;
}

button {
  border: 0;
  cursor: pointer;
}

${appSelector} {
  width: min(1040px, calc(100% - 32px));
  margin: 0 auto;
  padding: 48px 0;
}

.hero {
  padding: 32px 0 28px;
  border-bottom: 1px solid var(--border);
}

.eyebrow,
.section-kicker {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  max-width: 780px;
  margin-bottom: 14px;
  font-size: clamp(2.2rem, 7vw, 4.8rem);
  line-height: 1;
}

.hero-copy {
  max-width: 680px;
  margin-bottom: 0;
  color: var(--muted);
}

.workspace {
  display: grid;
  grid-template-columns: minmax(260px, 0.85fr) minmax(0, 1.4fr);
  gap: 20px;
  padding-top: 28px;
}

.panel {
  border: 1px solid var(--border);
  border-radius: 16px;
  background: rgba(23, 28, 38, 0.86);
  padding: 22px;
}

.composer {
  display: grid;
  gap: 10px;
}

label {
  color: var(--muted);
  font-size: 0.9rem;
}

.input-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

input {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  background: #111722;
  color: var(--text);
  outline: none;
}

input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(141, 211, 199, 0.18);
}

.composer button,
.filter-btn.active {
  border-radius: 12px;
  padding: 12px 16px;
  background: var(--accent);
  color: #0e141d;
  font-weight: 800;
}

.list-header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

.stats {
  margin: 0;
  color: var(--muted);
  font-size: 0.9rem;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 14px 0 18px;
}

.filter-btn,
.ghost-btn {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 12px;
  background: transparent;
  color: var(--text);
}

.empty {
  margin: 24px 0;
  color: var(--muted);
}

.item-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px;
  background: var(--panel-strong);
}

.item input[type="checkbox"] {
  width: 18px;
  height: 18px;
}

.item.done .item-text {
  color: var(--muted);
  text-decoration: line-through;
}

.delete-btn {
  border-radius: 10px;
  padding: 8px 10px;
  background: rgba(255, 123, 138, 0.12);
  color: var(--danger);
}

.ghost-btn {
  margin-top: 18px;
}

@media (max-width: 760px) {
  ${appSelector} {
    width: min(100% - 24px, 1040px);
    padding-top: 24px;
  }

  .workspace,
  .input-row {
    grid-template-columns: 1fr;
  }

  .list-header {
    display: block;
  }
}
`;
}

function generateFullLocalProject({ idea, frontend, backend }) {
  const projectName = slugify(idea);
  const cleanIdea = idea || 'Mendify app';
  const escapedIdea = escapeHtml(cleanIdea);
  const backendLabel = backend && backend !== 'none' ? ` and ${backend} backend` : '';
  const backendFiles = buildLocalBackendFiles(backend);
  const backendTree = backend === 'flask'
    ? `|-- backend/
|   |-- app.py
|   \`-- requirements.txt`
    : '';
  const readmeBranch = backendTree ? '|-- README.md' : '`-- README.md';

  if (frontend === 'react') {
    const files = {
      'public/index.html': `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapedIdea}</title>
</head>
<body>
  <div id="root"></div>
</body>
</html>`,
      'src/App.jsx': `import { useEffect, useMemo, useState } from 'react';
import './App.css';

const appIdea = ${JSON.stringify(cleanIdea)};
const storageKey = 'mendify:' + appIdea.toLowerCase().replace(/[^a-z0-9]+/g, '-');

const starterItems = [
  { id: crypto.randomUUID(), text: 'Customize this starter app', done: false },
  { id: crypto.randomUUID(), text: 'Connect the backend API when ready', done: false }
];

function loadItems() {
  try {
    const saved = window.localStorage.getItem(storageKey);
    return saved ? JSON.parse(saved) : starterItems;
  } catch {
    return starterItems;
  }
}

export default function App() {
  const [draft, setDraft] = useState('');
  const [filter, setFilter] = useState('all');
  const [items, setItems] = useState(loadItems);

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(items));
  }, [items]);

  const visibleItems = useMemo(() => {
    if (filter === 'active') return items.filter(item => !item.done);
    if (filter === 'done') return items.filter(item => item.done);
    return items;
  }, [filter, items]);

  const activeCount = items.filter(item => !item.done).length;
  const doneCount = items.length - activeCount;

  function addItem(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;

    setItems(current => [
      { id: crypto.randomUUID(), text, done: false },
      ...current
    ]);
    setDraft('');
  }

  function toggleItem(id) {
    setItems(current =>
      current.map(item => item.id === id ? { ...item, done: !item.done } : item)
    );
  }

  function deleteItem(id) {
    setItems(current => current.filter(item => item.id !== id));
  }

  function clearCompleted() {
    setItems(current => current.filter(item => !item.done));
  }

  return (
    <div className="app">
      <header className="hero">
        <p className="eyebrow">Generated by Mendify</p>
        <h1>{appIdea}</h1>
        <p>A complete React starter with persistent state, filters, and accessible controls.</p>
      </header>

      <main className="workspace">
        <section className="panel composer-panel" aria-labelledby="composerTitle">
          <p className="section-kicker">Create</p>
          <h2 id="composerTitle">Add a new item</h2>

          <form className="composer" onSubmit={addItem}>
            <label htmlFor="itemInput">Item text</label>
            <div className="input-row">
              <input
                id="itemInput"
                value={draft}
                onChange={event => setDraft(event.target.value)}
                placeholder="Write something to track"
              />
              <button type="submit">Add</button>
            </div>
          </form>
        </section>

        <section className="panel list-panel" aria-labelledby="listTitle">
          <div className="list-header">
            <div>
              <p className="section-kicker">Dashboard</p>
              <h2 id="listTitle">Items</h2>
            </div>
            <p className="stats">{activeCount} active / {doneCount} complete</p>
          </div>

          <div className="filters" role="group" aria-label="Filter items">
            {['all', 'active', 'done'].map(option => (
              <button
                key={option}
                className={'filter-btn ' + (filter === option ? 'active' : '')}
                type="button"
                onClick={() => setFilter(option)}
              >
                {option[0].toUpperCase() + option.slice(1)}
              </button>
            ))}
          </div>

          {visibleItems.length === 0 ? (
            <p className="empty">No items match this filter.</p>
          ) : (
            <ul className="item-list">
              {visibleItems.map(item => (
                <li className={'item ' + (item.done ? 'done' : '')} key={item.id}>
                  <input
                    type="checkbox"
                    checked={item.done}
                    onChange={() => toggleItem(item.id)}
                    aria-label={'Mark "' + item.text + '" complete'}
                  />
                  <span className="item-text">{item.text}</span>
                  <button className="delete-btn" type="button" onClick={() => deleteItem(item.id)}>
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}

          <button className="ghost-btn" type="button" onClick={clearCompleted}>
            Clear completed
          </button>
        </section>
      </main>
    </div>
  );
}
`,
      'src/index.jsx': `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
`,
      'src/App.css': fullStarterCss('.app'),
      'package.json': JSON.stringify({
        name: projectName,
        version: '1.0.0',
        private: true,
        dependencies: {
          '@vitejs/plugin-react': '^5.0.0',
          vite: '^7.0.0',
          react: '^18.2.0',
          'react-dom': '^18.2.0'
        },
        devDependencies: {},
        scripts: {
          dev: 'vite',
          build: 'vite build',
          preview: 'vite preview'
        }
      }, null, 2),
      'README.md': `# ${projectName}

${cleanIdea}

Generated by Mendify with React frontend${backendLabel}.

## Features

- Vite + React app structure
- Persistent browser state with localStorage
- Create, complete, delete, filter, and clear items
- Responsive CSS and accessible controls
- Optional backend files when a backend stack is selected

## Run

\`\`\`bash
npm install
npm run dev
\`\`\`
`,
      ...backendFiles
    };

    return {
      tree: `${projectName}/
|-- public/
|   \`-- index.html
|-- src/
|   |-- App.jsx
|   |-- App.css
|   \`-- index.jsx
|-- package.json
${readmeBranch}${backendTree ? `
${backendTree}` : ''}`,
      files
    };
  }

  const files = {
    'index.html': `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapedIdea}</title>
  <link rel="stylesheet" href="css/style.css" />
</head>
<body>
  <div id="app">
    <header class="hero">
      <p class="eyebrow">Generated by Mendify</p>
      <h1>${escapedIdea}</h1>
      <p class="hero-copy">A complete browser app starter with persistent state, filters, and clean UI structure.</p>
    </header>

    <main class="workspace">
      <section class="panel composer-panel" aria-labelledby="composerTitle">
        <div>
          <p class="section-kicker">Create</p>
          <h2 id="composerTitle">Add a new item</h2>
        </div>

        <form id="itemForm" class="composer">
          <label for="itemInput">Item text</label>
          <div class="input-row">
            <input id="itemInput" type="text" placeholder="Write something to track" autocomplete="off" />
            <button type="submit">Add</button>
          </div>
        </form>
      </section>

      <section class="panel list-panel" aria-labelledby="listTitle">
        <div class="list-header">
          <div>
            <p class="section-kicker">Dashboard</p>
            <h2 id="listTitle">Items</h2>
          </div>
          <p id="stats" class="stats">0 active / 0 complete</p>
        </div>

        <div class="filters" role="group" aria-label="Filter items">
          <button class="filter-btn active" type="button" data-filter="all">All</button>
          <button class="filter-btn" type="button" data-filter="active">Active</button>
          <button class="filter-btn" type="button" data-filter="done">Done</button>
        </div>

        <p id="emptyState" class="empty">No items yet. Add your first one above.</p>
        <ul id="itemList" class="item-list"></ul>

        <button id="clearDoneBtn" class="ghost-btn" type="button">Clear completed</button>
      </section>
    </main>
  </div>

  <script src="js/app.js"></script>
</body>
</html>`,
    'css/style.css': fullStarterCss('#app'),
    'js/app.js': `'use strict';

const appIdea = ${JSON.stringify(cleanIdea)};
const storageKey = 'mendify:' + appIdea.toLowerCase().replace(/[^a-z0-9]+/g, '-');

const state = {
  filter: 'all',
  items: loadItems()
};

function loadItems() {
  try {
    const saved = window.localStorage.getItem(storageKey);
    if (saved) return JSON.parse(saved);
  } catch (error) {
    console.warn('Could not read saved items:', error);
  }

  return [
    { id: crypto.randomUUID(), text: 'Customize this starter app', done: false },
    { id: crypto.randomUUID(), text: 'Connect the backend API when ready', done: false }
  ];
}

function saveItems() {
  window.localStorage.setItem(storageKey, JSON.stringify(state.items));
}

function visibleItems() {
  if (state.filter === 'active') return state.items.filter(item => !item.done);
  if (state.filter === 'done') return state.items.filter(item => item.done);
  return state.items;
}

function renderStats() {
  const active = state.items.filter(item => !item.done).length;
  const done = state.items.length - active;
  document.querySelector('#stats').textContent = active + ' active / ' + done + ' complete';
}

function renderItems() {
  const list = document.querySelector('#itemList');
  const emptyState = document.querySelector('#emptyState');
  const items = visibleItems();

  list.textContent = '';
  emptyState.hidden = items.length > 0;

  items.forEach(item => {
    const li = document.createElement('li');
    li.className = 'item' + (item.done ? ' done' : '');

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = item.done;
    checkbox.setAttribute('aria-label', 'Mark "' + item.text + '" complete');
    checkbox.addEventListener('change', () => toggleItem(item.id));

    const text = document.createElement('span');
    text.className = 'item-text';
    text.textContent = item.text;

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'delete-btn';
    deleteButton.textContent = 'Delete';
    deleteButton.addEventListener('click', () => deleteItem(item.id));

    li.append(checkbox, text, deleteButton);
    list.appendChild(li);
  });

  renderStats();
}

function addItem(text) {
  state.items.unshift({
    id: crypto.randomUUID(),
    text,
    done: false
  });
  saveItems();
  renderItems();
}

function toggleItem(id) {
  state.items = state.items.map(item =>
    item.id === id ? { ...item, done: !item.done } : item
  );
  saveItems();
  renderItems();
}

function deleteItem(id) {
  state.items = state.items.filter(item => item.id !== id);
  saveItems();
  renderItems();
}

function clearCompleted() {
  state.items = state.items.filter(item => !item.done);
  saveItems();
  renderItems();
}

function setFilter(filter) {
  state.filter = filter;
  document.querySelectorAll('.filter-btn').forEach(button => {
    button.classList.toggle('active', button.dataset.filter === filter);
  });
  renderItems();
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('#itemForm').addEventListener('submit', event => {
    event.preventDefault();
    const input = document.querySelector('#itemInput');
    const text = input.value.trim();
    if (!text) return;

    addItem(text);
    input.value = '';
    input.focus();
  });

  document.querySelectorAll('.filter-btn').forEach(button => {
    button.addEventListener('click', () => setFilter(button.dataset.filter));
  });

  document.querySelector('#clearDoneBtn').addEventListener('click', clearCompleted);

  renderItems();
});
`,
    'README.md': `# ${projectName}

${cleanIdea}

Generated by Mendify with vanilla frontend${backendLabel}.

## Features

- Responsive HTML, CSS, and JavaScript app shell
- Create, complete, delete, filter, and clear items
- Persistent browser state with localStorage
- Accessible labels and keyboard-friendly controls
- Optional backend files when a backend stack is selected

## Run

Open \`index.html\` in your browser.
`,
    ...backendFiles
  };

  return {
    tree: `${projectName}/
|-- index.html
|-- css/
|   \`-- style.css
|-- js/
|   \`-- app.js
${readmeBranch}${backendTree ? `
${backendTree}` : ''}`,
    files
  };
}

function renderCompiledProject(projectLike, { selectedPath, persist = true } = {}) {
  const compilerOut = $('#compilerOutput');
  if (compilerOut) compilerOut.classList.remove('hidden');
  renderAiStatus(compilerOut, projectLike);

  const treeContainer = $('#folderTree');
  const tabsContainer = $('#fileTabs');
  const contentContainer = $('#fileContentArea');

  if (!tabsContainer || !contentContainer) return;

  const treeStr = projectLike?.tree ?? '';
  const files = normaliseFiles(projectLike?.files ?? {});
  currentCompiledFiles = files;
  const initialPath = files.some(file => file.path === selectedPath)
    ? selectedPath
    : files[0]?.path;

  renderFolderTree(treeStr, treeContainer);

  tabsContainer.textContent = '';
  contentContainer.textContent = '';

  function renderFileContent(path) {
    const file = files.find(item => item.path === path);
    if (!file) return;
    renderPreWithLineNumbers(file.content, contentContainer);
  }

  files.forEach((file, index) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `file-tab${file.path === initialPath ? ' active' : ''}`;
    btn.textContent = file.path;
    btn.dataset.path = file.path;

    btn.addEventListener('click', () => {
      $$('.file-tab', tabsContainer).forEach(tab => tab.classList.remove('active'));
      btn.classList.add('active');
      renderFileContent(file.path);
      saveUiStatePatch({ selectedCompiledFile: file.path });
    });

    tabsContainer.appendChild(btn);
  });

  if (initialPath) renderFileContent(initialPath);
  wireCompilerQuickActions();
  refreshIcons();

  if (persist) {
    saveUiStatePatch({
      lastCompiledProject: projectLike,
      selectedCompiledFile: initialPath || ''
    });
  }
}

/* ============================================================
   5. AUTO DEBUGGER
   ============================================================ */

function debugLocal(code, lang) {
  const lines = String(code ?? '').split(/\r?\n/);
  const issues = [];
  const language = lang || 'javascript';

  lines.forEach((line, index) => {
    if (!line.trim()) return;

    const lineNum = index + 1;

    if (language === 'python') {
      if (/^print\s+[^()]/.test(line.trim())) {
        issues.push({
          severity: 'low',
          title: 'Python 2 style print',
          description: `Line ${lineNum}: In Python 3, print requires parentheses.`
        });
      }

      if (/\binput\s*\(/.test(line) && !/\.strip\(\)/.test(line)) {
        issues.push({
          severity: 'low',
          title: 'Input should be cleaned',
          description: `Line ${lineNum}: Consider using .strip() on input values.`
        });
      }
    }

    if (language === 'javascript' || language === 'html') {
      if (/\beval\s*\(/.test(line)) {
        issues.push({
          severity: 'high',
          title: 'Use of eval()',
          description: `Line ${lineNum}: eval() can execute unsafe code.`
        });
      }

      if (/\bvar\s+/.test(line)) {
        issues.push({
          severity: 'low',
          title: 'Use of var',
          description: `Line ${lineNum}: Prefer let or const.`
        });
      }

      if (/document\.write\s*\(/.test(line)) {
        issues.push({
          severity: 'high',
          title: 'Use of document.write()',
          description: `Line ${lineNum}: Prefer DOM methods like textContent or appendChild.`
        });
      }

      if (/(?<!=)==(?!=)/.test(line) || /(?<!!)!=(?!=)/.test(line)) {
        issues.push({
          severity: 'medium',
          title: 'Loose equality',
          description: `Line ${lineNum}: Prefer === or !==.`
        });
      }
    }

    if (/password|secret|api_key|token\s*=\s*['"][^'"]+['"]/i.test(line) && !/process\.env|import\.meta\.env|config/i.test(line)) {
      issues.push({
        severity: 'high',
        title: 'Hardcoded secret detected',
        description: `Line ${lineNum}: Move secrets into environment variables.`
      });
    }

    if (line.length > 120) {
      issues.push({
        severity: 'low',
        title: 'Line too long',
        description: `Line ${lineNum}: Consider breaking this line up.`
      });
    }
  });

  if (issues.length === 0 && String(code).trim()) {
    issues.push({
      severity: 'low',
      title: 'No critical issues detected',
      description: `Basic ${language} checks passed.`
    });
  }

  let fixed = String(code ?? '');

  if (language === 'python') {
    fixed = fixed.replace(/^print\s+(.+)$/gm, 'print($1)');
  }

  if (language === 'javascript' || language === 'html') {
    fixed = fixed
      .replace(/\bvar\b/g, 'let')
      .replace(/(?<!=)==(?!=)/g, '===')
      .replace(/(?<!!)!=(?!=)/g, '!==')
      .replace(/\beval\s*\(/g, '/* eval removed */ (')
      .replace(/document\.write\s*\(/g, '/* document.write removed */ ');
  }

  return {
    lang: language,
    issues,
    fixed,
    ai_generated: false,
    ai_error: 'Local fallback output'
  };
}

function renderDebugResults({ issues, fixed, ai_generated, ai_error }, { persist = true } = {}) {
  const debugOut = $('#debugOutput');
  if (debugOut) debugOut.classList.remove('hidden');
  renderAiStatus(debugOut, { ai_generated, ai_error });

  const bugList = $('#bugList');
  const fixedArea = $('#fixedCodeArea');

  if (bugList) {
    bugList.textContent = '';

    issues.forEach(issue => {
      const severity = normaliseSeverity(issue.severity);
      const item = document.createElement('div');
      item.className = 'bug-item';

      const badge = document.createElement('span');
      badge.className = `badge ${severity}`;
      badge.textContent = severity;

      const info = document.createElement('div');
      info.className = 'bug-info';

      const title = document.createElement('div');
      title.className = 'bug-title';
      title.textContent = issue.title;

      const desc = document.createElement('div');
      desc.className = 'bug-desc';
      desc.textContent = issue.description;

      info.append(title, desc);
      item.append(badge, info);
      bugList.appendChild(item);
    });
  }

  renderPreWithLineNumbers(fixed, fixedArea);

  if (persist) {
    saveUiStatePatch({ debugResult: { issues, fixed, ai_generated, ai_error } });
  }
}

/* ============================================================
   6. SECURITY AUDIT
   ============================================================ */

function scoreFromIssues(items) {
  const weight = { high: 30, medium: 18, low: 6 };
  const sum = items.reduce((acc, item) => acc + (weight[item.severity] || 0), 0);
  return Math.max(0, Math.min(100, 100 - Math.round(sum / 1.2)));
}

function auditLocal(code, lang) {
  const text = String(code ?? '');
  const language = lang || 'javascript';
  const issues = [];

  const checks = [
    {
      severity: 'high',
      title: 'Cross-Site Scripting risk',
      pattern: /(innerHTML\s*=|dangerouslySetInnerHTML|document\.write\(|<script\b|onerror\s*=|onload\s*=)/i,
      description: `Detected unsafe HTML insertion in ${language} code.`,
      fix: 'Use textContent, safe DOM methods, or a trusted sanitizer.'
    },
    {
      severity: 'high',
      title: 'SQL Injection risk',
      pattern: /(SELECT\s+.*FROM|UNION\s+SELECT|WHERE\s+.*=\s*["']?\s*\+|\bquery\b.*\+|mysql_query|pg_query|sqlite_query)/i,
      description: `Detected possible raw SQL construction in ${language} code.`,
      fix: 'Use parameterized queries or an ORM.'
    },
    {
      severity: 'high',
      title: 'Hardcoded secret',
      pattern: /(password|api_key|secret|token|private_key)\s*[:=]\s*['"][^'"]+['"]/i,
      description: `Detected a possible hardcoded credential in ${language} code.`,
      fix: 'Move secrets to environment variables or a secrets manager.'
    },
    {
      severity: 'high',
      title: 'Command injection risk',
      pattern: /(exec\(|shell_exec|system\(|passthru\(|subprocess\.call|subprocess\.Popen)/i,
      description: `Detected command execution in ${language} code.`,
      fix: 'Avoid shell execution with user input.'
    },
    {
      severity: 'med',
      title: 'Missing CSRF protection',
      pattern: /(fetch\(|axios\.|XMLHttpRequest|form\s+action)/i,
      description: `HTTP requests were found without visible CSRF protection.`,
      fix: 'Use CSRF tokens for state-changing requests.'
    }
  ];

  checks.forEach(check => {
    if (check.pattern.test(text)) {
      if (check.title === 'Missing CSRF protection' && /(csrf_token|csrf|SameSite|X-CSRF)/i.test(text)) {
        return;
      }

      issues.push({
        severity: check.severity,
        title: check.title,
        description: check.description,
        fix: check.fix
      });
    }
  });

  if ((language === 'javascript' || language === 'html') && /localStorage|sessionStorage/.test(text)) {
    issues.push({
      severity: 'med',
      title: 'Sensitive browser storage',
      description: 'localStorage and sessionStorage are accessible from JavaScript.',
      fix: 'Avoid storing sensitive tokens there. Prefer httpOnly cookies.'
    });
  }

  if (language === 'python' && /pickle\.loads|eval\(|exec\(/.test(text)) {
    issues.push({
      severity: 'high',
      title: 'Unsafe Python execution or deserialization',
      description: 'pickle.loads(), eval(), and exec() can execute arbitrary code.',
      fix: 'Use JSON, ast.literal_eval(), or safer parsing.'
    });
  }

  if (issues.length === 0 && text.trim()) {
    issues.push({
      severity: 'low',
      title: 'No vulnerabilities detected',
      description: `Basic security checks passed for ${language}.`,
      fix: 'Run a full SAST scan before production.'
    });
  }

  let hardened = text
    .replace(/innerHTML\s*=/gi, 'textContent =')
    .replace(/document\.write\s*\(/gi, '/* document.write removed */ ')
    .replace(/(password|api_key|secret|token)\s*[:=]\s*['"][^'"]+['"]/gi, '$1 = process.env.$1');

  if (language === 'python') {
    hardened = hardened.replace(/pickle\.loads/g, 'json.loads');
  }

  return {
    lang: language,
    issues,
    hardened,
    score: scoreFromIssues(issues)
  };
}

function renderAuditResults({ issues, hardened, score }, { persist = true } = {}) {
  const auditOut = $('#auditOutput');
  if (auditOut) auditOut.classList.remove('hidden');

  const scoreEl = $('#auditScore');
  if (scoreEl) {
    scoreEl.textContent = `Score: ${score}/100`;
    scoreEl.classList.remove('safe', 'risky', 'danger');

    if (score >= 75) scoreEl.classList.add('safe');
    else if (score >= 45) scoreEl.classList.add('risky');
    else scoreEl.classList.add('danger');
  }

  const vulnList = $('#vulnList');
  if (vulnList) {
    vulnList.textContent = '';

    issues.forEach(issue => {
      const item = document.createElement('div');
      const cls = issue.severity === 'high' ? '' : issue.severity === 'medium' ? 'warn' : 'info';
      item.className = `vuln-item ${cls}`.trim();

      const title = document.createElement('div');
      title.className = 'vuln-title';
      title.textContent = issue.title;

      const desc = document.createElement('div');
      desc.className = 'vuln-desc';
      desc.textContent = issue.description;

      const fix = document.createElement('div');
      fix.className = 'vuln-fix';
      fix.textContent = issue.fix || '';

      item.append(title, desc, fix);
      vulnList.appendChild(item);
    });
  }

  renderPreWithLineNumbers(hardened, $('#hardenedCodeArea'));

  if (persist) {
    saveUiStatePatch({ auditResult: { issues, hardened, score } });
  }
}

/* ============================================================
   7. AI CHAT
   ============================================================ */

let pendingEdits = [];

function addChatMessage(text, type, { persist = true } = {}) {
  const container = $('#chatMessages');
  if (!container) return;

  const msg = document.createElement('div');
  msg.className = `chat-msg ${type}`;

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = type === 'ai' ? 'AI' : 'You';

  const content = document.createElement('div');
  content.className = 'msg-content';
  content.textContent = String(text ?? '');

  msg.append(avatar, content);
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;

  if (persist) {
    addMessageToActiveSession(type, text);
  }
}

function addThinkingIndicator() {
  const container = $('#chatMessages');
  if (!container) return;

  const div = document.createElement('div');
  div.className = 'chat-msg ai';
  div.id = 'thinkingIndicator';

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = 'AI';

  const content = document.createElement('div');
  content.className = 'msg-content';
  content.textContent = 'Thinking...';

  div.append(avatar, content);
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeThinkingIndicator() {
  $('#thinkingIndicator')?.remove();
}

async function processChatMessage() {
  const input = $('#chatInput');
  const message = input?.value.trim();

  if (!message) return;

  input.value = '';
  saveCurrentControls();
  addChatMessage(message, 'user');
  addThinkingIndicator();

  try {
    const out = await apiRequest('/api/v1/chat/ask', {
      method: 'POST',
      body: { message }
    });

    removeThinkingIndicator();

    if (out.search_results?.length) {
      const text = out.search_results
        .map(result => `${result.path}\n${result.snippet}`)
        .join('\n\n');
      addChatMessage(`Search Results:\n\n${text}`, 'ai');
    }

    if (out.response) {
      addChatMessage(out.response, 'ai');
    }

    if (out.edits?.length) {
      pendingEdits = out.edits;
      saveUiStatePatch({ pendingEdits });

      const editText = out.edits
        .map((edit, index) => {
          return `${index + 1}. ${edit.file}\n- ${edit.search}\n+ ${edit.replace}`;
        })
        .join('\n\n');

      addChatMessage(`Proposed Edits:\n\n${editText}`, 'ai');

      const editPreview = $('#chatEditPreview');
      const editContent = $('#chatEditContent');

      if (editPreview && editContent) {
        editPreview.classList.remove('hidden');
        editContent.textContent = editText;
      }
    }
  } catch (error) {
    removeThinkingIndicator();
    addChatMessage(`Error: ${error.message}`, 'ai');
  }
}

async function applyPendingEdits() {
  if (pendingEdits.length === 0) {
    showToast('No pending edits to apply.');
    return;
  }

  let successCount = 0;
  let failCount = 0;

  for (const edit of pendingEdits) {
    try {
      const result = await apiRequest('/api/v1/chat/apply-edit', {
        method: 'POST',
        body: {
          file: edit.file,
          search: edit.search,
          replace: edit.replace
        }
      });

      if (result.success) successCount++;
      else failCount++;
    } catch (error) {
      failCount++;
      console.error(`Failed to edit ${edit.file}:`, error);
    }
  }

  addChatMessage(
    `Edit Results:\n${successCount} file(s) updated successfully.\n${failCount} edit(s) failed.\nBackups saved with .bak extension.`,
    'ai'
  );

  pendingEdits = [];
  saveUiStatePatch({ pendingEdits });
  $('#chatEditPreview')?.classList.add('hidden');
}

/* ============================================================
   8. WIRE UP UI
   ============================================================ */

function wirePanels() {
  $$('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const panel = btn.dataset.panel;
      if (!panel) return;

      $$('.nav-btn').forEach(item => item.classList.remove('active'));
      btn.classList.add('active');

      switchPanel(`panel-${panel}`);
    });
  });

  $('#heroStartBtn')?.addEventListener('click', () => {
    switchPanel('panel-compiler');
    $('#appIdea')?.focus();
  });
}

let compileDebounceTimer = 0;
let compileAbortController = null;
let compilePending = false;

function triggerCompile({ persistLocal = true } = {}) {
  const btn = $('#compileBtn');
  if (!btn) return;

  // cancel in-flight request and debounce window
  if (compileDebounceTimer) {
    window.clearTimeout(compileDebounceTimer);
    compileDebounceTimer = 0;
  }

  if (compileAbortController) {
    try { compileAbortController.abort(); } catch (e) {}
  }

  compileAbortController = new AbortController();

  compileDebounceTimer = window.setTimeout(async () => {
    // prevent duplicate in-flight compiles from multiple triggers
    if (compilePending) return;
    compilePending = true;

    // Build a signal that aborts on user cancel OR 90s timeout.
    // The backend can take up to ~60s to generate a full AI project.
    const cancelSignal = compileAbortController.signal;
    const deadline = AbortSignal.timeout(90000);
    const signal = AbortSignal.any ? AbortSignal.any([cancelSignal, deadline]) : cancelSignal;

    // Clear previous auto-analysis results
    const prevStatus = $('#autoAnalysisStatus');
    if (prevStatus) prevStatus.remove();
    const prevResults = $('#autoAnalysisResults');
    if (prevResults) prevResults.remove();
    lastAutoResults = [];

    setLoading(btn, true);

    try {
      const token = window.localStorage.getItem('access_token');

      // Prefer backend compile path so AbortController works.
      // compileProjectLocal() currently creates its own controller; we bypass it.
      const frontend = $('#stackSelect')?.value || 'vanilla';
      const backend = $('#backendSelect')?.value || 'flask';
      const idea = ($('#appIdea')?.value || '').trim();

      if (!idea) {
        showToast('Please describe your app idea first.');
        throw new Error('No idea provided');
      }

      let out;
      try {
        out = await apiRequest('/api/v1/compiler/compile', {
          method: 'POST',
          token: token || undefined,
          body: { frontend, backend, idea },
          signal
        });
      } catch (error) {
        // If backend is down or request fails, fall back to local generator.
        if (error?.name !== 'AbortError') {
          console.info('Backend compiler unavailable, using local fallback:', error.message);
        }
        out = null;
      }

      if (out && out.files && Object.keys(out.files || {}).length > 0) {
        renderCompiledProject(out);
        if (out.ai_generated) {
          showToast('AI-generated project ready.');
        } else {
          showToast('Project generated locally (AI unavailable).');
        }
        await autoAnalyzeProject(currentCompiledFiles);
        saveCurrentProject({ silent: true });
      } else {
        if (compileAbortController.signal.aborted) return;
        const compiled = generateFullLocalProject({ idea, frontend, backend });
        renderCompiledProject(compiled);
        showToast('Project generated locally (fallback).');
        await autoAnalyzeProject(currentCompiledFiles);
        saveCurrentProject({ silent: true });
      }
    } catch (error) {
      if (error?.name === 'AbortError') return;
      showToast(error.message || 'Compile failed.');
      console.error(error);
    } finally {
      compilePending = false;
      setLoading(btn, false);
    }
  }, 750);
}

function wireCompiler() {
  const btn = $('#compileBtn');

  btn?.addEventListener('click', () => {
    triggerCompile();
  });

  $('#saveProjectBtn')?.addEventListener('click', () => saveCurrentProject({ silent: false }));

  $('#copyCompilerBtn')?.addEventListener('click', async () => {
    const text = buildCopyAll(currentCompiledFiles);

    if (!text) {
      showToast('Nothing to copy.');
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied all files.');
    } catch {
      copyTextFallback(text, 'Copy all:');
    }
  });
}

function wireDebugger() {
  const btn = $('#debugBtn');

  btn?.addEventListener('click', async () => {
    setLoading(btn, true);

    try {
      const lang = $('#debugLang')?.value || 'javascript';
      const code = ($('#buggyCode')?.value || '').trim();

      if (!code) {
        showToast('Please paste some code to debug.');
        return;
      }

      let result;

      try {
        const out = await apiRequest('/api/v1/debugger/analyze', {
          method: 'POST',
          body: { code, language: lang }
        });

        result = {
          issues: out.issues || [],
          fixed: out.fixed || code,
          ai_generated: out.ai_generated,
          ai_error: out.ai_error
        };
      } catch (error) {
        console.info('Backend debug unavailable, using local fallback:', error.message);
        result = debugLocal(code, lang);
      }

      renderDebugResults(result);
    } catch (error) {
      showToast('Debug failed.');
      console.error(error);
    } finally {
      setLoading(btn, false);
    }
  });

  $('#copyDebugBtn')?.addEventListener('click', async () => {
    const pre = $('#fixedCodeArea pre');

    if (!pre) {
      showToast('Nothing to copy.');
      return;
    }

    const text = Array.from(pre.querySelectorAll('.line'))
      .map(line => line.textContent)
      .join('\n');

    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied fixed code.');
    } catch {
      copyTextFallback(text, 'Copy fixed code:');
    }
  });
}

function wireAudit() {
  const btn = $('#auditBtn');

  btn?.addEventListener('click', async () => {
    setLoading(btn, true);

    try {
      const lang = $('#auditLang')?.value || 'javascript';
      const code = ($('#auditCode')?.value || '').trim();

      if (!code) {
        showToast('Please paste some code to audit.');
        return;
      }

      let result;

      try {
        const out = await apiRequest('/api/v1/ai-security/audit', {
          method: 'POST',
          body: { code, language: lang }
        });

        result = {
          issues: out.issues || [],
          hardened: out.hardened || code,
          score: out.score || 50
        };
      } catch (error) {
        console.info('Backend audit unavailable, using local fallback:', error.message);
        result = auditLocal(code, lang);
      }

      renderAuditResults(result);
    } catch (error) {
      showToast('Audit failed.');
      console.error(error);
    } finally {
      setLoading(btn, false);
    }
  });

  $('#copyAuditBtn')?.addEventListener('click', async () => {
    const pre = $('#hardenedCodeArea pre');

    if (!pre) {
      showToast('Nothing to copy.');
      return;
    }

    const text = Array.from(pre.querySelectorAll('.line'))
      .map(line => line.textContent)
      .join('\n');

    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied hardened code.');
    } catch {
      copyTextFallback(text, 'Copy hardened code:');
    }
  });
}

/* ============================================================
   AUTO ANALYSIS AFTER COMPILATION
   ============================================================ */

let lastAutoResults = [];

async function autoAnalyzeProject(files) {
  const container = $('#compilerOutput');
  if (!container || !files || files.length === 0) return;

  try {
    let statusBar = container.querySelector('#autoAnalysisStatus');
    if (!statusBar) {
      statusBar = document.createElement('div');
      statusBar.id = 'autoAnalysisStatus';
      statusBar.className = 'auto-analysis-status';
      container.appendChild(statusBar);
    }
  statusBar.innerHTML = '<span>Running debug & security analysis...</span>';
  statusBar.classList.remove('hidden');

  lastAutoResults = [];
  let totalBugs = 0;
  let totalVulns = 0;
  let analyzedCount = 0;

  for (const file of files) {
    const ext = String(file.path || '').split('.').pop().toLowerCase();
    if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', 'woff', 'woff2', 'eot', 'ttf'].includes(ext)) continue;

    const lang = getLanguageFromExtension(file.path);
    statusBar.innerHTML = `<span>Analyzing ${file.path}...</span>`;

    const fileResult = { path: file.path, lang, code: file.content, bugs: [], vulns: [] };

    try {
      const debugOut = await apiRequest('/api/v1/debugger/analyze', {
        method: 'POST',
        body: { code: file.content, language: lang }
      });
      const debugIssues = debugOut.issues || [];
      if (debugOut.ai_generated !== undefined) fileResult.ai_generated = debugOut.ai_generated;
      fileResult.bugs = debugIssues;
      totalBugs += debugIssues.length;
    } catch (e) {
      const localResult = debugLocal(file.content, lang);
      fileResult.bugs = localResult.issues || [];
      totalBugs += fileResult.bugs.length;
    }

    try {
      const auditOut = await apiRequest('/api/v1/ai-security/audit', {
        method: 'POST',
        body: { code: file.content, language: lang }
      });
      const auditIssues = auditOut.issues || [];
      fileResult.vulns = auditIssues;
      fileResult.auditScore = auditOut.score;
      totalVulns += auditIssues.length;
    } catch (e) {
      const localResult = auditLocal(file.content, lang);
      fileResult.vulns = localResult.issues || [];
      fileResult.auditScore = localResult.score;
      totalVulns += fileResult.vulns.length;
    }

    lastAutoResults.push(fileResult);
    analyzedCount++;
  }

  if (analyzedCount === 0) {
    statusBar.innerHTML = '<span>No analyzable files found.</span>';
    return;
  }

  const bugLabel = totalBugs === 1 ? 'bug' : 'bugs';
  const vulnLabel = totalVulns === 1 ? 'vulnerability' : 'vulnerabilities';

  statusBar.innerHTML = `
    <span class="analysis-summary-text">
      <strong class="analysis-findings-badge">${totalBugs} ${bugLabel}</strong> ·
      <strong class="analysis-findings-badge vuln">${totalVulns} ${vulnLabel}</strong>
      across ${analyzedCount} file(s)
      ${totalBugs > 0 || totalVulns > 0 ? '&mdash; <a href="#" class="analysis-view-link" data-target="results">View details</a>' : ''}
    </span>
  `;

  // Remove auto-hide — keep results visible until next compile
  statusBar.classList.remove('hidden');

  // Render detailed findings panel below the status bar
  renderAutoAnalysisResults(container);

  // Save bugs to backend if a project is active
  if (currentProjectId && (totalBugs > 0 || totalVulns > 0)) {
    saveBugsFromAnalysis(currentProjectId, lastAutoResults);
  }

  // Auto-navigate after analysis completes
  window.setTimeout(() => {
    if (totalVulns > totalBugs && totalVulns > 0) {
      // More vulnerabilities — auto-open security panel with first file's results
      const firstWithVulns = lastAutoResults.find(r => r.vulns.length > 0);
      if (firstWithVulns) {
        showToast(`Auto-navigating to Security Audit — ${totalVulns} vulnerability(ies) found`);
        sendToSecurityAudit(firstWithVulns.code, firstWithVulns.path);
      }
    } else if (totalBugs > 0) {
      // More or equal bugs — auto-open debugger
      const firstWithBugs = lastAutoResults.find(r => r.bugs.length > 0);
      if (firstWithBugs) {
        showToast(`Auto-navigating to Debugger — ${totalBugs} bug(s) found`);
        sendToAutoDebugger(firstWithBugs.code, firstWithBugs.path);
      }
    } else {
      showToast('Analysis complete — no issues found');
    }
  }, 600);
  } catch (e) { console.error('Auto-analysis failed:', e); }
}

function renderAutoAnalysisResults(container) {
  let resultsPanel = container.querySelector('#autoAnalysisResults');
  if (!resultsPanel) {
    resultsPanel = document.createElement('div');
    resultsPanel.id = 'autoAnalysisResults';
    resultsPanel.className = 'auto-analysis-results';
    container.appendChild(resultsPanel);
  }

  resultsPanel.innerHTML = '<div class="analysis-results-header">File-by-file results</div>';

  lastAutoResults.forEach(result => {
    const row = document.createElement('div');
    row.className = 'analysis-file-row';

    const name = document.createElement('span');
    name.className = 'analysis-file-name';
    name.textContent = result.path;

    const info = document.createElement('span');
    info.className = 'analysis-file-info';

    const bugCount = result.bugs.length;
    const vulnCount = result.vulns.length;

    if (bugCount > 0) {
      const bugLink = document.createElement('a');
      bugLink.href = '#';
      bugLink.className = 'analysis-link';
      bugLink.textContent = `${bugCount} bug${bugCount === 1 ? '' : 's'}`;
      bugLink.addEventListener('click', (e) => {
        e.preventDefault();
        sendToAutoDebugger(result.code, result.path);
      });
      info.appendChild(bugLink);
    }

    if (bugCount > 0 && vulnCount > 0) {
      const sep = document.createTextNode(' · ');
      info.appendChild(sep);
    }

    if (vulnCount > 0) {
      const vulnLink = document.createElement('a');
      vulnLink.href = '#';
      vulnLink.className = 'analysis-link vuln-link';
      vulnLink.textContent = `${vulnCount} vuln${vulnCount === 1 ? '' : 's'}`;
      vulnLink.addEventListener('click', (e) => {
        e.preventDefault();
        sendToSecurityAudit(result.code, result.path);
      });
      info.appendChild(vulnLink);
    }

    if (bugCount === 0 && vulnCount === 0) {
      info.textContent = 'No issues';
      info.style.color = 'var(--success)';
    }

    row.append(name, info);
    resultsPanel.appendChild(row);
  });
}

/* ============================================================
   CROSS-PANEL AUTOMATION BRIDGE
   ============================================================ */

function getLanguageFromExtension(filePath) {
  const ext = String(filePath || '').split('.').pop().toLowerCase();
  const map = {
    js: 'javascript',
    mjs: 'javascript',
    cjs: 'javascript',
    py: 'python',
    html: 'html',
    css: 'css',
    go: 'go',
    php: 'php',
    java: 'java',
    cpp: 'cpp',
    cc: 'cpp'
  };
  return map[ext] || 'javascript';
}

function setTextareaValue(el, value) {
  if (!el) return;
  el.value = String(value ?? '');
}

function setSelectValue(el, value) {
  if (!el) return;
  el.value = value;
}

function switchToDebugPanel() {
  const debuggerTabBtn = document.querySelector('.nav-btn[data-panel="debugger"]');
  debuggerTabBtn?.click();
}

function switchToSecurityPanel() {
  const auditTabBtn =
    document.querySelector('.nav-btn[data-panel="security"]') ||
    document.querySelector('.nav-btn[data-panel="audit"]');
  auditTabBtn?.click();
}

function sendToAutoDebugger(code, filePath) {
  switchToDebugPanel();

  const debuggerTextarea = $('#buggyCode');
  const debuggerLangSelect = $('#debugLang');
  const debuggerSubmitBtn = $('#debugBtn');

  setTextareaValue(debuggerTextarea, code);
  setSelectValue(debuggerLangSelect, getLanguageFromExtension(filePath));

  if (debuggerSubmitBtn) {
    setTimeout(() => debuggerSubmitBtn.click(), 150);
  }
}

function sendToSecurityAudit(code, filePath) {
  switchToSecurityPanel();

  const auditTextarea = $('#auditCode');
  const auditLangSelect = $('#auditLang');
  const auditSubmitBtn = $('#auditBtn');

  setTextareaValue(auditTextarea, code);
  setSelectValue(auditLangSelect, getLanguageFromExtension(filePath));

  if (auditSubmitBtn) {
    setTimeout(() => auditSubmitBtn.click(), 150);
  }
}

function attachCompilerQuickActions() {
  // Ensure we have a visible toolbar area above the code viewer.
  // The UI already uses `#fileContentArea`.
  const contentArea = $('#fileContentArea');
  if (!contentArea) return;

  // Avoid duplicating.
  if (contentArea.querySelector('#compilerQuickActions')) return;

  const toolbar = document.createElement('div');
  toolbar.id = 'compilerQuickActions';
  toolbar.className = 'compiler-quick-actions';

  toolbar.innerHTML = `
    <div class="compiler-quick-actions-inner">
      <button type="button" class="btn btn-sm btn-primary" id="quickDebugBtn">
        <i data-lucide="bug"></i>
        Auto-Debug File
      </button>
      <button type="button" class="btn btn-sm btn-ghost" id="quickAuditBtn">
        <i data-lucide="shield-check"></i>
        Security Audit
      </button>
    </div>
  `;

  contentArea.prepend(toolbar);
  refreshIcons();
}

function wireCompilerQuickActions() {
  attachCompilerQuickActions();

  const debugBtn = $('#quickDebugBtn');
  const auditBtn = $('#quickAuditBtn');
  if (!debugBtn || !auditBtn) return;

  const getActiveFile = () => {
    const activeFile = $('#fileTabs')?.querySelector('.file-tab.active')?.dataset?.path || '';
    const file = currentCompiledFiles?.find(f => f.path === activeFile);

    return {
      code: file?.content || '',
      path: file?.path || activeFile
    };
  };

  const bindHandlers = () => {
    debugBtn.onclick = () => {
      const { code, path } = getActiveFile();
      sendToAutoDebugger(code, path);
    };

    auditBtn.onclick = () => {
      const { code, path } = getActiveFile();
      sendToSecurityAudit(code, path);
    };
  };

  // Also refresh handlers whenever user changes the file tab.
  $$('#fileTabs .file-tab').forEach(btn => {
    btn.addEventListener('click', () => setTimeout(bindHandlers, 0));
  });

  bindHandlers();
  refreshIcons();
}

function wireChat() {
  $('#chatSendBtn')?.addEventListener('click', processChatMessage);


  $('#chatInput')?.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      processChatMessage();
    }
  });

  $('#applyEditBtn')?.addEventListener('click', applyPendingEdits);

  $('#newChatBtn')?.addEventListener('click', () => {
    createChatSession();
    renderChatHistoryList();
    renderChatMessagesFromHistory();
    $('#chatInput')?.focus();
    showToast('Started a new chat.');
  });

  $('#clearHistoryBtn')?.addEventListener('click', () => {
    if (chatSessions.length === 0) return;
    const confirmed = window.confirm('Clear all saved chat history?');
    if (!confirmed) return;

    chatSessions = [];
    activeChatId = '';
    pendingEdits = [];
    saveChatState();
    saveUiStatePatch({ pendingEdits });
    $('#chatEditPreview')?.classList.add('hidden');
    renderChatHistoryList();
    renderChatMessagesFromHistory();
    showToast('Chat history cleared.');
  });
}

/* ============================================================
   Settings / Profile
   ============================================================ */

/* ============================================================
   AI Config
   ============================================================ */

async function loadAiConfig() {
  const body = $('#aiConfigBody');
  if (!body) return;

  try {
    const out = await apiRequest('/api/v1/ai/config/');
    const cfg = out.config || {};
    const models = out.available_models || {};
    const providers = out.providers || {};

    const geminiModels = models.gemini || [];
    const groqModels = models.groq || [];

    const geminiOnline = providers.gemini;
    const groqOnline = providers.groq;

    body.innerHTML = `
      <div class="ai-config-provider-header">
        <span class="ai-config-provider-dot ${geminiOnline ? 'online' : 'offline'}"></span>
        Gemini ${geminiOnline ? 'configured' : 'not configured'}
      </div>
      <div class="ai-config-section">
        <label for="aiGeminiModel">Model</label>
        <select id="aiGeminiModel">
          ${geminiModels.map(m => `<option value="${m}" ${m === cfg.gemini_model ? 'selected' : ''}>${m}</option>`).join('')}
          ${geminiModels.length === 0 ? '<option>gemini-2.5-flash</option>' : ''}
        </select>
      </div>
      <div class="ai-config-section">
        <label for="aiGeminiMaxTokens">Max output tokens</label>
        <input id="aiGeminiMaxTokens" type="number" min="256" max="65536" value="${cfg.gemini_max_tokens || 8192}" />
        <div class="ai-config-token-info">
          <span>Current: <strong id="aiGeminiTokensDisplay">${cfg.gemini_max_tokens || 8192}</strong></span>
        </div>
      </div>

      <div class="ai-config-divider"></div>

      <div class="ai-config-provider-header">
        <span class="ai-config-provider-dot ${groqOnline ? 'online' : 'offline'}"></span>
        Groq ${groqOnline ? 'configured' : 'not configured'}
      </div>
      <div class="ai-config-section">
        <label for="aiGroqModel">Model</label>
        <select id="aiGroqModel">
          ${groqModels.map(m => `<option value="${m.id}" ${m.id === cfg.groq_model ? 'selected' : ''}>${m.id} (${(m.context / 1000).toFixed(0)}K ctx)</option>`).join('')}
          ${groqModels.length === 0 ? '<option>llama-3.3-70b-versatile</option>' : ''}
        </select>
      </div>
      <div class="ai-config-section">
        <label for="aiGroqMaxTokens">Max output tokens</label>
        <input id="aiGroqMaxTokens" type="number" min="256" max="131072" value="${cfg.groq_max_tokens || 32768}" />
        <div class="ai-config-token-info">
          <span>Current: <strong id="aiGroqTokensDisplay">${cfg.groq_max_tokens || 32768}</strong></span>
        </div>
      </div>

      <div class="ai-config-actions">
        <button type="button" class="ai-config-btn" id="saveAiConfigBtn">
          <i data-lucide="save"></i>
          Save AI Config
        </button>
      </div>
    `;

    refreshIcons(body);

    // Live token display updates
    $('#aiGeminiMaxTokens')?.addEventListener('input', () => {
      const display = $('#aiGeminiTokensDisplay');
      if (display) display.textContent = $('#aiGeminiMaxTokens').value;
    });
    $('#aiGroqMaxTokens')?.addEventListener('input', () => {
      const display = $('#aiGroqTokensDisplay');
      if (display) display.textContent = $('#aiGroqMaxTokens').value;
    });

    // Save handler
    $('#saveAiConfigBtn')?.addEventListener('click', async () => {
      const btn = $('#saveAiConfigBtn');
      btn.textContent = 'Saving...';
      btn.disabled = true;

      const updates = {
        gemini_model: $('#aiGeminiModel')?.value || 'gemini-2.5-flash',
        gemini_max_tokens: parseInt($('#aiGeminiMaxTokens')?.value) || 8192,
        groq_model: $('#aiGroqModel')?.value || 'llama-3.3-70b-versatile',
        groq_max_tokens: parseInt($('#aiGroqMaxTokens')?.value) || 32768,
      };

      try {
        await apiRequest('/api/v1/ai/config/', {
          method: 'PUT',
          body: updates,
        });
        showToast('AI config saved. Changes apply immediately.');
      } catch (err) {
        showToast(err.message || 'Failed to save AI config.');
      } finally {
        btn.textContent = 'Save AI Config';
        btn.disabled = false;
        refreshIcons();
      }
    });

  } catch (err) {
    body.innerHTML = `<p class="ai-config-loading">Could not load AI config: ${err.message}</p>`;
  }
}

async function loadProfile() {
  try {
    const out = await apiRequest('/api/v1/auth/me');
    const user = out.user || {};

    const displayName = user.username || 'Mendify user';
    const email = user.email || 'No email loaded';
    const initials = (user.username || 'ME').slice(0, 2).toUpperCase();

    $('#settingsProfileInitials').textContent = initials;
    $('#settingsProfileName').textContent = displayName;
    $('#settingsProfileEmail').textContent = email;
    $('#settingsUsername').value = user.username || '';
    $('#settingsEmail').value = user.email || '';

    if (user.created_at) {
      const d = new Date(user.created_at);
      $('#settingsProfileJoined').textContent = d.toLocaleDateString(undefined, {
        year: 'numeric', month: 'long', day: 'numeric'
      });
    }
  } catch (err) {
    console.warn('Could not load profile:', err);
  }
}

async function saveSettingsProfile() {
  const btn = $('#saveSettingsProfileBtn');
  if (!btn) return;
  setLoading(btn, true);

  const username = $('#settingsUsername')?.value?.trim();
  const email = $('#settingsEmail')?.value?.trim();
  const body = {};
  if (username) body.username = username;
  if (email) body.email = email;

  try {
    const out = await apiRequest('/api/v1/auth/me', {
      method: 'PUT',
      body
    });
    if (out.user) {
      window.localStorage.setItem('user', JSON.stringify(out.user));
      displayUser();
    }
    showToast(out.message || 'Profile updated.');
    loadProfile();
  } catch (err) {
    showToast(err.message || 'Failed to save profile.');
  } finally {
    setLoading(btn, false);
  }
}

function wireSettings() {
  // Theme
  $$('.theme-option').forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.dataset.themeOption;
      applyTheme(theme);
      saveTheme(theme);
    });
  });

  // Density
  $$('.density-option').forEach(btn => {
    btn.addEventListener('click', () => {
      const density = btn.dataset.densityOption;
      applyDensity(density);
      saveDensity(density);
    });
  });

  // Profile
  $('#saveSettingsProfileBtn')?.addEventListener('click', saveSettingsProfile);

  // Load profile + AI config when settings panel becomes active
  const settingsPanel = $('#panel-settings');
  if (settingsPanel) {
    const observer = new MutationObserver(() => {
      if (settingsPanel.classList.contains('active')) {
        loadProfile();
        loadAiConfig();
      }
    });
    observer.observe(settingsPanel, { attributes: true, attributeFilter: ['class'] });
  }
}

/* ============================================================
   Keyboard shortcuts
   ============================================================ */

function wireKeyboardShortcuts() {
  let shortcutsVisible = false;
  let shortcutsOverlay = null;

  function showShortcuts() {
    if (shortcutsOverlay) {
      shortcutsOverlay.remove();
      shortcutsOverlay = null;
      shortcutsVisible = false;
      return;
    }

    const overlay = document.createElement('div');
    overlay.className = 'shortcuts-overlay';
    overlay.innerHTML = `
      <div class="shortcuts-modal">
        <div class="shortcuts-modal-header">
          <span>Keyboard Shortcuts</span>
          <button type="button" class="btn btn-sm btn-ghost" id="closeShortcutsBtn">Close</button>
        </div>
        <div class="shortcuts-modal-body">
          <div><kbd>Ctrl+1</kbd> <span>Compiler</span></div>
          <div><kbd>Ctrl+2</kbd> <span>Debugger</span></div>
          <div><kbd>Ctrl+3</kbd> <span>Security Audit</span></div>
          <div><kbd>Ctrl+4</kbd> <span>AI Chat</span></div>
          <div><kbd>Ctrl+5</kbd> <span>Settings</span></div>
          <div><kbd>Enter</kbd> <span>Send message</span></div>
          <div><kbd>?</kbd> <span>Toggle this panel</span></div>
          <div><kbd>Esc</kbd> <span>Close this panel</span></div>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    shortcutsOverlay = overlay;
    shortcutsVisible = true;

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.remove();
        shortcutsOverlay = null;
        shortcutsVisible = false;
      }
    });
    $('#closeShortcutsBtn')?.addEventListener('click', () => {
      overlay.remove();
      shortcutsOverlay = null;
      shortcutsVisible = false;
    });
  }

  document.addEventListener('keydown', (e) => {
    // Ctrl+1 through Ctrl+5 for panel navigation
    if (e.ctrlKey && !e.shiftKey && !e.altKey && e.key >= '1' && e.key <= '5') {
      e.preventDefault();
      const panels = ['compiler', 'debugger', 'security', 'chat', 'settings'];
      const idx = parseInt(e.key) - 1;
      const panel = panels[idx];
      if (panel) {
        const btn = document.querySelector(`.nav-btn[data-panel="${panel}"]`);
        btn?.click();
      }
    }

    // ? key to show/hide shortcuts
    if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      const active = document.activeElement;
      const isInput = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT');
      if (!isInput) {
        showShortcuts();
      }
    }

    // Escape to close shortcuts
    if (e.key === 'Escape' && shortcutsOverlay) {
      shortcutsOverlay.remove();
      shortcutsOverlay = null;
      shortcutsVisible = false;
    }
  });
}

async function checkAuth() {
  const token = localStorage.getItem('access_token');

  if (!token) {
    document.documentElement.style.visibility = 'visible';
    window.location.replace('login.html');
    return false;
  }


  try {
    await apiRequest('/api/v1/auth/me', { token, signal: AbortSignal.timeout(5000) });
    document.documentElement.style.visibility = 'visible';
  } catch (error) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    document.documentElement.style.visibility = 'visible';
    window.location.replace('login.html');

    return false;
  }

  return token;
}

function displayUser() {
  const userBadge = $('#userBadge');
  const userName = $('#userName');

  if (!userBadge || !userName) return;

  try {
    const userData = JSON.parse(localStorage.getItem('user') || '{}');

    if (userData.username) {
      userName.textContent = userData.username;
      userBadge.classList.remove('hidden');
    }
  } catch {
    console.warn('Could not parse user data.');
  }
}

function wireLogout() {
  $('#logoutBtn')?.addEventListener('click', () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');

    window.location.replace('login.html');
  });
}

async function init() {
  // checkAuth() verifies the token and makes the page visible.
  // If the token is invalid or the backend is offline, it redirects
  // to login.html (with a 5s timeout to avoid hanging).
  if (!await checkAuth()) return;

  // Apply saved theme/density before any render
  applyTheme(loadTheme());
  applyDensity(loadDensity());

  loadSavedState();
  displayUser();

  wirePanels();
  wireCompiler();
  wireDebugger();
  wireAudit();
  wireChat();
  wireSettings();
  wireKeyboardShortcuts();
  wireLogout();
  wireStatePersistence();

  // Projects sidebar
  $('#refreshProjectsBtn')?.addEventListener('click', loadSavedProjects);
  loadSavedProjects();

  renderChatHistoryList();
  renderChatMessagesFromHistory();
  restoreUiState();

  refreshIcons();

  // Check API health on load and periodically
  checkApiHealth();
  setInterval(checkApiHealth, 30000);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
