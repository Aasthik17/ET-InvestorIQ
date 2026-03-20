import React, { useState, useEffect } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell
} from 'recharts'
import { useDashboardData } from '../hooks/useMarketData'
import {
  formatIndianNumber, formatPrice, formatPct, formatCrores,
  formatVolume, formatShortDate
} from '../utils/formatters'

// ─── Skeleton ────────────────────────────────────────────────────────────────

function Skeleton({ w = '100%', h = 16, className = '' }) {
  return (
    <div className={`skeleton ${className}`}
         style={{ width: w, height: h, borderRadius: 2 }} />
  )
}

// ─── WebSocket status dot ────────────────────────────────────────────────────

function WsDot({ status }) {
  const color = status === 'open'
    ? '#26A69A'
    : status === 'connecting'
    ? '#F2A900'
    : '#EF5350'
  const label = status === 'open' ? 'Live' : status === 'connecting' ? 'Connecting…' : 'Offline'
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: color,
        display: 'inline-block',
        boxShadow: status === 'open' ? `0 0 4px ${color}` : 'none',
      }} />
      <span style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
        {label}
      </span>
    </span>
  )
}

// ─── Index Cell ──────────────────────────────────────────────────────────────

function IndexCell({ data, loading }) {
  if (loading || !data) {
    return (
      <div style={{ minWidth: 140, padding: '0 16px' }}>
        <Skeleton w={60} h={10} />
        <div style={{ marginTop: 4 }}><Skeleton w={90} h={16} /></div>
        <div style={{ marginTop: 4 }}><Skeleton w={50} h={10} /></div>
      </div>
    )
  }

  const pct = formatPct(data.change_pct)
  const isUp = (data.change_pct || 0) >= 0
  const sparkColor = isUp ? '#26A69A' : '#EF5350'
  const sparkData = (data.sparkline || []).map((v, i) => ({ i, v }))

  return (
    <div style={{
      minWidth: 140, padding: '0 16px',
      borderRight: '1px solid var(--border-primary)',
    }}>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 2 }}>
        {data.name}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span className="price" style={{ fontSize: 15, color: 'var(--text-primary)', fontWeight: 500 }}>
          {formatIndianNumber(data.value, 2)}
        </span>
        <span className={`price ${pct.cls}`} style={{ fontSize: 11 }}>
          {pct.text}
        </span>
      </div>
      {sparkData.length > 2 && (
        <LineChart width={100} height={22} data={sparkData} style={{ marginTop: 2 }}>
          <Line type="monotone" dataKey="v" stroke={sparkColor}
                strokeWidth={1} dot={false} isAnimationActive={false} />
        </LineChart>
      )}
    </div>
  )
}

// ─── Market Status Pill ──────────────────────────────────────────────────────

function MarketStatusPill({ status }) {
  const isOpen = status?.is_open
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '2px 8px', borderRadius: 2,
      background: isOpen ? 'rgba(38,166,154,0.12)' : 'rgba(239,83,80,0.10)',
      border: `1px solid ${isOpen ? 'rgba(38,166,154,0.3)' : 'rgba(239,83,80,0.2)'}`,
      fontSize: 10, letterSpacing: '0.06em',
    }}>
      <span style={{
        width: 5, height: 5, borderRadius: '50%',
        background: isOpen ? '#26A69A' : '#EF5350',
        animation: isOpen ? 'pulse 2s ease-in-out infinite' : 'none',
      }} />
      <span style={{ color: isOpen ? '#26A69A' : '#EF5350', fontWeight: 500 }}>
        NSE {isOpen ? 'Open' : 'Closed'}
      </span>
    </span>
  )
}

// ─── FII/DII Bar Chart ───────────────────────────────────────────────────────

const FII_TOOLTIP = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="card" style={{ padding: '8px 12px', fontSize: 11, minWidth: 160 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{d.date}</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
        <span>FII Net</span>
        <span className={d.fii_net >= 0 ? 'text-bull' : 'text-bear'}>
          {formatCrores(d.fii_net)}
        </span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginTop: 2 }}>
        <span>DII Net</span>
        <span style={{ color: '#2962FF' }}>
          {formatCrores(d.dii_net)}
        </span>
      </div>
    </div>
  )
}

