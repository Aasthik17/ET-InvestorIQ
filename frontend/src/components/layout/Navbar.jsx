/**
 * Navbar — 48px top bar with index ticker and market status.
 * TradingView/Kite style: dense, informational, no decoration.
 */
import { Settings } from 'lucide-react'
import Logo from './Logo'
import { useDashboardData } from '../../hooks/useMarketData'

function isMarketOpen() {
  const now = new Date()
  // Convert to IST (UTC+5:30)
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }))
  const day = ist.getDay()   // 0 = Sun, 6 = Sat
  const h = ist.getHours()
  const m = ist.getMinutes()
  const mins = h * 60 + m
  if (day === 0 || day === 6) return false
  return mins >= 555 && mins < 930  // 9:15 AM – 3:30 PM IST
}

function IndexPill({ name, value, changePct }) {
  const up = changePct >= 0
  return (
    <div className="index-pill">
      <span className="text-xs" style={{ color: '#787B86', fontFamily: 'Inter' }}>{name}</span>
      <span className="price" style={{ fontSize: '12px', color: '#D1D4DC' }}>
        {typeof value === 'number' ? value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
      </span>
      {changePct !== undefined && (
        <span className={`price text-xs ${up ? 'bull' : 'bear'}`}>
          {up ? '+' : ''}{changePct.toFixed(2)}%
        </span>
      )}
    </div>
  )
}

export default function Navbar() {
  const { indices: market, marketStatus } = useDashboardData()
  const open = marketStatus?.is_open ?? isMarketOpen()

  const nifty   = market?.nifty50    || {}
  const sensex  = market?.sensex     || {}
  const bankNifty = market?.banknifty || {}
  const vix       = market?.vix      || {}

  return (
    <header style={{
      height: '48px',
      background: '#1E222D',
      borderBottom: '1px solid #2A2E39',
      display: 'flex',
      alignItems: 'center',
      flexShrink: 0,
      zIndex: 20,
    }}>
      {/* Logo — left-aligned, 220px to align with sidebar */}
      <div style={{ width: '220px', minWidth: '220px', padding: '0 16px', display: 'flex', alignItems: 'center' }}>
        <Logo />
      </div>

      {/* Index ticker tape — center */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'stretch',
        height: '100%',
        borderLeft: '1px solid #2A2E39',
        overflow: 'hidden',
      }}>
        <IndexPill
          name="NIFTY 50"
          value={nifty?.level}
          changePct={nifty?.change_pct}
        />
        <IndexPill
          name="SENSEX"
          value={sensex?.level ?? 73847.15}
          changePct={sensex?.change_pct ?? 0.28}
        />
        <IndexPill
          name="BANK NIFTY"
          value={bankNifty?.level ?? 48234.50}
          changePct={bankNifty?.change_pct ?? -0.12}
        />
        <IndexPill
          name="INDIA VIX"
          value={vix ?? 13.45}
          changePct={vix != null ? 0 : undefined}
        />
      </div>

      {/* Right — status + settings */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '0 16px',
        borderLeft: '1px solid #2A2E39',
        height: '100%',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: open ? '#26A69A' : '#EF5350',
            boxShadow: open ? '0 0 4px #26A69A' : 'none',
          }} />
          <span className="text-xs" style={{ color: '#787B86', whiteSpace: 'nowrap' }}>
            NSE {open ? 'Open' : 'Closed'}
          </span>
        </div>
        <div className="divider-v" />
        <button
          aria-label="Settings"
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: '#4C525E', lineHeight: 0 }}
        >
          <Settings size={15} />
        </button>
      </div>
    </header>
  )
}
