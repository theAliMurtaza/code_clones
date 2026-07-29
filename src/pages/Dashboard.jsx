import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useApp } from '../context/AppContext'
import { Stat, SectionH, Badge, Btn } from '../components/UI'
import { WEEKLY, DIST } from '../utils/data'

const STATS = [
  { label:'Total Analyses', value:'1,284', color:'#00d4ff', sub:'+12% this month'   },
  { label:'Clone Pairs',    value:'759',   color:'#8b5cf6', sub:'All types combined' },
  { label:'Languages',      value:'2',     color:'#00e5b0', sub:'Python & Java'      },
  { label:'Avg F1-Score',   value:'0.91',  color:'#f59e0b', sub:'vs 0.67 SourcererCC'},
]

const STATUS_BADGE = { complete:'green', running:'blue', queued:'amber' }

export default function Dashboard() {
  const { projects, setPage } = useApp()

  return (
    <div className="animate-fadeUp space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {STATS.map(s => <Stat key={s.label} {...s}/>)}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-5 gap-4">
        {/* Recent projects */}
        <div className="col-span-3 card">
          <div className="card-header">
            <div className="card-title">Recent Projects · FR-08-02</div>
            <Btn variant="ghost" size="sm" onClick={() => setPage('account')}>View All</Btn>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-b1">
                {['Project','Language','Clones','F1','Status','Action'].map(h => (
                  <th key={h} className="text-left px-5 py-2.5 text-[9px] font-semibold font-mono text-t3 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {projects.map(p => (
                <tr key={p.id} className="border-b border-b1/50 hover:bg-s2/60 transition-colors cursor-pointer" onClick={() => setPage('results')}>
                  <td className="px-5 py-3 font-medium text-t1">{p.name}</td>
                  <td className="px-5 py-3 font-mono text-t2">{p.lang}</td>
                  <td className="px-5 py-3 font-mono text-t2">{p.clones}</td>
                  <td className="px-5 py-3 font-mono text-success font-bold">{p.f1}</td>
                  <td className="px-5 py-3"><Badge type={STATUS_BADGE[p.status]}>{p.status}</Badge></td>
                  <td className="px-5 py-3">
                    <Btn variant="ghost" size="sm" onClick={e => { e.stopPropagation(); setPage('results') }}>Inspect</Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Clone distribution */}
        <div className="col-span-2 space-y-4">
          <div className="card">
            <div className="card-header"><div className="card-title">Clone Type Distribution</div></div>
            <div className="card-body space-y-3">
              {DIST.map(d => (
                <div key={d.type}>
                  <div className="flex justify-between text-[11px] font-mono mb-1.5">
                    <span className="text-t2">{d.type}</span>
                    <span className="font-bold" style={{ color:d.color }}>{d.pct}%</span>
                  </div>
                  <div className="h-1.5 bg-b2 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width:`${d.pct}%`, background:d.color }}/>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header"><div className="card-title">Weekly Analyses</div></div>
            <div className="px-4 pb-4 pt-2">
              <ResponsiveContainer width="100%" height={90}>
                <BarChart data={WEEKLY} barSize={14}>
                  <XAxis dataKey="day" tick={{ fontSize:9, fill:'#484f58', fontFamily:'monospace' }} axisLine={false} tickLine={false}/>
                  <Tooltip contentStyle={{ background:'#131920', border:'1px solid #1e2d3d', borderRadius:8, fontSize:11, fontFamily:'monospace' }} cursor={{ fill:'rgba(255,255,255,.03)' }}/>
                  <Bar dataKey="v" radius={[2,2,0,0]}>
                    {WEEKLY.map((_, i) => <Cell key={i} fill={i===WEEKLY.length-1 ? '#00d4ff' : '#1e2d3d'}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Clone type legend */}
      <div className="card p-5">
        <div className="card-title mb-4">Clone Type Reference Guide</div>
        <div className="grid grid-cols-4 gap-4">
          {[
            { type:'Type-1', label:'Exact Clone',    color:'#10b981', desc:'Identical code — only whitespace or comments differ. Easiest to detect.' },
            { type:'Type-2', label:'Renamed Clone',  color:'#00d4ff', desc:'Same structure but identifiers, literals, or types have been renamed.' },
            { type:'Type-3', label:'Near-miss Clone',color:'#f59e0b', desc:'Similar structure with added, removed, or modified statements.' },
            { type:'Type-4', label:'Semantic Clone',  color:'#8b5cf6', desc:'Functionally equivalent but implemented differently. Hardest to detect.' },
          ].map(t => (
            <div key={t.type} className="p-4 bg-s2 rounded-xl border border-b1 hover:border-b2 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background:t.color }}/>
                <span className="text-xs font-bold font-mono" style={{ color:t.color }}>{t.type}</span>
              </div>
              <div className="text-xs font-semibold text-t1 mb-1.5">{t.label}</div>
              <div className="text-[11px] text-t3 leading-relaxed">{t.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
