import { AnimatePresence, motion } from 'framer-motion'
import clsx from 'clsx'
import { AlertTriangle, ArrowRight, Building2, ChevronDown, CircleSlash, Code2, ExternalLink, FileWarning, Hash, Info, Lock, PackageSearch, Search, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, axis, fmtPct, SEV_COLOR, tipStyle } from '../api'
import { AnimatedNumber, Badge, Button, Card, ErrorNote, IconBubble, inputCls, Segmented, Spinner } from '../components/ui'
import { useView } from '../mode'

const EXAMPLES = ['Nestor Pharmaceuticals', 'Sresan Pharmaceuticals', 'Cipla', 'Maiden Pharmaceuticals', 'Kaysons Pharma']
const LEVELS = [
  { label: 'No recent record', color: '#10b981', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  { label: 'Prefer alternatives', color: '#f59e0b', bg: 'bg-amber-50', text: 'text-amber-800' },
  { label: 'Test every batch', color: '#f97316', bg: 'bg-orange-50', text: 'text-orange-700' },
  { label: 'Pause new orders', color: '#e11d48', bg: 'bg-rose-50', text: 'text-rose-700' },
]

export default function Check({ initial }: { initial?: string }) {
  const { view, setView } = useView()
  const [q, setQ] = useState(initial ?? '')
  const [query, setQuery] = useState(initial ?? '')
  const [showBatch, setShowBatch] = useState(false)
  const [batch, setBatch] = useState('')
  const [batchQ, setBatchQ] = useState('')
  const [sugg, setSugg] = useState<any[]>([])
  useEffect(() => { if (initial) { setQ(initial); setQuery(initial) } }, [initial])
  useEffect(() => {
    if (q.trim().length < 2 || q === query) { setSugg([]); return }
    const t = setTimeout(() => api.search(q).then(setSugg).catch(() => setSugg([])), 200)
    return () => clearTimeout(t)
  }, [q, query])
  const run = (v: string) => { setQ(v); setQuery(v); setSugg([]); setBatchQ(batch.trim()) }

  return (
    <div className="space-y-8">
      <div className="text-center max-w-3xl mx-auto">
        <IconBubble icon={PackageSearch} size={56} />
        <h1 className="mt-4 font-display text-3xl sm:text-5xl font-extrabold tracking-tight">Check a manufacturer</h1>
        <p className="mt-3 text-muted text-lg">Type the name as it appears on an invoice or tender. You'll see every published failure, in plain language.</p>
      </div>

      <div className="max-w-3xl mx-auto">
        <form onSubmit={(e) => { e.preventDefault(); if (q.trim().length > 1) run(q.trim()) }} className="relative">
          <div className="flex items-center gap-2 rounded-full bg-white border border-line p-1.5 pl-5 shadow-[0_24px_50px_-24px_rgba(15,23,42,0.35)] focus-within:ring-4 focus-within:ring-teal-100 transition">
            <Search size={20} className="text-faint shrink-0" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Nestor Pharmaceuticals Ltd" autoFocus={!initial}
              className="flex-1 min-w-0 bg-transparent py-3 text-[17px] outline-none placeholder:text-faint" />
            <Button type="submit" className="!px-7 !py-3.5">Check</Button>
          </div>
          <AnimatePresence>
            {sugg.length > 0 && (
              <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="absolute left-4 right-4 mt-2 rounded-2xl border border-line bg-white shadow-xl overflow-hidden z-20">
                {sugg.slice(0, 7).map((r) => (
                  <button type="button" key={r.supplier_key} onClick={() => run(r.supplier_key)} className="w-full text-left px-4 py-2.5 hover:bg-surface-2 flex justify-between gap-3 text-sm">
                    <span className="truncate font-medium">{r.canonical_name}<span className="text-faint font-normal"> · {r.state}</span></span>
                    <span className="text-xs text-muted num shrink-0">{r.national_findings} failures</span>
                  </button>))}
              </motion.div>)}
          </AnimatePresence>
        </form>
        <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-sm">
          <span className="text-faint">Try</span>
          {EXAMPLES.map((e) => <button key={e} onClick={() => run(e)} className="rounded-full border border-line bg-white px-3 py-1 text-muted hover:text-ink hover:border-teal-300 transition">{e}</button>)}
          <button onClick={() => setShowBatch((x) => !x)} className="rounded-full px-3 py-1 text-ours font-semibold hover:bg-teal-50 inline-flex items-center gap-1"><Hash size={13} />{showBatch ? 'Hide batch number' : 'Add a batch number'}</button>
        </div>
        <AnimatePresence>
          {showBatch && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="mt-3 flex items-center gap-2 justify-center">
                <input value={batch} onChange={(e) => setBatch(e.target.value)} placeholder="Batch number on the pack, e.g. CITB-02" className={clsx(inputCls, 'max-w-xs')} />
                <span className="text-xs text-faint max-w-[220px]">Checks whether that exact batch is on the national failure list.</span>
              </div>
            </motion.div>)}
        </AnimatePresence>
        <div className="mt-6 flex flex-col items-center gap-2">
          <Segmented id="view" value={view} onChange={setView} options={[
            { value: 'public', label: <><ShieldCheck size={14} /> Public record</> },
            { value: 'buyer', label: <><Building2 size={14} /> Buyer view</> },
          ]} />
          <p className="text-xs text-faint text-center max-w-md">{view === 'public'
            ? 'Shows only what the government published. No predictions.'
            : 'Adds what a buyer should do now, a model\'s risk estimate and alternative suppliers.'}</p>
        </div>
      </div>

      {query && <LookupResult query={query} onPick={run} batch={batchQ} />}
      {!query && <EmptyHint />}
      <ApiNote />
    </div>
  )
}

