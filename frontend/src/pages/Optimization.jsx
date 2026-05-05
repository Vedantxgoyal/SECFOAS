import { useState } from 'react'
import KPICard from '../components/KPICard'
import GaugeRing from '../components/GaugeRing'
import StatBar from '../components/StatBar'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell, Legend, ReferenceLine
} from 'recharts'

const TT = { contentStyle: { background: '#0d1117', border: '1px solid #1f2d40', borderRadius: 10, fontSize: 12 } }

export default function Optimization({ data }) {
  const { optimization, impact } = data
  const [activeSlot, setActiveSlot] = useState(null)

  const chartData = optimization.map((d, i) => ({
    time:    d.timestamp.slice(11, 16),
    before:  +d.forecast_energy.toFixed(4),
    after:   +d.optimized_energy.toFixed(4),
    saved:   +(d.forecast_energy - d.optimized_energy).toFixed(4),
    hour:    parseInt(d.timestamp.slice(11, 13)),
    isPeak:  parseInt(d.timestamp.slice(11, 13)) >= 18 && parseInt(d.timestamp.slice(11, 13)) < 22,
    index:   i,
  }))

  const hourly = []
  for (let i = 0; i < chartData.length; i += 2) {
    hourly.push({
      hour:   chartData[i]?.time,
      before: +((chartData[i]?.before + (chartData[i+1]?.before||0))/2).toFixed(4),
      after:  +((chartData[i]?.after  + (chartData[i+1]?.after ||0))/2).toFixed(4),
      isPeak: chartData[i]?.isPeak,
    })
  }

  const disp = activeSlot ? {
    peak_reduction_pct: activeSlot.saved > 0 ? +((activeSlot.saved/activeSlot.before)*100).toFixed(1) : 0,
    cost_saved:  +(activeSlot.saved * (activeSlot.isPeak ? 12 : 8)).toFixed(2),
    peak_before_kwh: +(activeSlot.before * 5).toFixed(3),
    peak_after_kwh:  +(activeSlot.after  * 5).toFixed(3),
  } : impact

  const totalSaved = optimization.reduce((s,d) => s + Math.max(0, d.forecast_energy - d.optimized_energy), 0)
  const peakSaved  = optimization.filter(d => {
    const h = parseInt(d.timestamp.slice(11,13))
    return h >= 18 && h < 22
  }).reduce((s,d) => s + Math.max(0, d.forecast_energy - d.optimized_energy), 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.5px', marginBottom: 4 }}>
            LP Optimisation
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            PuLP/CBC solver · Peak cap 75th pct · Flexible load 25% · λ=0.5 (cost+carbon)
          </p>
        </div>
        {activeSlot && (
          <button onClick={() => setActiveSlot(null)} style={{
            padding: '6px 14px', borderRadius: 8, fontSize: 11, fontWeight: 700,
            background: 'rgba(239,68,68,0.12)', color: 'var(--accent-red)',
            border: '1px solid rgba(239,68,68,0.25)', cursor: 'pointer'
          }}>✕ Clear {activeSlot.time}</button>
        )}
      </div>

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
        <KPICard title={activeSlot ? 'Slot Reduction' : 'Peak Reduction'}
          value={`${disp.peak_reduction_pct}%`}
          sub={`${disp.peak_before_kwh} → ${disp.peak_after_kwh} kWh`}
          delta="Peak load shifted" deltaPositive
          accent="#3b82f6" borderAccent="#3b82f6"
          gauge={parseFloat(disp.peak_reduction_pct)} gaugeMax={30} gaugeUnit="%" />
        <KPICard title={activeSlot ? 'Slot Cost Saved' : 'Daily Cost Saved'}
          value={`Rs ${disp.cost_saved}`}
          sub={activeSlot ? `Rs ${activeSlot.isPeak ? 12 : 8}/unit tariff` : `Annual Rs ${impact.annual_cost.toLocaleString()}`}
          delta="Tariff optimised" deltaPositive
          accent="#10b981" borderAccent="#10b981"
          gauge={Math.min(100,(parseFloat(disp.cost_saved)/50)*100)} gaugeMax={100} gaugeUnit="/" />
        <KPICard title="Total Shifted"
          value={totalSaved.toFixed(4)}
          sub={`Peak: ${peakSaved.toFixed(4)} units`}
          accent="#f97316" borderAccent="#f97316"
          gauge={(peakSaved/totalSaved)*100} gaugeMax={100} gaugeUnit="%" />
        <KPICard title="Solver"
          value="LP / CBC"
          sub="PuLP · Feasible · <1s"
          accent="#8b5cf6" borderAccent="#8b5cf6"
          gauge={100} gaugeMax={100} gaugeUnit="ok" />
      </div>

      {/* Charts + gauges */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
            <p className="section-title" style={{ margin: 0 }}>Before vs After — 48 Slots</p>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>💡 Click to inspect slot</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart
              data={chartData}
              onClick={e => e?.activePayload?.[0] && setActiveSlot(s => s?.index === e.activePayload[0].payload.index ? null : e.activePayload[0].payload)}
              style={{ cursor: 'crosshair' }}
              margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="gBefore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="gAfter" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="time" tick={{ fill: '#4a5568', fontSize: 11 }} interval={5} />
              <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 10 }} />
              {activeSlot && <ReferenceLine x={activeSlot.time} stroke="#3b82f6" strokeDasharray="4 3" strokeWidth={2} />}
              <Area type="monotone" dataKey="before" name="Before" stroke="#f97316" fill="url(#gBefore)" strokeWidth={2} />
              <Area type="monotone" dataKey="after"  name="After"  stroke="#3b82f6" fill="url(#gAfter)"  strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
            {activeSlot
              ? `📍 ${activeSlot.time} · Before ${activeSlot.before} · After ${activeSlot.after} · Saved ${activeSlot.saved > 0 ? activeSlot.saved : '—'}`
              : 'Click any point to update KPI cards with slot-level values'}
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="card" style={{ textAlign: 'center' }}>
            <p className="section-title" style={{ justifyContent: 'center' }}>Peak Reduction</p>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}>
              <GaugeRing value={parseFloat(impact.peak_reduction_pct)} max={30} color="#3b82f6" size={110} unit="%" />
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{impact.peak_before_kwh} → {impact.peak_after_kwh} kWh</p>
          </div>
          <div className="card">
            <p className="section-title">Load Distribution</p>
            <StatBar label="Peak shifted"    value={+(peakSaved*100).toFixed(1)}   max={100} color="#ef4444" unit="%" />
            <StatBar label="Off-peak used"   value={+(((totalSaved-peakSaved)/totalSaved)*100).toFixed(1)} max={100} color="#10b981" unit="%" />
            <StatBar label="Total reduction" value={+(impact.peak_reduction_pct)}  max={30}  color="#3b82f6" unit="%" />
          </div>
        </div>
      </div>

      {/* Hourly bars */}
      <div className="card">
        <p className="section-title">Hourly Load Comparison</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={hourly} barGap={2} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="hour" tick={{ fill: '#4a5568', fontSize: 10 }} interval={2} />
            <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} />
            <Tooltip {...TT} />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 10 }} />
            <Bar dataKey="before" name="Before" fill="#f97316" opacity={0.8} radius={[3,3,0,0]} />
            <Bar dataKey="after"  name="After"  fill="#3b82f6" opacity={0.8} radius={[3,3,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

    </div>
  )
}