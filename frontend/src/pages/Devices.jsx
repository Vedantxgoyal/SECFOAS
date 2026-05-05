import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const TOOLTIP = { contentStyle: { background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 } }

const DEVICE_META = {
  'EV Charger':      { icon: '🔋', color: 'var(--accent-blue)',   window: '22:00–06:00', must: true,  wattage: 3000, typical_daily_kwh: 9.0  },
  'Water Heater':    { icon: '🚿', color: 'var(--accent-orange)', window: '06:00–10:00', must: true,  wattage: 2000, typical_daily_kwh: 2.0  },
  'Washing Machine': { icon: '👕', color: 'var(--accent-purple)', window: '08:00–18:00', must: false, wattage: 1600, typical_daily_kwh: 1.2  },
  'Refrigerator':    { icon: '❄️', color: '#60d8f8',              window: '00:00–24:00', must: true,  wattage: 300,  typical_daily_kwh: 3.6  },
  'Ceiling Fan':     { icon: '💨', color: 'var(--accent-green)',  window: '06:00–22:00', must: false, wattage: 75,   typical_daily_kwh: 0.6  },
  'Air Conditioner': { icon: '🌡️', color: 'var(--accent-red)',    window: '14:00–20:00', must: false, wattage: 1500, typical_daily_kwh: 4.5  },
}

const ALL_DEVICES = [
  { name: 'EV Charger',       power: 1.5,  slots: 4,  duration: 120  },
  { name: 'Water Heater',     power: 1.0,  slots: 2,  duration: 60   },
  { name: 'Washing Machine',  power: 0.8,  slots: 3,  duration: 90   },
  { name: 'Refrigerator',     power: 0.15, slots: 48, duration: 1440 },
  { name: 'Ceiling Fan',      power: 0.075,slots: 16, duration: 480  },
  { name: 'Air Conditioner',  power: 1.2,  slots: 6,  duration: 180  },
]

function getSuggestions(devices, allDevices) {
  const scheduled = new Set(devices.map(d => d.name))
  const suggestions = []

  if (!scheduled.has('Washing Machine')) {
    suggestions.push({
      icon: '👕', title: 'Run Washing Machine at 10:00',
      desc: 'Low carbon window (10:00–14:00) saves ~Rs 12 vs running at 18:00. Solar generation peaks at this time.',
      saving: 'Save ~Rs 12/cycle', color: 'var(--accent-purple)'
    })
  }
  if (!scheduled.has('Air Conditioner')) {
    suggestions.push({
      icon: '🌡️', title: 'Pre-cool before 18:00',
      desc: 'Run AC at 16:00–17:30 at off-peak rate (Rs 8/unit) instead of 18:00+ peak rate (Rs 12/unit).',
      saving: 'Save ~Rs 18/day', color: 'var(--accent-red)'
    })
  }
  suggestions.push({
    icon: '⚡', title: 'Shift high loads to 00:00–05:00',
    desc: 'Grid carbon intensity is lowest between midnight and 5am (0.77–0.79 kg CO₂/kWh). Schedule deferrable loads here.',
    saving: 'Reduce carbon ~8%', color: 'var(--accent-green)'
  })
  suggestions.push({
    icon: '🔋', title: 'EV already optimally scheduled',
    desc: 'EV charging at 03:00 takes advantage of lowest grid carbon intensity and off-peak tariff simultaneously.',
    saving: 'Optimal ✓', color: 'var(--accent-blue)'
  })
  return suggestions
}

