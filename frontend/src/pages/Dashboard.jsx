/**
 * Dashboard — Command center. Dense 12-column grid.
 * No hero banners, no gradient cards, no decorative elements.
 * Moneycontrol / NSE India information density.
 */
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis,
  ResponsiveContainer, ReferenceLine, Tooltip,
} from 'recharts'
import { useQuery } from '@tanstack/react-query'
import { radarAPI, marketAPI } from '../services/api'
import { useMarketOverview } from '../hooks/useMarketData'
import LoadingSpinner from '../components/common/LoadingSpinner'

/* ── Sparkline (tiny inline chart, no axes) ─────────────────────────── */
function Sparkline({ data = [], color = '#26A69A' }) {
  const pts = useMemo(() => {
    if (!data?.length) return Array.from({ length: 20 }, (_, i) => ({ v: 100 + Math.sin(i * 0.5) * 2 }))
    return data.slice(-20).map(d => ({ v: d.close ?? d.value ?? d }))
  }, [data])
  return (
    <ResponsiveContainer width={80} height={28}>
      <LineChart data={pts} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <Line type="monotone" dataKey="v" dot={false} stroke={color} strokeWidth={1.5} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

/* ── Index stat column ──────────────────────────────────────────────── */
function IndexColumn({ label, value, change, changePct, sparkData, isLast }) {
  const up = (changePct ?? change ?? 0) >= 0
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '0 16px',
      borderRight: isLast ? 'none' : '1px solid #2A2E39',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="label" style={{ marginBottom: '4px' }}>{label}</div>
        <div className="price" style={{ fontSize: '16px', color: '#D1D4DC', fontWeight: 500 }}>
          {typeof value === 'number' ? value.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '—'}
        </div>
        <div className={`price text-xs ${up ? 'bull' : 'bear'}`} style={{ marginTop: '2px' }}>
          {up ? '+' : ''}{typeof changePct === 'number' ? `${changePct.toFixed(2)}%` : '—'}
        </div>
      </div>
      <Sparkline color={up ? '#26A69A' : '#EF5350'} data={sparkData} />
    </div>
  )
}

/* ── Signal row in dashboard (compact, 36px) ────────────────────────── */
function DashSignalRow({ s }) {
  const dir = (s.direction || '').toUpperCase()
  const isBull = dir === 'BULLISH' || dir === 'BUY'
  const isBear = dir === 'BEARISH' || dir === 'SELL'
  const color = isBull ? '#26A69A' : isBear ? '#EF5350' : '#4C525E'
  const confidence = Math.round((s.confidence_score ?? 0) * 100)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      height: '36px', padding: '0 12px',
      borderBottom: '1px solid #1E222D',
    }}>
      <div style={{ width: '3px', height: '24px', borderRadius: '2px', background: color, flexShrink: 0 }} />
      <span className="price" style={{ fontSize: '12px', fontWeight: 600, color: '#D1D4DC', width: '64px' }}>
        {(s.symbol || '').replace('.NS', '')}
      </span>
      <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
        {s.signal_type?.replace(/_/g, ' ').toLowerCase()}
      </span>
      <span className={`price text-xs ${isBull ? 'bull' : isBear ? 'bear' : ''}`} style={{ marginLeft: 'auto' }}>
        {confidence}%
      </span>
    </div>
  )
}

/* ── Pattern row in dashboard ────────────────────────────────────────── */
function DashPatternRow({ p }) {
  const isBull = (p.direction || '').toUpperCase().includes('BULL')
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      height: '36px', padding: '0 12px',
      borderBottom: '1px solid #1E222D',
    }}>
      <span className="price" style={{ fontSize: '12px', fontWeight: 600, color: '#D1D4DC', width: '64px' }}>
        {(p.symbol || '').replace('.NS', '')}
      </span>
      <span style={{ flex: 1, fontSize: '12px', color: '#787B86', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {p.pattern_name?.replace(/_/g, ' ')}
      </span>
      <span className={isBull ? 'bull' : 'bear'} style={{ fontSize: '14px' }}>{isBull ? '▲' : '▼'}</span>
      <span className="price text-xs" style={{ color: '#4C525E', minWidth: '36px', textAlign: 'right' }}>
        {p.win_rate ? `${Math.round(p.win_rate)}%` : '—'}
      </span>
    </div>
  )
}

