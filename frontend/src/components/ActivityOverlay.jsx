import { useApp } from '../context/AppContext'
import { Spinner } from './UI'

export default function ActivityOverlay() {
  const { activities } = useApp()
  if (!activities.length) return null
  return <div className="activity-overlay" aria-live="polite" role="status">
    <div className="activity-panel">
      <div className="activity-icon"><Spinner size={28} /></div>
      <h2>{activities[activities.length - 1].label}</h2>
      <p>Just a moment. We’re on it.</p>
    </div>
  </div>
}
