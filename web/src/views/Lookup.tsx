import clsx from 'clsx'
import { CircleSlash, ExternalLink, FileWarning, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, fmtPct, SEV_COLOR } from '../api'
import { Badge, Button, Card, ErrorNote, inputCls, SectionTitle, Spinner } from '../components/ui'
import { useView } from '../mode'

const EXAMPLES = ['Nestor Pharmaceuticals', 'Sresan Pharmaceutical Manufacturer', 'Cipla', 'Maiden Pharmaceuticals', 'Kaysons Pharma']
const LEVEL_TONE = ['good', 'warn', 'bad', 'bad'] as const

export default function Lookup({ initial }: { initial?: string }) {
  const [q, setQ] = useState(initial ?? '')
  const [query, setQuery] = useState(initial ?? '')
  const [sugg, setSugg] = useState<any[]>([])
  useEffect(() => {
    if (q.trim().length < 2 || q === query) { setSugg([]); return }
    const t = setTimeout(() => api.search(q).then(setSugg).catch(() => setSugg([])), 200)
    return () => clearTimeout(t)
  }, [q, query])
  const run = (v: string) => { setQ(v); setQuery(v); setSugg([]) }

  return (
    <div className="space-y-6">
      <SectionTitle eyebrow="The memory's lookup" title="What does the national record say about this manufacturer?"
        sub="Type a name as it appears on an invoice or tender. The same lookup is an API that any buyer's ERP can call before a purchase order or a goods receipt." />
      <Card className="p-4">
        <form onSubmit={(e) => { e.preventDefault(); if (q.trim().length > 1) run(q.trim()) }} className="flex gap-2 relative">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-2.5 text-faint" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Nestor Pharmaceuticals Ltd" className={clsx(inputCls, 'pl-9')} />
            {sugg.length > 0 && (
              <div className="absolute left-0 right-0 mt-1 rounded-xl border border-line bg-surface shadow-2xl overflow-hidden z-10">
                {sugg.map((r) => (
                  <button type="button" key={r.supplier_key} onClick={() => run(r.supplier_key)}
                    className="w-full text-left px-3 py-2 hover:bg-surface-3 flex justify-between gap-3 text-sm">
                    <span className="truncate">{r.canonical_name}<span className="text-faint text-xs"> · {r.state}</span></span>
                    <span className="text-xs text-muted num shrink-0">{r.national_findings} alerts</span>
                  </button>))}
              </div>)}
          </div>
          <Button type="submit">Look up</Button>
        </form>
        <div className="flex flex-wrap gap-2 mt-3 text-xs">
          <span className="text-faint">Try:</span>
          {EXAMPLES.map((e) => <button key={e} onClick={() => run(e)} className="text-muted hover:text-ink underline decoration-dotted underline-offset-2">{e}</button>)}
        </div>
      </Card>
      {query && <LookupResult query={query} onPick={run} />}
      <ApiNote />
    </div>
  )
}

