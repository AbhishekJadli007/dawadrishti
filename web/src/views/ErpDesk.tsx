import { AnimatePresence, motion } from 'framer-motion'
import { Ban, CheckCircle2, ClipboardCheck, PackageCheck, PackageX, PieChart, Send, ShieldAlert, Truck } from 'lucide-react'
import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, fmtInt, fmtPct, type Check, type QueueRow } from '../api'
import { Badge, Button, Card, ErrorNote, inputCls, SectionTitle, Spinner } from '../components/ui'

const LEVEL = { ok: { tone: 'good' }, warn: { tone: 'warn' }, block: { tone: 'bad' } } as const

export default function ErpDesk({ openMfr }: { openMfr: (id: string) => void }) {
  const [m, setM] = useState<any>(null)
  const [buyer, setBuyer] = useState('B2')
  const [item, setItem] = useState('')
  const [sups, setSups] = useState<Check[] | null>(null)
  const [qty, setQty] = useState(5000)
  const [poRes, setPoRes] = useState<any>(null)
  const [queue, setQueue] = useState<QueueRow[]>([])
  const [msg, setMsg] = useState<{ tone: 'good' | 'bad' | 'warn'; text: string } | null>(null)
  const [caseId, setCaseId] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [contract, setContract] = useState<any>(null)
  const [batchEval, setBatchEval] = useState<any>(null)
  useEffect(() => { api.risk().then((r) => setBatchEval(r.batch.test.results)) }, [])

  useEffect(() => { api.masters().then((x) => { setM(x); setItem(x.items[0]?.item_id ?? '') }) }, [])
  const loadQueue = useCallback(() => api.queue(buyer).then(setQueue).catch((e) => setErr(String(e.message))), [buyer])
  useEffect(() => { loadQueue() }, [loadQueue])
  useEffect(() => {
    if (!item) return
    setSups(null); setPoRes(null)
    api.suppliers(buyer, item).then(setSups).catch((e) => setErr(String(e.message)))
    api.contract(buyer, item).then(setContract).catch(() => setContract(null))
  }, [buyer, item])

  const buyerName = useMemo(() => m?.buyers.find((b: any) => b.buyer_id === buyer)?.name, [m, buyer])
  if (!m) return <Spinner label="Opening the ERP…" />

  const raise = async (s: Check, override = false) => {
    setErr(null)
    try {
      const r = await api.createPO({ buyer_id: buyer, item_id: item, supplier_id: s.supplier_id, qty, override })
      setPoRes({ ...r, supplier: s })
      if (r.created) loadQueue()
    } catch (e: any) { setErr(e.message) }
  }
  const act = async (fn: () => Promise<any>, ok: (r: any) => { tone: 'good' | 'bad' | 'warn'; text: string }) => {
    setErr(null)
    try { const r = await fn(); setMsg(ok(r)); loadQueue() } catch (e: any) { setErr(e.message) }
  }

  return (
    <div className="space-y-6">
      <SectionTitle eyebrow="Reference buyer console · simulated buyers" title="What the memory changes inside a buyer's ERP"
        sub="Two moments: a purchase order is checked against the national record (graded response, with the supply position beside it), and a received batch cannot be issued until the lab clears it. The buyers, orders and debarments here are simulated; the national record behind each supplier is real."
        right={
          <div className="flex flex-wrap gap-1 rounded-xl bg-surface border border-line p-1">
            {m.buyers.map((b: any) => (
              <button key={b.buyer_id} onClick={() => setBuyer(b.buyer_id)} className={clsx('px-3 py-1.5 rounded-lg text-xs', buyer === b.buyer_id ? 'bg-surface-3 text-ink' : 'text-muted hover:text-ink')}>{b.name}</button>
            ))}
          </div>
        } />
      {err && <ErrorNote error={err} />}

      <div className="grid xl:grid-cols-[1fr_1.15fr] gap-5 items-start">
        <Card className="p-5">
          <div className="flex items-center gap-2 font-display font-semibold"><Truck size={17} className="text-ours" /> New purchase order · {buyerName}</div>
          <div className="grid grid-cols-[1fr_120px] gap-3 mt-4">
            <label className="text-xs text-muted">Item (from the national product master)
              <select className={clsx(inputCls, 'mt-1')} value={item} onChange={(e) => setItem(e.target.value)}>
                {m.items.map((i: any) => <option key={i.item_id} value={i.item_id}>{i.generic_name} · {i.dosage_form}</option>)}
              </select>
            </label>
            <label className="text-xs text-muted">Quantity
              <input type="number" className={clsx(inputCls, 'mt-1')} value={qty} min={1} onChange={(e) => setQty(Math.max(1, +e.target.value))} />
            </label>
          </div>
          {contract && <ContractPanel c={contract} />}
          <div className="text-xs text-muted mt-4 mb-2">Suppliers on the rate contract, checked against the national memory:</div>
          {!sups ? <Spinner /> : (
            <div className="space-y-2">
              {sups.map((s) => (
                <div key={s.supplier_id} className={clsx('rounded-xl border p-3', s.level === 'block' ? 'border-red-500/30 bg-red-500/[0.05]' : s.level === 'warn' ? 'border-amber-500/30 bg-amber-500/[0.04]' : 'border-line bg-surface-2/50')}>
                  <div className="flex items-center gap-2">
                    <button className="font-medium text-sm hover:underline text-left" onClick={() => s.manufacturer_id && openMfr(s.manufacturer_id)}>{s.name}</button>
                    <span className="text-xs text-faint">{s.state}</span>
                    <Badge tone={LEVEL[s.level].tone as any} className="ml-auto">{s.response}</Badge>
                  </div>
                  <div className="text-[11px] text-muted mt-1">
                    {s.manufacturer_id ? `${s.national_alerts_total} national alerts in total · ${s.national_alerts_12m} in the last 12 months · ${s.critical_12m} critical` : 'No national alert on record'}
                  </div>
                  {s.reasons.length > 0 && <ul className="mt-1.5 space-y-0.5">{s.reasons.map((r) => <li key={r} className="text-[11px] text-red-200 flex gap-1.5"><ShieldAlert size={12} className="mt-0.5 shrink-0" />{r}</li>)}</ul>}
                  <div className="mt-2 flex gap-2">
                    <Button variant={s.level === 'ok' ? 'primary' : 'ghost'} className="!py-1 !px-3 text-xs" onClick={() => raise(s)}>Raise PO</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <AnimatePresence>
            {poRes && (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className={clsx('mt-3 rounded-xl border p-3 text-sm', poRes.created ? 'border-emerald-500/30 bg-emerald-500/[0.06]' : 'border-red-500/30 bg-red-500/[0.06]')}>
                {poRes.created ? (
                  <div className="flex gap-2"><CheckCircle2 size={16} className="text-emerald-300 mt-0.5" /><div>PO <b>{poRes.po_id}</b> raised with {poRes.supplier.name}{poRes.check.reasons.length ? <span className="text-amber-200"> (with warnings recorded on the PO)</span> : ''}. It is now in the queue as <b>{poRes.case_id}</b>.</div></div>
                ) : (
                  <div className="flex gap-2"><Ban size={16} className="text-red-300 mt-0.5" /><div>
                    <div><b>Blocked by the national check.</b> {poRes.check.reasons.join('; ')}.</div>
                    <button className="text-xs underline text-muted mt-1" onClick={() => raise(poRes.supplier, true)}>Record an override (logged)</button>
                  </div></div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-2 font-display font-semibold"><ClipboardCheck size={17} className="text-ours" /> Quality-control queue · test the riskiest first</div>
          <p className="text-xs text-muted mt-1">Open batches for {buyerName}, ordered by the batch-risk score. Issue is refused until a batch is cleared.
            {batchEval && <> On held-out simulated 2026 batches, testing in this order caught {fmtPct(batchEval['DawaDrishti risk order'].caught_in_first_30pct)} of failing batches in the first 30% of tests, against {fmtPct(batchEval['First in, first out'].caught_in_first_30pct)} first-in-first-out.</>}</p>
          <AnimatePresence>{msg && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className={clsx('mt-3 rounded-xl border px-3 py-2 text-sm', msg.tone === 'good' ? 'border-emerald-500/30 bg-emerald-500/[0.06]' : msg.tone === 'bad' ? 'border-red-500/30 bg-red-500/[0.06]' : 'border-amber-500/30 bg-amber-500/[0.06]')}>{msg.text}</motion.div>
          )}</AnimatePresence>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-faint text-left"><tr><th className="py-2 font-normal">Batch</th><th className="font-normal">Product · supplier</th><th className="font-normal">Status</th><th className="font-normal">Risk</th><th className="font-normal text-right">Actions</th></tr></thead>
              <tbody>
                {queue.map((r) => (
                  <tr key={r.batch_id} className={clsx('border-t border-line/60 align-top', caseId === r.batch_id && 'bg-ours/[0.05]')}>
                    <td className="py-2 pr-2"><button className="font-mono text-xs hover:underline" onClick={() => setCaseId(r.batch_id)}>{r.batch_id}</button></td>
                    <td className="pr-2"><div className="truncate max-w-[220px]">{r.generic_name}</div><div className="text-[11px] text-faint truncate max-w-[220px]">{r.supplier}</div></td>
                    <td className="pr-2"><Badge tone={r.qc_status === 'cleared' ? 'good' : r.qc_status === 'held' ? 'bad' : r.qc_status === 'quarantine' ? 'warn' : 'neutral'}>{r.qc_status}</Badge></td>
                    <td className="pr-2 w-24">{r.risk_score != null && <div className="flex items-center gap-1.5"><span className="w-12 h-1.5 rounded bg-surface-3 overflow-hidden"><span className="block h-full bg-blood" style={{ width: `${Math.min(100, 100 * r.risk_score / 0.3)}%` }} /></span><span className="text-[11px] num text-muted">{(100 * r.risk_score).toFixed(0)}%</span></div>}</td>
                    <td className="text-right whitespace-nowrap space-x-1">
                      {r.qc_status === 'ordered' && <Button variant="ghost" className="!py-1 !px-2 text-xs" onClick={() => act(() => api.receive(r.batch_id), (x) => ({ tone: 'warn', text: `Received and quarantined. Risk score ${(100 * x.risk_score).toFixed(0)}%. Sample coded and sent to the lab.` }))}><PackageCheck size={13} /> Receive</Button>}
                      {r.qc_status === 'quarantine' && <>
                        <Button variant="ghost" className="!py-1 !px-2 text-xs" onClick={() => act(() => api.result(r.batch_id, true), (x) => ({ tone: 'good', text: x.actions.join(' ') }))}>Pass</Button>
                        <Button variant="ghost" className="!py-1 !px-2 text-xs" onClick={() => act(() => api.result(r.batch_id, false, 'Assay'), (x) => ({ tone: 'bad', text: x.actions.join(' ') }))}><PackageX size={13} /> Fail</Button>
                      </>}
                      {r.qc_status !== 'ordered' && <Button variant="ghost" className="!py-1 !px-2 text-xs" onClick={() => act(() => api.issue(r.batch_id), (x) => x.issued ? { tone: 'good', text: `Issued ${r.batch_id} to a facility.` } : { tone: 'bad', text: `Rule ${x.rule}: ${x.message}` })}><Send size={13} /> Issue</Button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {caseId && <CaseTimeline id={caseId} key={caseId + queue.length} />}
        </Card>
      </div>
    </div>
  )
}

function ContractPanel({ c }: { c: any }) {
  const tone = c.concentration === 'single source' ? 'bad' : c.concentration === 'concentrated' ? 'warn' : 'good'
  return (
    <div className="mt-4 rounded-xl border border-line bg-surface-2/50 p-3">
      <div className="flex items-center gap-2 text-xs text-muted"><PieChart size={13} /> Supply position for this item <Badge tone={tone as any} className="ml-auto">{c.concentration}</Badge></div>
      <div className="flex h-2 rounded overflow-hidden mt-2 bg-surface-3">
        {c.suppliers.map((s: any, i: number) => <div key={s.supplier_id} title={`${s.name}: ${fmtPct(s.share)}`} style={{ width: `${100 * s.share}%`, background: ['#22d3ee', '#a78bfa', '#f59e0b', '#34d399', '#fb7185'][i % 5] }} />)}
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2 text-[11px] text-muted num">
        <div>largest supplier <b className="text-ink">{c.top_share != null ? fmtPct(c.top_share) : '–'}</b> of 12-month volume</div>
        <div>days of cover <b className="text-ink">{c.days_of_cover ?? '–'}</b>{c.days_of_cover_with_testing != null && c.days_of_cover_with_testing !== c.days_of_cover && <> ({c.days_of_cover_with_testing} incl. stock in testing)</>}</div>
        <div>daily use <b className="text-ink">{c.daily_use != null ? fmtInt(c.daily_use) : '–'}</b> units</div>
      </div>
      {c.concentration === 'single source' && <div className="text-[11px] text-amber-200 mt-1.5">Pausing this supplier leaves no second source: line up an alternative before acting on a level-3 response.</div>}
    </div>
  )
}

function CaseTimeline({ id }: { id: string }) {
  const [c, setC] = useState<any>(null)
  useEffect(() => { api.caseTimeline(id).then(setC) }, [id])
  if (!c) return null
  return (
    <div className="mt-4 rounded-xl border border-line bg-surface-2/50 p-3">
      <div className="text-xs text-muted mb-2">Event log for case <span className="font-mono text-ink">{id}</span> (what process mining reads)</div>
      <ol className="relative border-l border-line ml-2 space-y-2">
        {c.events.map((e: any, i: number) => (
          <li key={i} className="ml-4 text-xs"><span className="absolute -left-[5px] mt-1 h-2.5 w-2.5 rounded-full bg-ours" />
            <span className="font-medium text-ink">{e.activity}</span> <span className="text-faint">· {e.erp_module} · {e.resource} · {e.ts.replace('T', ' ')}</span></li>
        ))}
      </ol>
    </div>
  )
}
