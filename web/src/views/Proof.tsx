import { AnimatePresence, motion } from 'framer-motion'
import { BarChart3, Brain, GitBranch, MessageSquareText, Radar, ShieldCheck } from 'lucide-react'
import type { Go } from '../App'
import { Segmented } from '../components/ui'
import Ask from './Ask'
import DataMining from './DataMining'
import ProcessMining from './ProcessMining'
import Quality from './Quality'
import Risk from './Risk'
import Study from './Study'

const SUBS = [
  { value: 'study', label: 'The study', icon: BarChart3, blurb: 'How we measured that two in three failures come from factories already on record.' },
  { value: 'quality', label: 'Data quality', icon: ShieldCheck, blurb: 'How accurately the alerts are read, and how well names are matched to factories.' },
  { value: 'models', label: 'Models', icon: Radar, blurb: 'Every prediction tested on data it never saw, next to simple rules.' },
  { value: 'process', label: 'Process checks', icon: GitBranch, blurb: 'The rule engine that spots stock released before testing, checked on a real SAP log.' },
  { value: 'patterns', label: 'Patterns', icon: Brain, blurb: 'Which medicines fail which tests, where, and how often.' },
  { value: 'ask', label: 'Ask the data', icon: MessageSquareText, blurb: 'Ask a question in plain English; get a table of published records.' },
] as const

export default function Proof({ sub, go, openMfr }: { sub?: string; go: Go; openMfr: (id: string) => void }) {
  const active = (SUBS.find((s) => s.value === sub)?.value ?? 'study') as (typeof SUBS)[number]['value']
  const info = SUBS.find((s) => s.value === active)!
  return (
    <div className="space-y-8">
      <div className="text-center max-w-3xl mx-auto">
        <h1 className="font-display text-3xl sm:text-5xl font-extrabold tracking-tight">How we know</h1>
        <p className="mt-3 text-muted text-lg">Every claim, with its evidence and its limits. Where a simple rule beats our model, we say so.</p>
      </div>
      <div className="flex justify-center">
        <Segmented id="proof" value={active} onChange={(v) => go('proof', { sub: v })}
          options={SUBS.map((s) => ({ value: s.value, label: <><s.icon size={14} /> {s.label}</> }))} />
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={active} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.25 }}>
          <p className="text-center text-sm text-faint -mt-3 mb-6">{info.blurb}</p>
          {active === 'study' && <Study />}
          {active === 'quality' && <Quality />}
          {active === 'models' && <Risk openMfr={openMfr} />}
          {active === 'process' && <ProcessMining />}
          {active === 'patterns' && <DataMining openMfr={openMfr} />}
          {active === 'ask' && <Ask />}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