export default function Devices({ data }) {
  const { devices } = data
  const scheduledNames = new Set(devices.map(d => d.name))
  const suggestions = getSuggestions(devices, ALL_DEVICES)

  // Consumption chart data
  const consumptionData = ALL_DEVICES.map(d => {
    const meta = DEVICE_META[d.name] || {}
    const isScheduled = scheduledNames.has(d.name)
    const totalKwh = isScheduled
      ? (d.power * d.slots)
      : meta.typical_daily_kwh || (d.power * d.slots)
    return {
      name:       d.name.split(' ')[0],
      fullName:   d.name,
      kwh:        +totalKwh.toFixed(2),
      scheduled:  isScheduled,
      color:      meta.color || 'var(--accent-blue)',
    }
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Header */}
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
          Device Scheduling
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          Binary LP scheduling — each appliance assigned to cheapest valid off-peak window ·
          &nbsp;{devices.length} of {ALL_DEVICES.length} devices scheduled this cycle
        </p>
      </div>

      {/* Consumption chart */}
      <div className="card">
        <p className="section-title">⚡ Estimated Energy Consumption per Appliance</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={consumptionData} margin={{ top: 5, right: 20, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} unit=" kWh" />
            <Tooltip
              {...TOOLTIP}
              formatter={(val, name, props) => [`${val} kWh`, props.payload.fullName]}
            />
            <Bar dataKey="kwh" radius={[6,6,0,0]}>
              {consumptionData.map((entry, i) => (
                <Cell key={i} fill={entry.color} opacity={entry.scheduled ? 1 : 0.4} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
          Solid bars = scheduled this cycle · Faded bars = not scheduled (estimated typical consumption shown)
        </p>
      </div>

      {/* Scheduled devices */}
      <div>
        <p className="section-title">✅ Scheduled This Cycle</p>
        {devices.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>
            No devices scheduled in this forecast window.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 14 }}>
            {devices.map(d => {
              const meta = DEVICE_META[d.name] || { icon: '⚡', color: 'var(--accent-blue)' }
              const totalKwh = (d.power_kwh * (d.duration_minutes / 30)).toFixed(2)
              return (
                <div key={d.name} className="card" style={{ borderLeft: `3px solid ${meta.color}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                    <span style={{ fontSize: 26 }}>{meta.icon}</span>
                    <div>
                      <p style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{d.name}</p>
                      <span style={{
                        fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 20,
                        background: 'rgba(62,207,142,0.15)', color: 'var(--accent-green)'
                      }}>✓ Scheduled</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {[
                      ['Scheduled Start',     d.start_time],
                      ['Duration',            `${d.duration_minutes} min`],
                      ['Power per 30-min',    `${d.power_kwh} kWh`],
                      ['Total Consumption',   `${totalKwh} kWh`],
                      ['Scheduled Cost',      `Rs ${d.cost_rs}`],
                    ].map(([label, val]) => (
                      <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</span>
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{val}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
                    <span style={{
                      fontSize: 11, padding: '3px 9px', borderRadius: 20,
                      background: 'var(--accent-blue-dim)', color: 'var(--accent-blue)', fontWeight: 600
                    }}>
                      Off-peak · Low carbon window
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Personalised suggestions */}
      <div>
        <p className="section-title">💡 Personalised Suggestions</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {suggestions.map((s, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: 14,
              padding: '14px 16px', borderRadius: 10,
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderLeft: `3px solid ${s.color}`
            }}>
              <span style={{ fontSize: 22, flexShrink: 0, marginTop: 2 }}>{s.icon}</span>
              <div style={{ flex: 1 }}>
                <p style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)', marginBottom: 3 }}>{s.title}</p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{s.desc}</p>
              </div>
              <span style={{
                fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 20,
                background: `rgba(${s.color === 'var(--accent-green)' ? '62,207,142' : s.color === 'var(--accent-blue)' ? '79,142,247' : '232,131,74'},0.15)`,
                color: s.color, whiteSpace: 'nowrap', flexShrink: 0
              }}>{s.saving}</span>
            </div>
          ))}
        </div>
      </div>

      {/* All devices table */}
      <div className="card">
        <p className="section-title">⚙️ All Device Configuration</p>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 6px', fontSize: 13 }}>
            <thead>
              <tr>
                {['Device', 'Wattage', 'Power/Slot', 'Duration', 'Window', 'Must Run', 'Status'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '8px 14px',
                    fontSize: 11, fontWeight: 600, letterSpacing: '0.05em',
                    textTransform: 'uppercase', color: 'var(--text-muted)',
                    borderBottom: '2px solid var(--border)'
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ALL_DEVICES.map(d => {
                const meta = DEVICE_META[d.name] || { icon: '⚡', color: 'var(--accent-blue)', window: '—', must: false, wattage: 0 }
                const scheduled = scheduledNames.has(d.name)
                return (
                  <tr key={d.name}>
                    <td style={{ padding: '12px 14px', borderRadius: '8px 0 0 8px', background: 'var(--bg-hover)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 18 }}>{meta.icon}</span>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{d.name}</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 14px', background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>{meta.wattage}W</td>
                    <td style={{ padding: '12px 14px', background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>{d.power} kWh</td>
                    <td style={{ padding: '12px 14px', background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>{d.duration} min</td>
                    <td style={{ padding: '12px 14px', background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>{meta.window}</td>
                    <td style={{ padding: '12px 14px', background: 'var(--bg-hover)' }}>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 20, fontWeight: 600,
                        background: meta.must ? 'rgba(62,207,142,0.12)' : 'rgba(96,104,128,0.2)',
                        color: meta.must ? 'var(--accent-green)' : 'var(--text-muted)'
                      }}>{meta.must ? 'Required' : 'Optional'}</span>
                    </td>
                    <td style={{ padding: '12px 14px', borderRadius: '0 8px 8px 0', background: 'var(--bg-hover)' }}>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 20, fontWeight: 600,
                        background: scheduled ? 'rgba(79,142,247,0.15)' : 'rgba(96,104,128,0.15)',
                        color: scheduled ? 'var(--accent-blue)' : 'var(--text-muted)'
                      }}>{scheduled ? '✓ Scheduled' : '— Not scheduled'}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  )
}