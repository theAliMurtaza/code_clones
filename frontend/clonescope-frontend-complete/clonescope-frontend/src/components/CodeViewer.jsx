// CodeViewer — renders code with line numbers and highlighted clone lines.
// Props:
//   lines       [{n: number, text: string}]  — from API code_lines_a / code_lines_b
//   cloneLines  [number]                      — line numbers to highlight
//   cloneType   "Type-1" | "Type-2" | "Type-3" | "Type-4"
//   file        string                        — filename shown in header
//   lang        string                        — language label

const TYPE_COLORS = {
  'Type-1': { bg: 'rgba(16,185,129,.12)',  border: '#10b981', num: '#10b981' },
  'Type-2': { bg: 'rgba(0,212,255,.12)',   border: '#00d4ff', num: '#00d4ff' },
  'Type-3': { bg: 'rgba(245,158,11,.12)',  border: '#f59e0b', num: '#f59e0b' },
  'Type-4': { bg: 'rgba(139,92,246,.12)',  border: '#8b5cf6', num: '#8b5cf6' },
}

// Minimal syntax colouring (Python + Java)
function ColourLine({ text }) {
  if (!text.trim()) return <span className="text-t2">&nbsp;</span>

  // Split into segments: keywords, strings, comments, numbers, functions, rest
  const segments = []
  let remaining = text
  let key = 0

  const PY_KW  = /\b(def|class|return|if|elif|else|for|while|try|except|import|from|in|not|and|or|True|False|None|with|as|pass|raise|yield|lambda|async|await)\b/
  const JAVA_KW = /\b(public|private|protected|static|void|int|String|boolean|List|Map|new|class|return|if|else|for|while|try|catch|finally|throws|import|extends|implements|this|super|null|true|false)\b/
  const STR    = /(["'`])(?:(?!\1)[^\\]|\\.)*?\1/
  const CMT    = /(#.*|\/\/.*|\/\*[\s\S]*?\*\/)/
  const NUM    = /\b\d+\.?\d*\b/
  const FN     = /\b([a-zA-Z_]\w*)\s*(?=\()/

  const combined = new RegExp(
    `(${CMT.source})|(${STR.source})|(${PY_KW.source})|(${JAVA_KW.source})|(${FN.source})|(${NUM.source})`,
    'g'
  )

  let last = 0, m
  while ((m = combined.exec(text)) !== null) {
    if (m.index > last) segments.push(<span key={key++} className="text-t2">{text.slice(last, m.index)}</span>)
    const v = m[0]
    if (m[1])  segments.push(<span key={key++} className="text-t3 italic">{v}</span>)
    else if (m[3] !== undefined) segments.push(<span key={key++} className="text-amber/80">{v}</span>)
    else if (m[5] !== undefined || m[6] !== undefined) segments.push(<span key={key++} className="text-violet/80 font-medium">{v}</span>)
    else if (m[7] !== undefined) segments.push(<span key={key++} className="text-accent/80">{v}</span>)
    else if (m[8] !== undefined) segments.push(<span key={key++} className="text-success/80">{v}</span>)
    else if (m[9] !== undefined) segments.push(<span key={key++} className="text-emerald/70">{v}</span>)
    last = m.index + v.length
  }
  if (last < text.length) segments.push(<span key={key++} className="text-t2">{text.slice(last)}</span>)
  return <>{segments.length ? segments : <span className="text-t2">{text}</span>}</>
}

export default function CodeViewer({ lines = [], cloneLines = [], cloneType = 'Type-4', file = '', lang = '' }) {
  const cloneSet = new Set(cloneLines)
  const colors   = TYPE_COLORS[cloneType] || TYPE_COLORS['Type-4']

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* File header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-s3 border-b border-b1 flex-shrink-0">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" className="text-t3 flex-shrink-0">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <span className="text-[11px] font-mono text-t2 truncate flex-1">{file || 'unknown'}</span>
        {lang && <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-b2 text-t3 uppercase">{lang}</span>}
        <span className="text-[9px] font-mono text-t3 flex-shrink-0">{lines.length} lines</span>
      </div>

      {/* Code body */}
      <div className="overflow-auto flex-1 min-h-0 bg-bg">
        <table className="w-full border-collapse text-[11px] font-mono">
          <tbody>
            {lines.map(({ n, text }) => {
              const isClone = cloneSet.has(n)
              return (
                <tr key={n} style={isClone ? { background: colors.bg } : undefined}
                  className={isClone ? '' : 'hover:bg-s3/40'}>
                  {/* Line number gutter */}
                  <td className="select-none text-right pr-3 pl-3 py-0.5 min-w-[44px] border-r leading-6 sticky left-0"
                    style={{
                      borderColor: isClone ? colors.border : '#1e2d3d',
                      borderLeftWidth: isClone ? 2 : 0,
                      background: isClone ? colors.bg : '#0f1117',
                      color: isClone ? colors.num : '#484f58',
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
                      <span className="text-[9px] font-bold font-mono opacity-60"
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
