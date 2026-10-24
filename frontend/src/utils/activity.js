let sequence = 0
export function beginActivity(label = 'Working…') {
  const id = ++sequence
  window.dispatchEvent(new CustomEvent('clonescope:activity', { detail: { id, label, active: true } }))
  let finished = false
  return () => {
    if (finished) return
    finished = true
    window.dispatchEvent(new CustomEvent('clonescope:activity', { detail: { id, active: false } }))
  }
}