function EmptyHint() {
  return (
    <div className="grid sm:grid-cols-3 gap-4 max-w-4xl mx-auto">
      {[
        { icon: FileWarning, t: 'Every published failure', d: 'Month, medicine, what failed, which lab found it, the batch number.' },
        { icon: ShieldCheck, t: 'No guessing', d: 'If a name is unclear you pick the right factory. Nothing is shown under the wrong name.' },
        { icon: Info, t: 'Limits stated', d: 'Each record says what the data cannot tell you, and how to request a correction.' },
      ].map((x, i) => (
        <motion.div key={x.t} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.08 }}>
          <Card className="p-5 h-full"><IconBubble icon={x.icon} size={40} /><div className="mt-3 font-semibold">{x.t}</div><p className="text-sm text-muted mt-1">{x.d}</p></Card>
        </motion.div>))}
    </div>
  )
}

export function LookupResult({ query, onPick, batch, compact }: { query: string; onPick: (q: string) => void; batch?: string; compact?: boolean }) {
  const { view } = useView()
  const [molecule, setMolecule] = useState('')
  const [d, setD] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [all, setAll] = useState(false)
  useEffect(() => { setD(null); setErr(null); setAll(false); api.lookup(query, view, molecule || undefined, batch || undefined).then(setD).catch((e) => setErr(e.message)) }, [query, view, molecule, batch])
  if (err) return <ErrorNote error={err} />
  if (!d) return <Spinner label="Checking the national record…" />
  const r = d.record

  if (!r) {
    return (
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="max-w-3xl mx-auto">
        <Card className="p-6 sm:p-8">
          {d.identity.candidates?.length ? (<>
            <div className="font-display text-xl font-bold">Which factory did you mean?</div>
            <p className="text-sm text-muted mt-1">"{d.query}" doesn't match one name closely enough. Pick the right one. We never guess, so no record is shown until you choose.</p>
            <div className="mt-4 space-y-2">
              {d.identity.candidates.map((c: any, i: number) => (
                <motion.button key={c.manufacturer_id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                  onClick={() => onPick(c.manufacturer_id)} className="w-full flex items-center justify-between gap-3 rounded-2xl border border-line bg-white px-4 py-3 hover:border-teal-300 hover:bg-teal-50/40 transition text-left">
                  <span><span className="font-semibold">{c.name}</span><span className="text-faint text-sm"> · {c.state}</span></span>
                  <span className="flex items-center gap-3 text-xs text-muted shrink-0"><span className="num">{c.alerts} failures</span><ArrowRight size={15} /></span>
                </motion.button>))}
            </div>
          </>) : (<>
            <div className="font-display text-xl font-bold">No failures found for "{d.query}"</div>
            <p className="text-sm text-muted mt-2">{d.statement}</p>
          </>)}
        </Card>
      </motion.div>
    )
  }

  const sev = r.by_severity as Record<string, number>
  const total = r.alerts || 1
  const entries = all ? r.entries : r.entries.slice(0, compact ? 6 : 8)
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      {/* summary */}
      <Card className="p-6 sm:p-8 overflow-hidden relative">
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-rose-50" />
        <div className="relative">
          <div className="flex flex-wrap gap-2">
            <Badge tone={view === 'buyer' ? 'warn' : 'ours'}>{view === 'buyer' ? 'Buyer view' : 'Public record'}</Badge>
            <Badge>Data as of {d.data_as_of}</Badge>
            <Badge tone={d.identity.match === 'exact' || d.identity.match === 'id' ? 'good' : 'warn'}>Name match: {d.identity.match}</Badge>
          </div>
          <h2 className="mt-4 font-display text-2xl sm:text-4xl font-extrabold tracking-tight">{r.unit.name}</h2>
          <div className="text-muted mt-1">{r.unit.state}{r.firm.name !== r.unit.name ? ` · part of ${r.firm.name}` : ''}</div>
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <BigNum value={r.alerts} label="failed batches on record" tone="text-blood" />
            <BigNum text={r.last_alert} label="most recent failure" />
            <BigNum text={r.first_alert} label="first failure on record" />
            <BigNum value={r.labs} label="different labs found them" />
          </div>
          <div className="mt-6">
            <div className="flex h-3 rounded-full overflow-hidden bg-surface-3">
              {['critical', 'major', 'minor', 'unclassified'].filter((k) => sev[k]).map((k, i) => (
                <motion.div key={k} initial={{ width: 0 }} animate={{ width: `${(100 * sev[k]) / total}%` }} transition={{ duration: 1, delay: 0.2 + i * 0.1 }} style={{ background: SEV_COLOR[k] }} />))}
            </div>
            <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted">
              {['critical', 'major', 'minor', 'unclassified'].filter((k) => sev[k]).map((k) => (
                <span key={k} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: SEV_COLOR[k] }} />{sev[k]} {k}</span>))}
            </div>
          </div>
        </div>
      </Card>

      {d.batch_check?.checked && <BatchCard b={d.batch_check} />}
      {view === 'buyer' && d.buyer && <BuyerPanel b={d.buyer} molecule={molecule} setMolecule={setMolecule} />}

      <div className={clsx('grid gap-5', compact ? '' : 'lg:grid-cols-[1.55fr_1fr]')}>
        <div className="space-y-5 min-w-0">
          {r.by_year?.length > 1 && (
            <Card className="p-5">
              <div className="font-display font-bold">Failures by year</div>
              <div className="h-48 mt-2">
                <ResponsiveContainer>
                  <BarChart data={r.by_year} margin={{ top: 8, right: 4, left: -24, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#eef2f7" />
                    <XAxis dataKey="year" tick={axis} axisLine={false} tickLine={false} />
                    <YAxis tick={axis} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={tipStyle} cursor={{ fill: '#f1f5f9' }} />
                    <Bar dataKey="alerts" name="failed batches" fill="#fda4af" radius={[6, 6, 0, 0]} animationDuration={1100} />
                    <Bar dataKey="critical" name="of which critical" fill="#e11d48" radius={[6, 6, 0, 0]} animationDuration={1300} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>)}
          <Card className="p-2 sm:p-3">
            <div className="px-3 pt-3 pb-2 font-display font-bold">Every published failure <span className="text-faint font-normal text-sm">({r.alerts})</span></div>
            <div className="divide-y divide-line">
              {entries.map((f: any, i: number) => (
                <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: Math.min(i, 10) * 0.03 }}
                  className="flex items-start gap-3 px-3 py-3 hover:bg-surface-2 rounded-xl">
                  <div className="w-16 shrink-0 text-xs font-semibold text-muted num pt-0.5">{f.month}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{f.generic_name} <span className="text-faint font-normal">· {f.dosage_form}</span></div>
                    <div className="text-xs text-muted mt-0.5 truncate">Failed on <b className="text-ink font-medium">{f.primary_failure}</b> · found by {f.reporting_lab} · batch <span className="font-mono">{f.batch_no}</span></div>
                  </div>
                  <span className="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize" style={{ background: `${SEV_COLOR[f.severity]}1f`, color: f.severity === 'unclassified' ? '#64748b' : SEV_COLOR[f.severity] }}>{f.severity}</span>
                </motion.div>))}
            </div>
            {r.entries.length > entries.length && <button onClick={() => setAll(true)} className="m-3 text-sm font-semibold text-ours">Show all {r.entries.length} <ChevronDown size={14} className="inline" /></button>}
          </Card>
        </div>
        <div className="space-y-4 min-w-0">
          {r.firm.other_units_on_record.length > 0 && (
            <Card className="p-5">
              <div className="font-semibold">Other factories of this firm</div>
              {r.firm.other_units_on_record.map((u: any) => (
                <button key={u.manufacturer_id} onClick={() => onPick(u.manufacturer_id)} className="w-full flex justify-between text-sm border-t border-line py-2 mt-2 first:mt-3 hover:text-ours">
                  <span>{u.state}</span><span className="num text-muted">{u.alerts} failures →</span></button>))}
            </Card>)}
          <Card className="p-5">
            <div className="flex items-center gap-2 font-semibold"><Lock size={15} className="text-faint" /> Regulatory action</div>
            <p className="text-sm text-muted mt-1">{r.regulatory_action ?? 'None recorded. We only fill this from a cited CDSCO or state order.'}</p>
          </Card>
          <Collapsible icon={CircleSlash} title="What this data can't tell you">
            <ul className="space-y-2 text-sm text-muted list-disc pl-4">{d.data_does_not_contain.map((x: string) => <li key={x}>{x}</li>)}</ul>
          </Collapsible>
          <Card className="p-5 bg-gradient-to-br from-white to-teal-50/60">
            <div className="flex items-center gap-2 font-semibold"><FileWarning size={15} className="text-ours" /> Something wrong?</div>
            <p className="text-sm text-muted mt-1">The firm, a buyer or anyone can ask for a record to be corrected or annotated. Every request is checked against the published alert.</p>
            <a href={d.correction.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-ours">Request a correction <ExternalLink size={13} /></a>
          </Card>
        </div>
      </div>
    </motion.div>
  )
}

