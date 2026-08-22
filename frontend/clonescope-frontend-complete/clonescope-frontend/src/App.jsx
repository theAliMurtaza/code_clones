import { AppProvider, useApp } from './context/AppContext'
import Sidebar from './components/Sidebar'
import { TopBar, Toasts } from './components/TopBar'
import Login     from './pages/Login'
import Dashboard from './pages/Dashboard'
import Upload    from './pages/Upload'
import Detection from './pages/Detection'
import Results   from './pages/Results'
import Benchmark from './pages/Benchmark'
import Account   from './pages/Account'
import './index.css'

const PAGES = { dashboard: Dashboard, upload: Upload, detection: Detection, results: Results, benchmark: Benchmark, account: Account }

function Layout() {
  const { page, isAuthed } = useApp()
  if (!isAuthed) return <Login />
  const Page = PAGES[page] || Dashboard
  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6"><Page key={page} /></main>
      </div>
      <Toasts />
    </div>
  )
}

export default function App() {
  return <AppProvider><Layout /></AppProvider>
}
