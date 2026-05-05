import { useState } from 'react'
import KPICard from '../components/KPICard'
import StatBar from '../components/StatBar'
import GaugeRing from '../components/GaugeRing'
import { TrendingDown, DollarSign, Leaf, Zap, Database, Cpu, BarChart2, Activity } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend
} from 'recharts'

const TT = { contentStyle: { background: '#0d1117', border: '1px solid #1f2d40', borderRadius: 10, fontSize: 12 } }

export default function Overview({ data }) {
  const { impact, dataset, selected_model, models, optimization, devices } = data
  const selectedModel = models.find(m => m.selected)
  const [activeSlot, setActiveSlot] = useState(null)

  const chartData = optimization.map((d, i) => ({
    time:    d.timestamp.slice(11, 16),
    before:  +d.forecast_energy.toFixed(4),
    after:   +d.optimized_energy.toFixed(4),
    saved:   +(d.forecast_energy - d.optimized_energy).toFixed(4),
    hour:    parseInt(d.timestamp.slice(11, 13)),
    index:   i,
  }))

  const disp = activeSlot ? {
    peak_reduction_pct: activeSlot.saved > 0
      ? +((activeSlot.saved / activeSlot.before) * 100).toFixed(1) : 0,
    cost_saved: +(activeSlot.saved * (activeSlot.hour >= 18 && activeSlot.hour < 22 ? 12 : 8)).toFixed(2),
    carbon_saved: +(activeSlot.saved * (activeSlot.hour >= 18 && activeSlot.hour < 22 ? 0.92 : 0.78)).toFixed(4),
    energy_saved_kwh: +(activeSlot.saved * 5).toFixed(3),
    peak_before_kwh: +(activeSlot.before * 5).toFixed(3),
    peak_after_kwh:  +(activeSlot.after  * 5).toFixed(3),
  } : impact

  const handleClick = (e) => {
    if (e?.activePayload?.[0]) {
      const d = e.activePayload[0].payload
      setActiveSlot(prev => prev?.index === d.index ? null : d)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.5px', marginBottom: 4 }}>
            System Overview
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            SECFAOS · {dataset.meters_loaded} meters · {dataset.total_records.toLocaleString()} records · {dataset.period_start} → {dataset.period_end}
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

      {/* Slot mode banner */}
      {activeSlot && (
        <div style={{
          padding: '10px 16px', borderRadius: 10,
          background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span>🔍</span>
          <p style={{ fontSize: 12, color: 'var(--accent-blue)', fontWeight: 600 }}>
            Slot {activeSlot.time} — Before: {activeSlot.before} · After: {activeSlot.after} · Saved: {activeSlot.saved > 0 ? activeSlot.saved : '—'}
            <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 12 }}>
              KPI cards updated for this slot · Click again to reset
            </span>
          </p>
        </div>
      )}

      {/* KPI Row 1 — Optimisation */}
      <div>
        <p className="section-title"><TrendingDown size={13} /> {activeSlot ? `Slot ${activeSlot.time} Breakdown` : '24-Hour Optimisation Results'}</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
          <KPICard title="Peak Reduction"
            value={`${disp.peak_reduction_pct}%`}
            sub={`${disp.peak_before_kwh} → ${disp.peak_after_kwh} kWh`}
            delta="Load shifted from peak" deltaPositive
            icon={TrendingDown} accent="#3b82f6" borderAccent="#3b82f6"
            gauge={parseFloat(disp.peak_reduction_pct)} gaugeMax={30} gaugeUnit="%"
            onClick={() => {}} active={!!activeSlot} />
          <KPICard title={activeSlot ? 'Slot Cost Saved' : 'Daily Cost Saved'}
            value={`Rs ${disp.cost_saved}`}
            sub={activeSlot ? `Tariff Rs ${activeSlot.hour >= 18 && activeSlot.hour < 22 ? 12 : 8}/unit` : `Annual: Rs ${impact.annual_cost.toLocaleString()}`}
            delta="Cost optimised" deltaPositive
            icon={DollarSign} accent="#10b981" borderAccent="#10b981"
            gauge={Math.min(100, (parseFloat(disp.cost_saved) / 50) * 100)} gaugeMax={100} gaugeUnit="/" />
          <KPICard title="Carbon Saved"
            value={`${disp.carbon_saved} kg`}
            sub={activeSlot ? `Intensity ${activeSlot.hour >= 18 && activeSlot.hour < 22 ? '0.92' : '0.78'} kg/kWh` : `Annual: ${impact.annual_carbon.toLocaleString()} kg CO₂`}
            delta="Emissions reduced" deltaPositive
            icon={Leaf} accent="#10b981" borderAccent="#10b981"
            gauge={Math.min(100, (parseFloat(disp.carbon_saved) / 3) * 100)} gaugeMax={100} gaugeUnit="/" />
          <KPICard title="Energy Saved"
            value={`${disp.energy_saved_kwh} kWh`}
            sub="Per 24-hour cycle"
            icon={Zap} accent="#f97316" borderAccent="#f97316"
            gauge={Math.min(100, (parseFloat(disp.energy_saved_kwh) / 20) * 100)} gaugeMax={100} gaugeUnit="/" />
        </div>
      </div>

      {/* KPI Row 2 — System */}
      <div>
        <p className="section-title"><Database size={13} /> Dataset & Model</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
          <KPICard title="Selected Model" value={selected_model}
            sub={`MAE: ${selectedModel?.mae}`}
            icon={BarChart2} accent="#8b5cf6" borderAccent="#8b5cf6"
            gauge={selectedModel ? Math.min(100, (1 - selectedModel.mae) * 100) : 0}
            gaugeMax={100} gaugeUnit="acc" />
          <KPICard title="Total Records" value={dataset.total_records.toLocaleString()}
            sub={`${dataset.meters_loaded} meters · std ${dataset.std}`}
            icon={Database} accent="#3b82f6"
            gauge={dataset.meters_loaded} gaugeMax={15} gaugeUnit="m" />
          <KPICard title="Devices Scheduled" value={`${devices.length} / 4`}
            sub={devices.map(d => d.name.split(' ')[0]).join(' · ')}
            icon={Cpu} accent="#f97316"
            gauge={(devices.length / 4) * 100} gaugeMax={100} gaugeUnit="%" />
          <KPICard title="Data Variance" value={dataset.std}
            sub="Combined 11-meter std" delta="OK — sufficient" deltaPositive
            icon={Activity} accent="#10b981"
            gauge={Math.min(100, (dataset.std / 0.3) * 100)} gaugeMax={100} gaugeUnit="/" />
        </div>
      </div>

      {/* Two column layout — chart + stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>

        {/* Main chart */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
            <p className="section-title" style={{ margin: 0 }}>24-Hour Optimisation</p>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>💡 Click to inspect slot</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData} onClick={handleClick} style={{ cursor: 'crosshair' }} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="gradBefore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="gradAfter" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="time" tick={{ fill: '#4a5568', fontSize: 11 }} interval={5} />
              <YAxis tick={{ fill: '#4a5568', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 10 }} />
              {activeSlot && <ReferenceLine x={activeSlot.time} stroke="#3b82f6" strokeDasharray="4 3" strokeWidth={1.5} />}
              <Area type="monotone" dataKey="before" name="Before" stroke="#f97316" fill="url(#gradBefore)" strokeWidth={2} />
              <Area type="monotone" dataKey="after"  name="After"  stroke="#3b82f6" fill="url(#gradAfter)"  strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
            {activeSlot
              ? `📍 ${activeSlot.time} — Before: ${activeSlot.before} After: ${activeSlot.after} Saved: ${activeSlot.saved}`
              : 'Click any point to inspect individual slot values in KPI cards above'}
          </p>
        </div>

        {/* Side stats */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Big gauge */}
          <div className="card" style={{ textAlign: 'center' }}>
            <p className="section-title" style={{ justifyContent: 'center' }}>Peak Reduction</p>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
              <GaugeRing
                value={parseFloat(impact.peak_reduction_pct)}
                max={30}
                color="#3b82f6"
                size={120}
                unit="%"
              />
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {impact.peak_before_kwh} kWh → {impact.peak_after_kwh} kWh
            </p>
          </div>

          {/* Stat bars */}
          <div className="card">
            <p className="section-title">Model Performance</p>
            <StatBar label="LSTM Accuracy" value={+((1-0.0576)*100).toFixed(1)} max={100} color="#3b82f6" unit="%" />
            <StatBar label="vs SARIMA"     value={+((1 - 0.0576/0.1611)*100).toFixed(1)} max={100} color="#10b981" unit="%" />
            <StatBar label="vs Naive"      value={+((1 - 0.0576/0.0628)*100).toFixed(1)} max={100} color="#8b5cf6" unit="%" />
          </div>

        </div>
      </div>

      {/* Device cards */}
      {devices.length > 0 && (
        <div>
          <p className="section-title"><Cpu size={13} /> Scheduled Devices</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 14 }}>
            {devices.map(d => (
              <div key={d.name} className="card-sm" style={{ borderLeft: '3px solid var(--accent-blue)' }}>
                <p style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)', marginBottom: 8 }}>{d.name}</p>
                <div style={{ display: 'flex', gap: 16 }}>
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--text-muted)' }}>Start</p>
                    <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent-blue)' }}>{d.start_time}</p>
                  </div>
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--text-muted)' }}>Duration</p>
                    <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>{d.duration_minutes}m</p>
                  </div>
                  <div>
                    <p style={{ fontSize: 10, color: 'var(--text-muted)' }}>Cost</p>
                    <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent-green)' }}>Rs {d.cost_rs}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}