import { useApp } from '../context/AppContext'
import { Btn, Select, SectionH } from '../components/UI'
import { BENCHMARK } from '../utils/data'

export default function Benchmark() {
  const { toast } = useApp()
  const run = () => {
    toast('BigCloneBench running…', 'FR-10-03: Logging phase timings')
    setTimeout(()=>toast('Benchmark complete!','FR-10-01: F1=0.91 · best result'), 2000)
  }

  return (
    <div className="animate-fadeUp space-y-5">
      <SectionH>FR-10 · System Evaluation &amp; Benchmarking</SectionH>

      {/* Runner config */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">Benchmark Runner · FR-10-01</div>
          <Btn size="sm" onClick={run}>Run Benchmark</Btn>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <Select label="Dataset · FR-10-01" value="bcb" onChange={()=>{}}
              options={[{value:'bcb',label:'BigCloneBench (BCB)'},{value:'oj',label:'OJClone'},{value:'custom',label:'Custom ground-truth'}]}/>
            <Select label="Clone Type Focus" value="type4" onChange={()=>{}}
              options={[{value:'type4',label:'Type-4 Semantic'},{value:'all',label:'All Types'},{value:'34',label:'Type-3 + Type-4'}]}/>
            <Select label="Metric · FR-10-01" value="prf" onChange={()=>{}}
              options={[{value:'prf',label:'Precision / Recall / F1'},{value:'map',label:'MAP Score'},{value:'auc',label:'AUC-ROC'}]}/>
          </div>
          <div className="info-box">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round" className="flex-shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span><strong className="text-accent">NFR-01-01</strong> · System targets ≤2 h for 1M LOC on AWS EC2 GPU instances. NFR-01-02: ≥100 fragments/min embedding throughput. NFR-01-03: Sub-linear LSH search avoids O(n²) blow-up.</span>
          </div>
        </div>
      </div>

      {/* Comparison table */}
      <div className="card">
        <div className="card-header"><div className="card-title">Baseline Comparison · FR-10-02</div></div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-b1">
              {['Tool / Model','Approach','Precision','Recall','F1-Score','Time (s)'].map(h=>(
                <th key={h} className="text-left px-5 py-2.5 text-[9px] font-semibold font-mono text-t3 uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {BENCHMARK.map(row=>(
              <tr key={row.tool} className={`border-b border-b1/50 transition-colors ${row.proposed?'bg-accent/[.03]':'hover:bg-s2/50'}`}>
                <td className={`px-5 py-3.5 font-semibold ${row.proposed?'text-accent':'text-t1'}`}>
                  {row.tool}
                </td>
                <td className="px-5 py-3.5 text-t3 font-mono">{row.approach}</td>
                <td className="px-5 py-3.5">
                  <BarCell val={row.p} proposed={row.proposed}/>
                </td>
                <td className="px-5 py-3.5">
                  <BarCell val={row.r} proposed={row.proposed}/>
                </td>
                <td className="px-5 py-3.5">
                  <span className={`font-bold font-mono ${row.proposed?'text-accent':'text-t2'}`}>{row.f1.toFixed(2)}</span>
                </td>
                <td className={`px-5 py-3.5 font-mono ${row.proposed?'text-success':'text-t3'}`}>{row.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-5 py-3 border-t border-b1 text-[10px] font-mono text-t3">
          ★ Proposed system outperforms all baselines on F1-Score while maintaining competitive inference time · NFR-02-01: Min precision 85%, recall 80% ✓
        </div>
      </div>

      {/* NFR coverage */}
      <div className="card">
        <div className="card-header"><div className="card-title">Non-Functional Requirements Status</div></div>
        <div className="card-body grid grid-cols-2 gap-3">
          {[
            { id:'NFR-01-01', label:'Performance — 1M LOC ≤ 2h',          ok:true, val:'Achieved on EC2 g4dn.xlarge' },
            { id:'NFR-01-02', label:'Throughput — ≥ 100 frags/min',        ok:true, val:'142 frags/min (CodeBERT batched)' },
            { id:'NFR-01-03', label:'Sub-linear comparison',                ok:true, val:'LSH index · O(n log n)' },
            { id:'NFR-02-01', label:'Precision ≥ 85%, Recall ≥ 80%',       ok:true, val:'P=89% R=93% ✓' },
            { id:'NFR-02-02', label:'Deterministic results',                ok:true, val:'Seed fixed · reproducible' },
            { id:'NFR-02-03', label:'False positive rate < 10%',            ok:true, val:'FPR = 7.2%' },
            { id:'NFR-03-01', label:'Encryption AES-256 + TLS 1.3',        ok:true, val:'AWS KMS + CloudFront' },
            { id:'NFR-03-02', label:'Auto-delete after 30 days',            ok:true, val:'Lambda scheduled job active' },
            { id:'NFR-05-01', label:'99.5% uptime during peak',             ok:true, val:'Current: 99.8% ✓' },
            { id:'NFR-06-01', label:'Test coverage ≥ 70%',                  ok:true, val:'74.3% (pytest + JUnit)' },
            { id:'NFR-07-01', label:'Dockerised + docker-compose',          ok:true, val:'Dockerfile present' },
            { id:'NFR-08-01', label:'Intelligent GPU batching',             ok:true, val:'Dynamic batch size auto-tuned' },
          ].map(n=>(
            <div key={n.id} className={`flex items-start gap-3 p-3 rounded-lg border ${n.ok?'border-success/20 bg-success/[.04]':'border-rose/20 bg-rose/[.04]'}`}>
              <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-[9px] font-bold ${n.ok?'bg-success/20 text-success':'bg-rose/20 text-rose'}`}>
                {n.ok?'✓':'✕'}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold font-mono text-t3">{n.id}</span>
                  <span className="text-xs text-t1">{n.label}</span>
                </div>
                <div className="text-[10px] text-t3 font-mono mt-0.5">{n.val}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function BarCell({ val, proposed }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-b2 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width:`${val*100}%`, background: proposed?'#00d4ff':'#2a3449' }}/>
      </div>
      <span className={`font-mono font-bold text-xs ${proposed?'text-accent':'text-t2'}`}>{val.toFixed(2)}</span>
    </div>
  )
}
