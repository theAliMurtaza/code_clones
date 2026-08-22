/**
 * api_client.js
 * Drop this file into your React frontend at:  src/utils/api_client.js
 *
 * Replace the mock data in Upload.jsx / Detection.jsx with these calls.
 * Every function returns the response body directly (throws on error).
 *
 * Usage in Upload.jsx:
 *   import { detectClones } from '../utils/api_client'
 *   const result = await detectClones(files, threshold, token)
 *   // result.status === 'queued' → poll with pollJob(result.job_id, token, onDone)
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── Internal helper ───────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}

// ── Auth ──────────────────────────────────────────────────────────────
export async function register(name, email, password) {
  return apiFetch('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  })
}

export async function login(email, password) {
  return apiFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

// ── Upload & detect ───────────────────────────────────────────────────
/**
 * Upload files and start detection.
 * files: array of File objects (from <input type="file">)
 * token: JWT from login()
 * Returns: { job_id, status, message }
 */
export async function detectClones(files, threshold = 0.75, token) {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  form.append('threshold', threshold)

  const res = await fetch(`${BASE_URL}/api/detect`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Poll for job completion ───────────────────────────────────────────
/**
 * Poll GET /api/jobs/{jobId} every `intervalMs` until status === 'done'.
 * Calls onProgress({ status, total_pairs }) on each poll.
 * Calls onDone(jobDetail) when complete.
 * Calls onError(Error) on failure.
 * Returns a cancel() function.
 */
export function pollJob(jobId, token, { onProgress, onDone, onError, intervalMs = 2000 } = {}) {
  let cancelled = false

  async function tick() {
    if (cancelled) return
    try {
      const data = await apiFetch(`/api/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      onProgress?.({ status: data.status, total_pairs: data.total_pairs })

      if (data.status === 'done') {
        onDone?.(data)
      } else if (data.status === 'failed') {
        onError?.(new Error(data.error || 'Job failed'))
      } else {
        setTimeout(tick, intervalMs)
      }
    } catch (err) {
      onError?.(err)
    }
  }

  tick()
  return () => { cancelled = true }  // cancel function
}

// ── Job management ────────────────────────────────────────────────────
export async function listJobs(token) {
  return apiFetch('/api/jobs', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function getJob(jobId, token) {
  return apiFetch(`/api/jobs/${jobId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function deleteJob(jobId, token) {
  return apiFetch(`/api/jobs/${jobId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
}

// ── Dashboard stats ───────────────────────────────────────────────────
export async function getStats(token) {
  return apiFetch('/api/stats', {
    headers: { Authorization: `Bearer ${token}` },
  })
}
