import { useApp } from '../context/AppContext'

const TITLES = {
  dashboard: 'Dashboard',
  upload:    'Upload Code',
  detection: 'Processing Analysis',
  results:   'Clone Detection Results',
  benchmark: 'Benchmarks & Comparison',
  account:   'My Projects',
}

export function TopBar() {
  const { page, setPage } = useApp()
  return (
    <div className="h-14 min-h-[56px] bg-surface border-b border-b1 flex items-center px-6 gap-4">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="text-[10px] font-mono text-t3 hidden md:block">clonescope</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" className="text-t3 flex-shrink-0 hidden md:block">
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span className="text-sm font-semibold text-t1 truncate">
          {TITLES[page] || page}
        </span>
      </div>
      <button onClick={() => setPage('upload')} className="btn btn-primary btn-sm">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        New Analysis
      </button>
    </div>
  )
}

export function Toasts() {
  const { toasts, removeToast } = useApp()
  const icon  = { success: '✓', info: 'ℹ', warn: '⚠', error: '✕' }
  const color = {
    success: 'border-success/30 text-success',
    info:    'border-accent/30  text-accent',
    warn:    'border-amber/30   text-amber',
    error:   'border-rose/30    text-rose',
  }
  return (
    <div className="fixed bottom-5 right-5 flex flex-col gap-2 z-50">
      {toasts.map(t => (
        <div key={t.id}
          className={`flex items-start gap-3 px-4 py-3 bg-s2 border rounded-xl min-w-[260px] max-w-sm shadow-2xl animate-slideIn ${color[t.type] || color.success}`}>
          <span className="text-base leading-none mt-0.5 flex-shrink-0">{icon[t.type] || '✓'}</span>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-t1">{t.msg}</div>
            {t.sub && <div className="text-[10px] text-t3 font-mono mt-0.5">{t.sub}</div>}
          </div>
          <button onClick={() => removeToast(t.id)} className="text-t3 hover:text-t1 text-lg leading-none flex-shrink-0">x</button>
        </div>
      ))}
    </div>
  )
}
