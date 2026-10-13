import { AnimatePresence, motion } from 'framer-motion'
import { Home as HomeIcon, Search, ShieldCheck, ShoppingCart, X } from 'lucide-react'
import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { ViewProvider } from './mode'
import Buyers from './views/Buyers'
import Check, { LookupResult } from './views/Check'
import Home from './views/Home'
import Proof from './views/Proof'

export const REPO_URL = 'https://github.com/AbhishekJadli007/dawadrishti'

const NAV = [
  { id: 'home', label: 'Home', short: 'Home', icon: HomeIcon },
  { id: 'check', label: 'Check a manufacturer', short: 'Check', icon: Search },
  { id: 'buyers', label: 'For buyers', short: 'Buyers', icon: ShoppingCart },
  { id: 'proof', label: 'How we know', short: 'Proof', icon: ShieldCheck },
] as const
export type Section = (typeof NAV)[number]['id']
export type Go = (section: Section, opts?: { sub?: string; q?: string }) => void

// old links (#study, #lookup, #erp, #quality...) keep working
const LEGACY: Record<string, string> = {
  study: 'home', lookup: 'check', erp: 'buyers', quality: 'proof/quality', risk: 'proof/models',
  process: 'proof/process', mining: 'proof/patterns', ask: 'proof/ask',
}

function readRoute(): { section: Section; sub?: string; q?: string } {
  let h = window.location.hash.replace(/^#/, '')
  const [path, query] = h.split('?')
  h = LEGACY[path] ?? path
  const [section, sub] = h.split('/')
  const q = new URLSearchParams(query ?? '').get('q') ?? undefined
  return { section: (NAV.some((n) => n.id === section) ? section : 'home') as Section, sub, q }
}

function useRoute(): [ReturnType<typeof readRoute>, Go] {
  const [route, setRoute] = useState(readRoute)
  useEffect(() => {
    const on = () => setRoute(readRoute())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go: Go = (section, opts) => {
    const hash = `${section}${opts?.sub ? `/${opts.sub}` : ''}${opts?.q ? `?q=${encodeURIComponent(opts.q)}` : ''}`
    if (window.location.hash !== `#${hash}`) window.location.hash = hash
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  return [route, go]
}

export default function App() {
  return <ViewProvider><Shell /></ViewProvider>
}

function Shell() {
  const [route, go] = useRoute()
  const [mfr, setMfr] = useState<string | null>(null)
  return (
    <div className="min-h-full page-glow overflow-x-clip">
      <header className="sticky top-0 z-[1000] border-b border-line/80 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto max-w-[1240px] px-4 sm:px-6 h-16 flex items-center gap-4">
          <button onClick={() => go('home')} className="flex items-center gap-2.5 shrink-0">
            <Logo />
            <div className="text-left leading-tight">
              <div className="font-display font-extrabold text-[17px] tracking-tight">DawaDrishti</div>
              <div className="text-[10.5px] text-faint -mt-0.5 hidden sm:block">दवा दृष्टि · India's medicine-quality memory</div>
            </div>
          </button>
          <nav className="hidden md:flex flex-1 justify-center">
            <div className="flex gap-1 rounded-full bg-surface-3/70 border border-line p-1">
              {NAV.map((n) => (
                <button key={n.id} onClick={() => go(n.id)}
                  className={clsx('relative flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-semibold whitespace-nowrap transition-colors',
                    route.section === n.id ? 'text-ink' : 'text-muted hover:text-ink')}>
                  {route.section === n.id && <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-full bg-white shadow-sm border border-line"
                    transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
                  <n.icon size={15} className="relative" />
                  <span className="relative">{n.label}</span>
                </button>
              ))}
            </div>
          </nav>
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="ml-auto md:ml-0 inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-muted hover:text-ink">
            <GithubMark /> <span className="hidden sm:inline">Open source</span>
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-[1240px] px-4 sm:px-6 pt-6 sm:pt-10 pb-28 md:pb-16">
        <AnimatePresence mode="wait">
          <motion.div key={route.section} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}>
            {route.section === 'home' && <Home go={go} openMfr={setMfr} />}
            {route.section === 'check' && <Check initial={route.q} />}
            {route.section === 'buyers' && <Buyers openMfr={setMfr} />}
            {route.section === 'proof' && <Proof sub={route.sub} go={go} openMfr={setMfr} />}
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="border-t border-line bg-white/60">
        <div className="mx-auto max-w-[1240px] px-4 sm:px-6 py-8 pb-28 md:pb-8 grid gap-4 md:grid-cols-[1.4fr_1fr] text-sm text-muted">
          <div>
            <div className="flex items-center gap-2 text-ink font-semibold"><Logo size={22} /> DawaDrishti</div>
            <p className="mt-2 max-w-xl">A public-record aggregator with a risk signal for buyers, not a blacklist. National data: real CDSCO alerts, 2017–2026.
              Buyer transactions in the demo are simulated and labelled. Public pages show records, never predicted scores.</p>
          </div>
          <div className="md:text-right space-y-1">
            <div><a href={REPO_URL} target="_blank" rel="noreferrer" className="hover:text-ink">GitHub · MIT licence</a></div>
            <div><a href="/docs" target="_blank" rel="noreferrer" className="hover:text-ink">API reference</a></div>
            <div className="text-faint text-xs">Built by Abhishek Jadli · COMMIT FOR GOOD 2026</div>
          </div>
        </div>
      </footer>

      {/* phone navigation */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-[1000] border-t border-line bg-white/90 backdrop-blur-xl pb-[env(safe-area-inset-bottom)]">
        <div className="grid grid-cols-4">
          {NAV.map((n) => (
            <button key={n.id} onClick={() => go(n.id)} className={clsx('relative flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-semibold', route.section === n.id ? 'text-ours' : 'text-faint')}>
              {route.section === n.id && <motion.span layoutId="nav-dot" className="absolute top-0 h-0.5 w-10 rounded-full bg-ours" />}
              <n.icon size={20} />
              {n.short}
            </button>
          ))}
        </div>
      </nav>

      <AnimatePresence>
        {mfr && (
          <motion.div className="fixed inset-0 z-[2000] bg-slate-900/25 backdrop-blur-sm flex justify-end" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setMfr(null)}>
            <motion.div initial={{ x: 80, opacity: 0.6 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 80, opacity: 0 }} transition={{ type: 'spring', stiffness: 300, damping: 32 }}
              onClick={(e) => e.stopPropagation()} className="h-full w-full max-w-[820px] overflow-y-auto bg-bg border-l border-line p-5 sm:p-7">
              <div className="flex items-center justify-between mb-4">
                <div className="text-xs uppercase tracking-[0.16em] text-ours font-semibold">Manufacturer record</div>
                <button onClick={() => setMfr(null)} className="rounded-full p-2 hover:bg-surface-3 text-muted"><X size={18} /></button>
              </div>
              <LookupResult query={mfr} onPick={setMfr} compact />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <linearGradient id="dd-logo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0d9488" /><stop offset="1" stopColor="#4f46e5" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="18" fill="url(#dd-logo)" />
      <path d="M11 32c5.5-9.5 12.5-14.5 21-14.5S47.5 22.5 53 32c-5.5 9.5-12.5 14.5-21 14.5S16.5 41.5 11 32z" fill="#fff" />
      <circle cx="32" cy="32" r="8.5" fill="#0d9488" />
      <circle cx="32" cy="32" r="3.4" fill="#fff" />
    </svg>
  )
}

function GithubMark() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}
