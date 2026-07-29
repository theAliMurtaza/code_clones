import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Btn, Input, Select, Badge, SectionH } from '../components/UI'

const SB = { complete:'green', running:'blue', queued:'amber' }

export default function Account() {
  const { projects, setPage, toast } = useApp()
  const [name,  setName]  = useState('Ahmad Khalid')
  const [email, setEmail] = useState('ahmad@university.edu')
  const [auth,  setAuth]  = useState('email')

  return (
    <div className="animate-fadeUp space-y-5">
      <SectionH>FR-08 · User &amp; Session Management</SectionH>

      <div className="grid grid-cols-2 gap-5">
        {/* Projects */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">My Projects · FR-08-02</div>
            <Btn size="sm" onClick={() => setPage('upload')}>+ New</Btn>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-b1">
                {['Project','Lang','Date','Clones','Status',''].map((h,i)=>(
                  <th key={i} className="text-left px-5 py-2.5 text-[9px] font-semibold font-mono text-t3 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {projects.map(p=>(
                <tr key={p.id} className="border-b border-b1/50 hover:bg-s2/50 transition-colors">
                  <td className="px-5 py-3 font-semibold text-t1">{p.name}</td>
                  <td className="px-5 py-3 font-mono text-t2">{p.lang}</td>
                  <td className="px-5 py-3 font-mono text-t3">{p.date}</td>
                  <td className="px-5 py-3 font-mono text-t2">{p.clones}</td>
                  <td className="px-5 py-3"><Badge type={SB[p.status]}>{p.status}</Badge></td>
                  <td className="px-5 py-3">
                    <Btn variant="ghost" size="sm" onClick={()=>setPage('results')}>View</Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Account */}
        <div className="card">
          <div className="card-header"><div className="card-title">Account &amp; Security · FR-08-01</div></div>
          <div className="card-body space-y-0">
            <Input label="Full Name"        value={name}  onChange={setName}  placeholder="Full name"/>
            <Input label="Email Address"    value={email} onChange={setEmail} type="email"/>
            <Select label="Authentication · FR-08-01" value={auth} onChange={setAuth}
              options={[{value:'email',label:'Email / Password'},{value:'github',label:'OAuth · GitHub'},{value:'google',label:'OAuth · Google'}]}/>
            <div className="info-box mt-2 mb-4">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" strokeWidth="2" strokeLinecap="round" className="flex-shrink-0 mt-0.5">
                <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
              </svg>
              <span><strong className="text-accent">FR-08-03 · NFR-03-03</strong> · RBAC enforced — data isolation active. Your code and results are strictly private.</span>
            </div>
            <Btn onClick={()=>toast('Profile updated','FR-08-01: Changes saved')}>Save Changes</Btn>
          </div>
        </div>

        {/* Session history */}
        <div className="card col-span-2">
          <div className="card-header"><div className="card-title">Session History · FR-08-02</div></div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-b1">
                {['Session ID','Project','Lang','Fragments','Clone Pairs','F1','Started','Duration'].map(h=>(
                  <th key={h} className="text-left px-5 py-2.5 text-[9px] font-semibold font-mono text-t3 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { id:'SES-001', proj:'auth-service', lang:'Python', frags:840,  pairs:247,  f1:'0.91', date:'2025-06-01 09:14', dur:'3.8s' },
                { id:'SES-002', proj:'ml-pipeline',  lang:'Java',   frags:1720, pairs:512,  f1:'0.89', date:'2025-05-28 14:32', dur:'5.6s' },
              ].map(s=>(
                <tr key={s.id} className="border-b border-b1/50 hover:bg-s2/50 transition-colors">
                  <td className="px-5 py-3 font-mono text-accent font-bold">{s.id}</td>
                  <td className="px-5 py-3 font-semibold text-t1">{s.proj}</td>
                  <td className="px-5 py-3 font-mono text-t2">{s.lang}</td>
                  <td className="px-5 py-3 font-mono text-t2">{s.frags.toLocaleString()}</td>
                  <td className="px-5 py-3 font-mono text-t2">{s.pairs}</td>
                  <td className="px-5 py-3 font-mono font-bold text-success">{s.f1}</td>
                  <td className="px-5 py-3 font-mono text-t3">{s.date}</td>
                  <td className="px-5 py-3 font-mono text-accent">{s.dur}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
