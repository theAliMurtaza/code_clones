import { CLONE_TYPES } from '../utils/data'

// Maps clone type → tailwind highlight class
const HIGHLIGHT_BG = {
  'Type-1': 'bg-success/18 border-l-2 border-success',
  'Type-2': 'bg-accent/18 border-l-2 border-accent',
  'Type-3': 'bg-amber/18 border-l-2 border-amber',
  'Type-4': 'bg-violet/18 border-l-2 border-violet',
}

const LINE_NUM_COLOR = {
  'Type-1': 'text-success',
  'Type-2': 'text-accent',
  'Type-3': 'text-amber',
  'Type-4': 'text-violet',
}

export default function CodeViewer({ lines = [], cloneLines = [], type = 'Type-1', file, lang = '' }) {
  const cloneSet = new Set(cloneLines)
  const hlBg = HIGHLIGHT_BG[type] || 'bg-accent/10 border-l-2 border-accent'
  const lnColor = LINE_NUM_COLOR[type] || 'text-accent'

  return (
    <div className="flex flex-col h-full">
      {/* File header */}
      <div className="flex items-center gap-2.5 px-4 py-2.5 bg-s3 border-b border-b1 shrink-0">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-t3">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
        </svg>
        <span className="text-xs font-mono text-t2 truncate flex-1">{file}</span>
        {lang && (
          <span className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded bg-b2 text-t3 uppercase tracking-wider">{lang}</span>
        )}
        <span className="text-[9px] font-mono text-t3">{lines.length} lines</span>
      </div>

      {/* Code */}
      <div className="overflow-auto flex-1 min-h-0">
        <table className="w-full border-collapse text-xs font-mono">
          <tbody>
            {lines.map(({ n, text }) => {
              const isClone = cloneSet.has(n)
              return (
                <tr
                  key={n}
                  className={`group transition-colors ${isClone ? '' : 'hover:bg-s3/60'}`}
                >
                  {/* Line number gutter */}
                  <td
                    className={`
                      select-none text-right pr-4 pl-4 py-0.5 min-w-[48px] border-r border-b1/50
                      text-[11px] leading-6 sticky left-0
                      ${isClone ? `${hlBg} ${lnColor} font-semibold` : 'text-t3 bg-s2'}
                    `}
                    style={{ userSelect: 'none' }}
                  >
                    {n}
                  </td>
                  {/* Code line */}
                  <td
                    className={`
                      pl-4 pr-6 py-0.5 leading-6 whitespace-pre
                      ${isClone ? hlBg : ''}
                    `}
                  >
                    <CodeLine text={text} isClone={isClone} />
                  </td>
                  {/* Clone indicator */}
                  {isClone && (
                    <td className="pr-3 py-0.5 leading-6 shrink-0">
                      <span className={`text-[9px] font-bold font-mono opacity-70 ${lnColor}`}>◀ clone</span>
                    </td>
                  )}
                  {!isClone && <td />}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Simple syntax coloriser for Python / Java / JS
function CodeLine({ text }) {
  const KW = /\b(def|class|return|if|elif|else|for|while|try|except|import|from|in|not|and|or|True|False|None|public|private|static|void|int|String|List|Map|new|throws|throw|catch|finally|function|const|let|var|typeof|async|await)\b/g
  const STR = /(["'`])(?:(?!\1)[^\\]|\\.)*\1/g
  const NUM = /\b\d+\.?\d*\b/g
  const CMT = /(#.*|\/\/.*)/g
  const FN  = /\b([a-zA-Z_]\w*)\s*(?=\()/g

  // Build colored spans via regex replacements
  let parts = []
  let i = 0
  const re = new RegExp(
    `(${CMT.source})|(${STR.source})|(${KW.source})|(${FN.source})|(${NUM.source})`,
    'g'
  )
  let match
  while ((match = re.exec(text)) !== null) {
    if (match.index > i) parts.push(<span key={i} className="text-t2">{text.slice(i, match.index)}</span>)
    const m = match[0]
    if (match[1]) parts.push(<span key={match.index} className="text-t3 italic">{m}</span>)
    else if (match[2] !== undefined) parts.push(<span key={match.index} className="text-amber/90">{m}</span>)
    else if (match[8] !== undefined) parts.push(<span key={match.index} className="text-violet/90 font-medium">{m}</span>)
    else if (match[9] !== undefined) parts.push(<span key={match.index} className="text-accent/80">{m}</span>)
    else if (match[10] !== undefined) parts.push(<span key={match.index} className="text-emerald/80">{m}</span>)
    i = match.index + m.length
  }
  if (i < text.length) parts.push(<span key={i} className="text-t2">{text.slice(i)}</span>)
  return <>{parts.length ? parts : <span className="text-t2">{text}</span>}</>
}
