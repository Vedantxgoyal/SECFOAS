import GaugeRing from './GaugeRing'

export default function KPICard({
  title, value, sub, delta, deltaPositive,
  icon: Icon, accent = '#3b82f6',
  gauge, gaugeMax = 100, gaugeUnit = '%',
  onClick, active, borderAccent,
}) {
  return (
    <div
      className="card-sm"
      onClick={onClick}
      style={{
        borderLeft: `3px solid ${borderAccent || accent}`,
        cursor: onClick ? 'pointer' : 'default',
        background: active ? `rgba(${hexToRgb(accent)},0.08)` : 'var(--bg-card)',
        boxShadow: active ? `0 0 0 1px ${accent}40` : 'none',
        display: 'flex', flexDirection: 'column', gap: 10,
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span className="label">{title}</span>
        {Icon && !gauge && <Icon size={14} style={{ color: accent, opacity: 0.7 }} />}
      </div>

      {/* Value + gauge row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="animate-count" style={{
            fontSize: 24, fontWeight: 800,
            color: accent, lineHeight: 1.1,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
          }}>
            {value}
          </div>
          {sub && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>
              {sub}
            </div>
          )}
        </div>
        {gauge !== undefined && (
          <GaugeRing
            value={gauge}
            max={gaugeMax}
            color={accent}
            size={58}
            unit={gaugeUnit}
          />
        )}
      </div>

      {/* Delta */}
      {delta && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 4,
          fontSize: 11, fontWeight: 600,
          color: deltaPositive ? 'var(--accent-green)' : 'var(--accent-red)',
        }}>
          <span>{deltaPositive ? '↑' : '↓'}</span>
          {delta}
        </div>
      )}

      {/* Active indicator */}
      {active && (
        <div style={{
          height: 2, borderRadius: 1,
          background: `linear-gradient(90deg, ${accent}, transparent)`,
          marginTop: 2,
        }} />
      )}
    </div>
  )
}

function hexToRgb(hex) {
  const r = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return r ? `${parseInt(r[1],16)},${parseInt(r[2],16)},${parseInt(r[3],16)}` : '59,130,246'
}