function FiiDiiChart({ data, loading }) {
  if (loading) return <Skeleton w="100%" h={120} />
  if (!data?.length) return <div style={{ height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 11 }}>No FII/DII data</div>

  const slice = [...data].reverse().slice(-7).map(d => ({
    date:    d.date,
    fii_net: parseFloat(d.fii_net || 0),
    dii_net: parseFloat(d.dii_net || 0),
  }))

  return (
    <ResponsiveContainer width="100%" height={120}>
      <BarChart data={slice} barSize={8} barGap={2} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#787B86' }} tickFormatter={formatShortDate} axisLine={false} tickLine={false} />
        <YAxis hide />
        <Tooltip content={<FII_TOOLTIP />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <ReferenceLine y={0} stroke="#2A2E39" strokeWidth={1} />
        <Bar dataKey="fii_net" name="FII Net" radius={[1, 1, 0, 0]}>
          {slice.map((d, i) => (
            <Cell key={i} fill={d.fii_net >= 0 ? '#26A69A' : '#EF5350'} />
          ))}
        </Bar>
        <Bar dataKey="dii_net" name="DII Net" fill="#2962FF" radius={[1, 1, 0, 0]} fillOpacity={0.7} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── Signal Row (mock data for signals section) ──────────────────────────────

function MoverRow({ item, type }) {
  const isGainer = type === 'gainer'
  const pct = formatPct(item.change_pct)
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr auto auto',
      alignItems: 'center', padding: '5px 0',
      borderBottom: '1px solid var(--border-primary)',
      gap: 8,
    }}>
      <div>
        <span className="price" style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
          {item.symbol}
        </span>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 120 }}>
          {item.company || item.symbol}
        </div>
      </div>
      <span className="price" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
        {formatPrice(item.ltp)}
      </span>
      <span className={`price ${pct.cls}`} style={{ fontSize: 12, textAlign: 'right', minWidth: 52 }}>
        {pct.text}
      </span>
    </div>
  )
}

// ─── IPO Row ──────────────────────────────────────────────────────────────────

function IpoRow({ ipo, type }) {
  const isListed = type === 'listed'
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: isListed ? '2fr 1fr 1fr 1fr' : '2fr 1fr 1fr',
      padding: '5px 0',
      borderBottom: '1px solid var(--border-primary)',
      alignItems: 'center',
      gap: 8,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-primary)', fontWeight: 500,
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {ipo.company}
      </div>
      <div className="price" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
        {ipo.issue_price ? `₹${ipo.issue_price}` : '—'}
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
        {isListed ? ipo.listing_date : ipo.close_date}
      </div>
      {isListed && (
        <div className={`price ${ipo.listing_gain_pct >= 0 ? 'text-bull' : 'text-bear'}`}
             style={{ fontSize: 11, textAlign: 'right' }}>
          {ipo.listing_gain_pct != null ? `${ipo.listing_gain_pct > 0 ? '+' : ''}${ipo.listing_gain_pct}%` : '—'}
        </div>
      )}
    </div>
  )
}

// ─── Refresh label ───────────────────────────────────────────────────────────

function useRelativeTime(ts) {
  const [label, setLabel] = useState('')
  useEffect(() => {
    function update() {
      if (!ts) return setLabel('')
      const diff = Math.floor((Date.now() - ts) / 1000)
      if (diff < 10)   setLabel('Updated just now')
      else if (diff < 60) setLabel(`Updated ${diff}s ago`)
      else             setLabel(`Updated ${Math.floor(diff / 60)}m ago`)
    }
    update()
    const id = setInterval(update, 10_000)
    return () => clearInterval(id)
  }, [ts])
  return label
}

// ─── MAIN Dashboard ───────────────────────────────────────────────────────────

