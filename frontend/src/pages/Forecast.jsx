import { useState } from 'react'
import KPICard from '../components/KPICard'
import GaugeRing from '../components/GaugeRing'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell, ReferenceLine, Legend
} from 'recharts'

const TT = { contentStyle: { background: '#0d1117', border: '1px solid #1f2d40', borderRadius: 10, fontSize: 12 } }

export default function Forecast({ data }) {
  const { forecast, selected_model, models } = data
  const selectedModel = models.find(m => m.selected)
  const [activeIdx, setActiveIdx] = useState(null)

  const chartData = forecast.map((d, i) => {
    const hour   = parseInt(d.timestamp.slice(11, 13))
    const isPeak = hour >= 18 && hour < 22
    return {
      time:    d.timestamp.slice(11, 16),
      energy:  +d.forecast_energy.toFixed(4),
      isPeak,
      hour,
      index:   i,
      tariff:  isPeak ? 12 : 8,
      carbon:  isPeak ? 0.92 : 0.78,
    }
  })

  const hourly = []
  for (let i = 0; i < chartData.length; i += 2) {
    const avg    = ((chartData[i]?.energy || 0) + (chartData[i+1]?.energy || 0)) / 2
    const isPeak = chartData[i]?.isPeak
    hourly.push({ hour: chartData[i]?.time, energy: +avg.toFixed(4), isPeak })
  }

  const peak   = Math.max(...forecast.map(d => d.forecast_energy))
  const mean   = forecast.reduce((s,d) => s + d.forecast_energy, 0) / forecast.length
  const std    = Math.sqrt(forecast.reduce((s,d) => s + Math.pow(d.forecast_energy - mean, 2), 0) / forecast.length)
  const peakSlots    = chartData.filter(d => d.isPeak).length
  const offpeakSlots = chartData.length - peakSlots

  const active = activeIdx !== null ? chartData[activeIdx] : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.5px', marginBottom: 4 }}>
            24-Hour Energy Forecast
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Model: <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>{selected_model}</span> ·
            MAE: <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>{selectedModel?.mae}</span> ·
            Strategy: 40% LSTM + 60% Historical Profile ·
            Horizon: <span style={{ color: 'var(--accent-orange)', fontWeight: 600 }}>24 hours ({forecast.length} slots)</span>
          </p>
        </div>
        {active && (
          <button onClick={() => setActiveIdx(null)} style={{
            padding: '6px 14px', borderRadius: 8, fontSize: 11, fontWeight: 700,
            background: 'rgba(239,68,68,0.12)', color: 'var(--accent-red)',
            border: '1px solid rgba(239,68,68,0.25)', cursor: 'pointer'
          }}>✕ Clear {active.time}</button>
        )}
      </div>

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
        <KPICard title="Forecast Peak"
          value={active ? active.energy.toFixed(4) : peak.toFixed(4)}
          sub={active ? `Slot ${active.time}` : 'Max 30-min slot'}
          accent="#f97316" borderAccent="#f97316"
          gauge={active ? (active.energy / peak) * 100 : 100} gaugeMax={100} gaugeUnit="/" />
        <KPICard title={active ? 'Slot Tariff' : 'Forecast Mean'}
          value={active ? `Rs ${active.tariff}/unit` : mean.toFixed(4)}
          sub={active ? (active.isPeak ? '🔴 Peak window' : '🟢 Off-peak') : '48-slot average'}
          accent={active ? (active.isPeak ? '#ef4444' : '#10b981') : '#94a3b8'}
          gauge={active ? (active.isPeak ? 100 : 33) : (mean / peak) * 100} gaugeMax={100} gaugeUnit="/" />
        <KPICard title={active ? 'Slot Carbon' : 'Std Deviation'}
          value={active ? `${active.carbon} kg` : std.toFixed(4)}
          sub={active ? 'kg CO₂/kWh intensity' : 'Forecast variance'}
          accent={active ? '#10b981' : '#8b5cf6'}
          gauge={active ? (active.carbon / 0.95) * 100 : (std / 0.1) * 100} gaugeMax={100} gaugeUnit="/" />
        <KPICard title="Peak Slots"
          value={`${peakSlots} / ${forecast.length}`}
          sub={`${offpeakSlots} off-peak · ${peakSlots} peak (18-22h)`}
          accent="#ef4444"
          gauge={(peakSlots / forecast.length) * 100} gaugeMax={100} gaugeUnit="%" />
      </div>

      {/* Active slot banner */}
      {active && (
        <div style={{
          padding: '10px 16px', borderRadius: 10,
          background: active.isPeak ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
          border: `1px solid ${active.isPeak ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}`,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <span style={{ fontSize: 20 }}>{active.isPeak ? '🔴' : '🟢'}</span>
          <div>
            <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
              Slot {active.time} — {active.isPeak ? 'PEAK TARIFF WINDOW' : 'OFF-PEAK'}
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Energy: {active.energy} · Tariff: Rs {active.tariff}/unit · Carbon: {active.carbon} kg CO₂/kWh
            </p>
          </div>
        </div>
      )}

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>

        {/* Forecast curve */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
            <p className="section-title" style={{ margin: 0 }}>Forecast Curve — {forecast.length} Slots · 24 Hours</p>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>💡 Click to inspect slot</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart
              data={chartData}
              onClick={e => e?.activePayload?.[0] && setActiveIdx(i => i === e.activePayload[0].payload.index ? null : e.activePayload[0].payload.index)}
              style={{ cursor: 'crosshair' }}
              margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="gradForecast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="time" tick={{ fill: '#4a5568', fontSize: 11 }} interval={5} />
              <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} domain={['auto', 'auto']} />
              <Tooltip {...TT} />
              <ReferenceLine y={peak} stroke="rgba(249,115,22,0.4)" strokeDasharray="4 3" label={{ value: 'Peak', fill: '#f97316', fontSize: 11 }} />
              {active && <ReferenceLine x={active.time} stroke="#3b82f6" strokeDasharray="4 3" strokeWidth={2} />}
              <Area type="monotone" dataKey="energy" name="Forecast Energy"
                stroke="#3b82f6" fill="url(#gradForecast)" strokeWidth={2.5} />
            </AreaChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 16, marginTop: 10 }}>
            <span style={{ fontSize: 11, color: 'var(--accent-red)' }}>🔴 18:00–22:00 peak tariff (Rs 12/unit)</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Orange line = forecast peak</span>
          </div>
        </div>

        {/* Slot breakdown gauge */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="card" style={{ textAlign: 'center' }}>
            <p className="section-title" style={{ justifyContent: 'center' }}>Peak Slot Ratio</p>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
              <GaugeRing value={peakSlots} max={forecast.length} color="#ef4444" size={110} unit="slots" />
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{peakSlots} peak · {offpeakSlots} off-peak</p>
          </div>
          <div className="card">
            <p className="section-title">Model Accuracy</p>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
              <GaugeRing value={+((1-selectedModel?.mae)*100).toFixed(1)} max={100} color="#10b981" size={100} unit="%" />
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>MAE: {selectedModel?.mae}</p>
          </div>
        </div>
      </div>

      {/* Hourly bars */}
      <div className="card">
        <p className="section-title">Hourly Breakdown — Mean per Hour</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={hourly} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="hour" tick={{ fill: '#4a5568', fontSize: 10 }} interval={2} />
            <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} />
            <Tooltip {...TT} />
            <Bar dataKey="energy" name="Mean Energy" radius={[4,4,0,0]}>
              {hourly.map((e, i) => (
                <Cell key={i} fill={e.isPeak ? '#ef4444' : '#3b82f6'} opacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
          🔴 Red = peak tariff (18:00–22:00, Rs 12/unit) · 🔵 Blue = off-peak (Rs 8/unit)
        </p>
      </div>

    </div>
  )
}