import KPICard from '../components/KPICard'
import GaugeRing from '../components/GaugeRing'
import StatBar from '../components/StatBar'
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const TT = { contentStyle: { background: '#0d1117', border: '1px solid #1f2d40', borderRadius: 10, fontSize: 12 } }

export default function Impact({ data }) {
  const { impact } = data

  const months  = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  const monthly = impact.cost_saved * 30
  const projection = months.map((m, i) => ({
    month: m,
    saving:     +monthly.toFixed(2),
    cumulative: +(monthly * (i+1)).toFixed(2),
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Header */}
      <div>
        <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.5px', marginBottom: 4 }}>
          Impact & Projections
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          Extrapolated from 24-hour optimisation × 365 days · Based on BSES Delhi TOU tariffs
        </p>
      </div>

      {/* Annual KPIs */}
      <div>
        <p className="section-title">💰 Annual Impact</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
          <KPICard title="Annual Cost Saving"
            value={`Rs ${impact.annual_cost.toLocaleString()}`}
            sub={`Rs ${(impact.annual_cost/12).toFixed(0)}/month`}
            delta="Savings locked in" deltaPositive
            accent="#10b981" borderAccent="#10b981"
            gauge={(impact.annual_cost/15000)*100} gaugeMax={100} gaugeUnit="/" />
          <KPICard title="Annual Carbon Saved"
            value={`${impact.annual_carbon.toLocaleString()} kg`}
            sub="kg CO₂ avoided"
            delta="Based on CEA 0.82 kg/kWh" deltaPositive
            accent="#10b981" borderAccent="#10b981"
            gauge={(impact.annual_carbon/1500)*100} gaugeMax={100} gaugeUnit="/" />
          <KPICard title="Trees Equivalent"
            value={`${Math.round(impact.annual_carbon/21)}`}
            sub="trees planted equivalent"
            delta="21 kg CO₂/tree/year" deltaPositive
            accent="#3b82f6" borderAccent="#3b82f6"
            gauge={Math.min(100,(Math.round(impact.annual_carbon/21)/100)*100)} gaugeMax={100} gaugeUnit="/" />
          <KPICard title="Monthly Saving"
            value={`Rs ${(impact.annual_cost/12).toFixed(0)}`}
            sub="Per meter per month"
            accent="#f97316" borderAccent="#f97316"
            gauge={(impact.annual_cost/12/1500)*100} gaugeMax={100} gaugeUnit="/" />
        </div>
      </div>

      {/* Daily KPIs */}
      <div>
        <p className="section-title">⚡ Daily Metrics</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14 }}>
          <KPICard title="Daily Energy Saved"
            value={`${impact.energy_saved_kwh} kWh`}
            sub="Per 24-hour cycle"
            accent="#f97316"
            gauge={(impact.energy_saved_kwh/20)*100} gaugeMax={100} gaugeUnit="/" />
          <KPICard title="Daily Cost Saved"
            value={`Rs ${impact.cost_saved}`}
            sub="Based on TOU tariffs"
            accent="#10b981"
            gauge={(impact.cost_saved/50)*100} gaugeMax={100} gaugeUnit="/" />
          <KPICard title="Daily Carbon Saved"
            value={`${impact.carbon_saved} kg`}
            sub="CEA grid factor"
            accent="#10b981"
            gauge={(impact.carbon_saved/3)*100} gaugeMax={100} gaugeUnit="/" />
        </div>
      </div>

      {/* Two col layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>

        {/* Projection chart */}
        <div className="card">
          <p className="section-title">📈 12-Month Cost Saving Projection</p>
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={projection} margin={{ top: 5, right: 40, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="month" tick={{ fill: '#4a5568', fontSize: 11 }} />
              <YAxis yAxisId="l" tick={{ fill: '#4a5568', fontSize: 11 }} />
              <YAxis yAxisId="r" orientation="right" tick={{ fill: '#4a5568', fontSize: 11 }} />
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12, paddingTop: 10 }} />
              <Bar    yAxisId="l" dataKey="saving"     name="Monthly (Rs)"    fill="#3b82f6" opacity={0.8} radius={[4,4,0,0]} />
              <Line   yAxisId="r" dataKey="cumulative" name="Cumulative (Rs)" stroke="#10b981" strokeWidth={2.5} dot={false} type="monotone" />
            </ComposedChart>
          </ResponsiveContainer>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
            Blue bars = monthly saving · Green line = cumulative annual total
          </p>
        </div>

        {/* Side gauges */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="card" style={{ textAlign: 'center' }}>
            <p className="section-title" style={{ justifyContent: 'center' }}>Annual Target</p>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 10 }}>
              <GaugeRing value={impact.annual_cost} max={15000} color="#10b981" size={110} unit="Rs" />
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Rs {impact.annual_cost.toLocaleString()} / Rs 15,000 target</p>
          </div>
          <div className="card">
            <p className="section-title">Savings Breakdown</p>
            <StatBar label="Peak hours"    value={+(impact.cost_saved * 0.7).toFixed(1)} max={50} color="#ef4444" unit=" Rs" />
            <StatBar label="Off-peak"      value={+(impact.cost_saved * 0.3).toFixed(1)} max={50} color="#10b981" unit=" Rs" />
            <StatBar label="Carbon credit" value={+(impact.carbon_saved * 2).toFixed(1)} max={10} color="#3b82f6" unit=" Rs" />
          </div>
        </div>
      </div>

      {/* Load factor + carbon cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div className="card">
          <p className="section-title">⚡ Load Factor Analysis</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 14 }}>
            {[
              { label: 'Before', value: impact.lf_before, color: 'var(--accent-orange)' },
              { label: 'After',  value: impact.lf_after,  color: 'var(--accent-blue)'   },
              { label: 'Change', value: `${impact.lf_improvement}%`,
                color: impact.lf_improvement >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' },
            ].map(c => (
              <div key={c.label} style={{ textAlign: 'center', padding: '12px', background: 'var(--bg-hover)', borderRadius: 10 }}>
                <p style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>{c.label}</p>
                <p style={{ fontSize: 20, fontWeight: 800, color: c.color }}>{c.value}</p>
              </div>
            ))}
          </div>
          <div style={{ padding: '10px 12px', background: 'rgba(59,130,246,0.06)', borderRadius: 8, border: '1px solid rgba(59,130,246,0.12)' }}>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              A slight LF decrease is expected when LP aggressively reduces peak load.
              The primary objective — {impact.peak_reduction_pct}% peak reduction — is achieved.
            </p>
          </div>
        </div>

        <div className="card" style={{ borderLeft: '3px solid var(--accent-green)' }}>
          <p className="section-title">🌱 Environmental Impact</p>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 14 }}>
            <GaugeRing value={impact.annual_carbon} max={1500} color="#10b981" size={100} unit="kg" />
          </div>
          <StatBar label={`${Math.round(impact.annual_carbon/21)} trees equiv`} value={impact.annual_carbon} max={1500} color="#10b981" unit=" kg" />
          <StatBar label="Daily saved" value={impact.carbon_saved} max={3} color="#3b82f6" unit=" kg" />
          <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10 }}>
            Based on CEA CO₂ Baseline v18 · 0.82 kg CO₂/kWh national average
          </p>
        </div>
      </div>

    </div>
  )
}