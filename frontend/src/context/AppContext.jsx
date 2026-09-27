import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { api, BASE_URL } from '../utils/api'

const Ctx = createContext(null)

export function AppProvider({ children }) {
  const [token,    setToken]    = useState(() => localStorage.getItem('cs_token') || '')
  const [userName, setUserName] = useState(() => localStorage.getItem('cs_user')  || '')
  const [isAuthed, setIsAuthed] = useState(() => !!localStorage.getItem('cs_token'))
  const [page,     setPage]     = useState('dashboard')
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [threshold,     setThreshold]     = useState(0.75)
  const [currentJobId,  setCurrentJobId]  = useState(null)
  const [jobProgress,   setJobProgress]   = useState(null)
  const [jobResults,    setJobResults]    = useState(null)
  const [recentJobs,    setRecentJobs]    = useState([])
  const [dashStats,     setDashStats]     = useState(null)
  const [loadingDash,   setLoadingDash]   = useState(false)
  const [toasts,        setToasts]        = useState([])
  const toastId = useRef(0)

  // Auth modal control
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [authModalMode, setAuthModalMode] = useState('login')
  const [authPendingAction, setAuthPendingAction] = useState(null)

  // Backend connection & cold-start tracking
  // status: 'connected' | 'waking' | 'offline' | 'checking'
  const [backendStatus, setBackendStatus] = useState('checking')
  const [wakeSeconds, setWakeSeconds] = useState(0)
  const healthCheckInterval = useRef(null)
  const wakeTimerRef = useRef(null)

  const toast = useCallback((msg, sub='', type='success') => {
    const id = ++toastId.current
    setToasts(p => [...p, { id, msg, sub, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 5000)
  }, [])

  const removeToast = useCallback(id => setToasts(p => p.filter(t => t.id !== id)), [])

  const openAuthModal = useCallback((mode = 'login', pendingAction = null) => {
    setAuthModalMode(mode)
    setAuthPendingAction(() => pendingAction)
    setAuthModalOpen(true)
  }, [])

  const closeAuthModal = useCallback(() => {
    setAuthModalOpen(false)
    setAuthPendingAction(null)
  }, [])

  const saveAuth = useCallback((accessToken, name) => {
    localStorage.setItem('cs_token', accessToken)
    localStorage.setItem('cs_user',  name)
    setToken(accessToken)
    setUserName(name)
    setIsAuthed(true)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('cs_token')
    localStorage.removeItem('cs_user')
    setToken('')
    setUserName('')
    setIsAuthed(false)
    setRecentJobs([])
    setDashStats(null)
    setJobResults(null)
    setCurrentJobId(null)
    setUploadedFiles([])
    setPage('dashboard')
  }, [])

  const getToken = useCallback(() => localStorage.getItem('cs_token') || '', [])

  // Health check logic for cold start detection
  const checkHealth = useCallback(async () => {
    try {
      await api.health({ timeout: 12000 })
      setBackendStatus('connected')
      setWakeSeconds(0)
      if (wakeTimerRef.current) {
        clearInterval(wakeTimerRef.current)
        wakeTimerRef.current = null
      }
      return true
    } catch {
      // Backend is either sleeping or offline
      setBackendStatus(prev => (prev === 'connected' ? 'waking' : prev === 'checking' ? 'waking' : prev))
      return false
    }
  }, [])

  // Wake timer ticker
  useEffect(() => {
    if (backendStatus === 'waking') {
      if (!wakeTimerRef.current) {
        wakeTimerRef.current = setInterval(() => {
          setWakeSeconds(s => s + 1)
        }, 1000)
      }
    } else {
      if (wakeTimerRef.current) {
        clearInterval(wakeTimerRef.current)
        wakeTimerRef.current = null
      }
    }
    return () => {
      if (wakeTimerRef.current) clearInterval(wakeTimerRef.current)
    }
  }, [backendStatus])

  // Periodic health check
  useEffect(() => {
    checkHealth()
    healthCheckInterval.current = setInterval(() => {
      checkHealth()
    }, backendStatus === 'waking' ? 4000 : 30000)

    return () => {
      if (healthCheckInterval.current) clearInterval(healthCheckInterval.current)
    }
  }, [checkHealth, backendStatus])

  const refreshDashboard = useCallback(async () => {
    const tk = localStorage.getItem('cs_token')
    if (!tk) return
    setLoadingDash(true)
    try {
      const [jobs, stats] = await Promise.all([api.jobs(tk), api.stats(tk)])
      setRecentJobs(jobs || [])
      setDashStats(stats || null)
    } catch (err) {
      if (err.message && err.message.includes('401')) logout()
    } finally {
      setLoadingDash(false)
    }
  }, [logout])

  useEffect(() => { if (isAuthed) refreshDashboard() }, [isAuthed, refreshDashboard])

  return (
    <Ctx.Provider value={{
      token, userName, isAuthed, saveAuth, logout, getToken,
      page, setPage,
      uploadedFiles, setUploadedFiles,
      threshold, setThreshold,
      currentJobId, setCurrentJobId,
      jobProgress, setJobProgress,
      jobResults, setJobResults,
      recentJobs, dashStats, loadingDash, refreshDashboard,
      toasts, toast, removeToast,
      // Auth modal
      authModalOpen, authModalMode, openAuthModal, closeAuthModal, authPendingAction,
      // Backend status & cold start
      backendStatus, wakeSeconds, retryBackendConnection: checkHealth, BASE_URL,
    }}>
      {children}
    </Ctx.Provider>
  )
}

export const useApp = () => useContext(Ctx)
