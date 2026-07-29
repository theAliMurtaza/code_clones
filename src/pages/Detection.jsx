import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Btn, Toggle, Select, Range, Badge, SectionH } from '../components/UI'
import CodeViewer from '../components/CodeViewer'
import { CLONE_PAIRS, CLONE_TYPES } from '../utils/data'

const STEPS = ['Ingest','Tokenize','Embed','Detect','Report']

const TYPE_FILTER = ['All','Type-1','Type-2','Type-3','Type-4']

const SIM_COLOR = (v) => v >= 0.9 ? '#10b981' : v >= 0.85 ? '#00d4ff' : v >= 0.80 ? '#f59e0b' : '#8b5cf6'

const TYPE_BADGE = { 'Type-1':'type1','Type-2':'type2','Type-3':'type3','Type-4':'type4' }

function Stepper({ step }) {
  return (
    <div className="flex items-start">
      {STEPS.map((s, i) => (
        <div key={s} className="flex items-start flex-1">
          <div className="flex flex-col items-center">
            <div className={`w-7 h-7 rounded-full border-2 flex items-center justify-center text-[10px] font-mono font-bold transition-all
              ${i < step  ? 'bg-accent border-accent text-bg'
              : i===step  ? 'border-accent text-accent shadow-[0_0_0_3px_rgba(0,212,255,.15)]'
              : 'border-b2 text-t3 bg-s2'}`}>
              {i < step ? '✓' : i+1}
            </div>
            <div className={`text-[9px] font-mono mt-1.5 ${i<=step?'text-t2':'text-t3'}`}>{s}</div>
          </div>
          {i < STEPS.length-1 && (
            <div className={`flex-1 h-0.5 mt-3.5 mx-1 transition-all ${i<step?'bg-accent':'bg-b2'}`}/>
          )}
        </div>
      ))}
    </div>
  )
}