export function LookupResult({ query, onPick }: { query: string; onPick: (q: string) => void }) {
  const { view } = useView()
  const [molecule, setMolecule] = useState<string>('')
  const [d, setD] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { setD(null); setErr(null); api.lookup(query, view, molecule || undefined).then(setD).catch((e) => setErr(e.message)) }, [query, view, molecule])
  if (err) return <ErrorNote error={err} />
  if (!d) return <Spinner label="Checking the national record…" />
  const r = d.record

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Badge tone={view === 'buyer' ? 'warn' : 'ours'}>{view === 'buyer' ? 'Buyer view' : 'Public view: record only'}</Badge>
          <Badge>data as of {d.data_as_of}</Badge>
          <Badge tone={d.identity.match === 'exact' || d.identity.match === 'id' ? 'good' : d.identity.manufacturer_id ? 'warn' : 'neutral'}>
            name match: {d.identity.match}{d.identity.score ? ` (${d.identity.score})` : ''}
          </Badge>
        </div>
        {r ? (
          <>
            <h2 className="font-display text-2xl font-semibold mt-3">{r.unit.name}</h2>
            <div className="text-sm text-muted">{r.unit.state} · unit {r.unit.manufacturer_id} · firm {r.firm.name}</div>
          </>
        ) : <h2 className="font-display text-xl font-semibold mt-3">“{d.query}”</h2>}
        <p className="text-sm mt-3">{d.statement}</p>
        {!r && d.identity.candidates?.length > 0 && (
          <div className="mt-3 space-y-1">
            <div className="text-xs text-faint">Possible matches. A record is shown only after you pick one:</div>
            {d.identity.candidates.map((c: any) => (
              <button key={c.manufacturer_id} onClick={() => onPick(c.manufacturer_id)} className="w-full flex justify-between rounded-lg px-3 py-2 bg-surface-2 hover:bg-surface-3 text-sm">
                <span>{c.name} <span className="text-faint text-xs">· {c.state}</span></span><span className="text-xs text-muted num">similarity {c.score} · {c.alerts} alerts</span>
              </button>))}
          </div>)}
      </Card>

      {r && view === 'buyer' && d.buyer && <BuyerPanel b={d.buyer} molecule={molecule} setMolecule={setMolecule} />}

      {r && (
        <div className="grid lg:grid-cols-[1.5fr_1fr] gap-5">
          <Card className="p-0 overflow-x-auto">
            <div className="px-4 pt-4 pb-2 flex flex-wrap gap-2 text-xs">
              <Badge tone={r.alerts >= 5 ? 'bad' : 'warn'}>{r.alerts} alerts for this unit</Badge>
              {r.alerts_all_units > r.alerts && <Badge>{r.alerts_all_units} across the firm's units</Badge>}
              {Object.entries(r.by_severity).map(([k, v]: any) => <Badge key={k}><span style={{ color: SEV_COLOR[k] }}>{k}</span> {v}</Badge>)}
              <Badge>{r.labs} labs</Badge>
            </div>
            <table className="w-full text-xs min-w-[640px]">
              <thead className="text-faint"><tr className="border-y border-line">{['Alert month', 'Product', 'Failed on', 'Severity', 'Reported by', 'Batch'].map((h) => <th key={h} className="text-left font-normal py-2 px-3">{h}</th>)}</tr></thead>
              <tbody>{r.entries.map((f: any, i: number) => (
                <tr key={i} className="border-b border-line/50"><td className="py-1.5 px-3 num whitespace-nowrap">{f.month}</td><td className="px-3">{f.generic_name} <span className="text-faint">· {f.dosage_form}</span></td>
                  <td className="px-3">{f.primary_failure}{f.is_spurious && <Badge tone="bad" className="ml-1">spurious</Badge>}</td>
                  <td className="px-3"><span style={{ color: SEV_COLOR[f.severity] }}>{f.severity}</span></td><td className="px-3 text-muted">{f.reporting_lab}</td><td className="px-3 font-mono text-faint">{f.batch_no}</td></tr>))}</tbody>
            </table>
            <div className="px-4 py-2 text-[11px] text-faint">Each row is one published CDSCO alert, as published. Showing up to 40.</div>
          </Card>
          <div className="space-y-4">
            {r.firm.other_units_on_record.length > 0 && (
              <Card className="p-4">
                <div className="text-sm font-medium">Other units of this firm on record</div>
                {r.firm.other_units_on_record.map((u: any) => (
                  <button key={u.manufacturer_id} onClick={() => onPick(u.manufacturer_id)} className="w-full flex justify-between text-sm border-t border-line/50 py-1.5 hover:text-ours">
                    <span>{u.state}</span><span className="num text-muted">{u.alerts} alerts</span></button>))}
              </Card>)}
            <Card className="p-4">
              <div className="text-sm font-medium">Regulatory action</div>
              <div className="text-sm text-muted mt-1">{r.regulatory_action ?? r.regulatory_action_note}</div>
            </Card>
            <Card className="p-4">
              <div className="text-sm font-medium flex items-center gap-1.5"><CircleSlash size={14} /> What this data does not contain</div>
              <ul className="mt-2 space-y-1.5 text-xs text-muted list-disc pl-4">{d.data_does_not_contain.map((x: string) => <li key={x}>{x}</li>)}</ul>
            </Card>
            <Card className="p-4">
              <div className="text-sm font-medium flex items-center gap-1.5"><FileWarning size={14} /> Something wrong?</div>
              <p className="text-xs text-muted mt-1">{d.correction.how}</p>
              <a href={d.correction.url} target="_blank" rel="noreferrer" className="text-xs text-ours hover:underline inline-flex items-center gap-1 mt-2">Request a correction <ExternalLink size={11} /></a>
            </Card>
          </div>
        </div>)}
    </div>
  )
}

