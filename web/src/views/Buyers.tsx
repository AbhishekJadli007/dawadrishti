import { AnimatePresence, motion } from 'framer-motion'
import clsx from 'clsx'
import { AlertTriangle, ArrowLeft, ArrowRight, Check, CheckCircle2, FlaskConical, Lock, PackageCheck, RotateCcw, Send, ShieldAlert, Sparkles, Truck, XCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api, fmtInt, fmtPct, type Check as SupplierCheck } from '../api'
import { Badge, Button, Card, ErrorNote, IconBubble, inputCls, Spinner } from '../components/ui'

const STEPS = ['What are you buying?', 'Pick a supplier', 'The goods arrive', 'Release to hospitals']
const LEVEL = [
  { label: 'No recent record', dot: '#10b981', ring: 'border-emerald-200', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  { label: 'Prefer alternatives', dot: '#f59e0b', ring: 'border-amber-200', bg: 'bg-amber-50', text: 'text-amber-800' },
  { label: 'Test every batch', dot: '#f97316', ring: 'border-orange-200', bg: 'bg-orange-50', text: 'text-orange-700' },
  { label: 'Pause new orders', dot: '#e11d48', ring: 'border-rose-200', bg: 'bg-rose-50', text: 'text-rose-700' },
]
const DEMO = { buyer: 'B4', item: 'I022' }   // Southern State Corporation · Bisacodyl tablets · a batch on the national list

export default function Buyers({ openMfr }: { openMfr: (id: string) => void }) {
  const [m, setM] = useState<any>(null)
  const [step, setStep] = useState(0)
  const [buyer, setBuyer] = useState('B4')
  const [item, setItem] = useState('')
  const [qty, setQty] = useState(5000)
  const [sups, setSups] = useState<SupplierCheck[] | null>(null)
  const [contract, setContract] = useState<any>(null)
  const [chosen, setChosen] = useState<SupplierCheck | null>(null)
  const [po, setPo] = useState<any>(null)
  const [blocked, setBlocked] = useState<any>(null)
  const [received, setReceived] = useState<any>(null)
  const [status, setStatus] = useState<string>('')
  const [msg, setMsg] = useState<{ tone: 'good' | 'bad' | 'warn'; text: string } | null>(null)
  const [timeline, setTimeline] = useState<any[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [shake, setShake] = useState(0)

  useEffect(() => { api.masters().then((x) => { setM(x); setItem(x.items.find((i: any) => i.item_id === DEMO.item)?.item_id ?? x.items[0].item_id) }) }, [])
  const itemObj = useMemo(() => m?.items.find((i: any) => i.item_id === item), [m, item])
  const buyerObj = useMemo(() => m?.buyers.find((b: any) => b.buyer_id === buyer), [m, buyer])
  const refreshTimeline = (id: string) => api.caseTimeline(id).then((c) => setTimeline(c.events)).catch(() => null)
  if (!m) return <Spinner label="Opening the buyer's system…" />

  const toStep2 = (b: string = buyer, it: string = item) => {
    setSups(null); setContract(null); setErr(null); setBlocked(null); setStep(1)
    api.suppliers(b, it).then(setSups).catch((e) => setErr(e.message))
    api.contract(b, it).then(setContract).catch(() => null)
  }
  const order = async (s: SupplierCheck, override = false) => {
    setErr(null)
    try {
      const r = await api.createPO({ buyer_id: buyer, item_id: item, supplier_id: s.supplier_id, qty, override })
      if (!r.created) { setBlocked({ ...r, supplier: s }); return }
      setBlocked(null); setChosen(s); setPo(r); setStatus('ordered'); setStep(2); refreshTimeline(r.case_id)
    } catch (e: any) { setErr(e.message) }
  }
  const receive = async (batch: string) => {
    setErr(null)
    try {
      const r = await api.receive(po.case_id, batch)
      setReceived({ ...r, batch }); setStatus(r.status); refreshTimeline(po.case_id)
    } catch (e: any) { setErr(e.message) }
  }
  const labResult = async (passed: boolean) => {
    const r = await api.result(po.case_id, passed, passed ? '' : 'Assay')
    setStatus(r.status); setMsg({ tone: passed ? 'good' : 'bad', text: r.actions.join(' ') }); refreshTimeline(po.case_id)
  }
  const issue = async () => {
    const r = await api.issue(po.case_id)
    if (r.issued) { setStatus('issued'); setMsg({ tone: 'good', text: 'Released to the hospitals. The batch had passed its lab test.' }) }
    else { setShake((x) => x + 1); setMsg({ tone: 'bad', text: `Blocked: this batch is "${status}". Only batches cleared by the lab can be released.` }) }
    refreshTimeline(po.case_id)
  }
  const reset = () => { setStep(0); setPo(null); setChosen(null); setReceived(null); setStatus(''); setMsg(null); setTimeline([]); setBlocked(null) }

  return (
    <div className="space-y-8">
      <div className="text-center max-w-3xl mx-auto">
        <Badge tone="warn">Simulated buyers · real national records</Badge>
        <h1 className="mt-4 font-display text-3xl sm:text-5xl font-extrabold tracking-tight">What changes inside a buyer's system</h1>
        <p className="mt-3 text-muted text-lg">Follow one order from purchase to the hospital shelf. Each step checks the national memory.</p>
      </div>

      <Stepper step={step} />
      {err && <ErrorNote error={err} />}

      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }} transition={{ duration: 0.3 }}>
          {step === 0 && (
            <Card className="p-6 sm:p-8 max-w-4xl mx-auto">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-display text-2xl font-bold">What are you buying?</h2>
                <button onClick={() => { setBuyer(DEMO.buyer); setItem(DEMO.item); toStep2(DEMO.buyer, DEMO.item) }}
                  className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1.5 text-sm font-semibold hover:bg-indigo-100">
                  <Sparkles size={14} /> Use the demo order
                </button>
              </div>
              <div className="mt-6 text-sm font-semibold text-muted">Buyer</div>
              <div className="mt-2 grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {m.buyers.map((b: any) => (
                  <button key={b.buyer_id} onClick={() => setBuyer(b.buyer_id)}
                    className={clsx('text-left rounded-2xl border px-4 py-3 transition', buyer === b.buyer_id ? 'border-ours bg-teal-50/60 ring-4 ring-teal-100' : 'border-line bg-white hover:border-teal-200')}>
                    <div className="font-semibold">{b.name}</div><div className="text-xs text-muted">{b.region}</div>
                  </button>))}
              </div>
              <div className="mt-6 grid sm:grid-cols-[1fr_160px] gap-4">
                <label className="block"><div className="text-sm font-semibold text-muted mb-2">Medicine</div>
                  <select className={inputCls} value={item} onChange={(e) => setItem(e.target.value)}>
                    {m.items.map((i: any) => <option key={i.item_id} value={i.item_id}>{i.generic_name} · {i.dosage_form}</option>)}
                  </select></label>
                <label className="block"><div className="text-sm font-semibold text-muted mb-2">Quantity</div>
                  <input type="number" className={inputCls} value={qty} min={1} onChange={(e) => setQty(Math.max(1, +e.target.value))} /></label>
              </div>
              <div className="mt-8 flex justify-end"><Button onClick={() => toStep2()}>Find suppliers <ArrowRight size={16} /></Button></div>
            </Card>)}

          {step === 1 && (
            <div className="space-y-5 max-w-5xl mx-auto">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div><h2 className="font-display text-2xl font-bold">Pick a supplier</h2>
                  <p className="text-muted text-sm">{buyerObj?.name} · {itemObj?.generic_name} · {fmtInt(qty)} units. Each supplier is checked against the national record.</p></div>
                <Button variant="ghost" onClick={() => setStep(0)}><ArrowLeft size={15} /> Back</Button>
              </div>
              {contract && <Supply c={contract} />}
              {!sups ? <Spinner label="Checking suppliers against the national record…" /> : (
                <div className="grid md:grid-cols-2 gap-4">
                  {sups.map((s, i) => {
                    const L = LEVEL[s.response_level ?? 0]
                    return (
                      <motion.div key={s.supplier_id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
                        <Card hover className={clsx('p-5 h-full flex flex-col border-2', L.ring)}>
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <button onClick={() => s.manufacturer_id && openMfr(s.manufacturer_id)} className="font-semibold text-left hover:text-ours">{s.name}</button>
                              <div className="text-xs text-muted">{s.state}</div>
                            </div>
                            <span className={clsx('shrink-0 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold', L.bg, L.text)}>
                              <span className="h-2 w-2 rounded-full" style={{ background: L.dot }} />{s.response}</span>
                          </div>
                          <div className="mt-3 text-sm text-muted">{s.manufacturer_id ? `${s.national_alerts_total} national failures on record · ${s.national_alerts_12m} in the last year` : 'No national failure on record'}</div>
                          {s.reasons.length > 0 && <ul className="mt-2 space-y-1 flex-1">{s.reasons.map((r) => <li key={r} className="text-xs text-ink/70 flex gap-1.5"><ShieldAlert size={13} className="text-blood mt-0.5 shrink-0" />{r}</li>)}</ul>}
                          <div className="mt-4"><Button variant={s.response_level === 3 ? 'ghost' : 'primary'} className="w-full" onClick={() => order(s)}>Order from this supplier</Button></div>
                        </Card>
                      </motion.div>)
                  })}
                </div>)}
              <AnimatePresence>
                {blocked && (
                  <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                    <Card className="p-6 border-rose-300 bg-rose-50/70 flex flex-col sm:flex-row gap-4 items-start">
                      <IconBubble icon={Lock} tone="blood" />
                      <div className="flex-1">
                        <div className="font-display text-lg font-bold text-rose-800">Order blocked by the national check</div>
                        <p className="text-sm text-rose-800/80 mt-1">{blocked.check.reasons.join('; ')}.</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Button variant="ghost" onClick={() => setBlocked(null)}>Choose another supplier</Button>
                          <Button variant="blood" onClick={() => order(blocked.supplier, true)}>Override (it is logged)</Button>
                        </div>
                      </div>
                    </Card>
                  </motion.div>)}
              </AnimatePresence>
            </div>)}

          {step === 2 && po && <Arrive po={po} supplier={chosen!} item={itemObj} received={received} onReceive={receive} onNext={() => setStep(3)} />}

          {step === 3 && po && (
            <div className="grid lg:grid-cols-[1.3fr_1fr] gap-5 max-w-5xl mx-auto">
              <Card className="p-6 sm:p-8">
                <h2 className="font-display text-2xl font-bold">Release to hospitals</h2>
                <p className="text-sm text-muted mt-1">The system refuses to release a batch until the lab has cleared it. Try it.</p>
                <div className="mt-5 flex items-center gap-3">
                  <StatusPill status={status} />
                  <span className="text-sm text-muted">{chosen?.name} · batch {received?.batch}</span>
                </div>
                <div className="mt-6 grid sm:grid-cols-2 gap-3">
                  <motion.div key={shake} animate={shake ? { x: [0, -10, 10, -6, 6, 0] } : {}} transition={{ duration: 0.45 }}>
                    <Button className="w-full" variant={status === 'cleared' ? 'primary' : 'dark'} onClick={issue} disabled={status === 'issued'}>
                      {status === 'cleared' || status === 'issued' ? <Send size={15} /> : <Lock size={15} />} Release to hospitals
                    </Button>
                  </motion.div>
                  {status === 'quarantine' && (
                    <div className="grid grid-cols-2 gap-2">
                      <Button variant="ghost" onClick={() => labResult(true)}><CheckCircle2 size={15} className="text-emerald-600" /> Lab: pass</Button>
                      <Button variant="ghost" onClick={() => labResult(false)}><XCircle size={15} className="text-blood" /> Lab: fail</Button>
                    </div>)}
                </div>
                <AnimatePresence mode="wait">
                  {msg && (
                    <motion.div key={msg.text} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      className={clsx('mt-5 rounded-2xl border px-4 py-3 text-sm flex gap-2',
                        msg.tone === 'good' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : msg.tone === 'bad' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-amber-200 bg-amber-50 text-amber-800')}>
                      {msg.tone === 'good' ? <CheckCircle2 size={17} className="shrink-0" /> : <AlertTriangle size={17} className="shrink-0" />}{msg.text}
                    </motion.div>)}
                </AnimatePresence>
                {status === 'issued' && (
                  <motion.div initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 260, damping: 16 }}
                    className="mt-6 flex items-center gap-3 rounded-2xl bg-gradient-to-r from-teal-50 to-indigo-50 p-4">
                    <div className="h-12 w-12 rounded-full bg-ours text-white flex items-center justify-center"><Check size={26} /></div>
                    <div className="text-sm"><b>Done.</b> Tested, cleared, released, with every step recorded in the event log process mining reads.</div>
                  </motion.div>)}
                <div className="mt-8"><Button variant="ghost" onClick={reset}><RotateCcw size={15} /> Start a new order</Button></div>
              </Card>
              <Timeline events={timeline} />
            </div>)}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

function Stepper({ step }: { step: number }) {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="relative flex justify-between">
        <div className="absolute left-[6%] right-[6%] top-5 h-1 rounded-full bg-surface-3" />
        <motion.div className="absolute left-[6%] top-5 h-1 rounded-full bg-gradient-to-r from-ours to-ours-2" animate={{ width: `${(88 * step) / (STEPS.length - 1)}%` }} transition={{ duration: 0.5 }} />
        {STEPS.map((s, i) => (
          <div key={s} className="relative flex flex-col items-center w-1/4">
            <motion.div animate={{ scale: i === step ? 1.12 : 1 }} className={clsx('h-11 w-11 rounded-full flex items-center justify-center font-display font-bold border-2 transition-colors',
              i < step ? 'bg-ours border-ours text-white' : i === step ? 'bg-white border-ours text-ours shadow-[0_0_0_6px_rgba(13,148,136,0.15)]' : 'bg-white border-line text-faint')}>
              {i < step ? <Check size={18} /> : i + 1}
            </motion.div>
            <div className={clsx('mt-2 text-xs sm:text-sm font-semibold text-center', i === step ? 'text-ink' : 'text-faint')}>{s}</div>
          </div>))}
      </div>
    </div>
  )
}