function ClonePair({ pair, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen)
  const pct = Math.round(pair.similarity * 100)
  const clr = SIM_COLOR(pair.similarity)
  const info = CLONE_TYPES[pair.type]

  return (
    <div className={`card overflow-hidden transition-all ${open?'ring-1 ring-inset':''}`}
      style={{ '--tw-ring-color': info?.highlight+'33' }}>
      {/* Header */}
      <button onClick={() => setOpen(o=>!o)}
        className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-s2/60 transition-colors text-left">
        {/* Type badge */}
        <Badge type={TYPE_BADGE[pair.type]}>{pair.type}</Badge>

        {/* Files */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="font-semibold text-t1 truncate">{pair.fileA}</span>
            <span className="text-t3 flex-shrink-0">L{pair.linesA[0]}–{pair.linesA[1]}</span>
            <span className="text-t3">↔</span>
            <span className="font-semibold text-t1 truncate">{pair.fileB}</span>
            <span className="text-t3 flex-shrink-0">L{pair.linesB[0]}–{pair.linesB[1]}</span>
          </div>
          <div className="text-[10px] text-t3 font-mono mt-0.5">{pair.desc}</div>
        </div>

        {/* Similarity */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {pair.crossLang && <Badge type="blue">Cross-lang</Badge>}
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-b2 rounded-full overflow-hidden">
              <div className="h-full rounded-full" style={{ width:`${pct}%`, background:clr }}/>
            </div>
            <span className="text-xs font-bold font-mono w-9 text-right" style={{ color:clr }}>{pct}%</span>
          </div>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
            className={`text-t3 transition-transform flex-shrink-0 ${open?'rotate-180':''}`}>
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
      </button>

      {/* Code view */}
      {open && (
        <div className="border-t border-b1">
          {/* Type description bar */}
          <div className="flex items-center gap-2 px-5 py-2 bg-s3 border-b border-b1">
            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background:info?.highlight }}/>
            <span className="text-[10px] font-mono text-t2">
              <strong style={{ color:info?.highlight }}>{pair.type}:</strong> {info?.desc}
            </span>
            <div className="ml-auto flex items-center gap-3 text-[10px] font-mono text-t3">
              <span>Clone lines highlighted in gutter</span>
              <div className="w-3 h-0.5 rounded" style={{ background:info?.highlight }}/>
            </div>
          </div>

          {/* Side by side code */}
          <div className="grid grid-cols-2 divide-x divide-b1 bg-s2" style={{ minHeight:220, maxHeight:380 }}>
            <CodeViewer
              lines={pair.codeA}
              cloneLines={pair.cloneLinesA}
              type={pair.type}
              file={pair.fileA}
              lang={pair.fileA.endsWith('.py') ? 'Python' : pair.fileA.endsWith('.java') ? 'Java' : 'JS'}
            />
            <CodeViewer
              lines={pair.codeB}
              cloneLines={pair.cloneLinesB}
              type={pair.type}
              file={pair.fileB}
              lang={pair.fileB.endsWith('.py') ? 'Python' : pair.fileB.endsWith('.java') ? 'Java' : 'JS'}
            />
          </div>

          {/* Footer stats */}
          <div className="flex items-center gap-5 px-5 py-2 bg-s3 border-t border-b1 text-[10px] font-mono text-t3">
            <span>Clone lines: <strong className="text-t2">{pair.cloneLinesA.length} (A) · {pair.cloneLinesB.length} (B)</strong></span>
            <span>Similarity: <strong style={{ color:clr }}>{pct}%</strong></span>
            <span>Method: <strong className="text-t2">CodeBERT cosine similarity</strong></span>
            {pair.crossLang && <span className="text-accent">✓ Cross-language detection</span>}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Detection() {
  const { detCfg, setDetCfg, setPage, toast } = useApp()
  const [filter, setFilter] = useState('All')
  const dc = (k,v) => setDetCfg(p=>({...p,[k]:v}))

  const filtered = CLONE_PAIRS.filter(p => filter === 'All' || p.type === filter)

  const typeCounts = TYPE_FILTER.slice(1).reduce((a, t) => {
    a[t] = CLONE_PAIRS.filter(p => p.type === t).length
    return a
  }, {})

  return (
    <div className="animate-fadeUp space-y-4">
      <SectionH>Clone Detection Engine</SectionH>

      {/* Progress */}
      <div className="card p-5">
        <Stepper step={3}/>
        <div className="mt-4 h-1.5 bg-b2 rounded-full overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-accent to-violet animate-pulse2" style={{ width:'100%' }}/>
        </div>
        <div className="flex justify-between mt-2 text-[10px] font-mono text-t3">
          <span>2,560 fragments compared · batch processing · LSH optimisation active</span>
          <span className="text-accent">Detection complete ✓</span>
        </div>
      </div>

      <div className="grid grid-cols-[260px_1fr] gap-4 items-start">
        {/* Config */}
        <div className="card">
          <div className="card-header"><div className="card-title">Config </div></div>
          <div className="card-body">
            <Range label="Similarity Threshold " value={detCfg.threshold} onChange={v=>dc('threshold',v)} min={50} max={99}/>
            <Select label="Metric " value={detCfg.metric} onChange={v=>dc('metric',v)}
              options={[{value:'cosine',label:'Cosine similarity'},{value:'euclid',label:'Euclidean distance'}]}/>
            <Select label="Optimization " value={detCfg.opt} onChange={v=>dc('opt',v)}
              options={[{value:'lsh',label:'LSH (sub-linear)'},{value:'faiss',label:'FAISS Index'},{value:'brute',label:'Brute force O(n²)'}]}/>
            <Toggle label="Cross-language detection" checked={detCfg.crossLanguage} onChange={v=>dc('crossLanguage',v)}/>
            <div className="mt-4 info-box">
              <span><strong className="text-accent">NFR-01-03</strong> · LSH maintains sub-linear complexity — avoids O(n²) blow-up for large codebases.</span>
            </div>
            <Btn onClick={() => { toast('Results ready', '8 clone pairs found'); setPage('results') }} className="!w-full !justify-center !mt-4">
              View Results →
            </Btn>
          </div>
        </div>

        {/* Clone pairs */}
        <div className="space-y-3">
          {/* Type filter tabs */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-t3 font-mono mr-1">Filter:</span>
            {TYPE_FILTER.map(t => {
              const active = filter === t
              const count = t === 'All' ? CLONE_PAIRS.length : typeCounts[t]
              const colors = { All:'accent','Type-1':'success','Type-2':'accent','Type-3':'amber','Type-4':'violet' }
              const col = colors[t]
              return (
                <button key={t} onClick={() => setFilter(t)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-mono border transition-all
                    ${active ? `border-${col}/40 bg-${col}/10 text-${col}` : 'border-b1 text-t3 hover:border-b2 hover:text-t2'}`}>
                  {t} <span className="opacity-60">({count})</span>
                </button>
              )
            })}
            <div className="flex-1"/>
            <span className="text-[10px] font-mono text-t3">{filtered.length} pairs shown</span>
          </div>

          {/* Pairs */}
          <div className="space-y-2">
            {filtered.map((pair, i) => (
              <ClonePair key={pair.id} pair={pair} defaultOpen={i === 0} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
