// CodeViewer — renders code with line numbers and highlighted clone lines.
import { highlightSegments } from '../utils/codeHighlight'

const TYPE_COLORS = {
  'Type-1': { bg: 'rgba(34,197,94,.12)',   border: '#22c55e', num: '#22c55e' },
  'Type-2': { bg: 'rgba(59,130,246,.12)',  border: '#3b82f6', num: '#3b82f6' },
  'Type-3': { bg: 'rgba(245,158,11,.12)',  border: '#f59e0b', num: '#f59e0b' },
  'Type-4': { bg: 'rgba(167,139,250,.12)', border: '#a78bfa', num: '#a78bfa' },
}

// Minimal syntax colouring (Python + Java) — dark theme colors
function ColourLine({ text }) {
  const colors = { plain: '#c9d8ef', comment: '#5e7494', string: '#34d399',
    keyword: '#60a5fa', function: '#86efac', number: '#fbbf24' }
  return <>{highlightSegments(text).map((segment, i) => (
    <span key={i} style={{ color: colors[segment.kind] || colors.plain,
      fontStyle: segment.kind === 'comment' ? 'italic' : undefined }}>{segment.text}</span>
  ))}</>
}

export default function CodeViewer({ lines = [], cloneLines = [], cloneType = 'Type-4', file = '', lang = '', onViewFull }) {
  const cloneSet = new Set(cloneLines)
  const colors   = TYPE_COLORS[cloneType] || TYPE_COLORS['Type-4']

  return (
    <div className="flex flex-col h-full min-h-0 min-w-0">
      {/* File header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-s2 border-b border-b1 flex-shrink-0">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" className="text-t3 flex-shrink-0">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <span className="text-[11px] font-mono text-t2 truncate flex-1 font-medium" title={file}>
          {file || 'unknown'}
        </span>
        {lang && <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-s3/80 text-t2 uppercase border border-b1">{lang}</span>}
        {onViewFull && <button type="button" onClick={onViewFull}
          className="text-[11px] font-mono text-accent whitespace-nowrap hover:underline">View full code</button>}
        {file && (
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(file)}
            title="Copy relative file path"
            className="text-[9px] font-mono text-t3 hover:text-accent px-1.5 py-0.5 rounded hover:bg-s3 transition-colors"
          >
            Copy Path
          </button>
        )}
        <span className="text-[9px] font-mono text-t3 flex-shrink-0">{lines.length} lines</span>
      </div>

      {/* Code body */}
      <div className="overflow-auto flex-1 min-h-0" style={{ background: '#0a0e14' }}>
        <table className="w-full border-collapse text-[11px] font-mono">
          <tbody>
            {lines.map(({ n, text }) => {
              const isClone = cloneSet.has(n)
              return (
                <tr key={n} style={isClone ? { background: colors.bg } : undefined}
                  className={isClone ? '' : 'hover:bg-white/[.02]'}>
                  {/* Line number gutter */}
                  <td className="select-none text-right pr-3 pl-3 py-0.5 min-w-[44px] border-r leading-6 sticky left-0"
                    style={{
                      borderColor: isClone ? colors.border : '#2a3448',
                      borderLeftWidth: isClone ? 2 : 0,
                      background: isClone ? colors.bg : '#0e1319',
                      color: isClone ? colors.num : '#4a5f7a',
                      fontWeight: isClone ? 600 : 400,
                    }}>
                    {n}
                  </td>
                  {/* Code */}
                  <td className="pl-4 pr-6 py-0.5 leading-6 whitespace-pre">
                    <ColourLine text={text} />
                  </td>
                  {/* Clone indicator */}
                  <td className="pr-3 py-0.5 leading-6 whitespace-nowrap">
                    {isClone && (
                      <span className="text-[9px] font-bold font-mono opacity-70"
                        style={{ color: colors.num }}>◀ clone</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
