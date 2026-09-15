import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { api } from '../utils/api'

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

  const toast = useCallback((msg, sub='', type='success') => {
    const id = ++toastId.current
    setToasts(p => [...p, { id, msg, sub, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 5000)
  }, [])

  const removeToast = useCallback(id => setToasts(p => p.filter(t => t.id !== id)), [])

  const saveAuth = useCallback((accessToken, name) => {
    localStorage.setItem('cs_token', accessToken)
    localStorage.setItem('cs_user',  name)
    setToken(accessToken); setUserName(name); setIsAuthed(true)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('cs_token'); localStorage.removeItem('cs_user')
    setToken(''); setUserName(''); setIsAuthed(false)
    setRecentJobs([]); setDashStats(null); setJobResults(null)
    setCurrentJobId(null); setUploadedFiles([]); setPage('dashboard')
  }, [])

  const getToken = useCallback(() => localStorage.getItem('cs_token') || '', [])

  const refreshDashboard = useCallback(async () => {
    const tk = localStorage.getItem('cs_token')
    if (!tk) return
    setLoadingDash(true)
    try {
      const [jobs, stats] = await Promise.all([api.jobs(tk), api.stats(tk)])
      setRecentJobs(jobs || [])
      setDashStats(stats || null)
    } catch (err) {
      if (err.message.includes('401')) logout()
    } finally {
      setLoadingDash(false)
    }
  }, [logout])

  useEffect(() => { if (isAuthed) refreshDashboard() }, [isAuthed])

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
    }}>
      {children}
    </Ctx.Provider>
  )
}

export const useApp = () => useContext(Ctx)
