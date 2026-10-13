import { Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'
import { Badge, Button, Card, ErrorNote, inputCls, SectionTitle, Spinner } from '../components/ui'

export default function Ask() {
  const [p, setP] = useState<{ questions: string[]; gemini: boolean } | null>(null)
  const [q, setQ] = useState('')
  const [res, setRes] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api.presets().then(setP) }, [])

  const run = async (question: string) => {
    setQ(question); setBusy(true); setErr(null); setRes(null)
    try { setRes(await api.ask(question)) } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <SectionTitle eyebrow="Questions · parameterised queries" title="Ask DawaDrishti"
        sub="A question is mapped to one of nine reviewed query templates, and its filters are checked against values that exist in the data. No model writes SQL, and no model writes text about any manufacturer: the answer is a table of published records." />
      <Card className="p-5">
        <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) run(q.trim()) }} className="flex gap-2">
          <input className={inputCls} value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Which antibiotic tablets from Gujarat failed since 2024?" />
          <Button type="submit" disabled={busy || !q.trim()}><Sparkles size={15} /> Ask</Button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {p?.questions.map((x) => <button key={x} onClick={() => run(x)} className="rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-muted hover:text-ink hover:border-ours/50">{x}</button>)}
        </div>
        {p && <div className="mt-3 text-[11px] text-faint">{p.gemini ? 'Gemini chooses the template and its filters.' : 'No LLM key set: keyword rules choose the template and its filters. Set GEMINI_API_KEY to let Gemini choose.'}</div>}
      </Card>
      {busy && <Spinner label="Querying the warehouse…" />}
      {err && <ErrorNote error={err} />}
      {res && (
        <Card className="p-5">
          <div className="flex flex-wrap items-center gap-2 mb-2"><div className="font-display font-semibold">{res.question}</div><Badge tone="ours">{res.source}</Badge>
            <Badge tone={res.data === 'real' ? 'bad' : 'warn'}>{res.data === 'real' ? 'real CDSCO data' : res.data}</Badge></div>
          <div className="text-xs text-muted mb-2">Template <span className="text-ink font-mono">{res.template}</span>: {res.description}</div>
          <div className="flex flex-wrap gap-1.5 mb-2">{Object.entries(res.params).map(([k, v]) => <Badge key={k}>{k} = {String(v)}</Badge>)}</div>
          <pre className="text-[11px] bg-surface-2 border border-line rounded-lg p-3 whitespace-pre-wrap text-muted font-mono">{res.sql}</pre>
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-sm num">
              <thead className="text-xs text-faint"><tr className="border-b border-line">{res.columns.map((c: string) => <th key={c} className="text-left font-normal py-2 pr-4">{c}</th>)}</tr></thead>
              <tbody>{res.rows.map((r: any[], i: number) => <tr key={i} className="border-b border-line/50">{r.map((v, j) => <td key={j} className="py-1.5 pr-4">{typeof v === 'number' ? v.toLocaleString('en-IN') : String(v ?? '')}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
