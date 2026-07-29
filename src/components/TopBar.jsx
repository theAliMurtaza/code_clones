import { useApp } from '../context/AppContext'

const TITLES = {
  dashboard: 'Dashboard',
  upload:    'FR-01 · Code Ingestion & Management',
  preprocess:'FR-02/03 · Tokenization & Embedding',
  detection: 'FR-04 · Clone Detection Engine',
  results:   'FR-09 · Results, Reports & Clone Viewer',
  benchmark: 'FR-10 · Benchmarking & Evaluation',
  account:   'FR-08 · My Projects',
}

export function TopBar() {
  const { page, setPage, toast } = useApp()
  return (
    <div className="h-14 min-h-[56px] bg-surface border-b border-b1 flex items-center px-6 gap-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="text-[10px] font-mono text-t3">clonescope</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-t3 flex-shrink-0">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
        <span className="text-sm font-semibold text-t1 truncate">{TITLES[page] || page}</span>
      </div>

      {/* NFR badge */}
      <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-success/20 bg-success/5">
        <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse2"/>
        <span className="text-[10px] font-mono text-success">NFR-05 · 99.8% uptime</span>
      </div>

      {/* Actions */}
      <button
        onClick={() => toast('Async job queued', 'FR-05-02: Notification will be sent on completion', 'info')}
        className="w-9 h-9 flex items-center justify-center rounded-lg border border-b1 text-t2 hover:border-accent/40 hover:text-accent transition-all">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 01-3.46 0"/>
        </svg>
      </button>
      <button
        onClick={() => setPage('upload')}
        className="btn btn-primary btn-sm">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        New Analysis
      </button>
    </div>
  )
}

export function Toasts() {
  const { toasts, removeToast } = useApp()
  const icon = { success:'✓', info:'ℹ', warn:'⚠', error:'✕' }
  const color = { success:'border-success/40 text-success', info:'border-accent/40 text-accent', warn:'border-amber/40 text-amber', error:'border-rose/40 text-rose' }
  return (
    <div className="fixed bottom-5 right-5 flex flex-col gap-2 z-50">
      {toasts.map(t => (
        <div key={t.id} className={`flex items-start gap-3 px-4 py-3 bg-s2 border rounded-xl min-w-[260px] max-w-xs shadow-2xl animate-slideIn ${color[t.type] || color.success}`}>
          <span className="text-base leading-none mt-0.5">{icon[t.type] || '✓'}</span>
          <div className="flex-1">
            <div className="text-xs font-semibold text-t1">{t.msg}</div>
            {t.sub && <div className="text-[10px] text-t3 font-mono mt-0.5">{t.sub}</div>}
          </div>
          <button onClick={() => removeToast(t.id)} className="text-t3 hover:text-t1 text-lg leading-none mt-0.5">×</button>
        </div>
      ))}
    </div>
  )
}
