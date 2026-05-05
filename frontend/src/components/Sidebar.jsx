import { useState } from 'react'
import {
  BarChart2, Zap, Brain, TrendingUp, Settings,
  Activity, Cpu, ChevronLeft, ChevronRight, DollarSign, RefreshCw
} from 'lucide-react'

const nav = [
  { id: 'overview',     label: 'Overview',        icon: BarChart2,  desc: 'System summary'    },
  { id: 'forecast',     label: 'Forecast',         icon: TrendingUp, desc: '24h prediction'    },
  { id: 'optimization', label: 'Optimization',     icon: Settings,   desc: 'LP scheduling'     },
  { id: 'devices',      label: 'Devices',          icon: Cpu,        desc: 'Appliance timing'  },
  { id: 'models',       label: 'Models',           icon: Brain,      desc: 'LSTM vs SARIMA'    },
  { id: 'analysis',     label: 'EDA',              icon: Activity,   desc: 'Data analysis'     },
  { id: 'impact',       label: 'Impact',           icon: DollarSign, desc: 'Cost & carbon'     },
]

export default function Sidebar({ page, setPage, loading, onRun, onRefresh, data }) {
  const [collapsed, setCollapsed] = useState(false)
  const W = collapsed ? 64 : 220

  return (
    <aside style={{
      width: W, background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border)',
      transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1)',
      position: 'fixed', left: 0, top: 0, height: '100%',
      display: 'flex', flexDirection: 'column', zIndex: 100,
      overflow: 'hidden',
    }}>

      {/* Logo */}
      <div style={{
        padding: collapsed ? '18px 0' : '18px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        minHeight: 72,
      }}>
        {!collapsed && (
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
              <div style={{
                width: 28, height: 28, borderRadius: 8,
                background: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <Zap size={16} color="white" />
              </div>
              <span style={{ fontWeight: 800, fontSize: 15, color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
                SECFAOS
              </span>
            </div>
            <p style={{ fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.5, paddingLeft: 36 }}>
              Smart Energy Consumption<br />Forecasting & Optimisation
            </p>
          </div>
        )}
        {collapsed && (
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Zap size={18} color="white" />
          </div>
        )}
        <button onClick={() => setCollapsed(!collapsed)} style={{
          background: 'var(--bg-hover)', border: '1px solid var(--border)',
          borderRadius: 6, padding: '4px 5px', cursor: 'pointer',
          color: 'var(--text-muted)', display: 'flex', alignItems: 'center',
          flexShrink: 0, marginLeft: collapsed ? 0 : 6,
        }}>
          {collapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
        </button>
      </div>

      {/* Buttons */}
      <div style={{ padding: collapsed ? '10px 8px' : '10px 12px', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
        <button onClick={onRun} disabled={loading} title="Run Pipeline" style={{
          width: '100%', padding: collapsed ? '9px 0' : '9px 12px',
          background: loading
            ? 'var(--border)'
            : 'linear-gradient(135deg, #3b82f6, #2563eb)',
          color: 'white', border: 'none', borderRadius: 9,
          fontSize: 12, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          boxShadow: loading ? 'none' : '0 4px 12px rgba(59,130,246,0.35)',
          transition: 'all 0.2s',
        }}>
          {loading
            ? <div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', animation: 'spin 0.8s linear infinite' }} />
            : <span>▶</span>
          }
          {!collapsed && (loading ? 'Running...' : 'Run Pipeline')}
        </button>

        {!collapsed && data && (
          <button onClick={onRefresh} title="Force refresh" style={{
            width: '100%', padding: '7px 12px',
            background: 'transparent', color: 'var(--text-muted)',
            border: '1px solid var(--border)', borderRadius: 9,
            fontSize: 11, fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}>
            <RefreshCw size={12} /> Refresh Data
          </button>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '8px', overflowY: 'auto', overflowX: 'hidden' }}>
        {nav.map(({ id, label, icon: Icon, desc }) => {
          const active = page === id
          return (
            <button key={id} onClick={() => setPage(id)} title={collapsed ? label : ''} style={{
              width: '100%',
              display: 'flex', alignItems: 'center',
              gap: collapsed ? 0 : 10,
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: collapsed ? '11px 0' : '10px 12px',
              marginBottom: 2,
              background: active
                ? 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(6,182,212,0.08))'
                : 'transparent',
              border: 'none',
              borderLeft: active ? '2px solid var(--accent-blue)' : '2px solid transparent',
              borderRadius: active ? '0 10px 10px 0' : '10px',
              cursor: 'pointer',
              color: active ? 'var(--accent-blue)' : 'var(--text-muted)',
              fontSize: 13, fontWeight: active ? 700 : 400,
              transition: 'all 0.15s', textAlign: 'left',
              whiteSpace: 'nowrap',
            }}>
              <Icon size={16} style={{ flexShrink: 0, opacity: active ? 1 : 0.7 }} />
              {!collapsed && (
                <div>
                  <div>{label}</div>
                  {!active && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>{desc}</div>}
                </div>
              )}
            </button>
          )
        })}
      </nav>

      {/* Status footer */}
      {data && !collapsed && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--accent-green)', boxShadow: '0 0 6px #10b981' }} />
            <span style={{ color: 'var(--accent-green)', fontWeight: 700, fontSize: 11 }}>Pipeline OK</span>
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 10, lineHeight: 1.7 }}>
            <div>{data.dataset.meters_loaded} meters · {data.dataset.total_records.toLocaleString()} records</div>
            <div>Model: <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>{data.selected_model}</span></div>
            <div>MAE: <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>{data.models.find(m => m.selected)?.mae}</span></div>
          </div>
        </div>
      )}
    </aside>
  )
}