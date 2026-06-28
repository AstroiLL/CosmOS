/* ── API client for CosmOS ──────────────────────────── */

const BASE = '/api/v1';

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const headers = { ...options.headers };

  // Try to read API key from cookie or use empty (dev mode)
  const token = getCookie('cosmos_api_key') || '';

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }

  return res.json();
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : '';
}

// ── Health ──
export function health() {
  return request('/health');
}

// ── Tasks ──
export function listTasks(limit = 10) {
  return request(`/tasks?limit=${limit}`);
}

export function getTask(taskId) {
  return request(`/tasks/${taskId}`);
}

export function createTask(description, agent = null, host = null) {
  return request('/tasks', {
    method: 'POST',
    body: JSON.stringify({ description, agent, host }),
  });
}

// ── Agents ──
export function listAgents() {
  return request('/agents');
}

// ── Doctor ──
export function doctor() {
  return request('/doctor');
}

// ── Memory ──
export function memorySearch(query, source = 'all', limit = 10) {
  return request('/memory/search', {
    method: 'POST',
    body: JSON.stringify({ query, source, limit }),
  });
}