function BuyerPanel({ b, molecule, setMolecule }: { b: any; molecule: string; setMolecule: (m: string) => void }) {
  const g = b.graded_response
  const a = b.future_regulatory_attention
  const [items, setItems] = useState<string[]>([])
  useEffect(() => { api.masters().then((m) => setItems([...new Set<string>(m.items.map((i: any) => i.generic_name))])) }, [])
  return (
    <div className="grid lg:grid-cols-3 gap-4">
      <Card className={clsx('p-5', g.level >= 2 && 'border-red-500/40')}>
        <div className="text-xs text-faint">What a buyer should do now</div>
        <div className="flex items-center gap-2 mt-1"><Badge tone={LEVEL_TONE[g.level]}>level {g.level}</Badge><span className="font-display text-xl font-semibold">{g.label}</span></div>
        <p className="text-xs text-muted mt-2">{g.rule}</p>
        <div className="grid grid-cols-2 gap-2 mt-3 text-xs num">
          <div>alerts, 12 mo: <b>{g.facts.alerts_12m}</b></div><div>critical, 12 mo: <b>{g.facts.critical_12m}</b></div>
          <div>alerts, 36 mo: <b>{g.facts.alerts_36m}</b></div><div>critical, 36 mo: <b>{g.facts.critical_36m}</b></div>
        </div>
        {b.debarred && <div className="text-xs text-red-300 mt-2">Debarred by buyer {b.debarred.debarred_by} on {b.debarred.debarred_on} (simulated network).</div>}
      </Card>
      <Card className="p-5">
        <div className="text-xs text-faint">Future regulatory attention (model)</div>
        {a ? (<>
          <div className="font-display text-3xl font-bold num mt-1">{fmtPct(a.probability_next_6_months)}</div>
          <p className="text-xs text-muted mt-2">{a.means}</p>
          {a.evaluation && <div className="text-[11px] text-faint mt-2">Held-out AUC: {Object.entries(a.evaluation).map(([k, v]) => `${k} ${v}`).join(' · ')}</div>}
        </>) : <p className="text-sm text-muted mt-2">No score: this unit has no alerts to score from.</p>}
      </Card>
      <Card className="p-5">
        <div className="text-xs text-faint">Alternatives in the buyer network's supplier masters <Badge tone="warn" className="ml-1">simulated</Badge></div>
        <select value={molecule || b.alternatives_for || ''} onChange={(e) => setMolecule(e.target.value)} className={clsx(inputCls, 'mt-2 py-1.5 text-xs')}>
          <option value="">{b.alternatives_for ? b.alternatives_for : 'choose a molecule…'}</option>
          {items.map((i) => <option key={i} value={i}>{i}</option>)}
        </select>
        <div className="mt-2 space-y-1">
          {b.alternatives.length === 0 && <div className="text-xs text-muted">No other supplier of this molecule in the masters. The alerts list only failing firms, so they cannot supply alternatives.</div>}
          {b.alternatives.map((x: any) => (
            <div key={x.supplier_id} className="flex justify-between text-xs border-t border-line/50 py-1.5"><span className="truncate">{x.name} <span className="text-faint">· {x.state}</span></span>
              <Badge tone={LEVEL_TONE[x.response_level]}>{x.response}</Badge></div>))}
        </div>
      </Card>
    </div>
  )
}

function ApiNote() {
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  return (
    <Card className="p-5">
      <div className="font-display font-semibold">For ERP integrators</div>
      <p className="text-xs text-muted mt-1">One GET request, called at purchase-order and goods-receipt time. The public view never returns a predicted score.</p>
      <pre className="mt-3 text-xs bg-surface-2 border border-line rounded-lg p-3 overflow-x-auto font-mono text-muted">{`curl "${origin}/api/v1/lookup?q=Nestor%20Pharmaceuticals%20Ltd&view=buyer&molecule=Paracetamol"

{ "identity": { "manufacturer_id": "M00008", "match": "exact" },
  "record":   { "alerts": 38, "last_alert": "2026-08", "entries": [...], "regulatory_action": null },
  "buyer":    { "graded_response": { "level": 2, "label": "Test every batch" },
                "future_regulatory_attention": { "probability_next_6_months": 0.98 },
                "alternatives": [...] },
  "data_as_of": "2026-08", "data_does_not_contain": [...], "correction": {...} }`}</pre>
      <a href="/docs" target="_blank" rel="noreferrer" className="text-xs text-ours hover:underline mt-2 inline-block">Full API reference (OpenAPI) →</a>
    </Card>
  )
}
