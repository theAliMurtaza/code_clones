import { useApp } from '../context/AppContext'
import { Spinner } from './UI'

export default function BackendStatusBanner() {
  const { backendStatus, wakeSeconds, retryBackendConnection } = useApp()

  if (backendStatus === 'connected' || backendStatus === 'checking') return null

  const isWaking = backendStatus === 'waking'

  return (
    <div className="bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border-b border-amber-500/20 px-4 py-2 text-xs font-mono">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 text-amber-600">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <span className="font-semibold">Backend Cold Starting:</span>
          <span className="text-t2 text-[11px]">
            {isWaking ? (
              <>
                The server is deployed on a free cloud instance (Render/Railway). It spins down when idle and takes <strong>~1 to 2 minutes</strong> to connect (elapsed: {wakeSeconds}s).
              </>
            ) : (
              'Backend is currently unreachable.'
            )}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={retryBackendConnection}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/15 hover:bg-amber-500/25 text-amber-700 text-[11px] font-semibold transition-colors"
          >
            <Spinner size={12} className="text-amber-600" />
            Check Connection
          </button>
        </div>
      </div>
    </div>
  )
}
