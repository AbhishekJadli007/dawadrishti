import clsx from 'clsx'
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, axis, fmtInt, fmtPct, tipStyle } from '../api'
import { ProcessMap } from '../components/ProcessMap'
import { Badge, Card, SectionTitle, Spinner } from '../components/ui'

const BUYERS = [['', 'All buyers'], ['B1', 'National'], ['B2', 'Northern'], ['B3', 'Western'], ['B4', 'Southern'], ['B5', 'Eastern']]

export default function ProcessMining() {
  const [buyer, setBuyer] = useState('')
  const [d, setD] = useState<any>(null)
  const [rule, setRule] = useState('R1')
  const [viol, setViol] = useState<any>(null)
  useEffect(() => { setD(null); api.process(buyer || undefined).then(setD) }, [buyer])
  useEffect(() => { api.violations(rule, buyer || undefined).then(setViol) }, [rule, buyer])
  if (!d) return <Spinner label="Mining the event log…" />
  const disc = d.discovery
  const rc = d.root_cause

  return (
    <div className="space-y-8">
      <SectionTitle eyebrow="Process mining · simulated buyer event log" title="The conformance engine, demonstrated on simulated buyers"
        sub={`${fmtInt(disc.cases)} procurement cases, ${fmtInt(disc.events)} events from 5 fictional buyers whose rule-breaking was simulated on purpose, so finding it shows the method works, not how real buyers behave. The rules are data in a declarative engine, which gives identical counts to hand-written checks on this log. The same engine is validated on the public BPI Challenge 2019 purchase-to-pay log (below).`}
        right={<div className="flex flex-wrap gap-1 rounded-xl bg-surface border border-line p-1">{BUYERS.map(([id, l]) => (
          <button key={id} onClick={() => setBuyer(id)} className={clsx('px-3 py-1.5 rounded-lg text-xs', buyer === id ? 'bg-surface-3 text-ink' : 'text-muted hover:text-ink')}>{l}</button>))}</div>} />

      <Card className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="font-display font-semibold">Discovered process map</div>
          <div className="flex gap-3 text-[11px] text-muted"><span className="flex items-center gap-1.5"><span className="h-1 w-5 bg-ours/60" /> normal path (width = cases)</span><span className="flex items-center gap-1.5"><span className="h-1 w-5 bg-red-500" /> path that breaks a rule</span></div>
        </div>
        <ProcessMap discovery={disc} />
        <p className="text-xs text-muted">Hover an arrow for its count and mean waiting time. Red arrows: stock issued or paid before the lab result, or a sample sent without blind coding.</p>
      </Card>

      <EngineCheck x={d.crosscheck} bpi={d.bpi2019} />

      <section>
        <SectionTitle title="Conformance: six rules from published quality-clearance processes" sub={<>Each card counts the cases that broke the rule. Click one to see the cases. <Badge tone="warn">simulated</Badge></>} />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(d.rules).map(([id, r]: [string, any]) => {
            const n = d.benchmark.reduce((s: number, b: any) => s + (buyer && b.buyer_id !== buyer ? 0 : b[id]), 0)
            return (
              <button key={id} onClick={() => setRule(id)} className={clsx('card p-4 text-left transition', rule === id && 'ring-1 ring-ours/50')}>
                <div className="flex items-center gap-2"><Badge tone={n ? 'bad' : 'good'}>{id}</Badge><span className="font-display text-2xl font-bold num">{fmtInt(n)}</span><span className="text-xs text-faint">cases</span></div>
                <div className="text-sm mt-1.5">{r.name}</div>
                <div className="text-[11px] text-faint mt-0.5">{r.why}</div>
              </button>
            )
          })}
        </div>
        {viol && (
          <Card className="p-0 mt-3 overflow-x-auto">
            <table className="w-full text-xs min-w-[700px]">
              <thead className="text-faint"><tr className="border-b border-line">{['Case', 'Buyer', 'Supplier', 'Product', 'What happened'].map((h) => <th key={h} className="text-left font-normal py-2 px-3">{h}</th>)}</tr></thead>
              <tbody>{viol.rows.slice(0, 12).map((v: any, i: number) => (
                <tr key={i} className="border-b border-line/50"><td className="py-1.5 px-3 font-mono">{v.case_id}</td><td className="px-3">{v.buyer}</td><td className="px-3 truncate max-w-[200px]">{v.supplier}</td><td className="px-3 truncate max-w-[180px]">{v.product}</td><td className="px-3 text-muted">{v.detail}</td></tr>
              ))}</tbody>
            </table>
            <div className="px-3 py-2 text-[11px] text-faint">Showing 12 of {fmtInt(viol.total)} cases for {rule}.</div>
          </Card>
        )}
      </section>

      <section className="grid lg:grid-cols-2 gap-5">
        <Card className="p-5">
          <div className="font-display font-semibold">National league table</div>
          <p className="text-xs text-muted mb-3">Conformance = share of cases that broke no rule.</p>
          <table className="w-full text-sm num">
            <thead className="text-xs text-faint"><tr><th className="text-left font-normal">Buyer</th><th className="text-right font-normal">Conformance</th><th className="text-right font-normal">Lab days</th><th className="text-right font-normal">Quarantine days</th></tr></thead>
            <tbody>{d.benchmark.map((b: any) => (
              <tr key={b.buyer_id} className={clsx('border-t border-line/60', buyer === b.buyer_id && 'bg-ours/[0.06]')}>
                <td className="py-2">{b.buyer}</td>
                <td className="text-right font-semibold" style={{ color: b.conformance > 0.8 ? '#10b981' : b.conformance > 0.5 ? '#f59e0b' : '#ef4444' }}>{fmtPct(b.conformance, 1)}</td>
                <td className="text-right">{b.median_lab_tat_days}</td><td className="text-right">{b.median_quarantine_days}</td>
              </tr>))}</tbody>
          </table>
        </Card>
        <Card className="p-5">
          <div className="font-display font-semibold">Root cause: slow labs push stock out untested</div>
          <p className="text-xs text-muted mb-2">Share of cases issued before clearance, by lab turnaround. Decision-tree top driver: {rc.drivers[0]?.feature} ({rc.drivers[0]?.importance}).</p>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={rc.early_issue_by_lab_tat.map((r: any) => ({ ...r, pct: +(100 * r.rate).toFixed(1) }))} margin={{ top: 18, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="#e3e8ef" />
                <XAxis dataKey="band" tick={axis} axisLine={false} tickLine={false} label={{ value: 'lab turnaround (days)', position: 'insideBottom', offset: -2, fill: '#94a3b8', fontSize: 10 }} />
                <YAxis tick={axis} axisLine={false} tickLine={false} unit="%" />
                <Tooltip contentStyle={tipStyle} formatter={(v) => `${v}%`} />
                <Bar dataKey="pct" radius={[6, 6, 0, 0]}>
                  {rc.early_issue_by_lab_tat.map((r: any, i: number) => <Cell key={i} fill={r.rate > 0.15 ? '#ef4444' : r.rate > 0.08 ? '#f59e0b' : '#0d9488'} />)}
                  <LabelList dataKey="pct" position="top" formatter={(v: unknown) => `${v}%`} style={{ fill: '#0f172a', fontSize: 11 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      <section className="grid lg:grid-cols-2 gap-5">
        <Card className="p-5">
          <div className="font-display font-semibold">Where the time goes</div>
          <p className="text-xs text-muted mb-2">Median and 90th-percentile days per step. Bottleneck: {d.performance.bottleneck}.</p>
          <div className="space-y-2">{d.performance.steps.map((s: any) => (
            <div key={s.step} className="grid grid-cols-[150px_1fr_90px] items-center gap-2 text-sm">
              <span className="text-muted">{s.step}</span>
              <span className="h-2 rounded bg-surface-3 overflow-hidden relative"><span className="absolute inset-y-0 left-0 bg-ours/40" style={{ width: `${Math.min(100, (100 * s.p90_days) / 40)}%` }} /><span className="absolute inset-y-0 left-0 bg-ours" style={{ width: `${Math.min(100, (100 * s.median_days) / 40)}%` }} /></span>
              <span className="text-right num text-xs">{s.median_days} / {s.p90_days} d</span>
            </div>))}</div>
        </Card>
        <Card className="p-5">
          <div className="font-display font-semibold">Process variants</div>
          <p className="text-xs text-muted mb-2">The most common paths through the process, across all buyers.</p>
          <div className="space-y-2 max-h-72 overflow-y-auto">{d.variants.slice(0, 8).map((v: any, i: number) => (
            <div key={i} className="text-xs"><div className="flex justify-between"><span className="text-faint">Variant {i + 1} · {v.steps} steps</span><span className="num">{fmtInt(v.cases)} cases ({fmtPct(v.share, 1)})</span></div>
              <div className="text-muted leading-relaxed">{v.variant}</div></div>))}</div>
        </Card>
      </section>
    </div>
  )
}

function EngineCheck({ x, bpi }: { x: any; bpi: any }) {
  return (
    <section className="grid lg:grid-cols-2 gap-5">
      <Card className="p-5">
        <div className="font-display font-semibold">Is the engine counting correctly?</div>
        <p className="text-xs text-muted mt-1">The same rules written two ways, as data for the declarative engine and as hand-written checks, run on the same {x ? fmtInt(x.cases) : ''} cases.</p>
        {x && <table className="w-full text-xs num mt-3">
          <thead className="text-faint"><tr><th className="text-left font-normal">Rule</th><th className="text-right font-normal">Hand-written</th><th className="text-right font-normal">Declarative</th></tr></thead>
          <tbody>{x.rules.map((r: any) => <tr key={r.rule} className="border-t border-line/50"><td className="py-1">{r.rule} {r.name}</td><td className="text-right">{fmtInt(r.hand_written)}</td><td className={`text-right ${r.hand_written === r.declarative ? 'text-emerald-600' : 'text-rose-600'}`}>{fmtInt(r.declarative)}</td></tr>)}</tbody>
        </table>}
      </Card>
      <Card className="p-5">
        <div className="flex items-center gap-2"><div className="font-display font-semibold">On a log we did not write: BPI Challenge 2019</div><Badge tone={bpi ? 'ours' : 'warn'}>{bpi ? 'real SAP log' : 'pending'}</Badge></div>
        {bpi ? (<>
          <p className="text-xs text-muted mt-1">{fmtInt(bpi.events)} events, {fmtInt(bpi.cases)} purchase-order items from a multinational's SAP system (public, 4TU.ResearchData). Same engine, purchase-to-pay rules.
            {bpi.reader_check?.all_match && <> Our reader reproduces the published counts exactly (events, cases, {fmtInt(bpi.purchase_documents)} purchase documents, {bpi.activities} activities).</>}</p>
          <table className="w-full text-xs num mt-3">
            <thead className="text-faint"><tr><th className="text-left font-normal">Rule</th><th className="text-right font-normal">Violating</th><th className="text-right font-normal">Share</th></tr></thead>
            <tbody>{bpi.rules.map((r: any) => <tr key={r.id} className="border-t border-line/50"><td className="py-1">{r.id} {r.name}</td><td className="text-right">{fmtInt(r.violating_cases)}</td><td className="text-right">{(100 * r.share).toFixed(1)}%</td></tr>)}</tbody>
          </table>
          {bpi.reading && <p className="text-[11px] text-faint mt-2">{bpi.reading}</p>}
        </>) : (
          <p className="text-xs text-muted mt-2">The public purchase-to-pay log (1,595,923 events, 251,734 cases) could not be downloaded from 4TU on the build machine. Download it from data.4tu.nl and run
            <span className="block font-mono text-ink mt-1">python -m dawadrishti.mining.conformance --bpi BPI_Challenge_2019.xes</span>
            The results appear here.</p>
        )}
      </Card>
    </section>
  )
}
