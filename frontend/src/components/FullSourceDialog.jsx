import { useEffect, useRef, useState } from 'react'
import { api } from '../utils/api'
import CodeViewer from './CodeViewer'

export default function FullSourceDialog({ jobId, file, token, cloneLines = [], cloneType, onClose }) {
  const dialog = useRef(null)
  const [source, setSource] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    dialog.current.showModal()
    let active = true
    api.source(jobId, file, token).then(data => {
      if (active) setSource(data)
    }).catch(err => {
      if (active) setError(err.message)
    })
    return () => { active = false }
  }, [jobId, file, token])

  const lines = source?.content.split(/\r\n|\n|\r/).map((text, i) => ({ n: i + 1, text })) || []
  return (
    <dialog ref={dialog} onCancel={onClose} aria-labelledby="source-title"
      className="w-[95vw] max-w-6xl bg-surface text-t1 rounded-xl border border-b1 p-0 backdrop:bg-black/60">
      <div className="flex items-center justify-between gap-3 p-4 border-b border-b1">
        <div className="min-w-0">
          <h2 id="source-title" className="font-semibold">Full source code</h2>
          <p className="text-xs font-mono break-all mt-1">{file}</p>
        </div>
        <button autoFocus onClick={onClose} className="btn btn-ghost btn-sm">Close</button>
      </div>
      <div style={{ height: '70vh' }}>
        {error ? <p role="alert" className="p-6 text-rose">{error}</p>
          : source ? <CodeViewer lines={lines} file={file} lang={source.language}
              cloneLines={cloneLines} cloneType={cloneType} />
            : <p role="status" className="p-6 text-t3">Loading source code…</p>}
      </div>
    </dialog>
  )
}
