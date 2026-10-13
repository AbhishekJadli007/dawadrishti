import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { api, axis, fmtInt, fmtPct, tipStyle } from '../api'
import { Badge, Card, SectionTitle, Spinner } from '../components/ui'

const ARCH: Record<string, string> = {
  'Many failures on record': '#ef4444', 'Mostly critical failures': '#8b5cf6', 'A few failures on record': '#f59e0b', 'Mostly injectable failures': '#0d9488',
  'One failure on record': '#64748b',
}

export default function DataMining({ openMfr }: { openMfr: (id: string) => void }) {
  const [d, setD] = useState<any>(null)
  useEffect(() => { api.mining().then(setD) }, [])
  if (!d) return <Spinner label="Mining national data…" />
  const r = d.repeat
  const failures = Object.entries(d.trends.failures).map(([k, v]) => ({ k, v })).slice(0, 10)

  return (
    <div className="space-y-8">
      <SectionTitle eyebrow="Data mining · real CDSCO alerts" title="Patterns in India's failed medicines"
        sub={`${fmtInt(d.findings)} failed batches from ${d.since} to ${d.as_of}, cleaned and loaded into the warehouse. Every number on this page comes from real national alerts.`} />

      <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat v={fmtInt(r.manufacturers)} l="manufacturing units with at least one failed batch" />
        <Stat v={fmtInt(r.repeat_manufacturers)} l={`units with more than one failed batch, behind ${fmtPct(r.repeat_share_of_findings)} of all failures`} c="text-blood-soft" />
        <Stat v={fmtPct(r.recurrence_12m)} l="of failures are followed by another from the same unit within 12 months" c="text-today" />
        <Stat v={`${r.median_months_between_failures} mo`} l="median gap between a unit's failures" />
      </section>

      <section className="grid lg:grid-cols-[1.2fr_1fr] gap-5">
        <Card className="p-5">
          <div className="font-display font-semibold">Units with the most failed batches on record</div>
          <p className="text-xs text-muted mb-2">Ranked by published alerts, not by any judgement of the firm. Click a name for its full record.</p>
          <div className="max-h-[420px] overflow-y-auto">
            <table className="w-full text-sm num">
              <thead className="text-xs text-faint sticky top-0 bg-surface"><tr><th className="text-left font-normal py-1">Manufacturer</th><th className="text-right font-normal">Failures</th><th className="text-right font-normal">Critical</th><th className="text-right font-normal">Products</th><th className="text-right font-normal">Active</th></tr></thead>
              <tbody>{r.top.slice(0, 25).map((x: any) => (
                <tr key={x.manufacturer_id} className="border-t border-line/60">
                  <td className="py-1.5"><button className="text-left hover:underline" onClick={() => openMfr(x.manufacturer_id)}>{x.manufacturer}</button><div className="text-[11px] text-faint">{x.state}</div></td>
                  <td className="text-right font-semibold">{x.findings}</td><td className="text-right text-rose-600">{x.critical}</td>
                  <td className="text-right">{x.products}</td><td className="text-right text-xs text-muted">{x.first} → {x.last}</td>
                </tr>))}</tbody>
            </table>
          </div>
        </Card>
        <Card className="p-5">
          <div className="font-display font-semibold">Groups of units by their alert history (k-means clustering)</div>
          <p className="text-xs text-muted mb-2">Each dot is a manufacturer: failures vs share of them that were critical.</p>
          <div className="h-64">
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 5, right: 8, left: -14, bottom: 5 }}>
                <CartesianGrid stroke="#e3e8ef" />
                <XAxis type="number" dataKey="findings" scale="log" domain={[1, 'auto']} tick={axis} name="failures" />
                <YAxis type="number" dataKey="critical_share" tick={axis} name="critical share" />
                <ZAxis range={[18, 18]} />
                <Tooltip contentStyle={tipStyle} formatter={(v: any, n: any) => (n === 'critical share' ? fmtPct(Number(v)) : v)} labelFormatter={() => ''} />
                {Object.keys(ARCH).map((a) => <Scatter key={a} name={a} data={d.clusters.points.filter((p: any) => p.archetype === a)} fill={ARCH[a]} fillOpacity={0.7} />)}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-1 mt-2">{d.clusters.summary.map((c: any) => (
            <div key={c.archetype} className="flex items-center gap-2 text-xs"><span className="h-2.5 w-2.5 rounded-full" style={{ background: ARCH[c.archetype] ?? '#888' }} />
              <span className="flex-1">{c.archetype}</span><span className="num text-muted">{c.manufacturers} units · {c.avg_findings} failures avg · {fmtPct(c.avg_critical_share)} critical</span></div>))}</div>
        </Card>
      </section>

      <section>
        <SectionTitle title="Association rules (FP-Growth)" sub="Which product types tend to fail which tests. Lift = how many times more likely than average." />
        <Card className="p-0 overflow-x-auto">
          <table className="w-full text-sm min-w-[720px]">
            <thead className="text-xs text-faint"><tr className="border-b border-line"><th className="text-left font-normal py-2 px-4">If the failed batch is…</th><th className="text-left font-normal px-4">…then it most often failed on</th><th className="text-right font-normal px-4">Confidence</th><th className="text-right font-normal px-4">Lift</th><th className="text-right font-normal px-4">Support</th></tr></thead>
            <tbody>{d.rules.slice(0, 12).map((x: any, i: number) => (
              <tr key={i} className="border-b border-line/50"><td className="py-2 px-4">{x.if.map((t: string) => <Badge key={t} className="mr-1">{t.replace('=', ': ')}</Badge>)}</td>
                <td className="px-4"><Badge tone="bad">{x.then.split('=')[1]}</Badge></td><td className="px-4 text-right num">{fmtPct(x.confidence)}</td>
                <td className="px-4 text-right num font-semibold">{x.lift}×</td><td className="px-4 text-right num text-muted">{fmtPct(x.support, 1)}</td></tr>))}</tbody>
          </table>
        </Card>
      </section>

      <section className="grid lg:grid-cols-2 gap-5">
        <Card className="p-5">
          <div className="font-display font-semibold">Spikes: anomaly detection</div>
          <p className="text-xs text-muted mb-2">Months where a state's or drug class's failures jumped far above its own previous 12 months (z ≥ 3).</p>
          <div className="space-y-1.5 max-h-80 overflow-y-auto">{d.anomalies.slice(0, 14).map((a: any, i: number) => (
            <div key={i} className="flex items-center gap-2 text-sm"><span className="text-xs text-faint w-16 num">{a.month}</span>
              <span className="flex-1">{a.value} <span className="text-[11px] text-faint">({a.dimension === 'state' ? 'state' : 'drug class'})</span></span>
              <span className="num text-xs">{a.count} vs {a.expected} expected</span><Badge tone="bad">z {a.z}</Badge></div>))}</div>
        </Card>
        <Card className="p-5">
          <div className="font-display font-semibold">What fails (text mining of failure reasons)</div>
          <p className="text-xs text-muted mb-2">Free-text NSQ results classified into categories and severity.</p>
          <div className="h-80">
            <ResponsiveContainer>
              <BarChart data={failures} layout="vertical" margin={{ top: 0, right: 20, left: 40, bottom: 0 }}>
                <CartesianGrid horizontal={false} stroke="#e3e8ef" />
                <XAxis type="number" tick={axis} axisLine={false} />
                <YAxis type="category" dataKey="k" tick={{ ...axis, fontSize: 11 }} width={150} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tipStyle} />
                <Bar dataKey="v" name="failed batches" radius={[0, 6, 6, 0]}>{failures.map((f, i) => <Cell key={i} fill={/DEG|Steril|Endotoxin|Microbial|Spurious|Identity/.test(f.k) ? '#ef4444' : '#f59e0b'} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>
    </div>
  )
}

function Stat({ v, l, c }: { v: string; l: string; c?: string }) {
  return <Card className="p-5"><div className={`font-display text-3xl font-bold ${c ?? ''}`}>{v}</div><div className="text-sm text-muted mt-1">{l}</div></Card>
}
