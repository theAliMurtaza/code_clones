import { useCallback } from 'react'
import { useApp } from '../context/AppContext'
import { api } from '../utils/api'
import { Spinner } from '../components/UI'
import { SUPPORTED_EXTS } from '../utils/data'

export default function Upload() {
  const {
    uploadedFiles, setUploadedFiles,
    threshold, setThreshold,
    setCurrentJobId, setJobProgress,
    setPage, toast, getToken,
  } = useApp()

  const addFiles = useCallback((fileList) => {
    const added = Array.from(fileList).map(f => ({
      name:  f.name,
      size:  f.size > 1024 ? (f.size / 1024).toFixed(1) + ' KB' : f.size + ' B',
      ext:   f.name.split('.').pop().toUpperCase(),
      valid: SUPPORTED_EXTS.some(e => f.name.endsWith(e)),
      raw:   f,
    }))
    setUploadedFiles(p => [...p, ...added])
    const inv = added.filter(f => !f.valid)
    if (inv.length) toast(inv.length + ' unsupported file(s)', 'Only .py and .java files are supported', 'warn')
    else toast(added.length + ' file(s) added', 'Ready to analyse')
  }, [setUploadedFiles, toast])

  const onDrop = useCallback(e => {
    e.preventDefault()
    addFiles(e.dataTransfer.files)
  }, [addFiles])

  const removeFile = i => setUploadedFiles(p => p.filter((_, j) => j !== i))

  const runAnalysis = async () => {
    const valid = uploadedFiles.filter(f => f.valid)
    if (valid.length === 0) { toast('No valid files', 'Add .py or .java files first', 'warn'); return }
    const token = getToken()
    if (!token) { toast('Not signed in', 'Please log in again', 'warn'); return }
    try {
      toast('Submitting analysis…', valid.length + ' file(s) queued')
      const rawFiles = valid.map(f => f.raw)
      const res = await api.detect(rawFiles, threshold, token)
      setCurrentJobId(res.job_id)
      setJobProgress(null)
      setPage('detection')
    } catch (err) {
      toast('Submission failed', err.message, 'error')
    }
  }

  return (
    <div className="animate-fadeUp">
      <div className="section-h">Upload Source Code</div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left — drop zone + file list */}
        <div className="space-y-4">
          <div
            onDrop={onDrop}
            onDragOver={e => e.preventDefault()}
            onClick={() => document.getElementById('fileInput').click()}
            className="border-2 border-dashed border-b2 rounded-xl p-10 text-center cursor-pointer
              hover:border-accent/40 hover:bg-accent/[.03] transition-all group">
            <input id="fileInput" type="file" multiple hidden
              accept=".py,.java"
              onChange={e => addFiles(e.target.files)} />
            <div className="w-12 h-12 rounded-xl bg-s2 border border-b1 flex items-center justify-center
              mx-auto mb-4 group-hover:border-accent/30 transition-colors">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb"
                strokeWidth="2" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <div className="text-sm font-semibold text-t1 mb-1">Drop source files here</div>
            <div className="text-xs text-t3 font-mono mb-4">or click to browse</div>
            <div className="flex gap-2 justify-center">
              {['.py','.java'].map(e => (
                <span key={e} className="text-[9px] font-mono font-bold px-2 py-1 rounded
                  bg-s2 border border-b1 text-t3">{e}</span>
              ))}
            </div>
          </div>

          {/* File list */}
          {uploadedFiles.length > 0 && (
            <div className="space-y-1.5 max-h-64 overflow-y-auto">
              {uploadedFiles.map((f, i) => (
                <div key={i} className={'flex items-center gap-3 px-3.5 py-2.5 rounded-lg border ' +
                  (f.valid ? 'bg-s2 border-b1' : 'border-rose/20') }
                  style={f.valid ? {} : { background: 'rgba(225,29,72,.04)' }}>
                  <div className="w-8 h-8 rounded-lg bg-s3 flex items-center justify-center
                    text-[9px] font-bold font-mono text-accent flex-shrink-0">{f.ext}</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-t1 truncate">{f.name}</div>
                    <div className="text-[10px] text-t3 font-mono">
                      {f.size}{!f.valid && <span className="text-rose ml-2">unsupported</span>}
                    </div>
                  </div>
                  <button onClick={() => removeFile(i)}
                    className="text-t3 hover:text-rose transition-colors text-lg leading-none">×</button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right — settings + run */}
        <div className="space-y-5">
          <div className="card p-5 space-y-5">
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="lbl mb-0">Similarity Threshold</label>
                <span className="text-xs font-bold font-mono text-accent">{Math.round(threshold * 100)}%</span>
              </div>
              <input type="range" min={50} max={99} value={Math.round(threshold * 100)}
                onChange={e => setThreshold(Number(e.target.value) / 100)}
                className="w-full h-1 rounded-full bg-s3 appearance-none cursor-pointer accent-accent"/>
              <div className="flex justify-between text-[10px] font-mono text-t3 mt-1.5">
                <span>50% — more pairs</span><span>99% — exact only</span>
              </div>
            </div>

            <div className="p-3.5 bg-s2 rounded-xl border border-b1 space-y-2 text-[11px] font-mono text-t2">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-success flex-shrink-0"/>
                Supported: Python (.py) and Java (.java)
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0"/>
                Cross-language detection enabled
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-violet flex-shrink-0"/>
                GraphCodeBERT semantic analysis
              </div>
            </div>
          </div>

          {/* Run button */}
          <button onClick={runAnalysis}
            disabled={uploadedFiles.filter(f => f.valid).length === 0}
            className="btn btn-primary w-full justify-center btn-lg">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            Run Clone Detection
            {uploadedFiles.filter(f => f.valid).length > 0 &&
              <span className="ml-1 text-white/70 font-normal">
                ({uploadedFiles.filter(f=>f.valid).length} file{uploadedFiles.filter(f=>f.valid).length>1?'s':''})
              </span>
            }
          </button>

          <p className="text-[11px] text-t3 font-mono text-center leading-relaxed">
            Files are encrypted in transit and automatically deleted after 30 days.
          </p>
        </div>
      </div>
    </div>
  )
}
