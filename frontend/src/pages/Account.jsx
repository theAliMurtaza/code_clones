import { useState, useEffect } from 'react'
import { useApp } from '../context/AppContext'
import { api } from '../utils/api'
import { Badge, Spinner, EmptyState } from '../components/UI'
import { STATUS_BADGE } from '../utils/data'

export default function Account() {
  const { userName, getToken, logout, setPage, setJobResults, setCurrentJobId, toast, recentJobs, loadingDash, refreshDashboard } = useApp()
  const [deleting, setDeleting] = useState(null)

  useEffect(() => { refreshDashboard() }, [])

  const openJob = async (jobId) => {
    const token = getToken()
    try {
      const data = await api.job(jobId, token)
      setJobResults(data)
      setCurrentJobId(jobId)
      setPage('results')
    } catch (err) {
      toast('Could not load job', err.message, 'error')
    }
  }

  const deleteJob = async (jobId) => {
    if (!window.confirm('Delete this analysis and all its results?')) return
    setDeleting(jobId)
    try {
      await api.deleteJob(jobId, getToken())
      toast('Analysis deleted', 'All data removed')
      refreshDashboard()
    } catch (err) {
      toast('Delete failed', err.message, 'error')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="animate-fadeUp space-y-5">
      <div className="section-h">My Projects</div>

      <div className="grid grid-cols-3 gap-5">
        {/* Jobs list — spans 2 cols */}
        <div className="col-span-2 card">
          <div className="card-header">
            <div className="card-title">Analysis History</div>
            <div className="flex gap-2">
              <button onClick={refreshDashboard} disabled={loadingDash} className="btn btn-ghost btn-sm">
                {loadingDash ? <Spinner size={12}/> : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <polyline points="1 4 1 10 7 10"/>
                    <path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
                  </svg>
                )}
                Refresh
              </button>
              <button onClick={() => setPage('upload')} className="btn btn-primary btn-sm">
                + New Analysis
              </button>
            </div>
          </div>

          {loadingDash ? (
            <div className="p-10 flex items-center justify-center gap-3 text-t3 text-sm">
              <Spinner size={16}/> Loading…
            </div>
          ) : recentJobs.length === 0 ? (
            <EmptyState
              icon={
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
              }
              title="No analyses yet"
              sub="Upload Python or Java source files to run your first clone detection analysis."
              action={
                <button onClick={() => setPage('upload')} className="btn btn-primary btn-sm">
                  Start First Analysis
                </button>
              }
            />
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-b1">
                  {['Files', 'Clone Pairs', 'Type Breakdown', 'Status', 'Date', 'Actions'].map(h => (
                    <th key={h} className="text-left px-5 py-2.5 text-[9px] font-semibold font-mono text-t3 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentJobs.map(j => (
                  <tr key={j.id} className="border-b border-b1/50 hover:bg-s2/50 transition-colors">
                    <td className="px-5 py-3 max-w-[160px]">
                      <div className="truncate text-t1 font-medium text-xs">
                        {j.files?.join(', ') || 'Analysis ' + j.id?.slice(0, 6)}
                      </div>
                      <div className="text-[10px] text-t3 font-mono mt-0.5">
                        {j.total_fragments ?? 0} fragments
                      </div>
                    </td>
                    <td className="px-5 py-3 font-mono font-bold text-accent">
                      {j.total_pairs ?? '—'}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex gap-1.5 flex-wrap">
                        {[
                          { t: 'T1', n: j.type1_count, c: '#059669' },
                          { t: 'T2', n: j.type2_count, c: '#2563eb' },
                          { t: 'T3', n: j.type3_count, c: '#d97706' },
                          { t: 'T4', n: j.type4_count, c: '#7c3aed' },
                        ].filter(x => x.n > 0).map(x => (
                          <span key={x.t} className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                            style={{ background: x.c + '15', color: x.c, border: '1px solid ' + x.c + '30' }}>
                            {x.t}:{x.n}
                          </span>
                        ))}
                        {!j.type1_count && !j.type2_count && !j.type3_count && !j.type4_count && (
                          <span className="text-t3 text-[10px] font-mono">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <Badge type={STATUS_BADGE[j.status] ?? 'blue'}>{j.status}</Badge>
                    </td>
                    <td className="px-5 py-3 font-mono text-t3 text-[10px]">
                      <div>{j.created_at?.slice(0, 10) ?? ''}</div>
                      <div className="text-[9px]">{j.runtime_seconds ? j.runtime_seconds + 's' : ''}</div>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex gap-1.5">
                        {j.status === 'done' && (
                          <button onClick={() => openJob(j.id)} className="btn btn-ghost btn-sm">
                            View
                          </button>
                        )}
                        <button
                          onClick={() => deleteJob(j.id)}
                          disabled={deleting === j.id}
                          className="btn btn-danger btn-sm">
                          {deleting === j.id ? <Spinner size={11}/> : (
                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                              stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                              <polyline points="3 6 5 6 21 6"/>
                              <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
                            </svg>
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Right — profile card */}
        <div className="space-y-4">
          <div className="card p-6">
            <div className="card-title mb-5">Profile</div>

            {/* Avatar */}
            <div className="flex flex-col items-center mb-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-violet
                flex items-center justify-center text-2xl font-bold text-white mb-3 shadow-lg shadow-accent/15">
                {userName ? userName[0].toUpperCase() : 'U'}
              </div>
              <div className="text-sm font-semibold text-t1">{userName || 'User'}</div>
              <div className="text-[10px] text-t3 font-mono mt-0.5">researcher</div>
            </div>

            {/* Stats */}
            <div className="space-y-3 mb-5">
              {[
                { label: 'Total Analyses', val: recentJobs.length },
                { label: 'Completed',      val: recentJobs.filter(j => j.status === 'done').length },
                { label: 'Total Pairs',    val: recentJobs.reduce((a, j) => a + (j.total_pairs || 0), 0) },
              ].map(s => (
                <div key={s.label} className="flex items-center justify-between py-2 border-b border-b1 last:border-0">
                  <span className="text-xs text-t3 font-mono">{s.label}</span>
                  <span className="text-xs font-bold font-mono text-accent">{s.val}</span>
                </div>
              ))}
            </div>

            <button onClick={logout}
              className="btn btn-danger w-full justify-center">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              Sign Out
            </button>
          </div>

          {/* Security info */}
          <div className="card p-4">
            <div className="card-title mb-3">Security</div>
            <div className="space-y-2.5">
              {[
                { label: 'Encryption', val: 'AES-256 at rest' },
                { label: 'Transport',  val: 'TLS 1.3' },
                { label: 'Access',     val: 'RBAC isolated' },
                { label: 'Retention',  val: 'Auto-delete 30d' },
              ].map(s => (
                <div key={s.label} className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-success flex-shrink-0 animate-pulse2"/>
                  <span className="text-[10px] font-mono text-t3">{s.label}:</span>
                  <span className="text-[10px] font-mono text-t2">{s.val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
