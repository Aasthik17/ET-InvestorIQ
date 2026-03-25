import React, { useState, useMemo } from 'react'
import { ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import {
  useRadarData, useInsiderTrades, useBulkDeals, useFilings
} from '../hooks/useMarketData'
import AgentTracePanel from '../components/agent/AgentTracePanel'
import {
  formatPrice, formatCrores, formatPct, formatRelativeTime,
  formatIndianNumber, formatShortDate
} from '../utils/formatters'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SIGNAL_TYPE_COLORS = {
  INSIDER:   { bg: 'rgba(233,69,96,0.15)',   border: '#E94560', text: '#E94560' },
  FILING:    { bg: 'rgba(41,98,255,0.12)',   border: '#2962FF', text: '#2962FF' },
  TECHNICAL: { bg: 'rgba(249,168,37,0.12)', border: '#F9A825', text: '#F9A825' },
  FII:       { bg: 'rgba(38,166,154,0.12)', border: '#26A69A', text: '#26A69A' },
  CORPORATE: { bg: 'rgba(120,123,134,0.15)', border: '#787B86', text: '#787B86' },
}

const FILING_CATEGORY_COLORS = {
  'Financial Results':  { bg: 'rgba(38,166,154,0.13)', color: '#26A69A' },
  'Insider Trading':    { bg: 'rgba(233,69,96,0.13)',  color: '#E94560' },
  'Board Meeting':      { bg: 'rgba(41,98,255,0.12)',  color: '#2962FF' },
  'Acquisition':        { bg: 'rgba(38,166,154,0.10)', color: '#26A69A' },
  'Resignation':        { bg: 'rgba(239,83,80,0.12)',  color: '#EF5350' },
  'Regulatory':         { bg: 'rgba(249,168,37,0.10)', color: '#F9A825' },
}

const KNOWN_FII = ['mirae', 'sbi mutual', 'hdfc mutual', 'nippon', 'axis mutual', 'franklin', 'icici prudential', 'dsp', 'kotak', 'aditya birla']

function isFII(name = '') {
  const lower = name.toLowerCase()
  return KNOWN_FII.some(f => lower.includes(f))
}

function Skeleton({ h = 32, className = '' }) {
  return <div className={`skeleton ${className}`} style={{ height: h, borderRadius: 2, marginBottom: 4 }} />
}

function Badge({ label, style }) {
  return (
    <span style={{
      fontSize: 9, letterSpacing: '0.06em', textTransform: 'uppercase',
      padding: '1px 5px', borderRadius: 2, fontWeight: 600,
      border: '1px solid', ...style,
    }}>
      {label}
    </span>
  )
}

function DirectionBadge({ dir }) {
  const color = dir === 'BUY' || dir === 'BULLISH' ? '#26A69A'
              : dir === 'SELL' || dir === 'BEARISH' ? '#EF5350' : '#787B86'
  return <Badge label={dir} style={{ color, borderColor: color + '66', background: color + '14' }} />
}

// ─── Stats Bar ────────────────────────────────────────────────────────────────

function StatsBar({ radarData, onToggleAgent }) {
  const signals = radarData?.signals || []
  const total   = radarData?.total   || signals.length
  const bullish = signals.filter(s => (s.expected_impact || '').toUpperCase() === 'BULLISH').length
  const bearish = signals.filter(s => (s.expected_impact || '').toUpperCase() === 'BEARISH').length
  const actionable = signals.filter(s => (s.confidence_score || 0) > 0.6).length
  const age = radarData?.generated_at ? formatRelativeTime(radarData.generated_at) : ''

  return (
    <div style={{
      display: 'flex', gap: 24, padding: '8px 16px',
      borderBottom: '1px solid var(--border-primary)',
      background: 'var(--bg-secondary)', flexShrink: 0,
      alignItems: 'center', flexWrap: 'wrap',
    }}>
      <StatItem label="Signals" value={total} />
      <StatItem label="Actionable" value={actionable} color="#26A69A" />
      <StatItem label="Bullish" value={bullish} color="#26A69A" />
      <StatItem label="Bearish" value={bearish} color="#EF5350" />
      {age && (
        <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          Refreshed {age}
        </span>
      )}
      <button
        onClick={onToggleAgent}
        style={{
          height: 32,
          background: '#2962FF',
          color: '#D1D4DC',
          borderRadius: 4,
          fontSize: 12,
          padding: '0 16px',
          fontWeight: 500,
          cursor: 'pointer',
          border: 'none',
        }}
      >
        ▶ Run Agent
      </button>
    </div>
  )
}

function StatItem({ label, value, color }) {
  return (
    <div>
      <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: color || 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
        {value ?? '—'}
      </div>
    </div>
  )
}

// ─── Signal row (for All Signals tab) ────────────────────────────────────────

function SignalRow({ signal }) {
  const [expanded, setExpanded] = useState(false)
  const direction = (signal.expected_impact || '').toUpperCase()
  const borderColor = direction === 'BULLISH' ? '#26A69A'
                    : direction === 'BEARISH' ? '#EF5350' : '#787B86'
  const sigType = (signal.signal_type || '').toUpperCase()
  const typeStyle = SIGNAL_TYPE_COLORS[sigType] || SIGNAL_TYPE_COLORS.CORPORATE
  const conf = Math.round((signal.confidence_score || 0) * 100)
  const barColor = conf >= 75 ? '#26A69A' : conf >= 50 ? '#F9A825' : '#787B86'

  return (
    <>
      <div
        onClick={() => setExpanded(v => !v)}
        style={{
          display: 'grid',
          gridTemplateColumns: '80px 80px 1fr 72px 52px 56px 20px',
          alignItems: 'center',
          gap: 8, padding: '7px 12px',
          borderBottom: '1px solid var(--border-primary)',
          borderLeft: `3px solid ${borderColor}`,
          cursor: 'pointer',
          background: expanded ? 'var(--bg-hover)' : 'transparent',
          transition: 'background 0.1s',
        }}
      >
        {/* Symbol */}
        <span className="price" style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
          {signal.symbol}
        </span>

        {/* Type badge */}
        <span style={{
          fontSize: 9, padding: '2px 5px', borderRadius: 2,
          background: typeStyle.bg, color: typeStyle.text,
          border: `1px solid ${typeStyle.border}66`,
          letterSpacing: '0.05em', textTransform: 'uppercase', fontWeight: 600,
          whiteSpace: 'nowrap',
        }}>
          {sigType}
        </span>

        {/* Headline */}
        <span style={{
          fontSize: 11, color: 'var(--text-secondary)',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {signal.headline || signal.summary || ''}
        </span>

        {/* Confidence bar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <div style={{
            height: 3, background: 'var(--border-primary)', borderRadius: 2, overflow: 'hidden',
          }}>
            <div style={{ width: `${conf}%`, height: '100%', background: barColor, borderRadius: 2 }} />
          </div>
          <span className="price" style={{ fontSize: 9, color: barColor }}>{conf}%</span>
        </div>

        {/* Direction */}
        <DirectionBadge dir={direction} />

        {/* Time */}
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
          {formatRelativeTime(signal.signal_date || signal.created_at)}
        </span>

        {/* Expand icon */}
        <span style={{ color: 'var(--text-muted)' }}>
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </span>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{
          padding: '10px 16px 12px',
          background: 'var(--bg-tertiary)',
          borderBottom: '1px solid var(--border-primary)',
          borderLeft: `3px solid ${borderColor}`,
          fontSize: 11, color: 'var(--text-secondary)',
          lineHeight: 1.6,
        }}>
          {signal.ai_analysis || signal.description || signal.summary || 'No analysis available.'}
          {signal.price_target && (
            <div style={{ marginTop: 8, display: 'flex', gap: 16 }}>
              <span>Target: <strong className="price text-bull">{formatPrice(signal.price_target)}</strong></span>
              {signal.stop_loss && <span>Stop Loss: <strong className="price text-bear">{formatPrice(signal.stop_loss)}</strong></span>}
            </div>
          )}
        </div>
      )}
    </>
  )
}

