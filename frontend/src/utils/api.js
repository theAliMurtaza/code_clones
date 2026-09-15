const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function req(path, options = {}, token = null) {
  const headers = {}
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
  })

  if (res.status === 204) return null
  const data = await res.json().catch(() => ({ detail: res.statusText }))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
  return data
}

export const api = {
  health: () => req('/health'),
  register: (name, email, password) =>
    req('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    }),
  login: (email, password) =>
    req('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: (token) => req('/api/me', {}, token),
  detect: async (files, threshold, token) => {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    form.append('threshold', String(threshold))
    return req('/api/detect', { method: 'POST', body: form }, token)
  },
  jobs:      (token)        => req('/api/jobs',            {}, token),
  job:       (id, token)    => req(`/api/jobs/${id}`,      {}, token),
  deleteJob: (id, token)    => req(`/api/jobs/${id}`, { method: 'DELETE' }, token),
  stats: (token) => req('/api/stats', {}, token),
}

export function pollJob(jobId, token, { onProgress, onDone, onError, intervalMs = 2500 } = {}) {
  let cancelled = false
  let timer

  const tick = async () => {
    if (cancelled) return
    try {
      const data = await api.job(jobId, token)
      onProgress?.(data)
      if (data.status === 'done') {
        onDone?.(data)
      } else if (data.status === 'failed') {
        onError?.(new Error(data.error || 'Job failed'))
      } else {
        timer = setTimeout(tick, intervalMs)
      }
    } catch (err) {
      onError?.(err)
    }
  }

  tick()
  return () => { cancelled = true; clearTimeout(timer) }
}