function Supply({ c }: { c: any }) {
  const single = c.concentration === 'single source'
  return (
    <Card className={clsx('p-5', single && 'border-amber-200 bg-amber-50/50')}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-semibold">Your supply of this medicine</div>
        <Badge tone={single ? 'warn' : c.concentration === 'concentrated' ? 'warn' : 'good'}>{c.concentration}</Badge>
      </div>
      <div className="mt-3 flex h-3 rounded-full overflow-hidden bg-surface-3">
        {c.suppliers.map((s: any, i: number) => <motion.div key={s.supplier_id} title={`${s.name}: ${fmtPct(s.share)}`} initial={{ width: 0 }} animate={{ width: `${100 * s.share}%` }}
          transition={{ duration: 0.9, delay: i * 0.1 }} style={{ background: ['#0d9488', '#4f46e5', '#f59e0b', '#10b981'][i % 4] }} />)}
      </div>
      <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
        <div><div className="font-display text-xl font-bold">{c.top_share != null ? fmtPct(c.top_share) : '–'}</div><div className="text-xs text-muted">from the biggest supplier</div></div>
        <div><div className="font-display text-xl font-bold">{c.days_of_cover ?? '–'}</div><div className="text-xs text-muted">days of stock left</div></div>
        <div><div className="font-display text-xl font-bold">{c.daily_use != null ? fmtInt(c.daily_use) : '–'}</div><div className="text-xs text-muted">units used per day</div></div>
      </div>
      {single && <p className="mt-3 text-xs text-amber-800">Only one supplier: pausing it would leave no second source. Line up an alternative first.</p>}
    </Card>
  )
}

