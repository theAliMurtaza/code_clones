import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import { api } from '../utils/api'
import { Spinner } from '../components/UI'

export default function Login() {
  const { saveAuth, setPage, toast } = useApp()
  const [mode,      setMode]      = useState('login')
  const [name,      setName]      = useState('')
  const [email,     setEmail]     = useState('')
  const [password,  setPassword]  = useState('')
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState('')
  const [backendOk, setBackendOk] = useState(null)

  useEffect(() => {
    api.health().then(() => setBackendOk(true)).catch(() => setBackendOk(false))
  }, [])

  const submit = async () => {
    setError('')
    if (!email.trim() || !password.trim()) { setError('Email and password are required.'); return }
    if (mode === 'register' && !name.trim()) { setError('Name is required.'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }
    setLoading(true)
    try {
      const data = mode === 'register'
        ? await api.register(name.trim(), email.trim(), password)
        : await api.login(email.trim(), password)
      saveAuth(data.access_token, data.name)
      toast('Welcome, ' + data.name + '!', mode === 'register' ? 'Account created' : 'Signed in')
      setPage('dashboard')
    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  const onKey = e => { if (e.key === 'Enter') submit() }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-[380px]">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-accent flex items-center justify-center mx-auto mb-4 shadow-lg shadow-accent/20">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-t1 tracking-tight">CloneScope</h1>
          <p className="text-xs text-t3 font-mono mt-1">GraphCodeBERT · Code Clone Detection</p>
        </div>
        <div className="card p-8 shadow-lg">
          <div className="flex gap-1 mb-6 p-1 bg-s2 rounded-xl">
            {['login','register'].map(m => (
              <button key={m} onClick={() => { setMode(m); setError('') }}
                className={'flex-1 py-2 text-xs font-semibold rounded-lg transition-all ' + (mode===m ? 'bg-surface text-t1 shadow-sm' : 'text-t3 hover:text-t2')}>
                {m === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>
          <div className="space-y-4">
            {mode === 'register' && (
              <div><label className="lbl">Full Name</label>
                <input className="inp" value={name} onChange={e=>setName(e.target.value)} onKeyDown={onKey} placeholder="Your full name" autoFocus/>
              </div>
            )}
            <div><label className="lbl">Email Address</label>
              <input className="inp" type="email" value={email} onChange={e=>setEmail(e.target.value)} onKeyDown={onKey} placeholder="you@example.com" autoFocus={mode==='login'}/>
            </div>
            <div><label className="lbl">Password</label>
              <input className="inp" type="password" value={password} onChange={e=>setPassword(e.target.value)} onKeyDown={onKey} placeholder="At least 6 characters"/>
            </div>
          </div>
          {error && <div className="mt-4 px-4 py-3 border border-rose/20 rounded-lg text-xs text-rose font-mono leading-relaxed" style={{background:'rgba(225,29,72,.05)'}}>{error}</div>}
          <button onClick={submit} disabled={loading} className="btn btn-primary w-full justify-center mt-5 btn-lg">
            {loading && <Spinner size={15}/>}
            {loading ? 'Please wait…' : mode==='login' ? 'Sign In' : 'Create Account'}
          </button>
        </div>
        <div className="flex items-center justify-center gap-2 mt-4 text-[10px] font-mono">
          <div className={'w-1.5 h-1.5 rounded-full flex-shrink-0 ' + (backendOk===null?'bg-t3 animate-pulse2':backendOk?'bg-success animate-pulse2':'bg-rose')}/>
          <span className={backendOk===null?'text-t3':backendOk?'text-success':'text-rose'}>
            {backendOk===null?'Connecting to backend…':backendOk?'Backend connected':'Backend offline - start uvicorn on port 8000'}
          </span>
        </div>
      </div>
    </div>
  )
}
