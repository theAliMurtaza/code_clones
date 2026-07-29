import { useApp } from '../context/AppContext'
import { Btn, Select, Input, SectionH } from '../components/UI'
import { EXTS, LANGS } from '../utils/data'

export default function Upload() {
  const { files, setFiles, gitUrl, setGitUrl, pasted, setPasted, lang, setLang, project, setProject, setPage, toast } = useApp()

  const addFiles = (fList) => {
    const added = Array.from(fList).map(f => ({
      name: f.name, ext: f.name.split('.').pop().toUpperCase(),
      size: f.size > 1024 ? (f.size/1024).toFixed(1)+' KB' : f.size+' B',
      valid: EXTS.some(e => f.name.endsWith(e)),
    }))
    setFiles(p => [...p, ...added])
    const inv = added.filter(f => !f.valid)
    if (inv.length) toast(`${inv.length} unsupported file(s)`, 'FR-01-02: Only .py .java .js .cpp .cs supported', 'warn')
    else toast(`${added.length} file(s) validated`, 'FR-01-01: Language check passed')
  }

  const validate = () => {
    if (!files.length && !pasted && !gitUrl) { toast('No source provided', 'Upload files, paste code, or enter a Git URL', 'warn'); return }
    toast('Validation passed ✓', 'FR-01-02: Language detected & files accepted')
    setTimeout(() => setPage('preprocess'), 600)
  }

  const cloneRepo = () => {
    if (!gitUrl) { toast('Enter a Git URL', '', 'warn'); return }
    toast('Cloning repository…', 'FR-01-01: Fetching from remote')
    setTimeout(() => {
      setFiles(p => [...p,
        { name:'auth.py',    ext:'PY',   size:'14.2 KB', valid:true },
        { name:'models.py',  ext:'PY',   size:'22.1 KB', valid:true },
        { name:'Service.java',ext:'JAVA',size:'18.7 KB', valid:true },
      ])
      toast('Cloned! 3 files found', 'FR-01-01: Python & Java detected')
    }, 1200)
  }

  return (
    <div className="animate-fadeUp">
      <SectionH>FR-01 · Source Code Ingestion &amp; Management</SectionH>

      {/* NFR security notice */}
      <div className="info-box mb-5">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round" className="flex-shrink-0 mt-0.5">
          <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
        </svg>
        <span><strong className="text-accent">NFR-03-01</strong> · All uploads encrypted with AES-256 at rest and TLS 1.3 in transit. Code is auto-deleted after 30 days (NFR-03-02).</span>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* LEFT */}
        <div className="space-y-4">
          {/* Drop zone */}
          <div
            onDrop={e => { e.preventDefault(); addFiles(e.dataTransfer.files) }}
            onDragOver={e => e.preventDefault()}
            onClick={() => document.getElementById('fi').click()}
            className="border-2 border-dashed border-b2 rounded-xl p-10 text-center cursor-pointer hover:border-accent/50 hover:bg-accent/[.03] transition-all group">
            <input id="fi" type="file" multiple hidden accept={EXTS.join(',')} onChange={e => addFiles(e.target.files)}/>
            <div className="w-12 h-12 rounded-xl bg-s3 border border-b1 flex items-center justify-center mx-auto mb-4 group-hover:border-accent/30 transition-colors">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <div className="text-sm font-semibold text-t1 mb-1">Drop source files here</div>
            <div className="text-xs text-t3 font-mono mb-4">or click to browse · FR-01-01</div>
            <div className="flex flex-wrap gap-1.5 justify-center">
              {EXTS.map(e => <span key={e} className="text-[9px] font-mono font-bold px-2 py-1 rounded bg-s3 border border-b1 text-t3">{e}</span>)}
            </div>
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="space-y-1.5 max-h-52 overflow-y-auto">
              {files.map((f, i) => (
                <div key={i} className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg border ${f.valid ? 'bg-s2 border-b1' : 'bg-rose/5 border-rose/25'}`}>
                  <div className="w-8 h-8 rounded-lg bg-s3 flex items-center justify-center text-[9px] font-bold font-mono text-accent flex-shrink-0">{f.ext}</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-t1 truncate">{f.name}</div>
                    <div className="text-[10px] text-t3 font-mono">{f.size} {!f.valid && <span className="text-rose">· unsupported</span>}</div>
                  </div>
                  <button onClick={() => setFiles(p => p.filter((_,j)=>j!==i))} className="text-t3 hover:text-rose text-lg leading-none">×</button>
                </div>
              ))}
            </div>
          )}

          {/* Git URL */}
          <div className="relative">
            <div className="absolute left-0 right-0 flex items-center gap-3 text-[11px] font-mono text-t3 -top-3 mx-4">
              <div className="flex-1 h-px bg-b1"/><span className="bg-surface px-2">or</span><div className="flex-1 h-px bg-b1"/>
            </div>
            <div className="pt-4 flex gap-2">
              <div className="flex-1">
                <label className="lbl">Git Repository URL · FR-01-01</label>
                <input className="inp" value={gitUrl} onChange={e=>setGitUrl(e.target.value)} placeholder="https://github.com/user/repo.git"/>
              </div>
              <Btn variant="ghost" size="sm" onClick={cloneRepo} className="!mt-[22px]">Clone</Btn>
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="space-y-4">
          <div>
            <label className="lbl">Paste Code · FR-01-01</label>
            <textarea className="inp resize-y !min-h-[160px]" value={pasted} onChange={e=>setPasted(e.target.value)} placeholder="# Paste source code here…"/>
          </div>
          <Select label="Language · FR-01-02" value={lang} onChange={setLang}
            options={LANGS.map(l=>({ value:l.toLowerCase().replace(/ /g,'_'), label:l }))}/>
          <Input label="Project Name · FR-01-03" value={project} onChange={setProject} placeholder="my-project"/>

          {files.length > 0 && (
            <div className="flex items-center gap-2 px-3.5 py-2.5 bg-success/5 border border-success/20 rounded-lg text-xs font-mono text-success">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              {files.filter(f=>f.valid).length} valid files in session · FR-01-03
            </div>
          )}
          <Btn onClick={validate} className="!w-full !justify-center">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            Validate &amp; Continue to Tokenizer
          </Btn>
        </div>
      </div>
    </div>
  )
}
