import { API_BASE } from './config.js';
const KEY = 'ov_token';
export const auth = { get: () => sessionStorage.getItem(KEY), set: t => sessionStorage.setItem(KEY, t), clear: () => sessionStorage.removeItem(KEY) };
export class ApiError extends Error { constructor(m, status, body) { super(m); this.status = status; this.body = body; } }

function msg(body, fallback) {
  const d = body?.detail ?? body;
  if (Array.isArray(d)) return d.map(e => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`).join('; ');
  return typeof d === 'string' ? d : (d?.detail || fallback);
}
export async function api(method, path, { body, query } = {}) {
  const qs = query ? '?' + new URLSearchParams(Object.entries(query).filter(([, v]) => v != null && v !== '')) : '';
  let res;
  try {
    res = await fetch(API_BASE + path + qs, { method,
      headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(auth.get() ? { Authorization: 'Bearer ' + auth.get() } : {}) },
      body: body ? JSON.stringify(body) : undefined });
  } catch { throw new ApiError(await diagnose(), 0); }
  let data = null; try { data = await res.json(); } catch {}
  if (res.status === 401 && auth.get()) { auth.clear(); window.dispatchEvent(new Event('ov:expired')); throw new ApiError('Session expired. Please sign in again.', 401); }
  if (!res.ok) throw new ApiError(msg(data, `Request failed (${res.status})`), res.status, data);
  return data;
}
export async function diagnose() {
  try {
    const r = await fetch(API_BASE + '/health');
    if (r.status === 502) return 'Frontend proxy is running, but the backend gateway on port 8000 is unreachable.';
    return `API health check returned HTTP ${r.status}. Check the Network tab for the failed request.`;
  } catch { return 'Network request failed. Check the frontend server, gateway, and browser Network tab for CORS or connection errors.'; }
}

export const get = (p, q) => api('GET', p, { query: q });
export const post = (p, b) => api('POST', p, { body: b ?? {} });
export const patch = (p, b) => api('PATCH', p, { body: b });
export const del = p => api('DELETE', p);
