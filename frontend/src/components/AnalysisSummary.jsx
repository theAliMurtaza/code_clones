export default function AnalysisSummary({ result }) {
  const info = result.analysis_info || {}
  const status = { embedding: 'Candidates', classifier: 'Candidates', structural: 'Not checked', not_run: 'No eligible pairs' }[info.mode] || 'Status unavailable'
  const counts = [
    ['Semantic pairs checked', info.semantic_pairs_checked],
    ['Type-4 candidates', result.type4_count],
    ['Rejected by checks', info.behavioral_rejections],
    ['Insufficient evidence', info.behavioral_inconclusive],
    ['Sample-supported', info.behavioral_consistent],
    ['Classifier-supported', info.classifier_supported],
  ].filter(([, value]) => value != null)
  return <section className="analysis-summary" aria-label="Analysis summary">
    <div className="analysis-summary-heading"><h2>Analysis overview</h2><span>Type-4 · {status}</span></div>
    {counts.length > 0 && <dl className="analysis-counts">{counts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{Number(value).toLocaleString()}</dd></div>)}</dl>}
    <div className="analysis-summary-footer">
      <span>{result.files?.length || 0} files · {result.total_fragments ?? 0} code regions</span>
      {info.comparison_scope === 'within_and_across_files' && <span>Within & across files</span>}
      {info.semantic_threshold != null && <span>Model cutoff {Math.round(info.semantic_threshold * 100)}%</span>}
      {info.semantic_corroborated_threshold != null && <span>Sample-supported cutoff {Math.round(info.semantic_corroborated_threshold * 100)}%</span>}
    </div>
  </section>
}
