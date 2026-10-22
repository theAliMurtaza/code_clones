// Cosmetic highlighting must preserve every character of the uploaded source.
export function highlightSegments(text) {
  const pattern = /(?<comment>#[^\n]*|\/\/[^\n]*|\/\*[\s\S]*?\*\/)|(?<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(?<keyword>\b(?:def|class|return|if|elif|else|for|while|try|except|import|from|in|not|and|or|True|False|None|with|as|pass|raise|yield|lambda|async|await|public|private|protected|static|void|int|String|boolean|List|Map|new|catch|finally|throws|extends|implements|this|super|null|true|false)\b)|(?<function>\b[a-zA-Z_]\w*(?=\s*\())|(?<number>\b\d+(?:\.\d+)?\b)/g
  const segments = []
  let last = 0
  for (const match of text.matchAll(pattern)) {
    if (match.index > last) segments.push({ kind: 'plain', text: text.slice(last, match.index) })
    const kind = Object.keys(match.groups).find(key => match.groups[key] !== undefined) || 'plain'
    segments.push({ kind, text: match[0] })
    last = match.index + match[0].length
  }
  if (last < text.length) segments.push({ kind: 'plain', text: text.slice(last) })
  return segments
}
