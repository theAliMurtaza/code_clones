import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Btn, Toggle, Select, SectionH } from '../components/UI'

const SAMPLE = [
  {t:'KW',v:'def'},{t:'FN',v:'validate_token'},{t:'P',v:'('},{t:'ID',v:'VAR'},{t:'P',v:','},{t:'ID',v:'VAR'},{t:'P',v:')'},
  {t:'KW',v:'try'},{t:'OP',v:':'},{t:'ID',v:'VAR'},{t:'OP',v:'='},{t:'FN',v:'jwt.decode'},{t:'P',v:'('},
  {t:'ID',v:'VAR'},{t:'P',v:','},{t:'ID',v:'VAR'},{t:'P',v:')'},{t:'KW',v:'return'},{t:'ID',v:'VAR'},
  {t:'P',v:'['},{t:'STR',v:'"STR"'},{t:'P',v:']'},{t:'KW',v:'except'},{t:'KW',v:'return'},{t:'KW',v:'None'},
]

const TC = { KW:'text-violet/90', FN:'text-accent/80', ID:'text-emerald/80', STR:'text-amber/80', OP:'text-t3', P:'text-t3' }

export default function Preprocess() {
  const { tokCfg, setTokCfg, embedCfg, setEmbedCfg, setPage, toast } = useApp()
  const [tokens, setTokens] = useState([])
  const [running, setRunning] = useState(false)

  const tc = (k,v) => setTokCfg(p=>({...p,[k]:v}))
  const ec = (k,v) => setEmbedCfg(p=>({...p,[k]:v}))

  const run = () => {
    setRunning(true); setTokens([])
    SAMPLE.forEach((tk, i) => setTimeout(() => setTokens(p=>[...p,tk]), i*60))
    setTimeout(() => { setRunning(false); toast('Tokenization complete', `FR-02-01: ${SAMPLE.length} tokens extracted`) }, SAMPLE.length*60+100)
  }

  const embed = () => {
    toast('Generating embeddings…', `FR-03-01: ${embedCfg.model.toUpperCase()} · ${embedCfg.dims}-dim`)
    setTimeout(() => { toast('Embeddings cached ✓', 'FR-03-03: Redis cache hit ratio 84%'); setPage('detection') }, 1400)
  }

  return (
    <div className="animate-fadeUp space-y-4">
      <SectionH>FR-02 / FR-03 · Tokenization &amp; Embedding Pipeline</SectionH>

      <div className="grid grid-cols-2 gap-4">
        {/* Config */}
        <div className="card">
          <div className="card-header"><div className="card-title">Tokenizer Configuration · FR-02</div></div>
          <div className="card-body space-y-1">
            <Toggle label="Remove comments & blank lines" sublabel="FR-02-03" checked={tokCfg.removeComments} onChange={v=>tc('removeComments',v)}/>
            <Toggle label="Normalize identifiers → VAR" sublabel="FR-02-02" checked={tokCfg.normalizeIds} onChange={v=>tc('normalizeIds',v)}/>
            <Toggle label="Abstract string literals → STR" sublabel="FR-02-02" checked={tokCfg.abstractStrings} onChange={v=>tc('abstractStrings',v)}/>
            <Toggle label="Preserve control flow keywords" sublabel="FR-02-01" checked={tokCfg.keepControl} onChange={v=>tc('keepControl',v)}/>
            <Btn onClick={run} disabled={running} className="!w-full !justify-center !mt-4">
              {running ? 'Tokenizing…' : 'Run Tokenizer · FR-02-01'}
            </Btn>
          </div>
        </div>

        {/* Output */}
        <div className="card flex flex-col">
          <div className="card-header">
            <div className="card-title">Token Stream · FR-02-01</div>
            {tokens.length > 0 && <span className="text-[10px] font-mono text-success">{tokens.length} tokens</span>}
          </div>
          <div className="flex-1 p-4 bg-s2 flex flex-wrap gap-1.5 content-start overflow-y-auto min-h-[140px]">
            {tokens.length === 0
              ? <span className="text-xs font-mono text-t3 italic">→ Run tokenizer to see output…</span>
              : tokens.map((tk, i) => (
                <span key={i} className="inline-flex items-center gap-1.5 px-2 py-1 bg-s3 border border-b1 rounded text-[10px] font-mono">
                  <span className="text-t3 text-[8px]">{tk.t}</span>
                  <span className={TC[tk.t]||'text-t2'}>{tk.v}</span>
                </span>
              ))
            }
          </div>
        </div>

        {/* Embedding config */}
        <div className="card col-span-2">
          <div className="card-header"><div className="card-title">LLM Embedding Configuration · FR-03</div></div>
          <div className="card-body">
            <div className="grid grid-cols-3 gap-4 mb-4">
              <Select label="LLM Model · FR-03-01" value={embedCfg.model} onChange={v=>ec('model',v)}
                options={[{value:'codebert',label:'CodeBERT (Primary)'},{value:'gpt4o',label:'GPT-4o Embeddings'},{value:'unixcoder',label:'UniXcoder'}]}/>
              <Select label="Dimensions · FR-03-02" value={embedCfg.dims} onChange={v=>ec('dims',v)}
                options={['512','768','1024'].map(d=>({value:d,label:`${d}-dim`}))}/>
              <Select label="Cache Strategy · FR-03-03" value={embedCfg.cache} onChange={v=>ec('cache',v)}
                options={[{value:'redis',label:'Redis (recommended)'},{value:'memory',label:'In-Memory'},{value:'none',label:'Disabled'}]}/>
            </div>
            <div className="info-box mb-4">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round" className="flex-shrink-0">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <span><strong className="text-accent">NFR-08-01</strong> · Intelligent batching maximises GPU throughput (≥100 fragments/min · NFR-01-02). CodeBERT maps semantically equivalent code to nearby vector space — enabling cross-language Type-4 detection (FR-06-02).</span>
            </div>
            <Btn onClick={embed}>Generate Embeddings &amp; Continue →</Btn>
          </div>
        </div>
      </div>
    </div>
  )
}
