import { useEffect, useState } from 'react'
import { Check, ArrowRight } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { pollJob } from '../utils/api'
import { ProgressBar, Spinner } from '../components/UI'

const STEPS = [
  ['queued', 'Queued'],
  ['extracting', 'Fragments'],
  ['tokenizing', 'Tokenizing'],
  ['structural', 'Comparing'],
  ['semantic', 'Model analysis'],
  ['preparing', 'Results'],
  ['complete', 'Complete'],
]
const DESCRIPTIONS = {
  queued: 'Your files are queued for the analysis engine.',
  extracting: 'Extracting code fragments from your files.',
  tokenizing: 'Tokenizing code and preparing identifiers for comparison.',
  structural: 'Comparing fragments for Type-1, Type-2, and Type-3 clones.',
  semantic: 'Running model inference and checking Type-4 candidates.',
  preparing: 'Preparing clone pairs and saving your results.',
}

export default function Detection() {
  const { currentJobId, jobProgress, setJobProgress, setJobResults, setPage, toast, getToken } = useApp()
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!currentJobId) { setPage('upload'); return }
    let finished = false
    setSeconds(0)
    const started = Date.now()
    const timer = setInterval(() => {
      if (!finished) setSeconds(Math.floor((Date.now() - started) / 1000))
    }, 1000)
    const cancel = pollJob(currentJobId, getToken(), {
      onProgress: setJobProgress,
      onDone: data => {
        finished = true
        setJobResults(data); setJobProgress(data)
      },
      onError: err => { toast('Analysis couldn’t finish', err.message, 'error'); setPage('upload') },
      intervalMs: 2000,
    })
    return () => { cancel(); clearInterval(timer) }
  }, [currentJobId])

  const status = jobProgress?.status || 'queued'
  const isDone = status === 'done'
  const progress = jobProgress?.analysis_info?.progress
  const stage = isDone ? 'complete' : status === 'queued' ? 'queued' : progress?.stage
  const stepIdx = STEPS.findIndex(([key]) => key === stage)
  const skipped = progress?.skipped_stages || []
  const pct = stepIdx < 0 ? 0 : stepIdx / (STEPS.length - 1) * 100

  return <div className="animate-fadeUp max-w-3xl mx-auto mt-8 sm:mt-12">
    <section className="card p-5 sm:p-8" aria-label="Analysis progress">
      <div className="flex justify-center mb-6">
        <div className={'w-16 h-16 rounded-2xl flex items-center justify-center border ' +
          (isDone ? 'bg-success/10 border-success/25 text-success' : 'bg-accent/10 border-accent/20 text-accent')}>
          {isDone ? <Check size={32}/> : <Spinner size={32}/>}
        </div>
      </div>

      <div role="status" aria-live="polite">
        <h2 className="text-lg font-bold text-t1 text-center mb-2">
          {isDone ? 'Analysis Complete' : 'Analysing Your Code…'}
        </h2>
        <p className="text-sm text-t2 text-center mb-6">
          {isDone ? `${jobProgress.total_pairs} clone pairs detected in ${jobProgress.runtime_seconds ?? seconds}s`
            : DESCRIPTIONS[stage] || 'The analysis engine is comparing your code.'}
        </p>
      </div>

      <div className="mb-6" aria-label="Analysis stages" role="progressbar"
        aria-valuemin={0} aria-valuemax={6} aria-valuenow={stepIdx >= 0 ? stepIdx : undefined}
        aria-valuetext={isDone ? 'Complete' : STEPS[stepIdx]?.[1] || 'Analysis in progress'}>
        <ProgressBar pct={pct} color={isDone ? '#22c55e' : '#3b82f6'} animated={!isDone}/>
      </div>

      <ol className="grid grid-cols-4 sm:grid-cols-7 gap-y-5 mb-8" aria-label="Processing steps">
        {STEPS.map(([key, label], i) => {
          const isSkipped = skipped.includes(key)
          const complete = !isSkipped && (isDone || i < stepIdx)
          const active = !isDone && i === stepIdx
          return <li key={key} className="relative flex flex-col items-center text-center min-w-0"
            aria-current={active ? 'step' : undefined}>
            {i < STEPS.length - 1 && <div aria-hidden="true" className={'hidden sm:block absolute h-0.5 top-3.5 left-1/2 w-full ' + (i < stepIdx ? 'bg-accent' : 'bg-s3')}/>}
            <div className={'relative z-10 w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-semibold transition-colors ' +
              (complete ? 'bg-accent border-accent text-white' : active ? 'border-accent text-accent bg-surface ring-4 ring-accent/10' : 'border-b2 text-t3 bg-s2')}>
              {isSkipped ? '–' : complete ? <Check size={15}/> : i + 1}
            </div>
            <span className={'text-[10px] sm:text-[11px] mt-2 px-1 ' + (active || complete ? 'text-t1' : 'text-t3')}>{label}</span>
            <span className="text-[9px] text-t3 mt-1">{isSkipped ? 'Not needed' : complete ? 'Done' : active ? (key === 'queued' ? 'Waiting' : 'Running') : 'Pending'}</span>
          </li>
        })}
      </ol>

      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          ['Fragments', jobProgress?.total_fragments > 0 || isDone ? jobProgress.total_fragments : '—'],
          ['Pairs Found', isDone ? jobProgress.total_pairs : '—'],
          [isDone ? 'Runtime' : 'Elapsed', `${isDone ? jobProgress.runtime_seconds ?? seconds : seconds}s`],
        ].map(([label, value]) => <div key={label} className="text-center p-3 bg-s2 rounded-xl border border-b1">
          <div className="text-lg font-bold font-mono text-accent" aria-live="off">{value}</div>
          <div className="text-[10px] text-t3 mt-1.5">{label}</div>
        </div>)}
      </div>

      {isDone ? <button onClick={() => setPage('results')} className="btn btn-primary w-full justify-center btn-lg">
        View Clone Results <ArrowRight size={16}/>
      </button> : <button onClick={() => setPage('account')} className="btn btn-ghost w-full justify-center">
        Continue in background
      </button>}
    </section>
  </div>
}
