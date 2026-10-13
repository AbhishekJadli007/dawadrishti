import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, axis, fmtInt, fmtPct, tipStyle } from '../api'
import { Badge, Card, SectionTitle, Spinner } from '../components/ui'
import { useView } from '../mode'

const COL: Record<string, string> = { 'Attention model (ML)': '#0d9488', 'DawaDrishti ML model': '#0d9488', 'DawaDrishti risk order': '#0d9488', 'Most past failures': '#f59e0b', 'Most recent failure': '#8b5cf6', 'First in, first out': '#f59e0b', Random: '#cbd5e1' }

export default function Risk({ openMfr }: { openMfr: (id: string) => void }) {
  const { view, setView } = useView()
  const [d, setD] = useState<any>(null)
  const [net, setNet] = useState<any>(null)
  useEffect(() => { api.risk(view).then(setD).catch(() => api.risk('public').then(setD)); api.overview().then((o) => setNet(o.network)) }, [view])
  if (!d) return <Spinner label="Loading risk models…" />
  const t = d.factory.test
  const fRows = Object.entries(t.results).map(([n, r]: [string, any]) => ({ n, p50: +(100 * r.top50.precision).toFixed(0), r200: +(100 * r.top200.recall).toFixed(0), auc: r.auc }))
  const b = d.batch.test
  const bRows = Object.entries(b.results).map(([n, r]: [string, any]) => ({ n, caught: +(100 * r.caught_in_first_30pct).toFixed(0), auc: r.auc }))

  return (
    <div className="space-y-8">
      <SectionTitle eyebrow="Models · evaluated against baselines" title="Where regulators will look next, and which batches to test first"
        sub="Each model is trained only on the past and tested on a period it never saw, next to the simple rules a regulator or buyer would otherwise use. Where a simple rule does as well, we say so." />

      <section className="grid lg:grid-cols-[1fr_1.1fr] gap-5">
        <Card className="p-5">
          <div className="flex items-center gap-2"><div className="font-display font-semibold">Future regulatory attention (real national data)</div><Badge tone="ours">real</Badge></div>
          <p className="text-xs text-muted mt-1">Trained on monthly snapshots up to Sep 2025; tested on {t.cutoff}: which of {fmtInt(t.universe)} units appear in the real alerts of the next {t.horizon_months} months ({fmtInt(t.positives)} did; base rate {fmtPct(t.base_rate)}).
            This predicts being sampled and failing again, which depends on where inspectors look as much as on the factory.</p>
          <div className="h-64 mt-3">
            <ResponsiveContainer>
              <BarChart data={fRows} margin={{ top: 18, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="#e3e8ef" />
                <XAxis dataKey="n" tick={{ ...axis, fontSize: 10 }} axisLine={false} tickLine={false} interval={0} />
                <YAxis tick={axis} axisLine={false} tickLine={false} unit="%" />
                <Tooltip contentStyle={tipStyle} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="p50" name="hit rate of top 50 inspections" radius={[6, 6, 0, 0]}>{fRows.map((r) => <Cell key={r.n} fill={COL[r.n]} />)}<LabelList dataKey="p50" position="top" formatter={(v: unknown) => `${v}%`} style={{ fill: '#0f172a', fontSize: 11 }} /></Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="w-full text-xs num mt-2">
            <thead className="text-faint"><tr><th className="text-left font-normal">Method</th><th className="text-right font-normal">AUC</th><th className="text-right font-normal">Top-50 hit rate</th><th className="text-right font-normal">Top-200 recall</th></tr></thead>
            <tbody>{fRows.map((r) => <tr key={r.n} className="border-t border-line/50"><td className="py-1">{r.n}</td><td className="text-right">{r.auc}</td><td className="text-right">{r.p50}%</td><td className="text-right">{r.r200}%</td></tr>)}</tbody>
          </table>
          <p className="text-[11px] text-faint mt-2">Honest reading: "most recent failure" is as good on the top 50 alone; the model ranks the whole list best (highest AUC and top-200 recall).</p>
          {t.confound && <Confound c={t.confound} />}
        </Card>
        {view !== 'buyer' ? (
          <Card className="p-5 flex flex-col justify-center">
            <div className="font-display font-semibold">Ranked list: buyer and regulator view only</div>
            <p className="text-sm text-muted mt-2">Public pages show what was published about a manufacturer, never a predicted score. A ranked list of named firms by predicted risk is for drug controllers and buyers deciding where to test, and is shown only in the buyer view.</p>
            <button onClick={() => setView('buyer')} className="text-sm text-amber-700 hover:underline mt-3 self-start">Switch to buyer view →</button>
          </Card>
        ) : (
        <Card className="p-5">
          <div className="font-display font-semibold">Where to sample next ({d.factory.as_of})</div>
          <p className="text-xs text-muted mb-2">For drug controllers planning sampling, with the alerts behind each rank. A signal for where to test, not a finding against anyone.</p>
          <div className="max-h-[430px] overflow-y-auto space-y-1">
            {d.factory.inspect_next.slice(0, 40).map((r: any, i: number) => (
              <button key={r.manufacturer_id} onClick={() => openMfr(r.manufacturer_id)} className="w-full text-left rounded-lg px-2 py-1.5 hover:bg-surface-3">
                <div className="flex items-center gap-2 text-sm"><span className="text-faint num w-6 text-xs">{i + 1}</span><span className="flex-1 truncate">{r.canonical_name}</span>
                  <span className="text-[11px] text-faint">{r.state}</span><span className="num text-xs text-blood-soft w-10 text-right">{fmtPct(r.risk)}</span></div>
                <div className="text-[11px] text-faint pl-8">{r.why}</div>
              </button>))}
          </div>
        </Card>)}
      </section>

      <section className="grid lg:grid-cols-2 gap-5">
        <Card className="p-5">
          <div className="flex items-center gap-2"><div className="font-display font-semibold">Batch risk: test the riskiest first</div><Badge tone="warn">simulated ERP</Badge></div>
          <p className="text-xs text-muted mt-1">{fmtInt(b.batches)} batches received in {b.period}; {b.failed} failed. If the lab can test only {b.lab_capacity_first} first, what share of the failing batches is caught early?</p>
          <div className="h-56 mt-3">
            <ResponsiveContainer>
              <BarChart data={bRows} margin={{ top: 18, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="#e3e8ef" />
                <XAxis dataKey="n" tick={axis} axisLine={false} tickLine={false} />
                <YAxis tick={axis} axisLine={false} tickLine={false} unit="%" />
                <Tooltip contentStyle={tipStyle} />
                <Bar dataKey="caught" name="failures caught in first 30% of tests" radius={[6, 6, 0, 0]}>{bRows.map((r) => <Cell key={r.n} fill={COL[r.n]} />)}<LabelList dataKey="caught" position="top" formatter={(v: unknown) => `${v}%`} style={{ fill: '#0f172a', fontSize: 11 }} /></Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        {net && (
          <Card className="p-5">
            <div className="flex items-center gap-2"><div className="font-display font-semibold">National memory vs isolated ERPs</div><Badge tone="warn">simulated ERP</Badge></div>
            <p className="text-xs text-muted mt-1">The same 20 months replayed twice: buyers seeing only their own tests (today), and buyers sharing national alerts and debarments at purchase-order time (DawaDrishti).</p>
            <table className="w-full text-sm num mt-4">
              <thead className="text-xs text-faint"><tr><th className="text-left font-normal">Measure</th><th className="text-right font-normal">Isolated (today)</th><th className="text-right font-normal">National memory</th><th className="text-right font-normal">Change</th></tr></thead>
              <tbody>{[
                ['Orders to a supplier already debarred elsewhere', 'orders_to_debarred'],
                ['Failed batches received', 'failed_batches'],
                ['Orders placed after the supplier failed at another buyer', 'orders_after_failure_elsewhere'],
              ].map(([l, k]) => {
                const a = net.isolated[k], z = net.network[k]
                return <tr key={k} className="border-t border-line/60"><td className="py-2">{l}</td><td className="text-right">{fmtInt(a)}</td><td className="text-right text-ours font-semibold">{fmtInt(z)}</td><td className="text-right text-emerald-600">{(100 * (z / a - 1)).toFixed(0)}%</td></tr>
              })}</tbody>
            </table>
          </Card>
        )}
      </section>
    </div>
  )
}

function Confound({ c }: { c: any }) {
  const rows = [...c.groups.map((g: any) => ({ k: g.group, n: g.units, m: g.model_auc, r: g.most_recent_failure_auc })),
    ...(c.detected_elsewhere ?? []).map((g: any) => ({ k: `next alert ${g.split}`, n: g.units, m: g.model_auc, r: g.most_recent_failure_auc }))]
  return (
    <div className="mt-4 border-t border-line/60 pt-3">
      <div className="text-xs font-medium">Is the model only learning where inspectors look?</div>
      <table className="w-full text-[11px] num mt-1.5">
        <thead className="text-faint"><tr><th className="text-left font-normal">Units scored</th><th className="text-right font-normal">n</th><th className="text-right font-normal">Model AUC</th><th className="text-right font-normal">Most recent failure</th></tr></thead>
        <tbody>{rows.map((x) => <tr key={x.k} className="border-t border-line/40"><td className="py-1 pr-2">{x.k}</td><td className="text-right">{x.n}</td><td className="text-right">{x.m}</td><td className="text-right">{x.r}</td></tr>)}</tbody>
      </table>
      <p className="text-[11px] text-faint mt-1.5">A model that knows only the unit's state scores {c.state_only_baseline_auc}. The model keeps its ranking when the next failure is caught by a lab or state that had never caught that unit, so it is not just predicting a lab's routine re-test.</p>
    </div>
  )
}
