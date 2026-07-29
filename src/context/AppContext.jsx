import { createContext, useContext, useState, useCallback } from 'react'

const Ctx = createContext(null)

export function AppProvider({ children }) {
  const [page, setPage] = useState('dashboard')
  const [files, setFiles] = useState([])
  const [gitUrl, setGitUrl] = useState('')
  const [pasted, setPasted] = useState('')
  const [lang, setLang] = useState('auto')
  const [project, setProject] = useState('')
  const [tokCfg, setTokCfg] = useState({ removeComments:true, normalizeIds:true, abstractStrings:false, keepControl:true })
  const [embedCfg, setEmbedCfg] = useState({ model:'codebert', dims:'768', cache:'redis' })
  const [detCfg, setDetCfg] = useState({ threshold:82, metric:'cosine', opt:'lsh', crossLang:true, batch:'256' })
  const [toasts, setToasts] = useState([])
  const [activeClone, setActiveClone] = useState(null)

  const toast = useCallback((msg, sub='', type='success') => {
    const id = Date.now()
    setToasts(p => [...p, { id, msg, sub, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 4000)
  }, [])
  const removeToast = useCallback(id => setToasts(p => p.filter(t => t.id !== id)), [])

  const projects = [
    { id:1, name:'auth-service', lang:'Python', clones:247, date:'2025-06-01', status:'complete', f1:'0.91' },
    { id:2, name:'ml-pipeline',  lang:'Java',   clones:512, date:'2025-05-28', status:'complete', f1:'0.89' },
  ]

  return (
    <Ctx.Provider value={{
      page, setPage,
      files, setFiles,
      gitUrl, setGitUrl,
      pasted, setPasted,
      lang, setLang,
      project, setProject,
      tokCfg, setTokCfg,
      embedCfg, setEmbedCfg,
      detCfg, setDetCfg,
      toasts, toast, removeToast,
      activeClone, setActiveClone,
      projects,
    }}>
      {children}
    </Ctx.Provider>
  )
}

export const useApp = () => useContext(Ctx)
