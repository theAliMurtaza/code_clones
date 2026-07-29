import { useState } from 'react'

export function Btn({ children, variant='primary', size='', onClick, disabled, className='' }) {
  const v = { primary:'btn-primary', ghost:'btn-ghost', danger:'btn-danger', violet:'btn-violet' }[variant] || 'btn-primary'
  const s = { sm:'btn-sm', lg:'btn-lg', '':'' }[size] || ''
  return (
    <button className={`btn ${v} ${s} ${className}`} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  )
}

export function Badge({ children, type }) {
  const cls = {
    'Type-1':'badge-type1','Type-2':'badge-type2','Type-3':'badge-type3','Type-4':'badge-type4',
    green:'badge-green', blue:'badge-blue', amber:'badge-amber', rose:'badge-rose',
  }[type] || 'badge bg-s3 text-t2'
  return <span className={`badge ${cls}`}>{children}</span>
}

export function Card({ children, className='', style }) {
  return <div className={`card ${className}`} style={style}>{children}</div>
}

export function CardHdr({ children }) { return <div className="card-header">{children}</div> }
export function CardTitle({ children }) { return <div className="card-title">{children}</div> }
export function CardBody({ children, className='' }) { return <div className={`card-body ${className}`}>{children}</div> }

export function Label({ children }) { return <label className="lbl">{children}</label> }

export function Input({ label, value, onChange, placeholder, type='text', className='' }) {
  return (
    <div className="mb-4">
      {label && <Label>{label}</Label>}
      <input type={type} className={`inp ${className}`} value={value}
        onChange={e => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  )
}

export function Select({ label, value, onChange, options, className='' }) {
  return (
    <div className="mb-4">
      {label && <Label>{label}</Label>}
      <select className={`sel ${className}`} value={value} onChange={e => onChange(e.target.value)}>
        {options.map(o => <option key={o.value??o} value={o.value??o}>{o.label??o}</option>)}
      </select>
    </div>
  )
}

export function Toggle({ label, sublabel, checked, onChange }) {
  return (
    <div className="toggle-row">
      <div>
        <div className="text-xs text-t1">{label}</div>
        {sublabel && <div className="text-[10px] text-t3 font-mono mt-0.5">{sublabel}</div>}
      </div>
      <label className="toggle-track cursor-pointer flex-shrink-0">
        <input type="checkbox" className="absolute opacity-0 w-0 h-0" checked={checked}
          onChange={e => onChange(e.target.checked)} />
        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all duration-200
          ${checked ? 'left-[18px]' : 'left-0.5'}`} />
      </label>
    </div>
  )
}

export function Range({ label, value, onChange, min=0, max=100, sublabel }) {
  return (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1.5">
        <Label>{label}</Label>
        <span className="text-xs font-bold font-mono text-accent">{value}%</span>
      </div>
      {sublabel && <div className="text-[10px] text-t3 font-mono mb-2">{sublabel}</div>}
      <input type="range" min={min} max={max} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1 rounded-full bg-b2 appearance-none cursor-pointer accent-accent" />
    </div>
  )
}

export function SectionH({ children }) {
  return <div className="section-h">{children}</div>
}

export function MetricRing({ value, label, color, size=80 }) {
  const r = 30, c = 2 * Math.PI * r
  const off = c - (value * c)
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox="0 0 80 80" style={{ transform:'rotate(-90deg)' }}>
          <circle cx="40" cy="40" r={r} fill="none" stroke="#1a2332" strokeWidth="7"/>
          <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="7"
            strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"
            style={{ transition:'stroke-dashoffset 1s ease' }}/>
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-sm font-bold font-mono" style={{ color }}>
          {value.toFixed(2)}
        </div>
      </div>
      <div className="text-[10px] font-mono text-t3 uppercase tracking-wider text-center">{label}</div>
    </div>
  )
}

export function Spinner({ size=16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="animate-spin">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeOpacity=".2"/>
      <path d="M12 2a10 10 0 010 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}

export function ProgressBar({ pct, color='accent' }) {
  return (
    <div className="w-full h-1.5 bg-b2 rounded-full overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-500 bg-${color}`} style={{ width:`${pct}%` }}/>
    </div>
  )
}

export function Stat({ label, value, color, sub }) {
  return (
    <div className="card p-5 relative overflow-hidden group hover:border-b2 transition-colors">
      <div className="absolute top-0 left-0 right-0 h-[2px]" style={{ background: color }}/>
      <div className="text-[10px] font-mono text-t3 uppercase tracking-wider mb-2">{label}</div>
      <div className="text-3xl font-bold tracking-tight mb-1" style={{ color }}>{value}</div>
      {sub && <div className="text-[11px] text-t3 font-mono">{sub}</div>}
    </div>
  )
}
