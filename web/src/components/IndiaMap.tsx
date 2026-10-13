import { CircleMarker, MapContainer, TileLayer, Tooltip, ZoomControl } from 'react-leaflet'

// Approximate centroids; the data's geography is by state (from manufacturer addresses / PIN codes).
const C: Record<string, [number, number]> = {
  'Himachal Pradesh': [31.9, 77.2], Uttarakhand: [30.1, 78.6], Gujarat: [22.7, 71.6], 'Madhya Pradesh': [23.5, 78.5],
  Maharashtra: [19.5, 75.7], Punjab: [30.9, 75.4], Haryana: [29.1, 76.1], 'Uttar Pradesh': [26.8, 80.9],
  'Tamil Nadu': [11.1, 78.6], Telangana: [17.9, 79.0], 'Andhra Pradesh': [15.9, 79.7], Karnataka: [15.3, 75.7],
  Kerala: [10.4, 76.3], 'West Bengal': [23.0, 87.8], Sikkim: [27.5, 88.5], Rajasthan: [26.6, 73.8], Delhi: [28.6, 77.2],
  'Jammu & Kashmir': [33.7, 75.1], Bihar: [25.6, 85.6], Jharkhand: [23.6, 85.3], Odisha: [20.5, 84.4], Assam: [26.2, 92.5],
  Goa: [15.4, 74.0], Chhattisgarh: [21.3, 81.9], Chandigarh: [30.73, 76.78], Puducherry: [11.94, 79.8],
  'Daman, Diu & DNH': [20.4, 72.9], Meghalaya: [25.5, 91.4], Tripura: [23.8, 91.3], 'Andaman & Nicobar': [11.7, 92.7],
  'Arunachal Pradesh': [28.0, 94.7], Manipur: [24.8, 93.9], Mizoram: [23.2, 92.8], Nagaland: [26.1, 94.5],
}

export function IndiaMap({ geo, height = 460, onPick }: { geo: any[]; height?: number; onPick?: (s: string) => void }) {
  const rows = geo.filter((g) => C[g.state])
  const max = Math.max(...rows.map((g) => g.findings), 1)
  return (
    <div style={{ height }} className="relative overflow-hidden rounded-[20px] border border-line shadow-sm">
      <MapContainer center={[23, 80.5]} zoom={4.4} zoomSnap={0.2} scrollWheelZoom={false} zoomControl={false} style={{ height: '100%', width: '100%' }}>
        <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" className="soft-tiles" 
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' />
        <ZoomControl position="bottomright" />
        {rows.map((g) => {
          const crit = g.critical_share as number
          const color = crit > 0.15 ? '#ef4444' : crit > 0.09 ? '#f97316' : '#f59e0b'
          return (
            <CircleMarker key={g.state} center={C[g.state]} radius={5 + 34 * Math.sqrt(g.findings / max)}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.28, weight: 1.5 }} eventHandlers={{ click: () => onPick?.(g.state) }}>
              <Tooltip direction="top" className="bank-tip">
                <b>{g.state}</b><br />{g.findings.toLocaleString('en-IN')} failed batches · {g.manufacturers} manufacturers<br />
                {(100 * crit).toFixed(1)}% critical · {(100 * g.share_of_india).toFixed(1)}% of India
              </Tooltip>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}
