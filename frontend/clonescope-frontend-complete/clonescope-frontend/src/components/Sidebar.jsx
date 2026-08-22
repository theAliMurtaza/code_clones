import { useApp } from '../context/AppContext'

const NAV = [
  {
    section: 'Overview',
    items: [
      { id: 'dashboard', label: 'Dashboard',       icon: 'M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z' },
    ],
  },
  {
    section: 'Analysis',
    items: [
      { id: 'upload',    label: 'Upload Code',     icon: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12' },
      { id: 'detection', label: 'Processing',      icon: 'M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83' },
      { id: 'results',   label: 'Clone Results',   icon: 'M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18' },
    ],
  },
  {
    section: 'Insights',
    items: [
      { id: 'benchmark', label: 'Benchmarks',      icon: 'M22 12h-4l-3 9L9 3l-3 9H2' },
      { id: 'account',   label: 'My Projects',     icon: 'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z' },
    ],
  },
]

export default function Sidebar() {
  const { page, setPage, userName, logout } = useApp()

  return (
    <aside className="w-56 min-w-[224px] bg-surface border-r border-b1 flex flex-col overflow-hidden">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-b1 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center flex-shrink-0 shadow-lg shadow-accent/25">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="#07090d" strokeWidth="2.5" strokeLinecap="round">
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
        </div>
        <div>
          <div className="text-sm font-bold text-t1 tracking-tight">CloneScope</div>
          <div className="text-[9px] font-mono text-t3 tracking-wide mt-0.5">GraphCodeBERT</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto space-y-5">
        {NAV.map(sec => (
          <div key={sec.section}>
            <div className="text-[9px] font-bold tracking-[.15em] uppercase text-t3 px-3 mb-2 font-mono">
              {sec.section}
            </div>
            {sec.items.map(item => {
              const active = page === item.id
              return (
                <button key={item.id} onClick={() => setPage(item.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg mb-0.5
                    text-left text-xs font-medium transition-all relative
                    ${active ? 'bg-accent/10 text-accent' : 'text-t2 hover:bg-s3 hover:text-t1'}`}>
                  {active && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent rounded-r" />
                  )}
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                    className="w-4 h-4 flex-shrink-0">
                    <path d={item.icon} />
                  </svg>
                  <span className="flex-1">{item.label}</span>
                </button>
              )
            })}
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="px-3 pb-3 border-t border-b1 pt-3">
        <div className="flex items-center gap-2.5 p-2.5 bg-s2 rounded-lg border border-b1">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-violet
            flex items-center justify-center text-[10px] font-bold text-bg flex-shrink-0">
            {userName ? userName[0].toUpperCase() : 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-t1 truncate">{userName || 'User'}</div>
            <div className="text-[9px] text-t3 font-mono">researcher</div>
          </div>
          <button onClick={logout} title="Sign out"
            className="text-t3 hover:text-rose transition-colors p-0.5">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  )
}
