import { useEffect } from 'react'
import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useApp } from '../context/AppContext'
import { StatCard, Spinner, Badge, EmptyState } from '../components/UI'
import { WEEKLY_ACTIVITY, STATUS_BADGE, CLONE_TYPE_META } from '../utils/data'

export default function Dashboard() {
  const { recentJobs, dashStats, loadingDash, refreshDashboard, setPage } = useApp()

  useEffect(() => { refreshDashboard() }, [])

  const dist = dashStats ? [
    { type: 'Type-1', n: dashStats.type_distribution?.['Type-1'] ?? 0, color: '#059669' },
    { type: 'Type-2', n: dashStats.type_distribution?.['Type-2'] ?? 0, color: '#2563eb' },
    { type: 'Type-3', n: dashStats.type_distribution?.['Type-3'] ?? 0, color: '#d97706' },
    { type: 'Type-4', n: dashStats.type_distribution?.['Type-4'] ?? 0, color: '#7c3aed' },
  ] : []
  const total = dist.reduce((a, d) => a + d.n, 0)

  const STATS = [
    { label: 'Total Analyses',   value: dashStats?.total_jobs   ?? '—', color: '#2563eb', sub: 'completed jobs' },
    { label: 'Clone Pairs Found',value: dashStats?.total_pairs  ?? '—', color: '#7c3aed', sub: 'across all analyses' },
    { label: 'Code Fragments',   value: dashStats?.total_fragments ?? '—', color: '#059669', sub: 'analyzed fragments' },
    { label: 'Model',            value: 'GCB',                         color: '#d97706', sub: 'GraphCodeBERT' },
  ]

  return (
    <div className="animate-fadeUp space-y-5">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {STATS.map(s => <StatCard key={s.label} {...s} />)}
      </div>

      <div className="grid grid-cols-5 gap-4">
        {/* Recent jobs */}
        <div className="col-span-3 card">
          <div className="card-header">
            <div className="card-title">Recent Analyses</div>
            <div className="flex items-center gap-2">
              <button onClick={refreshDashboard} disabled={loadingDash}
                className="btn btn-ghost btn-sm">
                {loadingDash ? <Spinner size={12}/> : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
                  </svg>
                )}
                Refresh
              </button>
              <button onClick={() => setPage('account')} className="btn btn-ghost btn-sm">View All</button>
            </div>
          </div>
          {loadingDash ? (
            <div className="p-10 flex items-center justify-center gap-3 text-t3 text-sm">
              <Spinner size={16}/> Loading jobs…
            </div>
          ) : recentJobs.length === 0 ? (
            <EmptyState
              icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>}
              title="No analyses yet"
              sub="Upload Python or Java files to detect code clones."
              action={<button onClick={() => setPage('upload')} className="btn btn-primary btn-sm">Start first analysis</button>}
            />
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-b1">
                  {['Files','Pairs','Status','Date',''].map(h => (
                    <th key={h} className="text-left px-5 py-2.5 text-[9px] font-semibold font-mono text-t3 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentJobs.slice(0, 8).map(j => (
                  <tr key={j.id} className="border-b border-b1/50 hover:bg-s2/60 transition-colors cursor-pointer"
                    onClick={() => setPage('account')}>
                    <td className="px-5 py-3 font-medium text-t1 max-w-[180px]">
                      <div className="truncate">{j.files?.join(', ') || 'Analysis'}</div>
                    </td>
                    <td className="px-5 py-3 font-mono text-t2 font-bold">{j.total_pairs ?? '—'}</td>
                    <td className="px-5 py-3">
                      <Badge type={STATUS_BADGE[j.status] ?? 'blue'}>{j.status}</Badge>
                    </td>
                    <td className="px-5 py-3 font-mono text-t3 text-[10px]">
                      {j.created_at?.slice(0, 10) ?? ''}
                    </td>
                    <td className="px-5 py-3">
                      <button onClick={e => { e.stopPropagation(); setPage('account') }}
                        className="btn btn-ghost btn-sm">Open</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Right column */}
        <div className="col-span-2 space-y-4">
          <div className="card">
            <div className="card-header"><div className="card-title">Clone Distribution</div></div>
            <div className="card-body space-y-3">
              {total === 0 ? (
                <p className="text-xs text-t3 font-mono text-center py-4">
                  Run an analysis to see clone breakdown
                </p>
              ) : dist.map(d => (
                <div key={d.type}>
                  <div className="flex justify-between text-[11px] font-mono mb-1.5">
                    <span className="text-t2">{d.type}</span>
                    <span className="font-bold" style={{ color: d.color }}>
                      {Math.round((d.n / total) * 100)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-s3 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${(d.n/total)*100}%`, background: d.color }}/>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="card-header"><div className="card-title">Activity</div></div>
            <div className="px-3 pb-3 pt-1">
              <ResponsiveContainer width="100%" height={90}>
                <BarChart data={WEEKLY_ACTIVITY} barSize={14}>
                  <XAxis dataKey="day" tick={{ fontSize:9, fill:'#94a3b8', fontFamily:'monospace' }} axisLine={false} tickLine={false}/>
                  <Tooltip contentStyle={{ background:'#ffffff', border:'1px solid #e2e8f0', borderRadius:8, fontSize:11, fontFamily:'monospace' }} cursor={{ fill:'rgba(0,0,0,.03)' }}/>
                  <Bar dataKey="v" radius={[2,2,0,0]}>
                    {WEEKLY_ACTIVITY.map((_,i) => <Cell key={i} fill={i===WEEKLY_ACTIVITY.length-1?'#2563eb':'#e2e8f0'}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Clone type guide */}
      <div className="card p-5">
        <div className="card-title mb-4">Clone Type Reference</div>
        <div className="grid grid-cols-4 gap-3">
          {Object.entries(CLONE_TYPE_META).map(([type, meta]) => (
            <div key={type} className="p-4 bg-s2 rounded-xl border border-b1 hover:border-b2 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: meta.color }}/>
                <span className="text-xs font-bold font-mono" style={{ color: meta.color }}>{type}</span>
              </div>
              <div className="text-xs font-semibold text-t1 mb-1">{meta.label}</div>
              <div className="text-[11px] text-t3 leading-relaxed">{meta.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