function BigNum({ value, text, label, tone }: { value?: number; text?: string; label: string; tone?: string }) {
  return (
    <div>
      <div className={clsx('font-display text-3xl sm:text-4xl font-extrabold tracking-tight', tone)}>{value != null ? <AnimatedNumber value={value} /> : text ?? '–'}</div>
      <div className="text-xs text-muted mt-1">{label}</div>
    </div>
  )
}

function BatchCard({ b }: { b: any }) {
  const hit = b.this_batch_failed
  return (
    <motion.div initial={{ scale: 0.97, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
      <Card className={clsx('p-5 flex items-start gap-4', hit ? 'border-rose-300 bg-rose-50/60' : '')}>
        <IconBubble icon={hit ? AlertTriangle : ShieldCheck} tone={hit ? 'blood' : 'emerald'} />
        <div>
          <div className="font-semibold">Batch {b.batch}: {hit ? <span className="text-blood">this exact batch is on the national failure list</span> : <span className="text-emerald-700">no failure on record for this batch</span>}</div>
          {b.alerts_for_this_batch.map((a: any, i: number) => <div key={i} className="text-sm text-muted mt-1">{a.month} · {a.generic_name} · failed on {a.primary_failure} · {a.reporting_lab}</div>)}
          {b.same_number_other_products?.length > 0 && <div className="text-xs text-faint mt-1">The same number appears on another of this firm's products ({b.same_number_other_products[0].generic_name}). That's a different batch.</div>}
          <div className="text-xs text-faint mt-1">This only matches when you hold that very batch. The factory's record is the main signal.</div>
        </div>
      </Card>
    </motion.div>
  )
}

function BuyerPanel({ b, molecule, setMolecule }: { b: any; molecule: string; setMolecule: (m: string) => void }) {
  const g = b.graded_response
  const lv = LEVELS[g.level]
  const a = b.future_regulatory_attention
  const [items, setItems] = useState<string[]>([])
  useEffect(() => { api.masters().then((m) => setItems([...new Set<string>(m.items.map((i: any) => i.generic_name))])) }, [])
  return (
    <div className="grid lg:grid-cols-[1.3fr_1fr_1fr] gap-5">
      <Card className={clsx('p-6', lv.bg)}>
        <div className="text-xs font-semibold uppercase tracking-wider text-muted">What should a buyer do now?</div>
        <div className={clsx('mt-2 font-display text-2xl font-extrabold', lv.text)}>{lv.label}</div>
        <div className="mt-4 flex gap-1.5">
          {LEVELS.map((L, i) => (
            <motion.div key={i} className="h-2.5 flex-1 rounded-full" initial={{ background: '#e2e8f0' }}
              animate={{ background: i <= g.level ? L.color : '#e2e8f0' }} transition={{ delay: 0.15 * i, duration: 0.4 }} />))}
        </div>
        <p className="mt-4 text-sm text-ink/80 leading-relaxed">{g.rule}</p>
        <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
          <Fact n={g.facts.alerts_12m} l="failures, last 12 months" /><Fact n={g.facts.critical_12m} l="critical, last 12 months" />
          <Fact n={g.facts.alerts_36m} l="failures, last 3 years" /><Fact n={g.facts.critical_36m} l="critical, last 3 years" />
        </div>
        {b.debarred && <div className="mt-3 text-xs text-rose-700">Debarred by buyer {b.debarred.debarred_by} on {b.debarred.debarred_on} (simulated network).</div>}
      </Card>
      <Card className="p-6">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted">Risk estimate (model)</div>
        {a ? (<>
          <Gauge value={a.probability_next_6_months} />
          <p className="text-sm text-muted -mt-2">Chance this factory shows up in the national alerts in the next 6 months. It reflects where inspectors look as much as the factory itself.</p>
          {a.evaluation && <div className="mt-2 text-[11px] text-faint">Tested on data it never saw: AUC {Object.values(a.evaluation)[0] as number} (simple rule: {Object.values(a.evaluation)[1] as number})</div>}
        </>) : <p className="text-sm text-muted mt-2">No estimate: no failures to learn from.</p>}
      </Card>
      <Card className="p-6">
        <div className="flex items-center justify-between gap-2"><div className="text-xs font-semibold uppercase tracking-wider text-muted">Other suppliers</div><Badge tone="warn">simulated</Badge></div>
        <select value={molecule || b.alternatives_for || ''} onChange={(e) => setMolecule(e.target.value)} className={clsx(inputCls, 'mt-3 py-2 text-xs')}>
          <option value="">{b.alternatives_for ?? 'Choose a medicine…'}</option>
          {items.map((i) => <option key={i} value={i}>{i}</option>)}
        </select>
        <div className="mt-3 space-y-2">
          {b.alternatives.length === 0 && <div className="text-sm text-muted">No other supplier of this medicine in the buyers' lists.</div>}
          {b.alternatives.map((x: any) => (
            <div key={x.supplier_id} className="flex items-center justify-between gap-2 text-sm">
              <span className="truncate">{x.name}</span>
              <span className="shrink-0 h-2.5 w-2.5 rounded-full" title={x.response} style={{ background: LEVELS[x.response_level].color }} />
            </div>))}
        </div>
      </Card>
    </div>
  )
}

function Fact({ n, l }: { n: number; l: string }) {
  return <div className="rounded-xl bg-white/70 px-3 py-2"><div className="font-display text-lg font-bold num">{n}</div><div className="text-[11px] text-muted leading-tight">{l}</div></div>
}

function Gauge({ value }: { value: number }) {
  const r = 70, c = Math.PI * r
  const color = value > 0.6 ? '#e11d48' : value > 0.3 ? '#f59e0b' : '#10b981'
  return (
    <div className="relative mx-auto mt-3" style={{ width: 180, height: 110 }}>
      <svg width="180" height="100" viewBox="0 0 180 100">
        <path d="M20 90 A70 70 0 0 1 160 90" fill="none" stroke="#eef2f7" strokeWidth="14" strokeLinecap="round" />
        <motion.path d="M20 90 A70 70 0 0 1 160 90" fill="none" stroke={color} strokeWidth="14" strokeLinecap="round" strokeDasharray={c}
          initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - value) }} transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }} />
      </svg>
      <div className="absolute inset-x-0 bottom-3 text-center font-display text-3xl font-extrabold"><AnimatedNumber value={100 * value} format={(v) => `${v.toFixed(0)}%`} /></div>
    </div>
  )
}

