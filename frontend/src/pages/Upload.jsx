import { useState, useCallback, useRef } from 'react'
import { useApp } from '../context/AppContext'
import { api } from '../utils/api'
import { Spinner } from '../components/UI'
import { SUPPORTED_EXTS } from '../utils/data'

// Recursively traverse directory entries from drag-and-drop
async function getFilesFromDataTransfer(items) {
  const filesWithPaths = []
  async function traverseEntry(entry, currentPath = '') {
    if (entry.isFile) {
      const file = await new Promise((resolve, reject) => entry.file(resolve, reject))
      const relPath = currentPath ? `${currentPath}/${file.name}` : file.name
      filesWithPaths.push({ file, path: relPath })
    } else if (entry.isDirectory) {
      const dirReader = entry.createReader()
      const entries = await new Promise((resolve, reject) => {
        const result = []
        const readBatch = () => {
          dirReader.readEntries((batch) => {
            if (!batch || batch.length === 0) {
              resolve(result)
            } else {
              result.push(...batch)
              readBatch()
            }
          }, reject)
        }
        readBatch()
      })
      const nextPath = currentPath ? `${currentPath}/${entry.name}` : entry.name
      for (const child of entries) {
        await traverseEntry(child, nextPath)
      }
    }
  }

  const entries = []
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.webkitGetAsEntry) {
      const entry = item.webkitGetAsEntry()
      if (entry) entries.push(entry)
    } else if (item.getAsFile) {
      const file = item.getAsFile()
      if (file) filesWithPaths.push({ file, path: file.name })
    }
  }

  for (const entry of entries) {
    await traverseEntry(entry)
  }

  return filesWithPaths
}

