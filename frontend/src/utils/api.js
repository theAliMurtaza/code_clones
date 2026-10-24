import { beginActivity } from './activity'
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const BASE_URL = BASE

async function req(path, options = {}, token = null) {
  const headers = {}
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const { timeout = 60000, silent = false, activity, ...fetchOptions } = options
  const finish = silent ? () => {} : beginActivity(activity || (
    path.includes('/auth/') ? 'Signing you in…' :
    path.includes('/detect') ? 'Preparing your analysis…' :
    options.method === 'DELETE' ? 'Deleting analysis…' : 'Loading your workspace…'))
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...fetchOptions,
      headers: { ...headers, ...fetchOptions.headers },
      signal: fetchOptions.signal || controller.signal,
    })

    if (res.status === 204) return null
    const data = await res.json().catch(() => ({ detail: res.statusText }))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    return data
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Connection timed out. The server might still be starting up.')
    }
    throw err
  } finally {
    finish()
    clearTimeout(id)
  }
}

export const api = {
  health: (options = {}) => req('/health', { timeout: 10000, silent: true, ...options }),
  googleConfig: () => req('/api/auth/google/config', { silent: true }),
  googleLogin: (credential, nonce) => req('/api/auth/google', {
    method: 'POST', body: JSON.stringify({ credential, nonce }),
  }),
  register: (name, email, password) =>
    req('/api/auth/register', {
      method: 'POST',
      activity: 'Creating your account…',
      body: JSON.stringify({ name, email, password }),
    }),
  login: (email, password) =>
    req('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: (token) => req('/api/me', {}, token),
  detect: async (files, threshold, token, filePaths = []) => {
    const form = new FormData()
    files.forEach((f, idx) => {
      const p = filePaths[idx] || f.webkitRelativePath || f.relativePath || f.name
      form.append('files', f, p)
    })
    if (filePaths.length) {
      form.append('paths_json', JSON.stringify(filePaths))
    }
    form.append('threshold', String(threshold))
    return req('/api/detect', { method: 'POST', body: form }, token)
  },
  detectFolder: (folderPath, threshold, token) =>
    req('/api/detect/folder', {
      method: 'POST',
      body: JSON.stringify({ folder_path: folderPath, threshold: Number(threshold) }),
    }, token),
  jobs:      (token)        => req('/api/jobs',            {}, token),
  job:       (id, token, options = {}) => req(`/api/jobs/${id}`, options, token),
  source: (id, path, token) => req(`/api/jobs/${id}/source?path=${encodeURIComponent(path)}`, {}, token),
  deleteJob: (id, token)    => req(`/api/jobs/${id}`, { method: 'DELETE' }, token),
  stats: (token) => req('/api/stats', {}, token),
}

export function pollJob(jobId, token, { onProgress, onDone, onError, intervalMs = 2500 } = {}) {
  let cancelled = false
  let timer
  let consecutiveErrors = 0

  const tick = async () => {
    if (cancelled) return
    try {
      const data = await api.job(jobId, token, { silent: true })
      if (cancelled) return
      consecutiveErrors = 0
      onProgress?.(data)
      if (data.status === 'done') {
        onDone?.(data)
      } else if (data.status === 'failed') {
        onError?.(new Error(data.error || 'Job failed'))
      } else {
        timer = setTimeout(tick, intervalMs)
      }
    } catch (err) {
      if (cancelled) return
      consecutiveErrors++
      // Allow up to 3 consecutive transient network glitches before declaring error
      if (consecutiveErrors >= 3) {
        onError?.(err)
      } else {
        timer = setTimeout(tick, intervalMs)
      }
    }
  }

  tick()
  return () => { cancelled = true; clearTimeout(timer) }
}
