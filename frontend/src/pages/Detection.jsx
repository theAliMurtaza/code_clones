import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { pollJob } from '../utils/api'
import { Spinner } from '../components/UI'

export default function Detection() {
  const { currentJobId, jobProgress, setJobProgress, setJobResults, setPage, toast, getToken } = useApp()
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!currentJobId) { setPage('upload'); return }
    const started = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000)
    const cancel = pollJob(currentJobId, getToken(), {
      onProgress: setJobProgress,
      onDone: data => {
        setJobResults(data); setJobProgress(data); setPage('results')
        toast('Your analysis is ready', `${data.total_pairs} pairs found. Open a pair to compare the code.`)
      },
      onError: err => { toast('Analysis couldn’t finish', err.message, 'error'); setPage('upload') },
      intervalMs: 2000,
    })
    return () => { cancel(); clearInterval(timer) }
  }, [currentJobId])
  return <div className="flex items-center justify-center min-h-[calc(100dvh-180px)]">
    <section className="activity-panel !w-full max-w-md" role="status" aria-live="polite">
      <div className="activity-icon"><Spinner size={34}/></div>
      <span className="text-xs text-emerald">{jobProgress?.status === 'running' ? 'Analysis in progress' : 'In the queue'}</span>
      <h2 className="mt-3">Comparing your code</h2>
      <p>We’ll open your results when the comparison is ready.</p>
      <div className="mt-6 py-4 border-y border-b1 flex justify-center gap-8 text-sm">
        <span>{jobProgress?.total_fragments || '—'} <span className="text-t2">code regions</span></span>
        <span aria-live="off">{seconds}s <span className="text-t2">elapsed</span></span>
      </div>
      <button onClick={() => setPage('account')} className="btn btn-ghost mt-6">Continue in background</button>
      <p className="!text-xs">You can return to this analysis from My Projects.</p>
    </section>
  </div>
}