export default function Upload() {
  const {
    uploadedFiles, setUploadedFiles,
    threshold, setThreshold,
    setCurrentJobId, setJobProgress,
    setPage, toast, getToken,
    isAuthed, openAuthModal,
  } = useApp()

  const [inputTab, setInputTab] = useState('upload') // 'upload' | 'local'
  const [localFolderPath, setLocalFolderPath] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [extractStats, setExtractStats] = useState(null) // { total, codeCount, skippedCount, folderName }

  const fileInputRef = useRef(null)
  const folderInputRef = useRef(null)

  // Process files or file-with-path objects
  const processAndAddFiles = useCallback((items, folderHint = '') => {
    let rawList = []
    if (items.length && items[0].file) {
      rawList = items.map(item => ({
        raw: item.file,
        path: (item.path || item.file.webkitRelativePath || item.file.name).replace(/\\/g, '/'),
      }))
    } else {
      rawList = Array.from(items).map(f => ({
        raw: f,
        path: (f.webkitRelativePath || f.name).replace(/\\/g, '/'),
      }))
    }

    let codeCount = 0
    let skippedCount = 0
    const added = []

    for (const item of rawList) {
      const f = item.raw
      const p = item.path.replace(/^\/+/, '')
      const ext = p.split('.').pop().toLowerCase()
      const isCode = SUPPORTED_EXTS.some(e => p.toLowerCase().endsWith(e.toLowerCase()))

      if (isCode) {
        codeCount++
        const parts = p.split('/')
        const name = parts[parts.length - 1]
        const dir = parts.length > 1 ? parts.slice(0, -1).join('/') + '/' : ''
        added.push({
          name,
          path: p,
          dir,
          size: f.size > 1024 ? (f.size / 1024).toFixed(1) + ' KB' : f.size + ' B',
          ext: ext.toUpperCase(),
          valid: true,
          raw: f,
        })
      } else {
        skippedCount++
      }
    }

    if (added.length === 0) {
      toast(
        'No coding files found',
        `No supported files (${SUPPORTED_EXTS.join(', ')}) extracted.`,
        'warn'
      )
      return
    }

    setUploadedFiles(prev => {
      const existing = new Set(prev.map(x => x.path || x.name))
      const fresh = added.filter(x => {
        if (existing.has(x.path)) return false
        existing.add(x.path)
        return true
      })
      return [...prev, ...fresh]
    })

    const folderName = folderHint || (added[0]?.path?.includes('/') ? added[0].path.split('/')[0] : '')
    setExtractStats({
      total: rawList.length,
      codeCount,
      skippedCount,
      folderName,
    })

    if (skippedCount > 0) {
      toast(
        `Extracted ${codeCount} coding file(s)`,
        `Filtered out ${skippedCount} non-coding/binary files`,
        'success'
      )
    } else {
      toast(`${codeCount} coding file(s) added`, 'Ready for clone detection', 'success')
    }

    if (!isAuthed) {
      openAuthModal('login')
    }
  }, [setUploadedFiles, toast, isAuthed, openAuthModal])

  const onDrop = useCallback(async (e) => {
    e.preventDefault()
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      try {
        const filesWithPaths = await getFilesFromDataTransfer(e.dataTransfer.items)
        if (filesWithPaths.length > 0) {
          processAndAddFiles(filesWithPaths, 'Dropped Folder')
          return
        }
      } catch (err) {
        toast('Folder could not be read', err.message || 'Please select the folder again.', 'error')
        return
      }
    }
    if (e.dataTransfer.files?.length > 0) {
      processAndAddFiles(e.dataTransfer.files)
    }
  }, [processAndAddFiles, toast])

  const removeFile = (i) => {
    setUploadedFiles(p => p.filter((_, j) => j !== i))
  }

  const clearAllFiles = () => {
    setUploadedFiles([])
    setExtractStats(null)
  }

  const executeDetection = async (authToken) => {
    const valid = uploadedFiles.filter(f => f.valid)
    if (valid.length === 0) {
      toast('No valid files', 'Add .py or .java files first', 'warn')
      return
    }
    const token = authToken || getToken()
    if (!token) {
      openAuthModal('login', () => executeDetection())
      return
    }

    setIsSubmitting(true)
    try {
      toast('Submitting analysis…', `${valid.length} file(s) queued with directory paths`)
      const rawFiles = valid.map(f => f.raw)
      const filePaths = valid.map(f => f.path || f.name)
      const res = await api.detect(rawFiles, threshold, token, filePaths)
      setCurrentJobId(res.job_id)
      setJobProgress(null)
      setPage('detection')
    } catch (err) {
      toast('Submission failed', err.message, 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  const runAnalysis = async () => {
    const valid = uploadedFiles.filter(f => f.valid)
    if (valid.length === 0) {
      toast('No valid files', 'Add .py or .java files first', 'warn')
      return
    }
    if (!isAuthed) {
      toast('Authentication required', 'Please sign in or create an account to run analysis', 'info')
      openAuthModal('login', () => executeDetection())
      return
    }
    executeDetection()
  }

  const runLocalFolderAnalysis = async () => {
    const trimmed = localFolderPath.trim()
    if (!trimmed) {
      toast('Path required', 'Enter a local folder path to scan', 'warn')
      return
    }
    const token = getToken()
    if (!token) {
      toast('Authentication required', 'Please sign in to scan local folders', 'info')
      openAuthModal('login', () => runLocalFolderAnalysis())
      return
    }

    setIsSubmitting(true)
    try {
      toast('Scanning folder…', `Extracting coding files from ${trimmed}`)
      const res = await api.detectFolder(trimmed, threshold, token)
      setCurrentJobId(res.job_id)
      setJobProgress(null)
      setPage('detection')
    } catch (err) {
      toast('Folder scan failed', err.message, 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="animate-fadeUp max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-t1 tracking-tight">Code Clone Analysis Input</h1>
          <p className="text-xs text-t3 font-mono mt-0.5">
            Select a project folder or source files to automatically extract and detect semantic code clones
          </p>
        </div>

        {/* Input mode selector tabs */}
        <div className="flex p-1 bg-s2 border border-b1 rounded-xl gap-1">
          <button
            onClick={() => setInputTab('upload')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
              inputTab === 'upload'
                ? 'bg-surface text-accent shadow-sm border border-b1'
                : 'text-t3 hover:text-t1'
            }`}
          >
            Folder & Files Upload
          </button>
          <button
            onClick={() => setInputTab('local')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
              inputTab === 'local'
                ? 'bg-surface text-accent shadow-sm border border-b1'
                : 'text-t3 hover:text-t1'
            }`}
          >
            Scan Local Directory
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Upload / Path Input */}
        <div className="lg:col-span-7 space-y-4">
          {inputTab === 'upload' ? (
            <>
              {/* Drop Zone */}
              <div
                onDrop={onDrop}
                onDragOver={e => e.preventDefault()}
                className="border-2 border-dashed border-b2 rounded-2xl p-8 text-center bg-surface/60 hover:bg-accent/[.02] hover:border-accent/40 transition-all group"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  hidden
                  accept=".py,.java"
                  onChange={e => e.target.files && processAndAddFiles(e.target.files)}
                />
                <input
                  ref={folderInputRef}
                  type="file"
                  webkitdirectory=""
                  directory=""
                  multiple
                  hidden
                  onChange={e => {
                    if (e.target.files && e.target.files.length > 0) {
                      const sample = e.target.files[0]
                      const fName = sample.webkitRelativePath ? sample.webkitRelativePath.split('/')[0] : ''
                      processAndAddFiles(e.target.files, fName)
                    }
                  }}
                />

                <div className="w-14 h-14 rounded-2xl bg-accent/10 border border-accent/20 flex items-center justify-center mx-auto mb-3.5 group-hover:scale-105 transition-transform text-accent">
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                    <line x1="12" y1="11" x2="12" y2="17"/>
                    <line x1="9" y1="14" x2="15" y2="14"/>
                  </svg>
                </div>

                <div className="text-sm font-semibold text-t1 mb-1">
                  Drop folder or source files here
                </div>
                <p className="text-xs text-t3 font-mono mb-4 max-w-md mx-auto">
                  Drag & drop an entire project folder. The system will recursively scan and extract coding files from it.
                </p>

                <div className="flex flex-wrap items-center justify-center gap-3">
                  <button
                    type="button"
                    onClick={() => folderInputRef.current?.click()}
                    className="btn btn-primary btn-sm"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                    </svg>
                    Select Folder
                  </button>

                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="btn btn-ghost btn-sm"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    Select Files
                  </button>
                </div>

                <div className="flex items-center justify-center gap-2 mt-4 pt-3 border-t border-b1/60">
                  <span className="text-[10px] font-mono text-t3">Coding files extracted:</span>
                  {SUPPORTED_EXTS.map(e => (
                    <span key={e} className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-s2 border border-b1 text-t2">
                      {e}
                    </span>
                  ))}
                </div>
              </div>

              {/* Extraction Feedback Banner */}
              {extractStats && (
                <div className="p-3.5 bg-accent/5 border border-accent/20 rounded-xl flex items-center justify-between gap-3 text-xs font-mono">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="w-2 h-2 rounded-full bg-success flex-shrink-0 animate-pulse2" />
                    <span className="text-t1 truncate">
                      Extracted <strong>{extractStats.codeCount}</strong> coding files from{' '}
                      <span className="text-accent">{extractStats.folderName || 'folder'}</span>
                      {extractStats.skippedCount > 0 && (
                        <span className="text-t3 ml-1 font-normal">
                          ({extractStats.skippedCount} non-coding files skipped)
                        </span>
                      )}
                    </span>
                  </div>
                  <button
                    onClick={() => setExtractStats(null)}
                    className="text-t3 hover:text-t1 flex-shrink-0 text-base leading-none"
                  >
                    ×
                  </button>
                </div>
              )}
            </>
          ) : (
            /* Local Directory Path Input */
            <div className="card p-6 space-y-4">
              <div className="space-y-1">
                <label className="lbl">Local Project Directory Path</label>
                <p className="text-xs text-t3 font-mono">
                  Enter the directory path on the API server. The engine will scan subdirectories and extract all coding files.
                </p>
              </div>

              <div className="space-y-2">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-t3 font-mono text-xs">
                    📁
                  </div>
                  <input
                    type="text"
                    value={localFolderPath}
                    onChange={e => setLocalFolderPath(e.target.value)}
                    placeholder="e.g. D:/my_repo/src or C:\projects\sample"
                    className="inp pl-9 text-xs"
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono text-t3">
                  <span>Supported files (.py, .java) will be automatically detected</span>
                  {localFolderPath && (
                    <button
                      onClick={() => setLocalFolderPath('')}
                      className="text-rose hover:underline"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              <div className="p-3.5 bg-s2 border border-b1 rounded-xl text-xs font-mono text-t2 space-y-1.5">
                <div className="font-semibold text-t1 flex items-center gap-1.5">
                  <span>💡 How folder scanning works:</span>
                </div>
                <div className="text-[11px] text-t3 leading-relaxed">
                  1. Scans the root folder and all child directories recursively.
                  <br />
                  2. Includes Python and Java files in every subfolder; skips other file types.
                  <br />
                  3. Preserves full relative file paths so clone locations are crystal-clear.
                </div>
              </div>

              <button
                onClick={runLocalFolderAnalysis}
                disabled={!localFolderPath.trim() || isSubmitting}
                className="btn btn-primary w-full justify-center btn-lg"
              >
                {isSubmitting ? (
                  <>
                    <Spinner size={16} className="text-white" />
                    Scanning & Analyzing…
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <circle cx="11" cy="11" r="8"/>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    Scan Local Folder & Detect Clones
                  </>
                )}
              </button>
            </div>
          )}

          {/* Extracted Files List with File Paths */}
          {inputTab === 'upload' && uploadedFiles.length > 0 && (
            <div className="card overflow-hidden">
              <div className="card-header">
                <div className="flex items-center gap-2">
                  <span className="card-title">Extracted Files ({uploadedFiles.length})</span>
                </div>
                <button
                  onClick={clearAllFiles}
                  className="text-[11px] font-mono text-t3 hover:text-rose transition-colors"
                >
                  Clear All
                </button>
              </div>

              <div className="p-2 space-y-1 max-h-72 overflow-y-auto divide-y divide-b1/40">
                {uploadedFiles.map((f, i) => (
                  <div
                    key={f.path || i}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-s2/60 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-lg bg-s3 flex items-center justify-center text-[9px] font-bold font-mono text-accent flex-shrink-0 border border-b1">
                      {f.ext}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-mono text-t1 truncate" title={f.path || f.name}>
                        {f.dir && <span className="text-t3 opacity-80">{f.dir}</span>}
                        <span className="font-semibold">{f.name}</span>
                      </div>
                      <div className="text-[10px] text-t3 font-mono flex items-center gap-2 mt-0.5">
                        <span>{f.size}</span>
                        {f.dir && <span className="truncate max-w-[200px] text-accent/80">path: {f.path}</span>}
                      </div>
                    </div>

                    <button
                      onClick={() => removeFile(i)}
                      title="Remove file"
                      className="text-t3 hover:text-rose transition-colors text-lg leading-none p-1"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column (5 cols): Parameters & Execution */}
        <div className="lg:col-span-5 space-y-5">
          <div className="card p-5 space-y-5">
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="lbl mb-0">Similarity Threshold</label>
                <span className="text-xs font-bold font-mono text-accent">
                  {Math.round(threshold * 100)}%
                </span>
              </div>
              <input
                type="range"
                min={40}
                max={99}
                value={Math.round(threshold * 100)}
                onChange={e => setThreshold(Number(e.target.value) / 100)}
                className="w-full h-1.5 rounded-full bg-s3 appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[10px] font-mono text-t3 mt-1.5">
                <span>40% (Semantic / Broad)</span>
                <span>99% (Exact Copy)</span>
              </div>
            </div>

            <div className="p-3.5 bg-s2 rounded-xl border border-b1 space-y-2 text-[11px] font-mono text-t2">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-success flex-shrink-0"/>
                <span>Automatic coding file extraction from folders</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0"/>
                <span>Full relative file paths preserved for every clone</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-violet flex-shrink-0"/>
                <span>Type-1 to Type-4 clone classification</span>
              </div>
            </div>

            {inputTab === 'upload' && (
              <button
                onClick={runAnalysis}
                disabled={uploadedFiles.filter(f => f.valid).length === 0 || isSubmitting}
                className="btn btn-primary w-full justify-center btn-lg"
              >
                {isSubmitting ? (
                  <>
                    <Spinner size={16} className="text-white" />
                    Submitting…
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                      <circle cx="11" cy="11" r="8"/>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    Run Clone Detection
                    {uploadedFiles.filter(f => f.valid).length > 0 && (
                      <span className="ml-1 text-white/80 font-normal">
                        ({uploadedFiles.filter(f => f.valid).length} coding file{uploadedFiles.filter(f => f.valid).length > 1 ? 's' : ''})
                      </span>
                    )}
                  </>
                )}
              </button>
            )}
          </div>

          <div className="p-4 bg-surface border border-b1 rounded-2xl text-[11px] font-mono text-t3 space-y-2">
            <div className="text-t1 font-semibold flex items-center gap-1.5">
              <span>📁 Folder Input Capabilities</span>
            </div>
            <p className="leading-relaxed">
              When uploading a folder, non-coding files (images, documentation, dependencies, git metadata) are automatically ignored. Only supported code files are compared against each other, and all results will show their complete file paths.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
