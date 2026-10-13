import { AnimatePresence, motion } from 'framer-motion'
import { BarChart3, Boxes, Brain, GitBranch, MessageSquareText, Radar, ScanSearch, Search, ShieldCheck, X } from 'lucide-react'
import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { api } from './api'
import { useView, ViewProvider } from './mode'
import Ask from './views/Ask'
import DataMining from './views/DataMining'
import ErpDesk from './views/ErpDesk'
import Lookup, { LookupResult } from './views/Lookup'
import ProcessMining from './views/ProcessMining'
import Quality from './views/Quality'
import Risk from './views/Risk'
import Study from './views/Study'

const TABS = [
  { id: 'study', label: 'Study', icon: BarChart3 },
  { id: 'lookup', label: 'Lookup', icon: ScanSearch },
  { id: 'erp', label: 'Buyers', icon: Boxes },
  { id: 'quality', label: 'Quality', icon: ShieldCheck },
  { id: 'mining', label: 'Patterns', icon: Brain },
  { id: 'process', label: 'Process', icon: GitBranch },
  { id: 'risk', label: 'Models', icon: Radar },
  { id: 'ask', label: 'Ask', icon: MessageSquareText },
] as const
export type TabId = (typeof TABS)[number]['id']
export const REPO_URL = 'https://github.com/AbhishekJadli007/dawadrishti'

