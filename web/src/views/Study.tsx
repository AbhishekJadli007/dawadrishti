import { ArrowRight, Building2, Clock, MapPinned, Repeat2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, axis, fmtInt, fmtPct, SEV_COLOR, tipStyle } from '../api'
import type { TabId } from '../App'
import { IndiaMap } from '../components/IndiaMap'
import { AnimatedNumber, Badge, Button, Card, SectionTitle, Source, Spinner } from '../components/ui'

const DEFAULT_RULE = 'fuzzy ≥92, same state (default)'

export default function Study({ go, openMfr }: { go: (t: TabId) => void; openMfr: (q: string) => void }) {
  const [s, setS] = useState<any>(null)
  const [o, setO] = useState<any>(null)
  useEffect(() => { api.study().then(setS); api.overview().then(setO) }, [])
  if (!s) return <Spinner label="Loading the study…" />
  const h = s.headline
  const [lo, hi] = h.repeat_share_ci95
  const buckets = Object.entries(h.firms_by_failures).map(([k, v]) => ({ k: `${k} failure${k === '1' ? '' : 's'}`, units: v as number }))
  const ablation = Object.entries(s.ablation).map(([rule, m]: [string, any]) => ({
    rule, units: m.firms, share: m.repeat_share, gap: m.median_months_first_to_next, isDefault: rule === DEFAULT_RULE,
  }))

  return (
    <div className="space-y-14">
      <section className="grid lg:grid-cols-[1.15fr_0.85fr] gap-10 items-center">
        <div>
          <div className="flex flex-wrap gap-2 mb-5">
            <Badge tone="bad">Real data · CDSCO alerts {s.data.from} to {s.data.to}</Badge>
            <Badge tone="ours">{fmtInt(s.data.records_used)} failed batches · {fmtInt(h.firms)} manufacturing units</Badge>
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-bold leading-[1.06] tracking-tight">
            Two in three failed medicine batches come from a factory <span className="bg-gradient-to-r from-blood-soft via-blood to-rose-500 bg-clip-text text-transparent">already on India's failure list.</span>
          </h1>
          <p className="mt-5 text-muted text-base sm:text-lg max-w-2xl">
            CDSCO publishes every batch that fails a government lab test. We joined nine years of those alerts by manufacturer and asked one question:
            when a batch fails, was its maker already on the national record? For {fmtPct(h.repeat_share)} of failed batches, it was. A buyer checking that record
            before ordering would have seen it. Today no buyer's ERP reads it.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Button onClick={() => go('lookup')}>Look up a manufacturer <ArrowRight size={16} /></Button>
            <Button variant="ghost" onClick={() => go('quality')}>How far the data can be trusted</Button>
          </div>
        </div>
        <Card className="p-7 text-center">
          <div className="text-xs uppercase tracking-[0.18em] text-faint">Failed batches whose maker was already on record</div>
          <div className="font-display text-7xl sm:text-8xl font-bold text-blood-soft mt-3"><AnimatedNumber value={100 * h.repeat_share} format={(v) => `${v.toFixed(1)}%`} /></div>
          <div className="text-sm text-muted mt-2 num">95% CI {fmtPct(lo, 1)} – {fmtPct(hi, 1)} (cluster bootstrap over units)</div>
          <div className="text-sm text-muted mt-1">Among critical failures (contamination, sterility, fakes): <span className="text-ink num">{fmtPct(h.repeat_share_critical, 1)}</span></div>
          <div className="mt-5 text-[11px] text-faint text-left leading-relaxed">
            "Already on record" means the same manufacturing unit appeared in an alert in an earlier month. Identity is resolved by our evaluated
            entity resolution; with exact name strings the share would look like {fmtPct(s.ablation['exact string'].repeat_share)}, because the same factory is spelled {fmtInt(s.ablation['exact string'].firms)} ways.
          </div>
        </Card>
      </section>

      <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi icon={Clock} value={`${h.median_months_first_to_next.toFixed(0)} months`} label="median time from a unit's first failure to its next"
          sub="the window in which a memory could act" />
        <Kpi icon={Repeat2} value={fmtPct(h.repeat_detected_by_new_lab)} label="of repeat failures were caught by a lab that had never caught that unit before"
          sub="the earlier failure was known, but somewhere else" color="text-today" />
        <Kpi icon={MapPinned} value={fmtPct(h.repeat_detected_in_new_state)} label="of repeats were caught in a state that had never caught that unit before"
          sub={`of ${fmtInt(h.repeats_with_state_known)} repeats where a state lab is named`} color="text-today" />
        <Kpi icon={Building2} value={fmtPct(h.top10pct_firms_share)} label="of all failed batches come from 10% of units"
          sub={`Gini ${h.gini.toFixed(2)}: failures are concentrated`} color="text-ours" />
      </section>

      <section className="grid lg:grid-cols-2 gap-5">
        <Card className="p-5">
          <div className="font-display font-semibold">Units by number of failed batches</div>
          <p className="text-xs text-muted mt-1">Most units fail once. A small group fails again and again, and produces most of the failures.</p>
          <div className="h-60 mt-3">
            <ResponsiveContainer>
              <BarChart data={buckets} margin={{ top: 18, right: 8, left: -14, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="#262c3b" />
                <XAxis dataKey="k" tick={axis} axisLine={false} tickLine={false} />
                <YAxis tick={axis} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={tipStyle} />
                <Bar dataKey="units" name="manufacturing units" radius={[6, 6, 0, 0]}>
                  {buckets.map((b, i) => <Cell key={b.k} fill={['#3f4659', '#f59e0b', '#fb7185', '#e11d48'][i]} />)}
                  <LabelList dataKey="units" position="top" style={{ fill: '#e9ecf3', fontSize: 11 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-5">
          <div className="font-display font-semibold">Does the result depend on how names are matched?</div>
          <p className="text-xs text-muted mt-1">Every number recomputed under five matching rules. Above exact strings, the answer stays between 63% and 68%.</p>
          <table className="w-full text-sm num mt-4">
            <thead className="text-xs text-faint"><tr><th className="text-left font-normal">Matching rule</th><th className="text-right font-normal">Units</th><th className="text-right font-normal">Repeat share</th><th className="text-right font-normal">Months to next</th></tr></thead>
            <tbody>{ablation.map((r) => (
              <tr key={r.rule} className={`border-t border-line/60 ${r.isDefault ? 'text-ours' : ''}`}>
                <td className="py-2 pr-2">{r.rule}</td><td className="text-right">{fmtInt(r.units)}</td>
                <td className="text-right font-semibold">{fmtPct(r.share, 1)}</td><td className="text-right">{r.gap ? r.gap.toFixed(1) : '–'}</td>
              </tr>))}</tbody>
          </table>
          <p className="text-[11px] text-faint mt-3">Missed merges split one factory into several and lower the share, so the default (which misses some merges, see Data quality) is conservative.</p>
        </Card>
      </section>

      <section>
        <SectionTitle eyebrow="Worked cases" title="The disasters, checked against the record"
          sub="The honest result: the national alerts alone would not have warned anyone about these three. That is why the memory must also take state-lab and buyer test results." />
        <div className="grid md:grid-cols-3 gap-4">
          {s.worked_cases.map((c: any) => (
            <Card key={c.case} className="p-5">
              <div className="font-display font-semibold">{c.case}</div>
              <div className="text-xs text-faint mt-0.5">{c.note}</div>
              <div className="mt-4 flex gap-6">
                <div><div className="font-display text-3xl font-bold num">{c.alerts_before_incident}</div><div className="text-[11px] text-muted">national alerts before {c.incident}</div></div>
                <div><div className="font-display text-3xl font-bold num text-muted">{c.national_alerts}</div><div className="text-[11px] text-muted">alerts in total</div></div>
              </div>
              <p className="text-xs text-muted mt-4">{caseReading(c)}</p>
              {c.national_alerts > 0 && <button onClick={() => openMfr(c.case.split(' (')[0])} className="text-xs text-ours hover:underline mt-3">see the record →</button>}
            </Card>
          ))}
        </div>
      </section>

      {o && (
        <section className="grid lg:grid-cols-[1fr_1.2fr] gap-5">
          <div>
            <SectionTitle eyebrow="The national record" title="Where failed batches are made" sub="By the state in the manufacturer's address. Sampling is uneven: states that test more find more." />
            <IndiaMap geo={o.geography} height={420} />
          </div>
          <div>
            <SectionTitle title="Failed batches each month, by severity" sub="Every alert, central and state labs. Critical = contamination, sterility, endotoxin, adulteration, fakes." />
            <Card className="p-4">
              <div className="h-[420px]">
                <ResponsiveContainer>
                  <AreaChart data={o.monthly} margin={{ top: 5, right: 10, left: -18, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#262c3b" />
                    <XAxis dataKey="month" tick={axis} axisLine={false} tickLine={false} minTickGap={30} />
                    <YAxis tick={axis} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={tipStyle} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {['critical', 'major', 'minor', 'unclassified'].map((k) => (
                      <Area key={k} type="monotone" dataKey={k} stackId="1" stroke={SEV_COLOR[k]} fill={SEV_COLOR[k]} fillOpacity={0.5} />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </section>
      )}

      <section>
        <SectionTitle eyebrow="Read before quoting" title="What this study can and cannot say" />
        <Card className="p-5 grid md:grid-cols-2 gap-x-8 gap-y-3 text-sm text-muted">
          <p><span className="text-ink">Alerts list failures, not tests.</span> A failure rate per manufacturer cannot be computed; we measure recurrence on the record.</p>
          <p><span className="text-ink">Sampling is uneven.</span> Units in heavily sampled states appear more often. Repeats partly reflect where inspectors look.</p>
          <p><span className="text-ink">The record starts in {s.data.from}.</span> Failures before then are invisible, so some "first" failures are really repeats. The share is a lower bound on that count.</p>
          <p><span className="text-ink">Excluded:</span> {s.data.excluded}. {fmtInt(s.data.outside_india_records)} records name a manufacturer outside India; they are kept and shown.</p>
          <p className="md:col-span-2 text-xs text-faint">Method and code: <Source href="https://github.com/AbhishekJadli007/dawadrishti/blob/main/dawadrishti/study.py">dawadrishti/study.py</Source> · Data: CDSCO NSQ portal and monthly alert PDFs (public).</p>
        </Card>
      </section>
    </div>
  )
}

function caseReading(c: any): string {
  if (c.national_alerts === 0) return 'Never named in CDSCO\'s national alerts. Its failures were found in state testing that did not reach the national list.'
  if (c.alerts_before_incident === 0) return `No national alert before the incident. The first one appeared in ${c.first_alert}, after it. Every alert since is on the record.`
  return `${c.alerts_before_incident} alerts were on record before the incident.`
}

function Kpi({ icon: Icon, value, label, sub, color }: { icon: any; value: string; label: string; sub: string; color?: string }) {
  return (
    <Card className="p-5">
      <Icon size={18} className="text-faint mb-2" />
      <div className={`font-display text-3xl font-bold num ${color ?? ''}`}>{value}</div>
      <div className="text-sm text-ink/85 mt-1">{label}</div>
      <div className="text-[11px] text-faint mt-1">{sub}</div>
    </Card>
  )
}
