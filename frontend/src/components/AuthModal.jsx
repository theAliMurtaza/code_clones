import { useEffect, useRef, useState } from 'react'
import { GitBranch, Files, ScanLine, FolderCheck, X, Eye, EyeOff } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { api } from '../utils/api'

let googleScript
function loadGoogle() {
  if (window.google?.accounts?.id) return Promise.resolve()
  if (!googleScript) googleScript = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    const fail = () => { clearTimeout(timer); script.remove(); googleScript = null; reject(new Error('Google could not load.')) }
    const timer = setTimeout(fail, 12000)
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => { clearTimeout(timer); resolve() }
    script.onerror = fail
    document.head.appendChild(script)
  })
  return googleScript
}

export default function AuthModal({ isOpen, onClose, onSuccess, initialMode = 'login' }) {
  const { saveAuth, toast, backendStatus } = useApp()
  const [mode, setMode] = useState(initialMode)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [googleStatus, setGoogleStatus] = useState('loading')
  const googleButton = useRef(null)
  const dialog = useRef(null)
  const handlers = useRef({})
  const submitLock = useRef(false)
  const finishSignIn = data => {
    saveAuth(data.access_token, data.name)
    onClose()
    toast(`Welcome, ${data.name}`, mode === 'register' ? 'Your account is ready.' : 'You’re signed in.')
    onSuccess?.(data)
  }
  handlers.current = { finishSignIn, onClose, loading, isOpen }
  useEffect(() => {
    if (!isOpen) return
    setMode(initialMode); setError(''); setPassword(''); setShowPassword(false); setLoading(false)
    const previous = document.activeElement
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialog.current?.querySelector('input')?.focus()
    const keyboard = event => {
      if (event.key === 'Escape' && !handlers.current.loading) handlers.current.onClose()
      if (event.key !== 'Tab') return
      const controls = [...dialog.current.querySelectorAll('button:not(:disabled), input, a[href], iframe, [tabindex="0"]')].filter(el => el.getClientRects().length)
      const first = controls[0], last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    document.addEventListener('keydown', keyboard)
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', keyboard); previous?.focus() }
  }, [isOpen, initialMode])
  useEffect(() => {
    if (!isOpen) return
    let active = true
    setGoogleStatus('loading')
    const nonce = crypto.randomUUID() + crypto.randomUUID()
    api.googleConfig().then(async config => {
      if (!active) return
      if (!config.client_id) { setGoogleStatus('unavailable'); return }
      await loadGoogle()
      if (!active || !googleButton.current) return
      window.google.accounts.id.initialize({
        client_id: config.client_id, nonce, auto_select: false,
        callback: async ({ credential }) => {
          if (!active || !handlers.current.isOpen || submitLock.current) return
          submitLock.current = true; setLoading(true); setError('')
          try { const data = await api.googleLogin(credential, nonce); if (active) handlers.current.finishSignIn(data) }
          catch (err) { if (active) setError(err.message) }
          finally { submitLock.current = false; if (active) setLoading(false) }
        },
      })
      window.google.accounts.id.renderButton(googleButton.current, {
        type: 'standard', theme: 'filled_black', size: 'large', text: 'continue_with',
        shape: 'rectangular', width: Math.min(400, googleButton.current.clientWidth),
      })
      setGoogleStatus('ready')
    }).catch(() => { if (active) setGoogleStatus('unavailable') })
    return () => { active = false; window.google?.accounts?.id?.cancel() }
  }, [isOpen])
  const submit = async event => {
    event.preventDefault()
    if (submitLock.current) return
    setError(''); submitLock.current = true; setLoading(true)
    try {
      const data = mode === 'register'
        ? await api.register(name.trim(), email.trim(), password)
        : await api.login(email.trim(), password)
      if (handlers.current.isOpen) finishSignIn(data)
    } catch (err) { setError(err.message || 'We couldn’t sign you in. Please try again.') }
    finally { submitLock.current = false; setLoading(false) }
  }
  if (!isOpen) return null
  return <div className="auth-screen">
    <div ref={dialog} className="auth-layout" role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <button className="auth-close" aria-label="Close sign-in" onClick={onClose} disabled={loading}><X size={20}/></button>
      <section className="auth-story" aria-label="About CloneScope">
        <div className="auth-brand"><span><GitBranch size={25}/></span><div>CloneScope<small>A clearer view of your code</small></div></div>
        <h1>Find repeated code.<br/><em>Make room for better.</em></h1>
        <p className="auth-intro">Bring your files together. See where logic repeats, compare it side by side, and decide what to improve.</p>
        <div className="auth-code-preview" aria-label="Illustrative code comparison">
          <div className="auth-code-heading"><span className="window-dots">● ● ●</span><span>order_total.py</span><span className="preview-label">Example</span></div>
          <pre><span className="code-muted">01  </span><span className="code-keyword">def</span>{' order_total(prices):\n'}<span className="code-muted">02  </span>{'    total = 0\n'}<span className="code-muted">03  </span>{'    for price in prices:\n'}<span className="code-muted">04  </span><span className="code-highlight">{'        total += price'}</span>{'\n'}<span className="code-muted">05  </span>{'    return total'}</pre>
          <div className="auth-code-footer"><ScanLine size={15}/> Compare the logic, not just the names.</div>
        </div>
        <div className="auth-features">
          {[[Files, 'Files or folders', 'Compare within and across files.'], [ScanLine, 'Side-by-side review', 'See matching code in context.'], [FolderCheck, 'Saved analyses', 'Return to your results anytime.']].map(([Icon, title, detail]) => <div key={title}><Icon size={20}/><strong>{title}</strong><p>{detail}</p></div>)}
        </div>
      </section>
      <section className="auth-form-panel"><div className="auth-form-inner">
        <span className="auth-eyebrow">YOUR CODE, IN FOCUS</span>
        <h2 id="auth-title">{mode === 'login' ? 'Welcome back' : 'Start with a fresh perspective'}</h2>
        <p className="auth-subtitle">{mode === 'login' ? 'Sign in to pick up where you left off.' : 'Create your account and run your first analysis.'}</p>
        <div className="google-button-host" ref={googleButton} aria-label="Google sign-in" style={loading ? { pointerEvents: 'none', opacity: .5 } : undefined}/>
        {googleStatus !== 'ready' && <button className="google-placeholder" type="button" disabled><span className="google-letter">G</span>Continue with Google</button>}
        {googleStatus === 'unavailable' && <p className="auth-provider-note">Google sign-in is not available yet. You can use email below.</p>}
        <div className="auth-divider"><span>or continue with email</span></div>
        <form onSubmit={submit}><fieldset disabled={loading}>
          {mode === 'register' && <label>Full name<input required maxLength={200} autoComplete="name" value={name} onChange={e => setName(e.target.value)} placeholder="Your name"/></label>}
          <label>Email address<input required type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com"/></label>
          <label>Password<div className="auth-password"><input required minLength={mode === 'register' ? 6 : undefined} maxLength={128} type={showPassword ? 'text' : 'password'} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} placeholder={mode === 'register' ? 'At least 6 characters' : 'Enter your password'}/><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}</button></div></label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          {backendStatus === 'waking' && <p className="auth-provider-note">We’re reconnecting. Sign-in may take a little longer.</p>}
          <button className="auth-submit" type="submit">{loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
        </fieldset></form>
        <p className="auth-switch">{mode === 'login' ? 'New to CloneScope?' : 'Already have an account?'} <button disabled={loading} onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); setPassword('') }}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></p>
        <p className="auth-footnote">Your analyses, organized in one place.</p>
      </div></section>
    </div>
  </div>
}
