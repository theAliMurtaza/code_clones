import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Btn, MetricRing, SectionH, Badge } from '../components/UI'
import CodeViewer from '../components/CodeViewer'
import { CLONE_PAIRS, CLONE_TYPES } from '../utils/data'

const TYPE_BADGE = { 'Type-1':'type1','Type-2':'type2','Type-3':'type3','Type-4':'type4' }

const PHASE_TIMINGS = [
  { label:'Tokenization',  time:'0.8s',  pct:19, color:'#00d4ff' },
  { label:'Embedding',     time:'2.1s',  pct:50, color:'#8b5cf6' },
  { label:'Comparison',    time:'1.3s',  pct:31, color:'#00e5b0' },
]

export default function Results() {
  const { toast } = useApp()
  const [selected, setSelected] = useState(null)

  const exportFn = fmt => toast(`Exported as ${fmt}`, `${CLONE_PAIRS.length} pairs · file ready`)

  return (
    <div className="animate-fadeUp space-y-5">
      <SectionH>Results, Reports &amp; Clone Viewer</SectionH>

      {/* Metrics row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-6 flex items-center justify-around">
          <MetricRing value={0.89} label="Precision" color="#10b981"/>
          <MetricRing value={0.93} label="Recall"    color="#00d4ff"/>
          <MetricRing value={0.91} label="F1-Score"  color="#f59e0b"/>
        </div>

        {/* Summary */}
        <div className="card p-5 col-span-2">
          <div className="card-title mb-4">Analysis Summary · FR-09-01</div>
          <div className="grid grid-cols-4 gap-3 mb-5">
            {[
              { label:'Fragments',   val:'2,560', color:'#00d4ff' },
              { label:'Clone Pairs', val:'8',     color:'#8b5cf6' },
              { label:'Type-4 Pairs',val:'2',     color:'#8b5cf6' },
              { label:'Runtime',     val:'4.2s',  color:'#f59e0b' },
            ].map(s=>(
              <div key={s.label} className="bg-s3 rounded-xl border border-b1 p-3.5 text-center">
                <div className="text-2xl font-bold font-mono mb-1" style={{ color:s.color }}>{s.val}</div>
                <div className="text-[10px] font-mono text-t3 uppercase tracking-wider">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Phase timings NFR-10-03 */}
          <div>
            <div className="text-[10px] font-mono text-t3 uppercase tracking-wider mb-3">Phase Timings </div>
            <div className="space-y-2">
              {PHASE_TIMINGS.map(p=>(
                <div key={p.label} className="flex items-center gap-3">
                  <span className="text-xs font-mono text-t2 w-28">{p.label}</span>
                  <div className="flex-1 h-1.5 bg-b2 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width:`${p.pct}%`, background:p.color }}/>
                  </div>
                  <span className="text-xs font-bold font-mono w-10 text-right" style={{ color:p.color }}>{p.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Export */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">Export Results </div>
          <div className="flex gap-2">
            {['JSON','CSV','PDF'].map(f=>(
              <Btn key={f} variant="ghost" size="sm" onClick={()=>exportFn(f)}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                </svg>
                {f}
              </Btn>
            ))}
          </div>
        </div>
        <div className="p-4 bg-s2 font-mono text-xs leading-6 text-t2">
          <span className="text-t3">{`// FR-09-02 · clone pair sample`}</span>{'\n'}
          {'{ '}<span className="text-accent2">"id"</span>{': '}<span className="text-amber">1</span>{', '}
          <span className="text-accent2">"type"</span>{': '}<span className="text-emerald">"Type-1"</span>{', '}
          <span className="text-accent2">"file_a"</span>{': '}<span className="text-emerald">"utils/validator.py"</span>{', '}
          <span className="text-accent2">"lines_a"</span>{': ['}<span className="text-amber">12</span>{','}<span className="text-amber">22</span>{'],\n'}
          {'  '}<span className="text-accent2">"file_b"</span>{': '}<span className="text-emerald">"helpers/validate.py"</span>{', '}
          <span className="text-accent2">"lines_b"</span>{': ['}<span className="text-amber">5</span>{','}<span className="text-amber">15</span>{'], '}
          <span className="text-accent2">"similarity"</span>{': '}<span className="text-amber">0.99</span>{' }'}
        </div>
      </div>

      {/* Clone pairs with highlighted code viewer */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="section-h flex-1 mb-0">Clone Pairs · Annotated Code View · FR-07-02</div>
        </div>

        {CLONE_PAIRS.map((pair, i) => {
          const info  = CLONE_TYPES[pair.type]
          const pct   = Math.round(pair.similarity * 100)
          const isOpen = selected === pair.id

          return (
            <div key={pair.id} className="card overflow-hidden">
              {/* Row header */}
              <button
                onClick={() => setSelected(isOpen ? null : pair.id)}
                className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-s2/50 transition-colors text-left">

                {/* Index */}
                <span className="text-[11px] font-mono text-t3 w-5 flex-shrink-0">#{i+1}</span>

                {/* Type */}
                <Badge type={TYPE_BADGE[pair.type]}>{pair.type}</Badge>

                {/* Files + lines */}
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-mono text-t1">
                    <span className="font-semibold">{pair.fileA}</span>
                    <span className="text-t3"> :{pair.linesA[0]}–{pair.linesA[1]} </span>
                    <span className="text-t3 mx-1">↔</span>
                    <span className="font-semibold">{pair.fileB}</span>
                    <span className="text-t3"> :{pair.linesB[0]}–{pair.linesB[1]}</span>
                  </div>
                  <div className="text-[10px] text-t3 font-mono mt-0.5">{pair.desc}</div>
                </div>

                {/* Cross-lang */}
                {pair.crossLang && <Badge type="blue">Cross-lang</Badge>}

                {/* Sim bar */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="w-20 h-1.5 bg-b2 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width:`${pct}%`, background:info?.highlight }}/>
                  </div>
                  <span className="text-xs font-bold font-mono w-9 text-right" style={{ color:info?.highlight }}>{pct}%</span>
                </div>

                {/* Chevron */}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                  className={`text-t3 flex-shrink-0 transition-transform ${isOpen?'rotate-180':''}`}>
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>

              {/* Code viewer */}
              {isOpen && (
                <div className="border-t border-b1">
                  {/* Type banner */}
                  <div className="flex items-center gap-2.5 px-5 py-2 bg-s3 border-b border-b1">
                    <div className="w-2 h-2 rounded-full" style={{ background:info?.highlight }}/>
                    <span className="text-[10px] font-mono">
                      <strong style={{ color:info?.highlight }}>{info?.label}:</strong>
                      <span className="text-t3 ml-2">{info?.desc}</span>
                    </span>
                    <div className="ml-auto flex items-center gap-2 text-[10px] font-mono text-t3">
                      <span>Highlighted lines = clone fragment</span>
                      <div className="w-3 h-0.5 rounded" style={{ background:info?.highlight }}/>
                    </div>
                  </div>

                  {/* Side-by-side code */}
                  <div className="grid grid-cols-2 divide-x divide-b1 bg-bg" style={{ minHeight:200, maxHeight:420 }}>
                    <CodeViewer
                      lines={pair.codeA} cloneLines={pair.cloneLinesA}
                      type={pair.type} file={pair.fileA}
                      lang={pair.fileA.endsWith('.py')?'Python':pair.fileA.endsWith('.java')?'Java':'JS'}
                    />
                    <CodeViewer
                      lines={pair.codeB} cloneLines={pair.cloneLinesB}
                      type={pair.type} file={pair.fileB}
                      lang={pair.fileB.endsWith('.py')?'Python':pair.fileB.endsWith('.java')?'Java':'JS'}
                    />
                  </div>

                  {/* Footer */}
                  <div className="flex gap-5 px-5 py-2.5 bg-s3 border-t border-b1 text-[10px] font-mono text-t3">
                    <span>Clone lines: <strong className="text-t2">{pair.cloneLinesA.length} in A · {pair.cloneLinesB.length} in B</strong></span>
                    <span>Similarity: <strong style={{ color:info?.highlight }}>{pct}%</strong></span>
                    <span>Engine: <strong className="text-t2">CodeBERT cosine</strong></span>
                    {pair.crossLang && <span className="text-accent">✓ Cross-language (FR-06-02)</span>}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
