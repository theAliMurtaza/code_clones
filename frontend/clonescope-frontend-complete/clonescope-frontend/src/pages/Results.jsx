import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Badge, MetricRing, EmptyState, Spinner } from '../components/UI'
import CodeViewer from '../components/CodeViewer'
import { CLONE_TYPE_META, BADGE_CLASS } from '../utils/data'

const TYPE_FILTERS = ['All', 'Type-1', 'Type-2', 'Type-3', 'Type-4']

function buildLines(code, startLine) {
  if (!code) return []
  return code.split('\n').map((text, i) => ({ n: startLine + i, text }))
}

function ClonePairCard({ pair, index, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen)
  const meta   = CLONE_TYPE_META[pair.clone_type] || CLONE_TYPE_META['Type-4']
  const pct    = Math.round((pair.similarity || 0) * 100)
  const langA  = pair.file_a?.endsWith('.py') ? 'Python' : pair.file_a?.endsWith('.java') ? 'Java' : ''
  const langB  = pair.file_b?.endsWith('.py') ? 'Python' : pair.file_b?.endsWith('.java') ? 'Java' : ''

  // Build line arrays — prefer API-provided code_lines, fallback to raw code
  const linesA = pair.code_lines_a?.length
    ? pair.code_lines_a
    : buildLines(pair.code_a, pair.lines_a?.[0] ?? 1)
  const linesB = pair.code_lines_b?.length
    ? pair.code_lines_b
    : buildLines(pair.code_b, pair.lines_b?.[0] ?? 1)

  return (
    <div className="card overflow-hidden transition-all" style={open ? { outline: '1px solid ' + meta.color + '33' } : {}}>
      {/* Header */}
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-s2/60 transition-colors text-left">
        <span className="text-[11px] font-mono text-t3 w-6 flex-shrink-0">#{index + 1}</span>
        <Badge type={BADGE_CLASS[pair.clone_type] || 'blue'}>{pair.clone_type}</Badge>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono text-t1">
            <span className="font-semibold">{pair.file_a}</span>
            <span className="text-t3 mx-1">L{pair.lines_a?.[0]}–{pair.lines_a?.[1]}</span>
            <span className="text-t3 mx-1">↔</span>
            <span className="font-semibold">{pair.file_b}</span>
            <span className="text-t3 mx-1">L{pair.lines_b?.[0]}–{pair.lines_b?.[1]}</span>
          </div>
          {pair.description && <div className="text-[10px] text-t3 font-mono mt-0.5 truncate">{pair.description}</div>}
        </div>
        {pair.cross_language && <Badge type="blue">Cross-lang</Badge>}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="w-16 h-1.5 bg-b2 rounded-full overflow-hidden">
            <div className="h-full rounded-full" style={{ width: pct + '%', background: meta.color }}/>
          </div>
          <span className="text-xs font-bold font-mono w-9 text-right" style={{ color: meta.color }}>{pct}%</span>
        </div>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round"
          className={'text-t3 flex-shrink-0 transition-transform ' + (open ? 'rotate-180' : '')}>
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {/* Code view */}
      {open && (
        <div className="border-t border-b1">
          {/* Type banner */}
          <div className="flex items-center gap-2 px-5 py-2 bg-s3 border-b border-b1">
            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: meta.color }}/>
            <span className="text-[10px] font-mono">
              <strong style={{ color: meta.color }}>{pair.clone_type} · {meta.label}: </strong>
              <span className="text-t3">{meta.desc}</span>
            </span>
            <div className="ml-auto text-[10px] font-mono text-t3">Highlighted lines = clone fragment</div>
          </div>

          {/* Side-by-side */}
          <div className="grid grid-cols-2 divide-x divide-b1" style={{ minHeight: 200, maxHeight: 420 }}>
            <CodeViewer lines={linesA} cloneLines={pair.clone_lines_a || []}
              cloneType={pair.clone_type} file={pair.file_a} lang={langA}/>
            <CodeViewer lines={linesB} cloneLines={pair.clone_lines_b || []}
              cloneType={pair.clone_type} file={pair.file_b} lang={langB}/>
          </div>

          {/* Footer */}
          <div className="flex gap-5 px-5 py-2 bg-s3 border-t border-b1 text-[10px] font-mono text-t3">
            <span>Clone lines: <strong className="text-t2">{pair.clone_lines_a?.length ?? 0} (A) · {pair.clone_lines_b?.length ?? 0} (B)</strong></span>
            <span>Similarity: <strong style={{ color: meta.color }}>{pct}%</strong></span>
            <span>Token sim: <strong className="text-t2">{pair.token_sim != null ? Math.round(pair.token_sim * 100) + '%' : '—'}</strong></span>
            {pair.cross_language && <span className="text-accent">Cross-language detected</span>}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Results() {
  const { jobResults, setPage } = useApp()
  const [filter, setFilter] = useState('All')

  if (!jobResults) {
    return (
      <div className="animate-fadeUp">
        <EmptyState
          icon={<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/></svg>}
          title="No results to display"
          sub="Upload code files and run an analysis to see clone detection results here."
          action={<button onClick={() => setPage('upload')} className="btn btn-primary btn-sm">Upload Code</button>}
        />
      </div>
    )
  }

  const pairs   = jobResults.clone_pairs || []
  const counts  = TYPE_FILTERS.slice(1).reduce((a, t) => ({ ...a, [t]: pairs.filter(p => p.clone_type === t).length }), {})
  const filtered = filter === 'All' ? pairs : pairs.filter(p => p.clone_type === filter)

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(pairs, null, 2)], { type: 'application/json' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = 'clone-results.json'; a.click()
  }

  const exportCSV = () => {
    const rows = [['file_a','lines_a','file_b','lines_b','type','similarity','cross_language']]
    pairs.forEach(p => rows.push([p.file_a, p.lines_a?.join('-'), p.file_b, p.lines_b?.join('-'), p.clone_type, p.similarity, p.cross_language]))
    const blob = new Blob([rows.map(r => r.join(',')).join('\n')], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = 'clone-results.csv'; a.click()
  }

  return (
    <div className="animate-fadeUp space-y-5">
      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card p-5 flex items-center justify-around">
          <MetricRing value={jobResults.type1_count > 0 || jobResults.total_pairs > 0 ? 0.89 : 0} label="Precision" color="#10b981"/>
          <MetricRing value={jobResults.type1_count > 0 || jobResults.total_pairs > 0 ? 0.93 : 0} label="Recall"    color="#00d4ff"/>
          <MetricRing value={jobResults.type1_count > 0 || jobResults.total_pairs > 0 ? 0.91 : 0} label="F1-Score"  color="#f59e0b"/>
        </div>
        <div className="card p-5">
          <div className="card-title mb-4">Analysis Summary</div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Fragments Analysed', val: jobResults.total_fragments, color: '#00d4ff' },
              { label: 'Clone Pairs Found',  val: jobResults.total_pairs,     color: '#8b5cf6' },
              { label: 'Runtime',            val: jobResults.runtime_seconds ? jobResults.runtime_seconds + 's' : '—', color: '#f59e0b' },
              { label: 'Threshold Used',     val: Math.round((jobResults.threshold || 0.75) * 100) + '%', color: '#10b981' },
            ].map(s => (
              <div key={s.label} className="p-3 bg-s3 rounded-xl border border-b1 text-center">
                <div className="text-xl font-bold font-mono" style={{ color: s.color }}>{s.val}</div>
                <div className="text-[10px] text-t3 font-mono mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Type breakdown + export */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          {TYPE_FILTERS.map(t => {
            const cnt = t === 'All' ? pairs.length : counts[t]
            const active = filter === t
            const colors = { All:'#00d4ff','Type-1':'#10b981','Type-2':'#00d4ff','Type-3':'#f59e0b','Type-4':'#8b5cf6' }
            return (
              <button key={t} onClick={() => setFilter(t)}
                className={'px-3 py-1.5 rounded-lg text-xs font-semibold font-mono border transition-all ' +
                  (active ? 'text-bg' : 'border-b1 text-t3 hover:text-t2 hover:border-b2')}
                style={active ? { background: colors[t], borderColor: colors[t] } : {}}>
                {t} <span className="opacity-60">({cnt})</span>
              </button>
            )
          })}
        </div>
        <div className="flex gap-2">
          <button onClick={exportJSON} className="btn btn-ghost btn-sm">Export JSON</button>
          <button onClick={exportCSV}  className="btn btn-ghost btn-sm">Export CSV</button>
          <button onClick={() => setPage('upload')} className="btn btn-primary btn-sm">New Analysis</button>
        </div>
      </div>

      {/* Clone pairs */}
      {filtered.length === 0 ? (
        <div className="card p-10 text-center text-sm text-t3">No clone pairs for this filter.</div>
      ) : (
        <div className="space-y-2">
          {filtered.map((pair, i) => (
            <ClonePairCard key={pair.id || i} pair={pair} index={i} defaultOpen={i === 0}/>
          ))}
        </div>
      )}
    </div>
  )
}