function useHashTab(): [TabId, (t: TabId) => void] {
  const read = () => (TABS.find((t) => `#${t.id}` === window.location.hash)?.id ?? 'study') as TabId
  const [tab, setTab] = useState<TabId>(read)
  useEffect(() => {
    const on = () => setTab(read())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return [tab, (t) => { window.location.hash = t; window.scrollTo({ top: 0, behavior: 'smooth' }) }]
}

export default function App() {
  return <ViewProvider><Shell /></ViewProvider>
}

function Shell() {
  const [tab, go] = useHashTab()
  const [mfr, setMfr] = useState<string | null>(null)
  return (
    <div className="min-h-full page-glow">
      <header className="sticky top-0 z-[1000] border-b border-line/80 bg-bg/85 backdrop-blur-xl">
        <div className="mx-auto max-w-[1360px] px-4 sm:px-6 h-16 flex items-center gap-4">
          <button onClick={() => go('study')} className="flex items-center gap-2.5 shrink-0">
            <Logo />
            <div className="text-left leading-tight">
              <div className="font-display font-bold text-lg tracking-tight">DawaDrishti</div>
              <div className="text-[10px] text-muted -mt-0.5">दवा दृष्टि · a national memory of medicine quality</div>
            </div>
          </button>
          <nav className="flex-1 flex justify-center overflow-x-auto">
            <div className="flex gap-1 rounded-2xl bg-surface/80 border border-line p-1">
              {TABS.map((t) => (
                <button key={t.id} onClick={() => go(t.id)} className={clsx('relative flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-sm font-medium whitespace-nowrap transition-colors', tab === t.id ? 'text-ink' : 'text-muted hover:text-ink')}>
                  {tab === t.id && <motion.div layoutId="tab-pill" className="absolute inset-0 rounded-xl bg-surface-3 border border-line" transition={{ type: 'spring', stiffness: 400, damping: 32 }} />}
                  <t.icon size={15} className="relative" />
                  <span className="relative hidden xl:inline">{t.label}</span>
                </button>
              ))}
            </div>
          </nav>
          <ViewSwitch />
          <GlobalSearch onPick={setMfr} />
        </div>
      </header>

      <main className="mx-auto max-w-[1360px] px-4 sm:px-6 py-6 sm:py-8">
        <AnimatePresence mode="wait">
          <motion.div key={tab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.22 }}>
            {tab === 'study' && <Study go={go} openMfr={setMfr} />}
            {tab === 'lookup' && <Lookup />}
            {tab === 'quality' && <Quality />}
            {tab === 'erp' && <ErpDesk openMfr={setMfr} />}
            {tab === 'process' && <ProcessMining />}
            {tab === 'mining' && <DataMining openMfr={setMfr} />}
            {tab === 'risk' && <Risk openMfr={setMfr} />}
            {tab === 'ask' && <Ask />}
          </motion.div>
        </AnimatePresence>
      </main>

      <AnimatePresence>
        {mfr && (
          <motion.div className="fixed inset-0 z-[2000] bg-black/60 backdrop-blur-sm flex justify-end" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setMfr(null)}>
            <motion.div initial={{ x: 60 }} animate={{ x: 0 }} exit={{ x: 60 }} onClick={(e) => e.stopPropagation()}
              className="h-full w-full max-w-[760px] overflow-y-auto bg-bg border-l border-line p-6">
              <button onClick={() => setMfr(null)} className="float-right text-muted hover:text-ink"><X size={20} /></button>
              <div className="text-[11px] uppercase tracking-[0.16em] text-blood-soft font-semibold mb-3">Manufacturer record</div>
              <LookupResult query={mfr} onPick={setMfr} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <footer className="border-t border-line/70 mt-10">
        <div className="mx-auto max-w-[1360px] px-4 sm:px-6 py-6 text-xs text-faint flex flex-wrap gap-x-6 gap-y-2 justify-between">
          <span className="flex items-center gap-1.5"><ShieldCheck size={13} /> A public-record aggregator with a risk signal for buyers, not a blacklist. National data: real CDSCO alerts (2017–2026). Buyer transactions: simulated and labelled. Public pages show records, never predicted scores.</span>
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="hover:text-muted">Open source · MIT</a>
        </div>
      </footer>
    </div>
  )
}

function ViewSwitch() {
  const { view, setView } = useView()
  return (
    <div className="hidden sm:flex rounded-xl border border-line bg-surface-2 p-0.5 text-xs shrink-0" title="Public view shows the published record only. Buyer view adds the graded response, model scores and alternatives.">
      {(['public', 'buyer'] as const).map((v) => (
        <button key={v} onClick={() => setView(v)} className={clsx('rounded-lg px-2.5 py-1 capitalize', view === v ? (v === 'buyer' ? 'bg-amber-500/15 text-amber-200' : 'bg-surface-3 text-ink') : 'text-muted')}>{v}</button>
      ))}
    </div>
  )
}

function GlobalSearch({ onPick }: { onPick: (id: string) => void }) {
  const [q, setQ] = useState('')
  const [res, setRes] = useState<any[]>([])
  useEffect(() => {
    if (q.trim().length < 2) { setRes([]); return }
    const t = setTimeout(() => api.search(q).then(setRes).catch(() => setRes([])), 200)
    return () => clearTimeout(t)
  }, [q])
  return (
    <div className="relative hidden 2xl:block w-52 shrink-0">
      <Search size={14} className="absolute left-3 top-2.5 text-faint" />
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search any manufacturer…"
        className="w-full rounded-xl bg-surface-2 border border-line pl-8 pr-3 py-2 text-sm outline-none focus:border-ours/60" />
      {res.length > 0 && (
        <div className="absolute right-0 mt-1 w-[340px] rounded-xl border border-line bg-surface shadow-2xl overflow-hidden">
          {res.map((r) => (
            <button key={r.supplier_key} onClick={() => { onPick(r.supplier_key); setQ(''); setRes([]) }}
              className="w-full text-left px-3 py-2 hover:bg-surface-3 flex items-center justify-between gap-3 text-sm">
              <span className="truncate">{r.canonical_name}<span className="text-faint text-xs"> · {r.state}</span></span>
              <span className={clsx('text-xs num shrink-0', r.national_findings >= 5 ? 'text-red-300' : 'text-muted')}>{r.national_findings} alerts</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function Logo() {
  return (
    <svg width="34" height="34" viewBox="0 0 64 64" aria-hidden>
      <rect width="64" height="64" rx="16" fill="#11141b" stroke="#262c3b" />
      <g transform="rotate(-30 32 32)">
        <rect x="12" y="23" width="40" height="18" rx="9" fill="#22d3ee" />
        <path d="M32 23h11a9 9 0 0 1 0 18H32z" fill="#e11d48" />
      </g>
      <circle cx="32" cy="32" r="7" fill="#11141b" stroke="#e9ecf3" strokeWidth="2.5" />
      <circle cx="32" cy="32" r="2.5" fill="#e9ecf3" />
    </svg>
  )
}