export default function Dashboard() {
  const {
    indices, movers, fiiDii, sectors, ipos,
    breadth, marketStatus, wsStatus, isLoading, lastUpdated,
  } = useDashboardData()

  const relTime = useRelativeTime(lastUpdated)
  const [activeIpoTab, setActiveIpoTab] = useState('current')   // current | upcoming | listed

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Row 0: Sub-header with status ──────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 16px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-primary)',
        flexShrink: 0, gap: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <MarketStatusPill status={marketStatus} />
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{relTime}</span>
        </div>
        <WsDot status={wsStatus} />
      </div>

      {/* ── Row 1: Index Bar ────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'flex-start', flexShrink: 0,
        padding: '8px 0',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-primary)',
        overflowX: 'auto',
      }}>
        {['nifty50', 'sensex', 'banknifty', 'vix'].map(k => (
          <IndexCell key={k} data={indices?.[k]} loading={isLoading && !indices} />
        ))}

        {/* Breadth pill */}
        {breadth && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '0 16px', marginLeft: 'auto',
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Adv/Dec</div>
              <div style={{ fontSize: 13, fontWeight: 500, marginTop: 2 }}>
                <span className="text-bull">{breadth.advances}</span>
                <span style={{ color: 'var(--text-muted)' }}> / </span>
                <span className="text-bear">{breadth.declines}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Main content grid ───────────────────────────────────────────────── */}
      <div style={{
        flex: 1, overflow: 'auto',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gridTemplateRows: 'auto auto',
        gap: 0,
        alignContent: 'start',
      }}>

        {/* Col 1: Top Gainers */}
        <div style={{ borderRight: '1px solid var(--border-primary)', borderBottom: '1px solid var(--border-primary)', padding: '0 0 8px' }}>
          <div style={{ padding: '8px 12px 6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Top Gainers</span>
          </div>
          <div style={{ padding: '0 12px' }}>
            {isLoading && !movers.gainers?.length
              ? Array(5).fill(0).map((_, i) => <Skeleton key={i} h={36} className="mb-1" />)
              : (movers.gainers || []).slice(0, 8).map(s => (
                  <MoverRow key={s.symbol} item={s} type="gainer" />
                ))
            }
          </div>
        </div>

        {/* Col 2: Top Losers */}
        <div style={{ borderRight: '1px solid var(--border-primary)', borderBottom: '1px solid var(--border-primary)', padding: '0 0 8px' }}>
          <div style={{ padding: '8px 12px 6px' }}>
            <span className="label">Top Losers</span>
          </div>
          <div style={{ padding: '0 12px' }}>
            {isLoading && !movers.losers?.length
              ? Array(5).fill(0).map((_, i) => <Skeleton key={i} h={36} className="mb-1" />)
              : (movers.losers || []).slice(0, 8).map(s => (
                  <MoverRow key={s.symbol} item={s} type="loser" />
                ))
            }
          </div>
        </div>

        {/* Col 3: Sector Performance */}
        <div style={{ borderBottom: '1px solid var(--border-primary)', padding: '0 0 8px' }}>
          <div style={{ padding: '8px 12px 6px' }}>
            <span className="label">Sector Performance (1D)</span>
          </div>
          <div style={{ padding: '0 12px' }}>
            {(sectors || []).slice(0, 9).map(s => {
              const pct = formatPct(s.return_1d_pct)
              return (
                <div key={s.sector} style={{
                  display: 'grid', gridTemplateColumns: '1fr 56px 56px',
                  padding: '4px 0', borderBottom: '1px solid var(--border-primary)',
                  alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 11, color: 'var(--text-primary)' }}>{s.sector}</span>
                  <span className={`price ${pct.cls}`} style={{ fontSize: 11, textAlign: 'right' }}>{pct.text}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'right' }}>
                    {formatPct(s.return_1m_pct).text}
                  </span>
                </div>
              )
            })}
            {(!sectors || !sectors.length) && isLoading && Array(9).fill(0).map((_, i) => <Skeleton key={i} h={26} className="mb-1" />)}
          </div>
          <div style={{ padding: '4px 12px 0' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 56px 56px', padding: '0', gap: 4 }}>
              <span style={{ fontSize: 9, color: 'var(--text-muted)' }}></span>
              <span style={{ fontSize: 9, color: 'var(--text-muted)', textAlign: 'right' }}>1D</span>
              <span style={{ fontSize: 9, color: 'var(--text-muted)', textAlign: 'right' }}>1M</span>
            </div>
          </div>
        </div>

        {/* Bottom Col 1+2: FII/DII Chart */}
        <div style={{
          gridColumn: '1 / 3',
          borderRight: '1px solid var(--border-primary)',
          padding: '0 0 8px',
        }}>
          <div style={{ padding: '8px 12px 6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">FII / DII Flow (7D net · ₹ Cr)</span>
            <div style={{ display: 'flex', gap: 12, fontSize: 10, color: 'var(--text-muted)' }}>
              <span>
                <span style={{ display: 'inline-block', width: 8, height: 8, background: '#26A69A', borderRadius: 1, marginRight: 4 }} />
                FII
              </span>
              <span>
                <span style={{ display: 'inline-block', width: 8, height: 8, background: '#2962FF', borderRadius: 1, marginRight: 4, opacity: 0.7 }} />
                DII
              </span>
            </div>
          </div>
          <div style={{ padding: '0 12px' }}>
            <FiiDiiChart data={fiiDii} loading={isLoading && !fiiDii?.length} />
          </div>
        </div>

        {/* Bottom Col 3: IPO Pipeline */}
        <div style={{ padding: '0 0 8px' }}>
          <div style={{ padding: '8px 12px 6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">IPO Pipeline</span>
            <div style={{ display: 'flex', gap: 0 }}>
              {['current', 'upcoming', 'listed'].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveIpoTab(tab)}
                  style={{
                    padding: '1px 8px', fontSize: 9, border: 'none',
                    background: activeIpoTab === tab ? 'var(--bg-tertiary)' : 'transparent',
                    color: activeIpoTab === tab ? 'var(--text-primary)' : 'var(--text-muted)',
                    cursor: 'pointer', textTransform: 'uppercase', letterSpacing: '0.04em',
                    borderRadius: 2,
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
          <div style={{ padding: '0 12px' }}>
            {/* Column headers */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: activeIpoTab === 'listed' ? '2fr 1fr 1fr 1fr' : '2fr 1fr 1fr',
              marginBottom: 4, gap: 8,
            }}>
              <span style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Company</span>
              <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>Price</span>
              <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{activeIpoTab === 'listed' ? 'Listed' : 'Closes'}</span>
              {activeIpoTab === 'listed' && <span style={{ fontSize: 9, color: 'var(--text-muted)', textAlign: 'right' }}>Gain</span>}
            </div>
            {(ipos?.[activeIpoTab] || []).map((ipo, i) => (
              <IpoRow key={i} ipo={ipo} type={activeIpoTab} />
            ))}
            {(!ipos?.[activeIpoTab]?.length) && !isLoading && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '16px 0', textAlign: 'center' }}>
                No {activeIpoTab} IPOs
              </div>
            )}
            {isLoading && Array(3).fill(0).map((_, i) => <Skeleton key={i} h={28} className="mb-1" />)}
          </div>
        </div>

      </div>

      {/* Pulse animation keyframe (inline) */}
      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .mb-1 { margin-bottom: 4px; }
      `}</style>
    </div>
  )
}
