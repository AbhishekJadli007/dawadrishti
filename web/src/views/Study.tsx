import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, axis, fmtInt, fmtPct, tipStyle } from '../api'
import { AnimatedNumber, Badge, Card, Reveal, Ring, Source, Spinner } from '../components/ui'

const DEFAULT_RULE = 'fuzzy ≥92, same state (default)'

/** The headline study in detail: method, uncertainty, robustness and limits. */
export default function Study() {
  const [s, setS] = useState<any>(null)
  useEffect(() => { api.study().then(setS) }, [])
  if (!s) return <Spinner label="Loading the study…" />
  const h = s.headline
  const [lo, hi] = h.repeat_share_ci95
  const buckets = Object.entries(h.firms_by_failures).map(([k, v]) => ({ k: `${k} failure${k === '1' ? '' : 's'}`, units: v as number }))
  const ablation = Object.entries(s.ablation).map(([rule, m]: [string, any]) => ({ rule, units: m.firms, share: m.repeat_share, gap: m.median_months_first_to_next, isDefault: rule === DEFAULT_RULE }))

  return (
    <div className="space-y-6">
      <Reveal>
        <Card className="p-6 sm:p-8 grid md:grid-cols-[auto_1fr] gap-8 items-center">
          <div className="mx-auto"><Ring value={h.repeat_share} size={210} stroke={16} label="already on record" /></div>
          <div>
            <Badge tone="bad">Real data · CDSCO alerts {s.data.from} to {s.data.to}</Badge>
            <h3 className="mt-3 font-display text-2xl font-bold">The question we asked</h3>
            <p className="mt-2 text-muted leading-relaxed">For every failed batch: had the same factory already appeared in an earlier month's alert? We matched {fmtInt(s.data.records_used)} failed
              batches to {fmtInt(h.firms)} factories and counted.</p>
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
              <div><div className="font-display text-2xl font-bold num">{fmtPct(lo, 1)}–{fmtPct(hi, 1)}</div><div className="text-xs text-muted">95% confidence interval (bootstrap over factories)</div></div>
              <div><div className="font-display text-2xl font-bold num"><AnimatedNumber value={100 * h.repeat_share_critical} format={(v) => `${v.toFixed(1)}%`} /></div><div className="text-xs text-muted">among critical failures (contamination, sterility, fakes)</div></div>
              <div><div className="font-display text-2xl font-bold num"><AnimatedNumber value={h.firms_with_repeat} /></div><div className="text-xs text-muted">factories failed more than once</div></div>
            </div>
          </div>
        </Card>
      </Reveal>
      <div className="grid lg:grid-cols-2 gap-5">
        <Reveal>
          <Card className="p-6 h-full">
            <div className="font-display font-bold">Factories by number of failed batches</div>
            <p className="text-sm text-muted mt-1">Most fail once. A small group fails again and again and produces most of the failures.</p>
            <div className="h-60 mt-4">
              <ResponsiveContainer>
                <BarChart data={buckets} margin={{ top: 20, right: 8, left: -14, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="#eef2f7" />
                  <XAxis dataKey="k" tick={axis} axisLine={false} tickLine={false} />
                  <YAxis tick={axis} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tipStyle} cursor={{ fill: '#f1f5f9' }} />
                  <Bar dataKey="units" name="factories" radius={[8, 8, 0, 0]} animationDuration={1200}>
                    {buckets.map((b, i) => <Cell key={b.k} fill={['#cbd5e1', '#fbbf24', '#fb7185', '#e11d48'][i]} />)}
                    <LabelList dataKey="units" position="top" style={{ fill: '#0f172a', fontSize: 12, fontWeight: 600 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Reveal>
        <Reveal delay={0.1}>
          <Card className="p-6 h-full">
            <div className="font-display font-bold">Does the answer depend on how names are matched?</div>
            <p className="text-sm text-muted mt-1">Recomputed under five matching rules. Above exact strings, it stays between 63% and 68%.</p>
            <div className="mt-4 space-y-3">
              {ablation.map((r) => (
                <div key={r.rule}>
                  <div className="flex justify-between text-sm"><span className={r.isDefault ? 'font-semibold text-ours' : 'text-muted'}>{r.rule}</span><span className="num font-semibold">{fmtPct(r.share, 1)}</span></div>
                  <div className="mt-1 h-2 rounded-full bg-surface-3 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${100 * r.share}%`, background: r.isDefault ? '#0d9488' : '#cbd5e1' }} /></div>
                  <div className="text-[11px] text-faint mt-0.5">{fmtInt(r.units)} factories{r.gap ? ` · ${r.gap.toFixed(1)} months to the next failure` : ''}</div>
                </div>))}
            </div>
          </Card>
        </Reveal>
      </div>
      <Reveal>
        <Card className="p-6">
          <div className="font-display font-bold">What this study can and cannot say</div>
          <div className="mt-3 grid md:grid-cols-2 gap-x-8 gap-y-3 text-sm text-muted">
            <p><b className="text-ink">Alerts list failures, not tests.</b> A failure rate per factory can't be computed; we measure repetition on the record.</p>
            <p><b className="text-ink">Sampling is uneven.</b> Factories in heavily tested states appear more often.</p>
            <p><b className="text-ink">The record starts in {s.data.from}.</b> Earlier failures are invisible, so some "first" failures are really repeats. The share is a lower bound.</p>
            <p><b className="text-ink">Left out:</b> {s.data.excluded}. {fmtInt(s.data.outside_india_records)} records name a maker outside India; they are kept.</p>
          </div>
          <div className="mt-4"><Source href="https://github.com/AbhishekJadli007/dawadrishti/blob/main/dawadrishti/study.py">Method and code: dawadrishti/study.py</Source></div>
        </Card>
      </Reveal>
    </div>
  )
}