/* ── FII/DII Bar chart ───────────────────────────────────────────────── */
function FiiDiiChart({ data = [] }) {
  const fmt = v => (v >= 0 ? '+' : '') + (v / 100).toFixed(0) + ' Cr'
  return (
    <>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '6px', padding: '0 4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#26A69A' }} />
          <span className="text-xs" style={{ color: '#787B86' }}>FII Net</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#2962FF' }} />
          <span className="text-xs" style={{ color: '#787B86' }}>DII Net</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={100}>
        <BarChart data={data.slice(-7)} barSize={10} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#4C525E' }} tickLine={false} axisLine={false}
            tickFormatter={d => d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }).slice(0, 6) : ''} />
          <YAxis hide />
          <Tooltip
            contentStyle={{ background: '#1E222D', border: '1px solid #2A2E39', borderRadius: '4px', fontSize: '11px' }}
            labelStyle={{ color: '#787B86' }}
            formatter={(v) => [`₹${fmt(v)}`, '']}
          />
          <ReferenceLine y={0} stroke="#2A2E39" />
          <Bar dataKey="fii_net" fill="#26A69A" radius={[2, 2, 0, 0]} />
          <Bar dataKey="dii_net" fill="#2962FF" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </>
  )
}

/* ── Gainers / Losers table ─────────────────────────────────────────── */
function GainerLoserTable({ items = [], isGainer }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid #2A2E39' }}>
          {['SYMBOL', 'LTP', 'CHG%'].map(h => (
            <th key={h} className="label" style={{ padding: '0 8px', height: '28px', textAlign: h === 'CHG%' ? 'right' : 'left' }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {items.slice(0, 5).map((item, i) => (
          <tr key={i} style={{ height: '32px', borderBottom: '1px solid #1E222D' }}>
            <td className="price" style={{ padding: '0 8px', fontWeight: 600, color: '#D1D4DC' }}>
              {(item.symbol || item.ticker || '').replace('.NS', '')}
            </td>
            <td className="price" style={{ padding: '0 8px', color: '#D1D4DC' }}>
              ₹{(item.price || item.close || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </td>
            <td className={`price ${isGainer ? 'bull' : 'bear'}`} style={{ padding: '0 8px', textAlign: 'right' }}>
              {isGainer ? '+' : ''}{(item.change_pct || item.pct_change || 0).toFixed(2)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/* ── IPO row ─────────────────────────────────────────────────────────── */
function IpoRow({ ipo }) {
  const cls = ipo.status === 'OPEN' ? 'badge-open' : ipo.status === 'UPCOMING' ? 'badge-upcoming' : 'badge-closed'
  return (
    <div style={{ padding: '8px 12px', borderBottom: '1px solid #1E222D' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
        <span style={{ fontSize: '12px', color: '#D1D4DC', fontWeight: 500 }}>{ipo.company}</span>
        <span className={`badge ${cls}`}>{ipo.status}</span>
      </div>
      <div style={{ display: 'flex', gap: '12px' }}>
        <span className="text-xs" style={{ color: '#787B86' }}>{ipo.date_range || ipo.open_date}</span>
        {ipo.price_band && (
          <span className="price text-xs" style={{ color: '#787B86' }}>₹{ipo.price_band}</span>
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════
   MAIN DASHBOARD
   ═══════════════════════════════════════════════════════════════════════ */
export default function Dashboard() {
  const { data: market, isLoading: mktLoading } = useMarketOverview()
  const { data: signals, isLoading: sigLoading } = useQuery({
    queryKey: ['radar', 'signals', 'dashboard'],
    queryFn: () => radarAPI.signals({ limit: 5 }),
    staleTime: 60_000,
  })
  const { data: fiiData } = useQuery({
    queryKey: ['fii-dii'],
    queryFn: radarAPI.fiiDii,
    staleTime: 5 * 60_000,
  })
  const { data: ipoData } = useQuery({
    queryKey: ['ipos-dashboard'],
    queryFn: marketAPI.ipos,
    staleTime: 10 * 60_000,
  })

  const nifty  = market?.nifty50  || {}
  const sensex = market?.sensex   || {}
  const gainers = market?.top_gainers || []
  const losers  = market?.top_losers  || []
  const signalList = Array.isArray(signals) ? signals : signals?.signals || []
  // mock patterns for dashboard
  const patterns = [
    { symbol: 'HDFCBANK.NS', pattern_name: 'GOLDEN_CROSS', direction: 'BULLISH', win_rate: 72 },
    { symbol: 'INFY.NS', pattern_name: 'RSI_OVERSOLD', direction: 'BULLISH', win_rate: 65 },
    { symbol: 'ICICIBANK.NS', pattern_name: 'MACD_CROSSOVER', direction: 'BULLISH', win_rate: 68 },
    { symbol: 'TATAMOTORS.NS', pattern_name: 'BEARISH_ENGULFING', direction: 'BEARISH', win_rate: 61 },
    { symbol: 'SUNPHARMA.NS', pattern_name: 'DOUBLE_BOTTOM', direction: 'BULLISH', win_rate: 70 },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'auto', background: '#131722' }}>

      {/* ── ROW 1: Index bar (52px) ──────────────────────────────────── */}
      <div style={{
        display: 'flex',
        height: '52px',
        background: '#1E222D',
        borderBottom: '1px solid #2A2E39',
        flexShrink: 0,
      }}>
        {mktLoading ? (
          <div style={{ display: 'flex', alignItems: 'center', padding: '0 16px' }}>
            <LoadingSpinner size={14} />
          </div>
        ) : (
          <>
            <IndexColumn label="NIFTY 50" value={nifty.level ?? 22456.80} changePct={nifty.change_pct ?? 0.34} />
            <IndexColumn label="SENSEX" value={sensex.level ?? 73847.15} changePct={sensex.change_pct ?? 0.28} />
            <IndexColumn label="BANK NIFTY" value={48234.50} changePct={-0.12} />
            <IndexColumn label="INDIA VIX" value={13.45} changePct={2.1} isLast />
          </>
        )}
      </div>

      {/* ── ROW 2: Three-column grid ──────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0, borderBottom: '1px solid #2A2E39', flexShrink: 0 }}>

        {/* Signals column */}
        <div style={{ borderRight: '1px solid #2A2E39' }}>
          <div className="panel-header">
            <span className="label">Opportunity Radar</span>
            <Link to="/radar" className="btn-ghost" style={{ fontSize: '11px' }}>View All →</Link>
          </div>
          {sigLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '20px' }}><LoadingSpinner size={14} /></div>
          ) : signalList.length > 0 ? (
            signalList.slice(0, 5).map((s, i) => <DashSignalRow key={i} s={s} />)
          ) : (
            <div style={{ padding: '12px', fontSize: '12px', color: '#4C525E' }}>No signals</div>
          )}
        </div>

        {/* Patterns column */}
        <div style={{ borderRight: '1px solid #2A2E39' }}>
          <div className="panel-header">
            <span className="label">Chart Patterns</span>
            <Link to="/charts" className="btn-ghost" style={{ fontSize: '11px' }}>View All →</Link>
          </div>
          {patterns.map((p, i) => <DashPatternRow key={i} p={p} />)}
        </div>

        {/* FII/DII column */}
        <div>
          <div className="panel-header">
            <span className="label">FII / DII Net Flows</span>
          </div>
          <div style={{ padding: '12px' }}>
            <FiiDiiChart data={Array.isArray(fiiData) ? fiiData : fiiData?.flows || []} />
          </div>
        </div>
      </div>

      {/* ── ROW 3: Breadth table + IPO tracker ───────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 0, flex: 1, minHeight: 0 }}>

        {/* Market breadth — gainers + losers side by side */}
        <div style={{ borderRight: '1px solid #2A2E39', overflow: 'auto' }}>
          <div className="panel-header">
            <span className="label">Market Breadth</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
            <div style={{ borderRight: '1px solid #2A2E39' }}>
              <div style={{ padding: '6px 8px 4px' }}>
                <span className="label" style={{ color: '#26A69A' }}>Top Gainers</span>
              </div>
              <GainerLoserTable items={gainers} isGainer />
            </div>
            <div>
              <div style={{ padding: '6px 8px 4px' }}>
                <span className="label" style={{ color: '#EF5350' }}>Top Losers</span>
              </div>
              <GainerLoserTable items={losers} isGainer={false} />
            </div>
          </div>
        </div>

        {/* IPO pipeline */}
        <div style={{ overflow: 'auto' }}>
          <div className="panel-header">
            <span className="label">IPO Pipeline</span>
          </div>
          {Array.isArray(ipoData) && ipoData.length > 0 ? (
            ipoData.slice(0, 4).map((ipo, i) => <IpoRow key={i} ipo={ipo} />)
          ) : (
            [
              { company: 'Bajaj Housing Finance', status: 'OPEN', date_range: 'Mar 19–21', price_band: '66–70' },
              { company: 'NTPC Green Energy', status: 'UPCOMING', date_range: 'Mar 25–27', price_band: '102–108' },
              { company: 'KRN Heat Exchanger', status: 'CLOSED', date_range: 'Mar 10–12', price_band: '209' },
            ].map((ipo, i) => <IpoRow key={i} ipo={ipo} />)
          )}
        </div>
      </div>
    </div>
  )
}
