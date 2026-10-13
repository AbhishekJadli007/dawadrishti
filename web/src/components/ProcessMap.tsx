// Directly-follows graph drawn on a fixed layout that mirrors the quality-clearance process.
// Edge width = how many cases took that step; red edges are paths that break a rule.

const POS: Record<string, [number, number]> = {
  'PO created': [90, 60], 'PO approved': [250, 60], 'Goods received': [410, 60], 'Quarantined': [570, 60],
  'Sample drawn': [730, 60], 'Sample coded': [890, 60],
  'Sent to lab': [890, 180], 'Report received': [730, 180], 'Cleared': [570, 180], 'Issued': [410, 180],
  'Payment released': [250, 180],
  'Held': [730, 300], 'Supplier notified': [570, 300], 'Supplier debarred': [410, 300],
  'Recall started': [890, 300], 'Recall closed': [890, 400],
}
const EARLY = new Set(['Goods received', 'Quarantined', 'Sample drawn', 'Sample coded', 'Sent to lab', 'Report received'])

export function isDeviation(source: string, target: string) {
  if (target === 'Issued' && EARLY.has(source)) return true
  if (target === 'Payment released' && !['Cleared', 'Issued', 'Payment released'].includes(source)) return true
  if (source === 'Sample drawn' && target === 'Sent to lab') return true
  if (source === 'Issued' && ['Report received', 'Cleared', 'Held', 'Sent to lab'].includes(target)) return true
  return false
}

export function ProcessMap({ discovery, minShare = 0.004 }: { discovery: any; minShare?: number }) {
  const cases = discovery.cases || 1
  const edges = (discovery.edges as any[]).filter((e) => POS[e.source] && POS[e.target] && e.source !== e.target &&
    (e.count / cases >= minShare || isDeviation(e.source, e.target)))
  const maxC = Math.max(...edges.map((e) => e.count), 1)
  const W = 128, H = 46
  return (
    <svg viewBox="0 0 980 450" className="w-full h-auto" role="img" aria-label="Discovered process map">
      <defs>
        <marker id="pm-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
          <path d="M0 0L10 5L0 10z" fill="#94a3b8" />
        </marker>
        <marker id="pm-arrow-bad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
          <path d="M0 0L10 5L0 10z" fill="#ef4444" />
        </marker>
      </defs>
      {edges.map((e, i) => {
        const [x1, y1] = POS[e.source]
        const [x2, y2] = POS[e.target]
        const bad = isDeviation(e.source, e.target)
        const dx = x2 - x1, dy = y2 - y1
        const len = Math.hypot(dx, dy) || 1
        // start/end on box borders, bend sideways so opposite edges do not overlap
        const sx = x1 + (dx / len) * (W / 2) * (Math.abs(dx) > Math.abs(dy) ? 1 : 0.2)
        const sy = y1 + (dy / len) * (H / 2) * (Math.abs(dy) >= Math.abs(dx) ? 1 : 0.4)
        const ex = x2 - (dx / len) * (W / 2) * (Math.abs(dx) > Math.abs(dy) ? 1 : 0.2)
        const ey = y2 - (dy / len) * (H / 2) * (Math.abs(dy) >= Math.abs(dx) ? 1 : 0.4)
        const bend = len > 200 ? 0.18 : 0.08
        const cx = (sx + ex) / 2 - dy * bend, cy = (sy + ey) / 2 + dx * bend
        const w = 1 + 7 * Math.sqrt(e.count / maxC)
        return (
          <path key={i} d={`M${sx} ${sy} Q${cx} ${cy} ${ex} ${ey}`} fill="none" stroke={bad ? '#ef4444' : '#0d9488'}
            strokeOpacity={bad ? 0.85 : 0.35} strokeWidth={w} markerEnd={`url(#${bad ? 'pm-arrow-bad' : 'pm-arrow'})`}>
            <title>{`${e.source} → ${e.target}: ${e.count.toLocaleString('en-IN')} cases, mean wait ${e.mean_wait_days} days${bad ? ' (breaks a rule)' : ''}`}</title>
          </path>
        )
      })}
      {Object.entries(POS).map(([a, [x, y]]) => {
        const n = discovery.activities?.[a] || 0
        const fail = ['Held', 'Supplier notified', 'Supplier debarred', 'Recall started', 'Recall closed'].includes(a)
        return (
          <g key={a}>
            <rect x={x - W / 2} y={y - H / 2} width={W} height={H} rx={10} fill="#ffffff" stroke={fail ? '#f59e0b' : '#cbd5e1'} strokeWidth={1.2} />
            <text x={x} y={y - 3} textAnchor="middle" fontSize={11.5} fontWeight={600} fill="#0f172a">{a}</text>
            <text x={x} y={y + 13} textAnchor="middle" fontSize={11} fill="#64748b">{n.toLocaleString('en-IN')}</text>
          </g>
        )
      })}
    </svg>
  )
}
