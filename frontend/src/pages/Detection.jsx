import { useEffect, useRef } from 'react'
import { useApp } from '../context/AppContext'
import { pollJob } from '../utils/api'
import { ProgressBar, Spinner } from '../components/UI'

const STEPS = ['Queued', 'Tokenizing', 'Embedding', 'Detecting', 'Complete']

export default function Detection() {
  const { currentJobId, jobProgress, setJobProgress, setJobResults, setPage, toast, getToken } = useApp()
  const cancelRef = useRef(null)

  useEffect(() => {
    if (!currentJobId) { setPage('upload'); return }
    const token = getToken()
    cancelRef.current = pollJob(currentJobId, token, {
      onProgress: data => setJobProgress(data),
      onDone: data => {
        setJobResults(data)
        setJobProgress(data)
        toast('Detection complete!', data.total_pairs + ' clone pairs found')
        setTimeout(() => setPage('results'), 800)
      },
      onError: err => {
        toast('Analysis failed', err.message, 'error')
        setPage('upload')
      },
      intervalMs: 2000,
    })
    return () => cancelRef.current?.()
  }, [currentJobId])

  const status  = jobProgress?.status || 'queued'
  const isDone  = status === 'done'
  const isFail  = status === 'failed'
  const stepIdx = { queued: 0, running: 2, done: 4, failed: 0 }[status] ?? 1
  const pct     = isDone ? 100 : status === 'running' ? 65 : 10

  return (
    <div className="animate-fadeUp max-w-2xl mx-auto mt-12">
      <div className="card p-8">
        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className={'w-16 h-16 rounded-2xl flex items-center justify-center ' +
            (isDone ? 'bg-success/10 border border-success/25' :
             isFail ? 'bg-rose/10 border border-rose/25' :
             'bg-accent/10 border border-accent/20')}>
            {isDone
              ? <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
              : isFail
              ? <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#e11d48" strokeWidth="2.5" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              : <Spinner size={32} className="text-accent"/>
            }
          </div>
        </div>

        {/* Status text */}
        <h2 className="text-lg font-bold text-t1 text-center mb-2">
          {isDone ? 'Analysis Complete' : isFail ? 'Analysis Failed' : 'Analysing Your Code…'}
        </h2>
        <p className="text-sm text-t3 font-mono text-center mb-8">
          {isDone
            ? jobProgress?.total_pairs + ' clone pairs detected in ' + jobProgress?.runtime_seconds + 's'
            : isFail
            ? jobProgress?.error || 'Something went wrong'
            : 'The analysis engine is comparing your code. This may take a moment.'}
        </p>

        {/* Progress bar */}
        <div className="mb-6">
          <ProgressBar pct={pct} color={isDone ? '#059669' : isFail ? '#e11d48' : '#2563eb'} animated={!isDone && !isFail}/>
        </div>

        {/* Step indicators */}
        <div className="flex items-center mb-8">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div className={'w-6 h-6 rounded-full border-2 flex items-center justify-center text-[10px] font-bold font-mono transition-all ' +
                  (i < stepIdx ? 'bg-accent border-accent text-white' :
                   i === stepIdx ? 'border-accent text-accent shadow-[0_0_0_3px_rgba(37,99,235,.1)]' :
                   'border-b2 text-t3 bg-s2')}>
                  {i < stepIdx ? '✓' : i + 1}
                </div>
                <div className={'text-[9px] font-mono mt-1.5 ' + (i <= stepIdx ? 'text-t2' : 'text-t3')}>{s}</div>
              </div>
              {i < STEPS.length - 1 && (
                <div className={'flex-1 h-0.5 mx-1 mb-4 transition-all ' + (i < stepIdx ? 'bg-accent' : 'bg-s3')}/>
              )}
            </div>
          ))}
        </div>

        {/* Stats if available */}
        {jobProgress?.total_fragments > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { label: 'Fragments', val: jobProgress.total_fragments },
              { label: 'Pairs Found', val: jobProgress.total_pairs ?? '…' },
              { label: 'Runtime', val: jobProgress.runtime_seconds ? jobProgress.runtime_seconds + 's' : '…' },
            ].map(s => (
              <div key={s.label} className="text-center p-3 bg-s2 rounded-xl border border-b1">
                <div className="text-lg font-bold font-mono text-accent">{s.val}</div>
                <div className="text-[10px] text-t3 font-mono mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {isDone && (
          <button onClick={() => setPage('results')} className="btn btn-primary w-full justify-center btn-lg">
            View Clone Results
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
            </svg>
          </button>
        )}
        {!isDone && !isFail && (
          <button onClick={() => setPage('upload')} className="btn btn-ghost w-full justify-center">
            Cancel
          </button>
        )}
      </div>
    </div>
  )
}