function Collapsible({ icon: Icon, title, children }: { icon: any; title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <Card className="p-5">
      <button onClick={() => setOpen((x) => !x)} className="w-full flex items-center justify-between font-semibold">
        <span className="flex items-center gap-2"><Icon size={15} className="text-faint" /> {title}</span>
        <motion.span animate={{ rotate: open ? 180 : 0 }}><ChevronDown size={16} /></motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden"><div className="pt-3">{children}</div></motion.div>}
      </AnimatePresence>
    </Card>
  )
}

function ApiNote() {
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  return (
    <div className="max-w-4xl mx-auto">
      <Collapsible icon={Code2} title="For developers: use this check inside any ERP">
        <p className="text-sm text-muted">One GET request at purchase-order and goods-receipt time. The public view never returns a predicted score.</p>
        <pre className="mt-3 text-xs bg-slate-900 text-slate-100 rounded-xl p-4 overflow-x-auto font-mono">{`curl "${origin}/api/v1/lookup?q=Nestor%20Pharmaceuticals%20Ltd&view=buyer&batch=CITB-02&molecule=Ciprofloxacin"`}</pre>
        <a href="/docs" target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-ours">Full API reference <ExternalLink size={13} /></a>
      </Collapsible>
    </div>
  )
}

export { fmtPct }
