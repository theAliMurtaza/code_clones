import { useApp } from '../context/AppContext'

const NAV = [
  { section:'Overview', items:[
    { id:'dashboard', label:'Dashboard',       icon:'M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z' },
  ]},
  { section:'Pipeline', items:[
    { id:'upload',     label:'Code Ingestion', icon:'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12' },
    { id:'preprocess', label:'Tokenizer',     icon:'M16 18l6-6-6-6M8 6l-6 6 6 6' },
    { id:'detection',  label:'Clone Detection', icon:'M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z' },
  ]},
  { section:'Analysis', items:[
    { id:'results',    label:'Results',         bw:true, icon:'M18 20V10M12 20V4M6 20v-6' },
    { id:'benchmark',  label:'Benchmarking',    icon:'M22 12h-4l-3 9L9 3l-3 9H2' },
  ]},
  { section:'Account', items:[
    { id:'account',    label:'My Projects',    icon:'M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z' },
  ]},
]

export default function Sidebar() {
  const { page, setPage, toast } = useApp()

  return (
    <aside className="w-[220px] min-w-[220px] bg-surface border-r border-b1 flex flex-col overflow-hidden">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-b1">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center flex-shrink-0 glow-accent">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#07090d" strokeWidth="2.5" strokeLinecap="round">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
          </div>
          <div>
            <div className="text-sm font-bold text-t1 tracking-tight">CloneScope</div>
            <div className="text-[9px] font-mono text-t3 tracking-wider mt-0.5">LLM · v2.1.0</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 overflow-y-auto space-y-5">
        {NAV.map(sec => (
          <div key={sec.section}>
            <div className="text-[9px] font-bold tracking-[.15em] uppercase text-t3 px-3 mb-2 font-mono">{sec.section}</div>
            {sec.items.map(item => {
              const active = page === item.id
              return (
                <button key={item.id} onClick={() => setPage(item.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg mb-0.5 transition-all text-left relative
                    ${active
                      ? 'bg-accent/10 text-accent'
                      : 'text-t2 hover:bg-s3 hover:text-t1'}`}>
                  {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent rounded-r"/>}
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 flex-shrink-0">
                    <path d={item.icon}/>
                  </svg>
                  <span className="text-xs font-medium flex-1">{item.label}</span>
                  {item.badge && (
                    <span className={`text-[8px] font-bold font-mono px-1.5 py-0.5 rounded-full
                      ${item.bw ? 'bg-amber/20 text-amber' : 'bg-accent/15 text-accent'}`}>
                      {item.badge}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        ))}
      </nav>

      {/* NFR status strip */}
      <div className="px-3 py-2 border-t border-b1">
        <div className="text-[9px] font-mono text-t3 mb-1.5 tracking-wider">SYSTEM STATUS</div>
        {[
          { label:'Uptime', val:'99.8%', ok:true },
          { label:'Latency', val:'4.2s', ok:true },
          { label:'Cache', val:'Redis', ok:true },
        ].map(s => (
          <div key={s.label} className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-t3 font-mono">{s.label}</span>
            <div className="flex items-center gap-1">
              <div className={`w-1.5 h-1.5 rounded-full ${s.ok ? 'bg-success animate-pulse2' : 'bg-rose'}`}/>
              <span className={`text-[10px] font-mono font-bold ${s.ok ? 'text-success' : 'text-rose'}`}>{s.val}</span>
            </div>
          </div>
        ))}
      </div>

      {/* User */}
      <div className="px-3 pb-3">
        <div className="flex items-center gap-2.5 p-2.5 bg-s2 rounded-lg border border-b1">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-violet flex items-center justify-center text-[10px] font-bold text-bg flex-shrink-0">AK</div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-t1 truncate">Ali Murtaza</div>
            <div className="text-[9px] text-t3 font-mono">researcher · pro</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
