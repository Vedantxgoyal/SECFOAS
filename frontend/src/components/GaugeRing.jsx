import { CircularProgressbar, buildStyles } from 'react-circular-progressbar'
import 'react-circular-progressbar/dist/styles.css'

export default function GaugeRing({
  value,
  max = 100,
  color = '#3b82f6',
  size = 64,
  label,
  unit = '%',
  animate = true,
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div style={{ width: size, height: size, position: 'relative', flexShrink: 0 }}>
      <CircularProgressbar
        value={pct}
        styles={buildStyles({
          rotation:         0.75,
          strokeLinecap:    'round',
          pathTransitionDuration: animate ? 0.8 : 0,
          pathColor:        color,
          trailColor:       'rgba(255,255,255,0.06)',
          textColor:        color,
        })}
      />
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: size < 60 ? 10 : 12, fontWeight: 700, color, lineHeight: 1 }}>
          {typeof value === 'number' ? value.toFixed(value < 10 ? 2 : 1) : value}
        </span>
        {unit && <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', marginTop: 1 }}>{unit}</span>}
      </div>
    </div>
  )
}