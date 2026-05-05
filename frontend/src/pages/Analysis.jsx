import { useState } from 'react'
import KPICard from '../components/KPICard'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, Cell, Legend } from 'recharts'

const TT = { contentStyle: { background: '#0d1117', border: '1px solid #1f2d40', borderRadius: 10, fontSize: 12 } }

export default function Analysis({ data }) {
  const { optimization, dataset } = data
  const [activeHour, setActiveHour] = useState(null)

  const hourMap = {}
  optimization.forEach(d => {
    const h = parseInt(d.timestamp.slice(11, 13))
    if (!hourMap[h]) hourMap[h] = []
    hourMap[h].push(d.forecast_energy)
  })

  const daily = Object.entries(hourMap).map(([h, vals]) => {
    const avg    = vals.reduce((a,b) => a+b, 0) / vals.length
    const isPeak = parseInt(h) >= 18 && parseInt(h) < 22
    return { hour: `${String(h).padStart(2,'0')}:00`, energy: +avg.toFixed(4), isPeak, h: parseInt(h) }
  })

  const areaData = optimization.map(d => ({
    time:      d.timestamp.slice(11, 16),
    forecast:  +d.forecast_energy.toFixed(4),
    optimized: +d.optimized_energy.toFixed(4),
  }))

  const active = activeHour !== null ? daily[activeHour] : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.5px', marginBottom: 4 }}>
            Exploratory Analysis
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            {dataset.total_records.toLocaleString()} records · {dataset.meters_loaded} BSES meters ·
            {dataset.period_start} → {dataset.period_end}
          </p>
        </div>
        {active && (
          <button onClick={() => setActiveHour(null)} style={{
            padding: '6px 14px', borderRadius: 8, fontSize: 11, fontWeight: 700,
            background: 'rgba(239,68,68,0.12)', color: 'var(--accent-red)',
            border: '1px solid rgba(239,68,68,0.25)', cursor: 'pointer'
          }}>✕ Clear {active.hour}</button>
        )}
      </div>

      {/* KPI row — updates on bar click */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
        <KPICard title={active ? `${active.hour} Energy` : 'Total Records'}
          value={active ? active.energy.toFixed(4) : dataset.total_records.toLocaleString()}
          sub={active ? (active.isPeak ? '🔴 Peak hour' : '🟢 Off-peak') : `${dataset.meters_loaded} meters`}
          accent={active ? (active.isPeak ? '#ef4444' : '#10b981') : '#3b82f6'}
          gauge={active ? (active.energy / 0.6) * 100 : (dataset.meters_loaded/15)*100}
          gaugeMax={100} gaugeUnit="/" />
        <KPICard title={active ? 'Hour Tariff' : 'Std Deviation'}
          value={active ? `Rs ${active.isPeak ? 12 : 8}/unit` : dataset.std}
          sub={active ? `Carbon: ${active.isPeak ? '0.92' : '0.78'} kg/kWh` : 'Combined variance'}
          accent={active ? (active.isPeak ? '#ef4444' : '#10b981') : '#8b5cf6'}
          gauge={active ? (active.isPeak ? 100 : 33) : (dataset.std/0.3)*100}
          gaugeMax={100} gaugeUnit="/" />
        <KPICard title="Meters Loaded"
          value={dataset.meters_loaded}
          sub="BSES Delhi smart meters"
          accent="#3b82f6"
          gauge={(dataset.meters_loaded/15)*100} gaugeMax={100} gaugeUnit="/" />
        <KPICard title="Data Mean"
          value={dataset.mean}
          sub="Normalised consumption index"
          accent="#f97316"
          gauge={dataset.mean*100} gaugeMax={100} gaugeUnit="/" />
      </div>

      {/* Daily pattern — interactive */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
          <p className="section-title" style={{ margin: 0 }}>Daily Average Consumption Pattern</p>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>💡 Click bar to inspect hour</span>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart
            data={daily}
            onClick={e => e?.activeTooltipIndex !== undefined && setActiveHour(i => i === e.activeTooltipIndex ? null : e.activeTooltipIndex)}
            style={{ cursor: 'pointer' }}
            margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="hour" tick={{ fill: '#4a5568', fontSize: 10 }} interval={2} />
            <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} />
            <Tooltip {...TT} />
            <Bar dataKey="energy" name="Avg Energy" radius={[4,4,0,0]}>
              {daily.map((e, i) => (
                <Cell key={i}
                  fill={e.isPeak ? '#ef4444' : '#3b82f6'}
                  opacity={activeHour === null || activeHour === i ? 0.85 : 0.3}
                  stroke={activeHour === i ? 'white' : 'transparent'}
                  strokeWidth={2}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
          {active
            ? `📍 ${active.hour} · Avg energy: ${active.energy} · Tariff: Rs ${active.isPeak ? 12 : 8}/unit · Carbon: ${active.isPeak ? '0.92' : '0.78'} kg/kWh`
            : '🔴 Red = 18:00–22:00 peak tariff · 🔵 Blue = off-peak · Click any bar to inspect'}
        </p>
      </div>

      {/* Forecast vs Optimized */}
      <div className="card">
        <p className="section-title">Forecast vs Optimised — Full 24h</p>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={areaData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="gF" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#f97316" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0}   />
              </linearGradient>
              <linearGradient id="gO" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="time" tick={{ fill: '#4a5568', fontSize: 11 }} interval={5} />
            <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} />
            <Tooltip {...TT} />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 10 }} />
            <Area type="monotone" dataKey="forecast"  name="LSTM Forecast" stroke="#f97316" fill="url(#gF)" strokeWidth={2} />
            <Area type="monotone" dataKey="optimized" name="LP Optimised"  stroke="#3b82f6" fill="url(#gO)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
          Gap = load successfully shifted from peak to off-peak slots by LP optimiser
        </p>
      </div>

      {/* Dataset table */}
      <div className="card">
        <p className="section-title">🔌 Dataset Summary</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 10 }}>
          {[
            ['Data Period',         `${dataset.period_start} → ${dataset.period_end}`],
            ['Total Records',       dataset.total_records.toLocaleString()],
            ['Meters Loaded',       `${dataset.meters_loaded} BSES Delhi meters`],
            ['Combined Std Dev',    dataset.std],
            ['Combined Mean',       dataset.mean],
            ['Sampling Frequency',  '30-minute intervals'],
            ['Normalisation',       'MinMaxScaler 0–1 per meter'],
            ['Train / Test Split',  '80% / 20% positional'],
          ].map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'var(--bg-hover)', borderRadius: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{k}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{v}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}