function Arrive({ po, supplier, item, received, onReceive, onNext }: { po: any; supplier: SupplierCheck; item: any; received: any; onReceive: (b: string) => void; onNext: () => void }) {
  const [batch, setBatch] = useState(`BN${Math.floor(100000 + Math.random() * 900000)}`)
  const [alerted, setAlerted] = useState<string | null>(null)
  useEffect(() => {   // offer a real batch number from this firm's national record for the same medicine, if one exists
    if (!supplier?.manufacturer_id || !item) return
    const first = (x: string) => x.toLowerCase().replace(/[^a-z ]/g, ' ').trim().split(/\s+/)[0]
    api.lookup(supplier.manufacturer_id, 'public').then((d) => {
      const e = d.record?.entries.find((x: any) => first(x.generic_name) === first(item.generic_name) && x.batch_no && x.batch_no.length > 3)
      setAlerted(e ? e.batch_no : null)
    }).catch(() => null)
  }, [supplier, item])
  const held = received?.status === 'held'
  return (
    <div className="grid lg:grid-cols-[1fr_1fr] gap-5 max-w-5xl mx-auto">
      <Card className="p-6 sm:p-8">
        <IconBubble icon={Truck} tone="indigo" size={52} />
        <h2 className="mt-4 font-display text-2xl font-bold">The goods arrive</h2>
        <p className="text-sm text-muted mt-1">Order <span className="font-mono">{po.po_id}</span> from {supplier.name}. Enter the batch number printed on the delivery.</p>
        {!received ? (<>
          <input value={batch} onChange={(e) => setBatch(e.target.value)} className={clsx(inputCls, 'mt-5 font-mono text-base')} />
          {alerted && (
            <button onClick={() => setBatch(alerted)} className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-rose-50 border border-rose-200 px-3 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-100">
              <AlertTriangle size={12} /> Try a batch from the national failure list: {alerted}
            </button>)}
          <div className="mt-6"><Button onClick={() => onReceive(batch.trim())}><PackageCheck size={16} /> Receive the delivery</Button></div>
        </>) : (
          <div className="mt-6"><Button onClick={onNext}>Next: release <ArrowRight size={16} /></Button></div>
        )}
      </Card>
      <AnimatePresence mode="wait">
        {!received ? (
          <motion.div key="wait" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Card className="p-8 h-full flex flex-col items-center justify-center text-center bg-gradient-to-br from-white to-surface-2">
              <motion.div animate={{ x: [0, 14, 0] }} transition={{ repeat: Infinity, duration: 2.2, ease: 'easeInOut' }}><Truck size={56} className="text-faint" /></motion.div>
              <p className="mt-4 text-sm text-muted max-w-xs">When the batch is received, its number is checked against the national list, and it goes into quarantine for testing.</p>
            </Card>
          </motion.div>
        ) : (
          <motion.div key="res" initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: 'spring', stiffness: 240, damping: 20 }}>
            <Card className={clsx('p-8 h-full text-center flex flex-col items-center justify-center', held ? 'bg-rose-50 border-rose-300' : 'bg-amber-50 border-amber-200')}>
              <motion.div initial={{ rotate: -20, scale: 0.4 }} animate={{ rotate: 0, scale: 1 }} transition={{ type: 'spring', stiffness: 260, damping: 12 }}
                className={clsx('h-20 w-20 rounded-full flex items-center justify-center', held ? 'bg-blood text-white' : 'bg-amber-500 text-white')}>
                {held ? <ShieldAlert size={40} /> : <FlaskConical size={38} />}
              </motion.div>
              <div className={clsx('mt-5 font-display text-2xl font-extrabold', held ? 'text-rose-800' : 'text-amber-800')}>{held ? 'Held on arrival' : 'In quarantine for testing'}</div>
              {held ? (
                <p className="mt-2 text-sm text-rose-900/80 max-w-sm">Batch {received.batch} already failed a government test ({received.national_alert_on_this_batch[0].month}, {received.national_alert_on_this_batch[0].primary_failure}). It is held without waiting for your own lab, and the supplier is notified.</p>
              ) : (
                <p className="mt-2 text-sm text-amber-900/80 max-w-sm">No national alert on batch {received.batch}. A coded sample goes to the lab. Test-priority score: <b>{fmtPct(received.risk_score)}</b> (the riskiest batches are tested first).</p>
              )}
            </Card>
          </motion.div>)}
      </AnimatePresence>
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, [string, string]> = {
    ordered: ['Ordered', 'bg-surface-3 text-muted'], quarantine: ['In quarantine', 'bg-amber-100 text-amber-800'],
    held: ['Held: failed', 'bg-rose-100 text-rose-800'], cleared: ['Cleared by the lab', 'bg-emerald-100 text-emerald-800'], issued: ['Released', 'bg-teal-100 text-teal-800'],
  }
  const [l, c] = map[status] ?? [status, 'bg-surface-3 text-muted']
  return <motion.span key={status} initial={{ scale: 0.8 }} animate={{ scale: 1 }} className={clsx('rounded-full px-3 py-1 text-sm font-bold', c)}>{l}</motion.span>
}

function Timeline({ events }: { events: any[] }) {
  return (
    <Card className="p-6">
      <div className="font-display font-bold">Event log</div>
      <p className="text-xs text-muted">Every step is recorded. Process mining reads this log to find rule-breaking across all buyers.</p>
      <ol className="mt-4 relative border-l-2 border-line ml-2 space-y-3">
        <AnimatePresence initial={false}>
          {events.map((e, i) => (
            <motion.li key={`${e.activity}-${i}`} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.04 * i }} className="ml-4">
              <span className={clsx('absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full border-2 border-white',
                /Held|debarred|Recall/.test(e.activity) ? 'bg-blood' : /Cleared|Issued/.test(e.activity) ? 'bg-emerald-500' : 'bg-ours')} />
              <div className="text-sm font-semibold">{e.activity}</div>
              <div className="text-[11px] text-faint">{e.erp_module} · {e.resource}</div>
            </motion.li>))}
        </AnimatePresence>
        {events.length === 0 && <li className="ml-4 text-sm text-faint">Nothing yet.</li>}
      </ol>
    </Card>
  )
}