function AgentAlertRow({ alert }) {
  const [expanded, setExpanded] = useState(false)
  const action = (alert.action || 'WATCH').toUpperCase()
  const actionColor = action.includes('BUY') ? '#26A69A'
    : action.includes('SELL') ? '#EF5350'
      : '#787B86'
  const score = Math.round(((alert.scores?.personalised_score || 0) * 100))

  return (
    <>
      <div
        onClick={() => setExpanded(v => !v)}
        style={{
          display: 'grid',
          gridTemplateColumns: '80px 80px 1fr 72px 52px 20px',
          alignItems: 'center',
          gap: 8,
          padding: '7px 12px',
          borderBottom: '1px solid var(--border-primary)',
          borderLeft: '3px solid #2962FF',
          cursor: 'pointer',
          background: expanded ? 'rgba(41,98,255,0.08)' : 'transparent',
          transition: 'background 0.1s',
        }}
      >
        <span className="price" style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
          {alert.symbol}
        </span>

        <span style={{
          fontSize: 9,
          padding: '2px 5px',
          borderRadius: 2,
          background: 'rgba(41,98,255,0.12)',
          color: '#2962FF',
          border: '1px solid rgba(41,98,255,0.35)',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          fontWeight: 700,
          whiteSpace: 'nowrap',
        }}>
          AGENT
        </span>

        <div style={{ minWidth: 0 }}>
          <div style={{
            fontSize: 11,
            color: 'var(--text-primary)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {alert.headline}
          </div>
          <div style={{ marginTop: 3, fontSize: 10, color: 'var(--text-muted)' }}>
            {alert.company_name} {alert.conviction ? `· ${alert.conviction}` : ''}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <div style={{
            height: 3,
            background: 'var(--border-primary)',
            borderRadius: 2,
            overflow: 'hidden',
          }}>
            <div style={{ width: `${score}%`, height: '100%', background: '#2962FF', borderRadius: 2 }} />
          </div>
          <span className="price" style={{ fontSize: 9, color: '#2962FF' }}>{score}%</span>
        </div>

        <span style={{
          fontSize: 9,
          padding: '2px 5px',
          borderRadius: 2,
          background: `${actionColor}14`,
          color: actionColor,
          border: `1px solid ${actionColor}55`,
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          fontWeight: 600,
          whiteSpace: 'nowrap',
        }}>
          {action}
        </span>

        <span style={{ color: 'var(--text-muted)' }}>
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </span>
      </div>

      {expanded && (
        <div style={{
          padding: '10px 16px 12px',
          background: 'rgba(41,98,255,0.06)',
          borderBottom: '1px solid var(--border-primary)',
          borderLeft: '3px solid #2962FF',
          fontSize: 11,
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
        }}>
          {alert.portfolio_note && (
            <div style={{ marginBottom: 8, fontStyle: 'italic' }}>{alert.portfolio_note}</div>
          )}

          <div>{alert.reasoning}</div>

          <div style={{ marginTop: 8, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {alert.trade_levels?.entry_low != null && alert.trade_levels?.entry_high != null && (
              <span>Entry: <strong className="price" style={{ color: '#2962FF' }}>
                ₹{alert.trade_levels.entry_low} - ₹{alert.trade_levels.entry_high}
              </strong></span>
            )}
            {alert.trade_levels?.target != null && (
              <span>Target: <strong className="price text-bull">₹{alert.trade_levels.target}</strong></span>
            )}
            {alert.trade_levels?.stop_loss != null && (
              <span>Stop Loss: <strong className="price text-bear">₹{alert.trade_levels.stop_loss}</strong></span>
            )}
            {alert.trade_levels?.horizon && <span>Horizon: <strong>{alert.trade_levels.horizon}</strong></span>}
          </div>
        </div>
      )}
    </>
  )
}

// ─── Insider trade row ────────────────────────────────────────────────────────

function InsiderRow({ trade }) {
  const isUp = (trade.trade_type || '').toUpperCase() === 'BUY'
  const delta = (trade.post_holding_pct || 0) - (trade.pre_holding_pct || 0)
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '72px 160px 80px 72px 80px 80px 72px',
      alignItems: 'center', gap: 8, padding: '6px 12px',
      borderBottom: '1px solid var(--border-primary)',
      borderLeft: `3px solid ${isUp ? '#26A69A' : '#EF5350'}`,
    }}>
      <span className="price" style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
        {trade.symbol}
      </span>
      <span style={{ fontSize: 11, color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {trade.person_name}
      </span>
      <Badge label={trade.category?.split(' ')[0] || 'Promoter'}
        style={{ color: '#F9A825', borderColor: '#F9A82566', background: '#F9A82514', fontSize: 9 }} />
      <DirectionBadge dir={trade.trade_type || 'BUY'} />
      <span className="price" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
        {formatIndianNumber(trade.quantity, 0)} sh
      </span>
      <span className="price" style={{ fontSize: 11 }}>
        {formatCrores(trade.value_cr)}
      </span>
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
        {delta !== 0 ? (
          <span className={delta > 0 ? 'text-bull' : 'text-bear'}>
            {delta > 0 ? '▲' : '▼'}{Math.abs(delta).toFixed(2)}%
          </span>
        ) : formatShortDate(trade.date)}
      </span>
    </div>
  )
}

// ─── Bulk/Block deal row ──────────────────────────────────────────────────────

function DealRow({ deal }) {
  const isUp    = (deal.buy_sell || '').toUpperCase() === 'BUY'
  const isBlock = (deal.deal_type || '').toUpperCase() === 'BLOCK'
  const fiiClient = isFII(deal.client_name)

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '72px 64px 200px 64px 80px 72px 60px',
      alignItems: 'center', gap: 8, padding: '6px 12px',
      borderBottom: '1px solid var(--border-primary)',
      borderLeft: `3px solid ${isUp ? '#26A69A' : '#EF5350'}`,
    }}>
      <span className="price" style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
        {deal.symbol}
      </span>
      <Badge label={deal.deal_type || 'BULK'}
        style={{ color: isBlock ? '#2962FF' : '#F9A825', borderColor: (isBlock ? '#2962FF' : '#F9A825') + '55', background: (isBlock ? '#2962FF' : '#F9A825') + '14', fontSize: 9 }} />
      <span style={{
        fontSize: 11,
        color: fiiClient ? '#2962FF' : 'var(--text-secondary)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {deal.client_name}
      </span>
      <DirectionBadge dir={deal.buy_sell || 'BUY'} />
      <span className="price" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
        {formatPrice(deal.price)}
      </span>
      <span className="price" style={{ fontSize: 11 }}>
        {formatCrores(deal.value_cr)}
      </span>
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
        {formatShortDate(deal.date)}
      </span>
    </div>
  )
}

// ─── Filing row ───────────────────────────────────────────────────────────────

function FilingRow({ filing }) {
  const catStyle = FILING_CATEGORY_COLORS[filing.category] || { bg: 'rgba(120,123,134,0.15)', color: '#787B86' }
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '160px 120px 1fr 72px',
      alignItems: 'center', gap: 8, padding: '6px 12px',
      borderBottom: '1px solid var(--border-primary)',
    }}>
      <span style={{ fontSize: 11, color: 'var(--text-primary)', fontWeight: 500,
                     whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {filing.company?.slice(0, 22) || filing.symbol}
      </span>
      <span style={{
        fontSize: 9, padding: '2px 5px', borderRadius: 2,
        background: catStyle.bg, color: catStyle.color,
        border: `1px solid ${catStyle.color}44`,
        letterSpacing: '0.04em', textTransform: 'uppercase', fontWeight: 600,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {(filing.category || '').slice(0, 18)}
      </span>
      <span style={{
        fontSize: 11, color: 'var(--text-secondary)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {(filing.headline || filing.subject || '').slice(0, 70)}
      </span>
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
        {formatShortDate(filing.date)}
      </span>
    </div>
  )
}

// ─── Column headers ───────────────────────────────────────────────────────────

function ColHeaders({ tab }) {
  const configs = {
    signals:  ['Symbol', 'Type', 'Headline', 'Confidence', 'Direction', 'Time', ''],
    insider:  ['Symbol', 'Person', 'Category', 'Trade', 'Quantity', 'Value', 'Δ Holding'],
    bulk:     ['Symbol', 'Type', 'Client', 'Side', 'Price', 'Value', 'Date'],
    filings:  ['Company', 'Category', 'Headline', 'Date'],
  }
  const widths = {
    signals:  '80px 80px 1fr 72px 52px 56px 20px',
    insider:  '72px 160px 80px 72px 80px 80px 72px',
    bulk:     '72px 64px 200px 64px 80px 72px 60px',
    filings:  '160px 120px 1fr 72px',
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: widths[tab] || '1fr',
      padding: '5px 12px',
      gap: 8,
      borderBottom: '1px solid var(--border-secondary)',
      background: 'var(--bg-secondary)',
      position: 'sticky', top: 0, zIndex: 2,
    }}>
      {(configs[tab] || []).map((col, i) => (
        <span key={i} style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {col}
        </span>
      ))}
    </div>
  )
}

// ─── MAIN Opportunity Radar ───────────────────────────────────────────────────

const TABS = [
  { id: 'signals',  label: 'All Signals' },
  { id: 'insider',  label: 'Insider Trades' },
  { id: 'bulk',     label: 'Bulk/Block Deals' },
  { id: 'filings',  label: 'Filings' },
]

export default function OpportunityRadar() {
  const [activeTab, setActiveTab] = useState('signals')
  const [showAgent, setShowAgent] = useState(false)
  const [agentAlerts, setAgentAlerts] = useState([])
  const [portfolio, setPortfolio] = useState({
    holdings: [],
    risk_profile: 'MODERATE',
  })

  // Filters for signals tab
  const [dirFilter,  setDirFilter]  = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [minConf,    setMinConf]    = useState(0)

  const filters = useMemo(() => ({
    ...(dirFilter  ? { direction: dirFilter }              : {}),
    ...(typeFilter ? { signal_types: typeFilter }          : {}),
    ...(minConf    ? { min_confidence: minConf / 100 }     : {}),
  }), [dirFilter, typeFilter, minConf])

  const radarQ   = useRadarData(filters)
  const insiderQ = useInsiderTrades()
  const bulkQ    = useBulkDeals()
  const filingsQ = useFilings()

  const activeQuery = {
    signals: radarQ,
    insider: insiderQ,
    bulk:    bulkQ,
    filings: filingsQ,
  }[activeTab]

  // Extract data arrays
  const signals = radarQ.data?.signals || []
  const insiders = insiderQ.data?.trades || (Array.isArray(insiderQ.data) ? insiderQ.data : [])
  const bulkData = bulkQ.data
  const bulk    = [...(bulkData?.bulk || []), ...(bulkData?.block || [])]
  const filings = filingsQ.data?.filings || (Array.isArray(filingsQ.data) ? filingsQ.data : [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Stats bar */}
      <StatsBar radarData={radarQ.data} onToggleAgent={() => setShowAgent(v => !v)} />

      {showAgent && (
        <div style={{ padding: '12px', borderBottom: '1px solid var(--border-primary)', background: 'var(--bg-primary)' }}>
          <AgentTracePanel
            pipeline="Opportunity Radar"
            endpoint="/api/agent/radar/stream"
            payload={{ portfolio }}
            onAlerts={(alerts) => {
              setAgentAlerts(alerts)
            }}
            onComplete={(run) => console.log('Agent run complete:', run.run_id)}
          />
        </div>
      )}

      {/* Tab bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 0,
        padding: '0 12px',
        borderBottom: '1px solid var(--border-primary)',
        background: 'var(--bg-secondary)',
        flexShrink: 0,
      }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 14px', fontSize: 11, fontWeight: 500,
              border: 'none', background: 'transparent', cursor: 'pointer',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
              borderBottom: activeTab === tab.id ? '2px solid #2962FF' : '2px solid transparent',
              transition: 'all 0.1s',
            }}
          >
            {tab.label}
          </button>
        ))}

        {/* Filters — only on signals tab */}
        {activeTab === 'signals' && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
            <select
              value={dirFilter}
              onChange={e => setDirFilter(e.target.value)}
              style={{
                background: 'var(--bg-tertiary)', border: '1px solid var(--border-primary)',
                color: 'var(--text-secondary)', fontSize: 10, padding: '3px 6px',
                borderRadius: 2, outline: 'none',
              }}
            >
              <option value="">All Directions</option>
              <option value="BULLISH">Bullish</option>
              <option value="BEARISH">Bearish</option>
              <option value="NEUTRAL">Neutral</option>
            </select>
            <select
              value={typeFilter}
              onChange={e => setTypeFilter(e.target.value)}
              style={{
                background: 'var(--bg-tertiary)', border: '1px solid var(--border-primary)',
                color: 'var(--text-secondary)', fontSize: 10, padding: '3px 6px',
                borderRadius: 2, outline: 'none',
              }}
            >
              <option value="">All Types</option>
              <option value="INSIDER">Insider</option>
              <option value="FILING">Filing</option>
              <option value="TECHNICAL">Technical</option>
              <option value="FII">FII</option>
            </select>
            <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--text-muted)' }}>
              Min conf
              <input type="range" min={0} max={90} step={10} value={minConf}
                onChange={e => setMinConf(Number(e.target.value))}
                style={{ width: 56, accentColor: '#2962FF' }} />
              <span>{minConf}%</span>
            </label>
            <button
              onClick={() => activeQuery.refetch?.()}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}
              title="Refresh"
            >
              <RefreshCw size={11} />
            </button>
          </div>
        )}
      </div>

      {/* Column headers */}
      <ColHeaders tab={activeTab} />

      {/* Data rows */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {activeQuery?.isLoading && Array(8).fill(0).map((_, i) => <Skeleton key={i} h={36} />)}

        {activeQuery?.isError && (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
            Data unavailable — will retry shortly
          </div>
        )}

        {/* Signals */}
        {activeTab === 'signals' && !activeQuery?.isLoading && (
          (agentAlerts.length > 0 || signals.length > 0)
            ? (
              <>
                {agentAlerts.map(alert => <AgentAlertRow key={`${alert.symbol}-${alert.rank}`} alert={alert} />)}
                {signals.map(s => <SignalRow key={s.signal_id || s.id} signal={s} />)}
              </>
            )
            : <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>No signals found</div>
        )}

        {/* Insider */}
        {activeTab === 'insider' && !activeQuery?.isLoading && (
          insiders.length > 0
            ? insiders.map((t, i) => <InsiderRow key={i} trade={t} />)
            : <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>No insider trades</div>
        )}

        {/* Bulk deals */}
        {activeTab === 'bulk' && !activeQuery?.isLoading && (
          bulk.length > 0
            ? bulk.map((d, i) => <DealRow key={i} deal={d} />)
            : <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>No deals</div>
        )}

        {/* Filings */}
        {activeTab === 'filings' && !activeQuery?.isLoading && (
          filings.length > 0
            ? filings.map((f, i) => <FilingRow key={i} filing={f} />)
            : <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>No filings</div>
        )}
      </div>
    </div>
  )
}
