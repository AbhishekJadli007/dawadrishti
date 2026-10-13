// Typed-enough client for the DawaDrishti API. Shapes mirror api/main.py; `any` where the payload is report-like.

async function req<T = any>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try {
      const j = await r.json()
      msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch { /* keep status */ }
    throw new Error(msg)
  }
  return r.json() as Promise<T>
}
const post = <T = any>(path: string, body: unknown) => req<T>(path, { method: 'POST', body: JSON.stringify(body) })

export type Check = {
  supplier_id: string; name: string; state: string; manufacturer_id: string | null
  national_alerts_12m: number; critical_12m: number; national_alerts_total: number; last_alert: string | null
  debarred_by: string | null; debarred_on: string | null; level: 'ok' | 'warn' | 'block'; reasons: string[]
  recent_failures: any[]; response_level: number; response: string; response_rule: string
}
export type QueueRow = {
  batch_id: string; po_id: string; qc_status: string; risk_score: number | null; received_at: string | null
  batch_no: string | null; supplier: string; supplier_id: string; generic_name: string; dosage_form: string; qty: number
}

export type View = 'public' | 'buyer'

export const api = {
  study: () => req('/api/study'),
  quality: () => req('/api/quality'),
  lookup: (q: string, view: View, molecule?: string) =>
    req(`/api/v1/lookup?q=${encodeURIComponent(q)}&view=${view}${molecule ? `&molecule=${encodeURIComponent(molecule)}` : ''}`),
  overview: () => req('/api/overview'),
  mining: () => req('/api/mining'),
  process: (buyer?: string) => req(`/api/process${buyer ? `?buyer=${buyer}` : ''}`),
  violations: (rule?: string, buyer?: string) => req(`/api/violations?limit=60${rule ? `&rule=${rule}` : ''}${buyer ? `&buyer=${buyer}` : ''}`),
  risk: () => req('/api/risk'),
  search: (q: string) => req<any[]>(`/api/search?q=${encodeURIComponent(q)}`),
  manufacturer: (id: string) => req(`/api/manufacturer/${encodeURIComponent(id)}`),
  masters: () => req('/api/erp/masters'),
  suppliers: (buyer: string, item: string) => req<Check[]>(`/api/erp/suppliers?buyer_id=${buyer}&item_id=${item}`),
  createPO: (b: { buyer_id: string; item_id: string; supplier_id: string; qty: number; override?: boolean }) => post('/api/erp/po', b),
  receive: (case_id: string) => post('/api/erp/receive', { case_id }),
  result: (case_id: string, passed: boolean, failure = '') => post('/api/erp/result', { case_id, passed, failure }),
  issue: (case_id: string) => post('/api/erp/issue', { case_id }),
  contract: (buyer: string, item: string) => req(`/api/erp/contract?buyer_id=${buyer}&item_id=${item}`),
  queue: (buyer: string) => req<QueueRow[]>(`/api/erp/queue?buyer_id=${buyer}`),
  caseTimeline: (id: string) => req(`/api/erp/case/${encodeURIComponent(id)}`),
  presets: () => req<{ questions: string[]; gemini: boolean }>('/api/ask/presets'),
  ask: (question: string) => post('/api/ask', { question }),
}

export const fmtInt = (x: number) => Math.round(x).toLocaleString('en-IN')
export const fmtPct = (x: number, d = 0) => `${(100 * x).toFixed(d)}%`
export const SEV_COLOR: Record<string, string> = { critical: '#ef4444', major: '#f59e0b', minor: '#64748b', unclassified: '#3f4659' }
export const tipStyle = { background: '#171b24', border: '1px solid #262c3b', borderRadius: 10, fontSize: 12 }
export const axis = { fill: '#5b6378', fontSize: 10 }
