// Shared primitive components — buttons, cards, badges, inputs, etc.

export function Btn({ children, variant = 'primary', size = '', onClick, disabled, className = '', type = 'button' }) {
  const v = { primary: 'btn-primary', ghost: 'btn-ghost', danger: 'btn-danger', violet: 'btn-violet' }[variant] || 'btn-primary'
  const s = size === 'sm' ? 'btn-sm' : size === 'lg' ? 'btn-lg' : ''
  return (
    <button type={type} className={`btn ${v} ${s} ${className}`} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  )
}

export function Badge({ children, type = 'blue' }) {
  const cls = {
    'Type-1': 'badge-type1', 'Type-2': 'badge-type2',
    'Type-3': 'badge-type3', 'Type-4': 'badge-type4',
    green: 'badge-green', blue: 'badge-blue',
    amber: 'badge-amber', rose: 'badge-rose',
  }[type] || 'badge bg-s3 text-t2'
  return <span className={`badge ${cls}`}>{children}</span>
}

export function Card({ children, className = '', style }) {
  return <div className={`card ${className}`} style={style}>{children}</div>
}

export function CardHeader({ children }) {
  return <div className="card-header">{children}</div>
}

export function CardTitle({ children }) {
  return <div className="card-title">{children}</div>
}

export function CardBody({ children, className = '' }) {
  return <div className={`card-body ${className}`}>{children}</div>
}

export function SectionH({ children }) {
  return <div className="section-h">{children}</div>
}

export function Spinner({ size = 16, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      className={`animate-spin ${className}`}>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeOpacity=".2" />
      <path d="M12 2a10 10 0 010 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function MetricRing({ value, label, color, size = 80 }) {
  const r = 30; const c = 2 * Math.PI * r
  return (
    <div className="flex flex-col items-center gap-2">
      <div style={{ width: size, height: size, position: 'relative' }}>
        <svg width={size} height={size} viewBox="0 0 80 80" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="40" cy="40" r={r} fill="none" stroke="#1a2332" strokeWidth="7" />
          <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="7"
            strokeDasharray={c} strokeDashoffset={c - value * c} strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s ease' }} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-sm font-bold font-mono"
          style={{ color }}>{value.toFixed(2)}</div>
      </div>
      <div className="text-[10px] font-mono text-t3 uppercase tracking-wider text-center leading-tight">{label}</div>
    </div>
  )
}

export function ProgressBar({ pct, color = '#00d4ff', animated = false }) {
  return (
    <div className="w-full h-1.5 bg-b2 rounded-full overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-500 ${animated ? 'animate-pulse2' : ''}`}
        style={{ width: `${pct}%`, background: color }} />
    </div>
  )
}

export function StatCard({ label, value, color, sub }) {
  return (
    <div className="card p-5 relative overflow-hidden hover:border-b2 transition-colors">
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: color }} />
      <div className="text-[10px] font-mono text-t3 uppercase tracking-wider mb-2">{label}</div>
      <div className="text-3xl font-bold tracking-tight mb-1" style={{ color }}>{value}</div>
      {sub && <div className="text-[11px] text-t3 font-mono">{sub}</div>}
    </div>
  )
}

export function Toggle({ label, checked, onChange }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-b1 last:border-0">
      <span className="text-xs text-t2">{label}</span>
      <label className="relative w-9 h-5 cursor-pointer flex-shrink-0">
        <input type="checkbox" className="absolute opacity-0 w-0 h-0"
          checked={checked} onChange={e => onChange(e.target.checked)} />
        <div className={`absolute inset-0 rounded-full border transition-all duration-200
          ${checked ? 'bg-accent/80 border-accent/60' : 'bg-s3 border-b2'}`} />
        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all duration-200
          ${checked ? 'left-[18px]' : 'left-0.5'}`} />
      </label>
    </div>
  )
}

export function EmptyState({ icon, title, sub, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-14 h-14 rounded-2xl bg-s3 border border-b1 flex items-center justify-center mb-4 text-t3">
        {icon}
      </div>
      <div className="text-sm font-semibold text-t2 mb-1">{title}</div>
      {sub && <div className="text-xs text-t3 mb-4 max-w-xs">{sub}</div>}
      {action}
    </div>
  )
}
