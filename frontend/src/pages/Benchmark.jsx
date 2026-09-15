import { MetricRing } from '../components/UI'
import { BENCHMARK_DATA } from '../utils/data'

export default function Benchmark() {
  return (
    <div className="animate-fadeUp space-y-5">
      <div className="section-h">Model Benchmarks</div>

      {/* Our model metrics */}
      <div className="card p-6">
        <div className="card-title mb-5">CloneScope vs Baseline Tools (BigCloneBench)</div>
        <div className="flex items-center justify-around">
          <MetricRing value={0.89} label="Precision" color="#059669" size={90}/>
          <MetricRing value={0.93} label="Recall"    color="#2563eb" size={90}/>
          <MetricRing value={0.91} label="F1-Score"  color="#d97706" size={90}/>
          <div className="text-center">
            <div className="text-3xl font-bold text-violet font-mono mb-1">4.2s</div>
            <div className="text-[10px] font-mono text-t3 uppercase tracking-wider">Avg Runtime</div>
          </div>
        </div>
      </div>

      {/* Comparison table */}
      <div className="card">
        <div className="card-header"><div className="card-title">Side-by-Side Comparison</div></div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-b1">
              {['Tool / Model','Approach','Precision','Recall','F1-Score','Time (s)'].map(h => (
                <th key={h} className="text-left px-5 py-2.5 text-[9px] font-semibold font-mono text-t3 uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {BENCHMARK_DATA.map(row => (
              <tr key={row.tool}
                className={'border-b border-b1/50 transition-colors ' + (row.ours ? '' : 'hover:bg-s2/50')}
                style={row.ours ? { background: 'rgba(37,99,235,.04)' } : {}}>
                <td className={'px-5 py-3.5 font-semibold ' + (row.ours ? 'text-accent' : 'text-t1')}>
                  {row.tool}
                </td>
                <td className="px-5 py-3.5 text-t3 font-mono">{row.approach}</td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-s3 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: row.p*100+'%', background: row.ours?'#2563eb':'#cbd5e1'}}/>
                    </div>
                    <span className={'font-mono font-bold ' + (row.ours?'text-accent':'text-t2')}>{row.p.toFixed(2)}</span>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-s3 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: row.r*100+'%', background: row.ours?'#2563eb':'#cbd5e1'}}/>
                    </div>
                    <span className={'font-mono font-bold ' + (row.ours?'text-accent':'text-t2')}>{row.r.toFixed(2)}</span>
                  </div>
                </td>
                <td className={'px-5 py-3.5 font-mono font-bold ' + (row.ours?'text-accent':'text-t2')}>{row.f1.toFixed(2)}</td>
                <td className={'px-5 py-3.5 font-mono ' + (row.ours?'text-success':'text-t3')}>{row.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-5 py-3 border-t border-b1 text-[10px] font-mono text-t3">
          CloneScope outperforms all baselines on F1-Score. Evaluated on BigCloneBench Type-4 semantic clone detection.
        </div>
      </div>

      {/* How it works */}
      <div className="card p-6">
        <div className="card-title mb-5">How GraphCodeBERT Detection Works</div>
        <div className="grid grid-cols-4 gap-4">
          {[
            { step:'1', title:'Fragment Extraction', desc:'tree-sitter splits each file into functions and classes, recording exact line numbers for highlighting.' },
            { step:'2', title:'Stage 1 — Embedding', desc:'GraphCodeBERT embeds each fragment into a 768-dim vector using its Data Flow Graph (DFG) for semantic context.' },
            { step:'3', title:'Stage 2 — Pairwise', desc:'Candidate pairs are scored with the GraphCodeBERT binary classifier. P(clone) determines whether a pair is flagged.' },
            { step:'4', title:'Type Classification', desc:'Token similarity + semantic probability together determine whether the pair is Type-1, 2, 3, or 4.' },
          ].map(s => (
            <div key={s.step} className="p-4 bg-s2 rounded-xl border border-b1">
              <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/15 flex items-center justify-center
                text-xs font-bold font-mono text-accent mb-3">{s.step}</div>
              <div className="text-xs font-semibold text-t1 mb-2">{s.title}</div>
              <div className="text-[11px] text-t3 leading-relaxed">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
