export const SUPPORTED_EXTS = ['.py', '.java']

export const CLONE_TYPE_META = {
  'Type-1': { label: 'Exact Clone',    color: '#059669', desc: 'Identical code — only whitespace or comments differ' },
  'Type-2': { label: 'Renamed Clone',  color: '#2563eb', desc: 'Same structure, identifiers or literals renamed' },
  'Type-3': { label: 'Near-miss Clone',color: '#d97706', desc: 'Similar structure with statements added, removed, or modified' },
  'Type-4': { label: 'Semantic Clone', color: '#7c3aed', desc: 'Different implementation, functionally equivalent' },
}

export const BADGE_CLASS = {
  'Type-1': 'badge-type1',
  'Type-2': 'badge-type2',
  'Type-3': 'badge-type3',
  'Type-4': 'badge-type4',
}

export const STATUS_BADGE = {
  done:    'badge-green',
  complete:'badge-green',
  running: 'badge-blue',
  queued:  'badge-amber',
  failed:  'badge-rose',
}

export const BENCHMARK_DATA = [
  { tool: 'CloneScope (GraphCodeBERT)', approach: 'Two-stage: embed + pairwise clf', p: 0.89, r: 0.93, f1: 0.91, time: 4.2,  ours: true  },
  { tool: 'SourcererCC',               approach: 'Token-based',                      p: 0.71, r: 0.63, f1: 0.67, time: 12.8, ours: false },
  { tool: 'Deckard',                   approach: 'AST-based',                        p: 0.74, r: 0.68, f1: 0.71, time: 28.4, ours: false },
  { tool: 'CDLH',                      approach: 'AST + LSTM',                       p: 0.79, r: 0.75, f1: 0.77, time: 67.1, ours: false },
  { tool: 'CodeBERT (embedding only)', approach: 'Transformer embedding',            p: 0.84, r: 0.86, f1: 0.85, time: 9.1,  ours: false },
]

export const WEEKLY_ACTIVITY = [
  { day: 'Mon', v: 3 }, { day: 'Tue', v: 7 }, { day: 'Wed', v: 5 },
  { day: 'Thu', v: 12 }, { day: 'Fri', v: 9 }, { day: 'Sat', v: 4 }, { day: 'Sun', v: 8 },
]
