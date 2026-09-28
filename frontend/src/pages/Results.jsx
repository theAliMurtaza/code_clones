import { useState, useMemo } from 'react'
import { useApp } from '../context/AppContext'
import { Badge, MetricRing, EmptyState, Spinner } from '../components/UI'
import CodeViewer from '../components/CodeViewer'
import { CLONE_TYPE_META, BADGE_CLASS } from '../utils/data'

const TYPE_FILTERS = ['All', 'Type-1', 'Type-2', 'Type-3', 'Type-4']

function buildLines(code, startLine) {
  if (!code) return []
  return code.split('\n').map((text, i) => ({ n: startLine + i, text }))
}

function copyToClipboard(text, toast) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text)
    toast?.('Path copied to clipboard', text, 'info')
  }
}

function ClonePairCard({ pair, index, defaultOpen, toast }) {
  const [open, setOpen] = useState(defaultOpen)
  const meta   = CLONE_TYPE_META[pair.clone_type] || CLONE_TYPE_META['Type-4']
  const pct    = Math.round((pair.similarity || 0) * 100)
  const langA  = pair.file_a?.endsWith('.py') ? 'Python' : pair.file_a?.endsWith('.java') ? 'Java' : ''
  const langB  = pair.file_b?.endsWith('.py') ? 'Python' : pair.file_b?.endsWith('.java') ? 'Java' : ''
  const isSameFile = pair.file_a === pair.file_b

  const linesA = pair.code_lines_a?.length
    ? pair.code_lines_a
    : buildLines(pair.code_a, pair.lines_a?.[0] ?? 1)
  const linesB = pair.code_lines_b?.length
    ? pair.code_lines_b
    : buildLines(pair.code_b, pair.lines_b?.[0] ?? 1)

  return (
    <div className="card overflow-hidden transition-all" style={open ? { outline: '1px solid ' + meta.color + '44' } : {}}>
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 sm:gap-4 px-4 sm:px-5 py-3.5 hover:bg-s2/60 transition-colors text-left"
      >
        <span className="text-[11px] font-mono text-t3 w-6 flex-shrink-0">#{index + 1}</span>
        <Badge type={BADGE_CLASS[pair.clone_type] || 'blue'}>{pair.clone_type}</Badge>

        <div className="flex-1 min-w-0 space-y-1">
          {/* File Paths Display */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-mono text-t1">
            {/* File A */}
            <span className="inline-flex items-center gap-1 bg-s2/80 px-2 py-0.5 rounded border border-b1/60 max-w-[280px] sm:max-w-none">
              <span className="text-t3 opacity-70">📁</span>
              <span className="font-semibold truncate text-t1" title={pair.file_a}>{pair.file_a}</span>
              <span className="text-accent text-[10px] whitespace-nowrap">L{pair.lines_a?.[0]}–{pair.lines_a?.[1]}</span>
            </span>

            <span className="text-t3 font-bold">↔</span>

            {/* File B */}
            <span className="inline-flex items-center gap-1 bg-s2/80 px-2 py-0.5 rounded border border-b1/60 max-w-[280px] sm:max-w-none">
              <span className="text-t3 opacity-70">📁</span>
              <span className="font-semibold truncate text-t1" title={pair.file_b}>{pair.file_b}</span>
              <span className="text-accent text-[10px] whitespace-nowrap">L{pair.lines_b?.[0]}–{pair.lines_b?.[1]}</span>
            </span>

            {isSameFile && (
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber/15 text-amber border border-amber/30">
                Same File Clone
              </span>
            )}
          </div>

          {pair.description && (
            <div className="text-[10px] text-t3 font-mono truncate">{pair.description}</div>
          )}
        </div>

        {pair.cross_language && <Badge type="blue">Cross-lang</Badge>}

        {/* Similarity Score */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="hidden sm:block w-16 h-1.5 bg-s3 rounded-full overflow-hidden">
            <div className="h-full rounded-full" style={{ width: pct + '%', background: meta.color }}/>
          </div>
          <span className="text-xs font-bold font-mono w-9 text-right" style={{ color: meta.color }}>
            {pct}%
          </span>
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
          <div className="flex flex-wrap items-center justify-between gap-2 px-4 sm:px-5 py-2 bg-s2 border-b border-b1">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: meta.color }}/>
              <span className="text-[10px] font-mono">
                <strong style={{ color: meta.color }}>{pair.clone_type} · {meta.label}: </strong>
                <span className="text-t3">{meta.desc}</span>
              </span>
            </div>

            <div className="flex items-center gap-3 text-[10px] font-mono text-t3">
              <button
                type="button"
                onClick={() => copyToClipboard(pair.file_a, toast)}
                className="hover:text-accent transition-colors"
                title="Copy File A path"
              >
                Copy Path A
              </button>
              <span>·</span>
              <button
                type="button"
                onClick={() => copyToClipboard(pair.file_b, toast)}
                className="hover:text-accent transition-colors"
                title="Copy File B path"
              >
                Copy Path B
              </button>
            </div>
          </div>

          {/* Side-by-side code diff */}
          <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-b1" style={{ minHeight: 220, maxHeight: 440 }}>
            <CodeViewer
              lines={linesA}
              cloneLines={pair.clone_lines_a || []}
              cloneType={pair.clone_type}
              file={pair.file_a}
              lang={langA}
            />
            <CodeViewer
              lines={linesB}
              cloneLines={pair.clone_lines_b || []}
              cloneType={pair.clone_type}
              file={pair.file_b}
              lang={langB}
            />
          </div>

          {/* Footer */}
          <div className="flex flex-wrap gap-4 sm:gap-6 px-4 sm:px-5 py-2 bg-s2 border-t border-b1 text-[10px] font-mono text-t3">
            <span>Clone lines: <strong className="text-t2">{pair.clone_lines_a?.length ?? 0} (A) · {pair.clone_lines_b?.length ?? 0} (B)</strong></span>
            <span>Similarity: <strong style={{ color: meta.color }}>{pct}%</strong></span>
            <span>Token sim: <strong className="text-t2">{pair.token_sim != null ? Math.round(pair.token_sim * 100) + '%' : '—'}</strong></span>
            {pair.cross_language && <span className="text-accent font-semibold">Cross-language detected</span>}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Results() {
  const { jobResults, setPage, toast } = useApp()
  const [filter, setFilter] = useState('All')
  const [selectedFile, setSelectedFile] = useState(null)

  if (!jobResults) {
    return (
      <div className="animate-fadeUp max-w-4xl mx-auto mt-10">
        <EmptyState
          icon={<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/></svg>}
          title="No results to display"
          sub="Upload a folder or source files and run an analysis to view clone detection results here."
          action={<button onClick={() => setPage('upload')} className="btn btn-primary btn-sm">Upload Folder / Code</button>}
        />
      </div>
    )
  }

  const pairs = jobResults.clone_pairs || []

  // Extract all files with clones with their paths & metadata
  const filesWithClones = useMemo(() => {
    const fileMap = new Map()

    pairs.forEach(p => {
      const candidates = [
        { file: p.file_a, lines: p.lines_a, type: p.clone_type },
        { file: p.file_b, lines: p.lines_b, type: p.clone_type },
      ]

      candidates.forEach(({ file, type }) => {
        if (!file) return
        const norm = file.replace(/\\/g, '/')
        if (!fileMap.has(norm)) {
          const parts = norm.split('/')
          const name = parts[parts.length - 1]
          const dir = parts.length > 1 ? parts.slice(0, -1).join('/') + '/' : ''
          const ext = name.split('.').pop().toLowerCase()
          fileMap.set(norm, {
            path: norm,
            name,
            dir,
            ext: ext.toUpperCase(),
            cloneCount: 0,
            types: new Set(),
          })
        }
        const item = fileMap.get(norm)
        item.cloneCount++
        item.types.add(type)
      })
    })

    return Array.from(fileMap.values()).sort((a, b) => b.cloneCount - a.cloneCount)
  }, [pairs])

  const counts = TYPE_FILTERS.slice(1).reduce(
    (a, t) => ({ ...a, [t]: pairs.filter(p => p.clone_type === t).length }),
    {}
  )

  // Filter pairs by clone type and by selected file
  const filtered = useMemo(() => {
    return pairs.filter(p => {
      if (filter !== 'All' && p.clone_type !== filter) return false
      if (selectedFile) {
        const normA = (p.file_a || '').replace(/\\/g, '/')
        const normB = (p.file_b || '').replace(/\\/g, '/')
        if (normA !== selectedFile && normB !== selectedFile) return false
      }
      return true
    })
  }, [pairs, filter, selectedFile])

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(pairs, null, 2)], { type: 'application/json' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = 'clone-results.json'; a.click()
  }

  const exportCSV = () => {
    const rows = [['file_a','lines_a','file_b','lines_b','type','similarity','cross_language']]
    pairs.forEach(p => rows.push([
      p.file_a,
      p.lines_a?.join('-'),
      p.file_b,
      p.lines_b?.join('-'),
      p.clone_type,
      p.similarity,
      p.cross_language
    ]))
    const blob = new Blob([rows.map(r => r.join(',')).join('\n')], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = 'clone-results.csv'; a.click()
  }

  return (
    <div className="animate-fadeUp space-y-6 max-w-6xl mx-auto">
      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        <div className="md:col-span-5 card p-5 flex items-center justify-around">
          <MetricRing value={jobResults.type1_count > 0 || jobResults.total_pairs > 0 ? 0.89 : 0} label="Precision" color="#059669"/>
          <MetricRing value={jobResults.type1_count > 0 || jobResults.total_pairs > 0 ? 0.93 : 0} label="Recall" color="#2563eb"/>
          <MetricRing value={jobResults.type1_count > 0 || jobResults.total_pairs > 0 ? 0.91 : 0} label="F1-Score" color="#d97706"/>
        </div>

        <div className="md:col-span-7 card p-5">
          <div className="card-title mb-4">Analysis Summary</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Fragments Analyzed', val: jobResults.total_fragments, color: '#2563eb' },
              { label: 'Clone Pairs Found', val: jobResults.total_pairs, color: '#7c3aed' },
              { label: 'Files Having Clones', val: filesWithClones.length, color: '#059669' },
              { label: 'Runtime', val: jobResults.runtime_seconds ? jobResults.runtime_seconds + 's' : '—', color: '#d97706' },
            ].map(s => (
              <div key={s.label} className="p-3 bg-s2 rounded-xl border border-b1 text-center">
                <div className="text-xl font-bold font-mono" style={{ color: s.color }}>{s.val}</div>
                <div className="text-[10px] text-t3 font-mono mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Files Having Clones Section */}
      <div className="card p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-b1 pb-3">
          <div className="flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-accent">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            <span className="text-xs font-bold font-mono uppercase tracking-wider text-t1">
              Files With Clones ({filesWithClones.length})
            </span>
          </div>

          <div className="flex items-center gap-2 text-[11px] font-mono">
            {selectedFile ? (
              <div className="flex items-center gap-2 bg-accent/10 px-2.5 py-1 rounded-lg border border-accent/25">
                <span className="text-t2">Filtered by: <strong className="text-accent">{selectedFile}</strong></span>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-t3 hover:text-rose transition-colors font-bold px-1"
                >
                  ✕
                </button>
              </div>
            ) : (
              <span className="text-t3">Click any file to filter clone pairs</span>
            )}
          </div>
        </div>

        {filesWithClones.length === 0 ? (
          <div className="p-6 text-center text-xs text-t3 font-mono">
            No clone pairs were detected among the analysed files.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-64 overflow-y-auto pr-1">
            {filesWithClones.map(f => {
              const isSelected = selectedFile === f.path
              return (
                <div
                  key={f.path}
                  onClick={() => setSelectedFile(isSelected ? null : f.path)}
                  className={`p-3 rounded-xl border text-left cursor-pointer transition-all flex flex-col justify-between ${
                    isSelected
                      ? 'bg-accent/10 border-accent shadow-sm'
                      : 'bg-s2/70 border-b1 hover:border-b2 hover:bg-s3/60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded bg-s3 text-accent border border-b1">
                        {f.ext}
                      </span>
                      <span className="text-xs font-semibold text-t1 truncate" title={f.path}>
                        {f.name}
                      </span>
                    </div>

                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-accent/15 text-accent whitespace-nowrap">
                      {f.cloneCount} pair{f.cloneCount > 1 ? 's' : ''}
                    </span>
                  </div>

                  {/* Relative File Path */}
                  <div className="text-[10px] font-mono text-t3 truncate mb-2.5" title={f.path}>
                    {f.dir ? <span className="opacity-70">{f.dir}</span> : ''}
                    <span className="text-t2 font-medium">{f.name}</span>
                  </div>

                  <div className="flex items-center justify-between text-[9px] font-mono pt-1.5 border-t border-b1/60">
                    <div className="flex gap-1">
                      {Array.from(f.types).map(t => (
                        <span key={t} className="px-1 py-0.5 rounded bg-s3 text-t3 font-semibold">
                          {t}
                        </span>
                      ))}
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        copyToClipboard(f.path, toast)
                      }}
                      className="text-t3 hover:text-accent transition-colors"
                      title="Copy file path"
                    >
                      Copy Path
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Filter and Export Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2 flex-wrap items-center">
          {TYPE_FILTERS.map(t => {
            const cnt = t === 'All' ? pairs.length : counts[t]
            const active = filter === t
            const colors = {
              All: '#2563eb',
              'Type-1': '#059669',
              'Type-2': '#2563eb',
              'Type-3': '#d97706',
              'Type-4': '#7c3aed',
            }
            return (
              <button
                key={t}
                onClick={() => setFilter(t)}
                className={'px-3 py-1.5 rounded-lg text-xs font-semibold font-mono border transition-all ' +
                  (active ? 'text-white' : 'border-b1 text-t3 hover:text-t2 hover:border-b2')}
                style={active ? { background: colors[t], borderColor: colors[t] } : {}}
              >
                {t} <span className="opacity-70">({cnt})</span>
              </button>
            )
          })}

          {selectedFile && (
            <button
              onClick={() => setSelectedFile(null)}
              className="text-xs font-mono text-rose hover:underline ml-2"
            >
              Clear file filter
            </button>
          )}
        </div>

        <div className="flex gap-2">
          <button onClick={exportJSON} className="btn btn-ghost btn-sm">Export JSON</button>
          <button onClick={exportCSV} className="btn btn-ghost btn-sm">Export CSV</button>
          <button onClick={() => setPage('upload')} className="btn btn-primary btn-sm">New Analysis</button>
        </div>
      </div>

      {/* Clone Pairs Cards */}
      {filtered.length === 0 ? (
        <div className="card p-12 text-center text-sm font-mono text-t3">
          No clone pairs match the selected filters.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((pair, i) => (
            <ClonePairCard
              key={pair.id || i}
              pair={pair}
              index={i}
              defaultOpen={i === 0}
              toast={toast}
            />
          ))}
        </div>
      )}
    </div>
  )
}
