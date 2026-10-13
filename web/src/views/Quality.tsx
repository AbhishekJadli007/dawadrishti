import { Download } from 'lucide-react'
import { useEffect, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, axis, fmtInt, fmtPct, tipStyle } from '../api'
import { Badge, Button, Card, SectionTitle, Spinner } from '../components/ui'

type Decision = 'same' | 'different'

export default function Quality() {
  const [d, setD] = useState<any>(null)
  useEffect(() => { api.quality().then(setD) }, [])
  if (!d) return <Spinner label="Loading data-quality checks…" />
  const x = d.extraction
  const e = d.entities
  const sweep = e.sweep.filter((s: any) => s.scorer === 'v2').map((s: any) => ({
    t: s.threshold, precision: +(100 * s.test.firm.precision).toFixed(1), recall: +(100 * s.test.firm.recall).toFixed(1),
  }))

  return (
    <div className="space-y-10">
      <SectionTitle eyebrow="Data quality" title="How far can this record be trusted?"
        sub="Two things decide whether a national memory is right: reading the alerts correctly, and knowing which names are the same factory. Both are measured here." />

      <section>
        <div className="font-display text-lg font-semibold mb-3">1 · Reading the alerts: PDF parser vs CDSCO's structured portal</div>
        <div className="grid lg:grid-cols-[1fr_1.4fr] gap-5">
          <Card className="p-5 min-w-0">
            <p className="text-sm text-muted">Alerts before 2019 exist only as PDFs. For {x.audited_months.length} later months CDSCO published both, so we parsed {x.pdf_documents} of those PDFs and compared them with the portal, row by row, on batch number.</p>
            <div className="grid grid-cols-2 gap-3 mt-4">
              <Stat v={fmtPct(x.row_precision, 1)} l="of parsed rows match a portal row" />
              <Stat v={fmtPct(x.row_recall, 1)} l="of portal rows were found in the PDFs" />
              <Stat v={fmtInt(x.pdf_rows)} l="rows parsed" />
              <Stat v={fmtInt(x.matched_rows)} l="rows compared field by field" />
            </div>
            <p className="text-[11px] text-faint mt-3">{x.note}</p>
          </Card>
          <Card className="p-5 min-w-0">
            <div className="text-sm font-medium mb-2">Field agreement on matched rows</div>
            {Object.entries(x.fields).map(([f, v]: [string, any]) => (
              <div key={f} className="py-1.5">
                <div className="flex justify-between text-sm"><span>{f}</span><span className="num">{v.agreement != null ? fmtPct(v.agreement, 1) : '–'} <span className="text-faint text-xs">n={v.compared}{v.missing_in_pdf ? `, missing ${v.missing_in_pdf}` : ''}</span></span></div>
                <div className="h-1.5 rounded bg-surface-3 mt-1 overflow-hidden"><div className="h-full bg-ours" style={{ width: `${100 * (v.agreement ?? 0)}%` }} /></div>
                {v.examples_of_disagreement?.[0] && <div className="text-[11px] text-faint mt-0.5 truncate">e.g. PDF “{v.examples_of_disagreement[0].pdf}” vs portal “{v.examples_of_disagreement[0].portal}”</div>}
              </div>))}
            <p className="text-[11px] text-faint mt-2">The audit found two parser bugs, both fixed: header words split by the PDF layout (“Manufactu ring Date”) and letter-spaced text (“P h a r m a”).</p>
          </Card>
        </div>
      </section>

      <section>
        <div className="font-display text-lg font-semibold mb-3">2 · Knowing which names are the same factory</div>
        <div className="grid sm:grid-cols-4 gap-4">
          <Stat card v={fmtInt(e.population.distinct_raw_strings)} l="distinct manufacturer strings in the alerts" />
          <Stat card v={fmtInt(e.population.units)} l="manufacturing units after resolution (firm + state)" />
          <Stat card v={fmtInt(e.population.firms)} l="firms (units joined across states)" />
          <Stat card v={fmtInt(e.population.units_with_several_spellings)} l={`units spelled more than one way (up to ${e.population.max_spellings_in_one_unit})`} />
        </div>
        <div className="grid lg:grid-cols-[1.4fr_1fr] gap-5 mt-5">
          <Card className="p-5 overflow-x-auto min-w-0">
            <div className="text-sm font-medium">Matchers on labelled hard pairs</div>
            <p className="text-xs text-muted mt-1">{e.labelled.dev} development pairs (used to find errors and pick the threshold) and {e.labelled.test} test pairs drawn afterwards and labelled with scores hidden. {e.labelled.labelled_by}.</p>
            <table className="w-full text-xs num mt-3 min-w-[520px]">
              <thead className="text-faint"><tr><th className="text-left font-normal">Matcher</th><th className="text-right font-normal">Precision</th><th className="text-right font-normal">Recall</th><th className="text-right font-normal">F1</th><th className="text-right font-normal">Unit recall</th></tr></thead>
              <tbody>{e.matchers.map((m: any) => (
                <tr key={m.matcher} className={`border-t border-line/60 ${m.matcher === e.chosen ? 'text-ours' : ''}`}>
                  <td className="py-1.5 pr-2">{m.matcher}{m.matcher === e.chosen && <Badge tone="ours" className="ml-1">in use</Badge>}</td>
                  <td className="text-right">{m.test.firm.precision.toFixed(2)}</td><td className="text-right">{m.test.firm.recall.toFixed(2)}</td>
                  <td className="text-right">{m.test.firm.f1.toFixed(2)}</td><td className="text-right">{m.test.unit.recall.toFixed(2)}</td></tr>))}</tbody>
            </table>
            <p className="text-[11px] text-faint mt-3">Held-out test pairs, firm level. Automatic merges stop at 92 because a false merge would put one firm's failures on another's record; a missed merge only splits a history.
              Pairs scoring {e.with_human_review.band[0]}–{e.with_human_review.band[1]} go to a person: confirming them raises recall to {fmtPct(e.with_human_review.recall_if_reviewers_confirm.test.firm.recall)}.</p>
          </Card>
          <Card className="p-5">
            <div className="text-sm font-medium">Threshold sweep (test pairs)</div>
            <div className="h-56 mt-2">
              <ResponsiveContainer>
                <LineChart data={sweep} margin={{ top: 5, right: 10, left: -18, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="#262c3b" />
                  <XAxis dataKey="t" tick={axis} axisLine={false} tickLine={false} />
                  <YAxis tick={axis} axisLine={false} tickLine={false} unit="%" domain={[0, 100]} />
                  <Tooltip contentStyle={tipStyle} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <ReferenceLine x={92} stroke="#22d3ee" strokeDasharray="3 3" />
                  <Line dataKey="precision" stroke="#34d399" strokeWidth={2} dot={false} />
                  <Line dataKey="recall" stroke="#f59e0b" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="text-xs text-muted mt-2 space-y-1">{e.rules.slice(0, 4).map((r: any) => <div key={r.rule}>· {r.rule}</div>)}</div>
          </Card>
        </div>
        <ReviewQueue rows={e.review_queue} total={e.review_queue_total} />
      </section>
    </div>
  )
}

function ReviewQueue({ rows, total }: { rows: any[]; total: number }) {
  const [shown, setShown] = useState(25)
  const key = (r: any) => `${r.a[0]}|${r.b[0]}`
  const [dec, setDec] = useState<Record<string, Decision>>(() => {
    try { return JSON.parse(localStorage.getItem('dd-er-decisions') || '{}') } catch { return {} }
  })
  const decide = (r: any, v: Decision) => {
    const next = { ...dec, [key(r)]: v }
    setDec(next)
    try { localStorage.setItem('dd-er-decisions', JSON.stringify(next)) } catch { /* private mode */ }
  }
  const exportJson = () => {
    const blob = new Blob([JSON.stringify(Object.entries(dec).map(([k, v]) => ({ pair: k.split('|'), decision: v })), null, 1)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'entity_decisions.json'
    a.click()
  }
  return (
    <Card className="p-5 mt-5 overflow-x-auto">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-medium">Review queue</div>
          <p className="text-xs text-muted">{total} pairs near the threshold, the ones that move the most alerts first. Decisions are kept in this browser; export them to apply in the next build.</p>
        </div>
        <Button variant="ghost" onClick={exportJson} disabled={!Object.keys(dec).length}><Download size={14} /> Export {Object.keys(dec).length} decisions</Button>
      </div>
      <table className="w-full text-xs mt-3 min-w-[760px]">
        <thead className="text-faint"><tr className="border-b border-line">{['Score', 'Name A (spellings · alerts · states)', 'Name B', 'Now', 'Your call'].map((h) => <th key={h} className="text-left font-normal py-2 px-2">{h}</th>)}</tr></thead>
        <tbody>{rows.slice(0, shown).map((r) => {
          const d = dec[key(r)]
          return (
            <tr key={key(r)} className="border-b border-line/50 align-top">
              <td className="py-2 px-2 num">{r.score}</td>
              <td className="px-2"><div>{r.a.join(' / ')}</div><div className="text-faint">{r.a_alerts} alerts · {r.a_states.join(', ')}</div></td>
              <td className="px-2"><div>{r.b.join(' / ')}</div><div className="text-faint">{r.b_alerts} alerts · {r.b_states.join(', ')}</div></td>
              <td className="px-2"><Badge tone={r.status.startsWith('merged') ? 'ours' : 'warn'}>{r.status}</Badge></td>
              <td className="px-2 whitespace-nowrap">
                {(['same', 'different'] as Decision[]).map((v) => (
                  <button key={v} onClick={() => decide(r, v)} className={`mr-1 rounded-md border px-2 py-0.5 ${d === v ? 'border-ours text-ours' : 'border-line text-muted hover:text-ink'}`}>{v}</button>))}
              </td>
            </tr>)
        })}</tbody>
      </table>
      {shown < rows.length && <button onClick={() => setShown(rows.length)} className="text-xs text-ours hover:underline mt-3">show {rows.length - shown} more (of {total} in the full queue)</button>}
    </Card>
  )
}

function Stat({ v, l, card }: { v: string; l: string; card?: boolean }) {
  const body = <><div className="font-display text-2xl font-bold num">{v}</div><div className="text-xs text-muted mt-0.5">{l}</div></>
  return card ? <Card className="p-4">{body}</Card> : <div>{body}</div>
}
