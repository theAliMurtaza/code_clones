import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { api } from '../utils/api'
import { Spinner } from './UI'

export default function AuthModal({ isOpen, onClose, onSuccess, initialMode = 'login' }) {
  const { saveAuth, toast, backendStatus, retryBackendConnection } = useApp()
  const [mode, setMode] = useState(initialMode)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (!isOpen) return null

  const submit = async (e) => {
    if (e) e.preventDefault()
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
      if (onSuccess) onSuccess(data)
      onClose()
    } catch (err) {
      setError(err.message || 'Authentication failed.')
    } finally {
      setLoading(false)
    }
  }

  const onKey = e => { if (e.key === 'Enter') submit() }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div 
        className="w-full max-w-[420px] bg-surface rounded-2xl border border-b1 shadow-[0_25px_60px_rgba(0,0,0,.7)] overflow-hidden animate-fadeUp"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 pt-6 pb-4 border-b border-b1 bg-s2/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-accent flex items-center justify-center shadow-md shadow-accent/20">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
              </svg>
            </div>
            <div>
              <h3 className="text-base font-bold text-t1 leading-tight">
                {mode === 'login' ? 'Sign In to Continue' : 'Create Account'}
              </h3>
              <p className="text-[11px] text-t3 font-mono">Sign in is required to upload & detect clones</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-t3 hover:text-t1 hover:bg-s2 flex items-center justify-center transition-colors text-lg"
          >
            ×
          </button>
        </div>

        {/* Server waking banner if cold starting */}
        {backendStatus === 'waking' && (
          <div className="bg-amber/10 border-b border-amber/20 px-4 py-2 flex items-center justify-between text-xs text-amber font-mono">
            <span className="flex items-center gap-2">
              <Spinner size={12} className="text-amber" />
              Free tier server is spinning up (~1-2m)…
            </span>
            <button onClick={retryBackendConnection} className="underline text-[10px] hover:text-amber/80">
              Check
            </button>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6">
          <div className="flex gap-1 mb-5 p-1 bg-s2 rounded-xl">
            {['login', 'register'].map(m => (
              <button 
                key={m} 
                type="button"
                onClick={() => { setMode(m); setError('') }}
                className={'flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ' + 
                  (mode === m ? 'bg-surface text-t1 shadow-sm' : 'text-t3 hover:text-t2')}
              >
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-3.5">
            {mode === 'register' && (
              <div>
                <label className="lbl">Full Name</label>
                <input 
                  className="inp" 
                  value={name} 
                  onChange={e => setName(e.target.value)} 
                  onKeyDown={onKey} 
                  placeholder="Your full name" 
                  autoFocus
                />
              </div>
            )}
            <div>
              <label className="lbl">Email Address</label>
              <input 
                className="inp" 
                type="email" 
                value={email} 
                onChange={e => setEmail(e.target.value)} 
                onKeyDown={onKey} 
                placeholder="you@example.com" 
                autoFocus={mode === 'login'}
              />
            </div>
            <div>
              <label className="lbl">Password</label>
              <input 
                className="inp" 
                type="password" 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
                onKeyDown={onKey} 
                placeholder="At least 6 characters"
              />
            </div>

            {error && (
              <div className="px-3.5 py-2.5 border border-rose/20 rounded-lg text-xs text-rose font-mono leading-relaxed" style={{ background: 'rgba(225,29,72,.05)' }}>
                {error}
              </div>
            )}

            <button 
              type="submit" 
              disabled={loading} 
              className="btn btn-primary w-full justify-center mt-2 btn-lg"
            >
              {loading && <Spinner size={15}/>}
              {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          {/* Quick guest reminder */}
          <p className="mt-4 text-[11px] text-center text-t3 font-mono">
            Files and clone results are private to your account.
          </p>
        </div>
      </div>
    </div>
  )
}
