import { useState, useCallback } from 'react'
import { usePipeline } from './hooks/usePipeline'
import { refreshPipeline } from './api/client'
import Sidebar      from './components/Sidebar'
import Overview     from './pages/Overview'
import Forecast     from './pages/Forecast'
import Optimization from './pages/Optimization'
import Models       from './pages/Models'
import Impact       from './pages/Impact'
import Devices      from './pages/Devices'
import Analysis     from './pages/Analysis'

const STEPS = [
  'Loading 11 BSES meters...',
  'Running ADF stationarity test...',
  'Fitting SARIMA model...',
  'Loading LSTM from disk...',
  'Generating 24-hour forecast...',
  'Running LP optimisation...',
  'Scheduling devices...',
  'Computing impact metrics...',
  'Finalising results...',
]

export default function App() {
  const [page, setPage]       = useState('overview')
  const [step, setStep]       = useState(0)
  const { data, loading, error, run } = usePipeline()

  const handleRun = useCallback(async () => {
    setStep(0)
    const interval = setInterval(() => {
      setStep(s => s < STEPS.length - 1 ? s + 1 : s)
    }, 13000)
    await run()
    clearInterval(interval)
  }, [run])

  const handleRefresh = useCallback(async () => {
    await refreshPipeline()
    handleRun()
  }, [handleRun])

  const sidebarWidth = 220

  const renderPage = () => {
    if (!data) return null
    const props = { data }
    switch (page) {
      case 'overview':     return <Overview     {...props} />
      case 'forecast':     return <Forecast     {...props} />
      case 'optimization': return <Optimization {...props} />
      case 'models':       return <Models       {...props} />
      case 'impact':       return <Impact       {...props} />
      case 'devices':      return <Devices      {...props} />
      case 'analysis':     return <Analysis     {...props} />
      default:             return <Overview     {...props} />
    }
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <Sidebar
        page={page} setPage={setPage}
        loading={loading} onRun={handleRun}
        onRefresh={handleRefresh} data={data}
      />

      <main style={{
        marginLeft: sidebarWidth, flex: 1,
        padding: '28px 36px', minHeight: '100vh',
        overflowX: 'hidden',
      }}>

        {/* Error */}
        {error && (
          <div style={{
            marginBottom: 20, padding: '12px 16px',
            background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: 10, fontSize: 13, color: 'var(--accent-red)'
          }}>⚠ {error}</div>
        )}

        {/* Loading */}
        {loading && (
          <div style={{
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            height: '75vh', gap: 32,
          }}>
            {/* Animated logo */}
            <div style={{ position: 'relative', width: 80, height: 80 }}>
              <div style={{
                position: 'absolute', inset: 0, borderRadius: '50%',
                border: '2px solid rgba(59,130,246,0.15)',
              }} />
              <div style={{
                position: 'absolute', inset: 0, borderRadius: '50%',
                border: '2px solid transparent',
                borderTopColor: '#3b82f6',
                animation: 'spin 1s linear infinite',
              }} />
              <div style={{
                position: 'absolute', inset: 10, borderRadius: '50%',
                border: '2px solid transparent',
                borderTopColor: '#06b6d4',
                animation: 'spin 1.5s linear infinite reverse',
              }} />
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 24,
              }}>⚡</div>
            </div>

            {/* Step indicator */}
            <div style={{ textAlign: 'center', maxWidth: 400 }}>
              <p style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
                Running SECFAOS Pipeline
              </p>
              <p style={{ fontSize: 13, color: 'var(--accent-blue)', fontWeight: 600, marginBottom: 20 }}>
                {STEPS[step]}
              </p>

              {/* Progress bar */}
              <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, marginBottom: 16 }}>
                <div style={{
                  height: '100%', borderRadius: 2,
                  width: `${((step + 1) / STEPS.length) * 100}%`,
                  background: 'linear-gradient(90deg, #3b82f6, #06b6d4)',
                  transition: 'width 0.5s ease',
                  boxShadow: '0 0 8px rgba(59,130,246,0.6)',
                }} />
              </div>

              {/* Step dots */}
              <div style={{ display: 'flex', justifyContent: 'center', gap: 6 }}>
                {STEPS.map((_, i) => (
                  <div key={i} style={{
                    width: i === step ? 20 : 6, height: 6, borderRadius: 3,
                    background: i <= step ? '#3b82f6' : 'rgba(255,255,255,0.1)',
                    transition: 'all 0.3s ease',
                  }} />
                ))}
              </div>
            </div>

            <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Loading 11 meters · LSTM from disk · LP optimisation · Device scheduling
            </p>
          </div>
        )}

        {/* Empty state */}
        {!loading && !data && !error && (
          <div style={{
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            height: '75vh', gap: 20, textAlign: 'center',
            animation: 'fade-in 0.6s ease',
          }}>
            <div style={{
              width: 80, height: 80, borderRadius: 20,
              background: 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(6,182,212,0.1))',
              border: '1px solid rgba(59,130,246,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 36, boxShadow: 'var(--glow-blue)',
            }}>⚡</div>
            <div>
              <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 8, letterSpacing: '-0.5px' }}>
                SECFAOS Ready
              </h2>
              <p style={{ color: 'var(--text-secondary)', maxWidth: 420, lineHeight: 1.7, fontSize: 14 }}>
                Smart Energy Consumption Forecasting & Optimisation System
              </p>
              <p style={{ color: 'var(--text-muted)', maxWidth: 420, lineHeight: 1.7, fontSize: 13, marginTop: 6 }}>
                11 BSES Delhi meters · LSTM forecasting · LP optimisation · Device scheduling
              </p>
            </div>
            <button onClick={handleRun} style={{
              padding: '12px 32px',
              background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
              color: 'white', border: 'none', borderRadius: 12,
              fontWeight: 700, fontSize: 15, cursor: 'pointer',
              boxShadow: '0 4px 20px rgba(59,130,246,0.4)',
              transition: 'all 0.2s', marginTop: 8,
            }}>
              ▶ Run Pipeline
            </button>
          </div>
        )}

        {/* Page */}
        {!loading && data && (
          <div style={{ maxWidth: 1440, animation: 'slide-up 0.4s ease' }}>
            {renderPage()}
          </div>
        )}
      </main>
    </div>
  )
}