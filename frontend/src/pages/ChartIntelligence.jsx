import React, { useState, useMemo, useCallback, useRef } from 'react'
import {
  ComposedChart, LineChart, BarChart,
  Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ReferenceArea, Cell
} from 'recharts'
import { Search, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { useStockChart, usePatternScan } from '../hooks/useMarketData'
import { computeAllIndicators } from '../utils/indicators'
import {
  formatPrice, formatPct, formatIndianNumber,
  formatVolume, formatRelativeTime
} from '../utils/formatters'
import NSE_SYMBOLS from '../data/nseSymbols'

// ─── Candlestick custom bar shape ────────────────────────────────────────────

const CandlestickBar = (props) => {
  const { x, width, openValue, closeValue, highValue, lowValue } = props
  if (openValue == null || closeValue == null) return null

  const scale = props.yAxisMap?.[props.yAxisId]
  if (!scale) return null

  const yOpen  = scale.scale(openValue)
  const yClose = scale.scale(closeValue)
  const yHigh  = scale.scale(highValue)
  const yLow   = scale.scale(lowValue)

  const isBull  = closeValue >= openValue
  const color   = isBull ? '#26A69A' : '#EF5350'
  const bodyTop = Math.min(yOpen, yClose)
  const bodyH   = Math.max(Math.abs(yClose - yOpen), 1)
  const cx      = x + width / 2

  return (
    <g>
      {/* Wick */}
      <line x1={cx} y1={yHigh} x2={cx} y2={yLow}
            stroke="#787B86" strokeWidth={1} />
      {/* Body */}
      <rect x={x + 1} y={bodyTop} width={Math.max(width - 2, 1)} height={bodyH}
            fill={isBull ? '#26A69A' : '#EF5350'}
            stroke={color} strokeWidth={0.5} />
    </g>
  )
}

// ─── Stock search autocomplete ────────────────────────────────────────────────

function StockSearch({ value, onChange }) {
  const [query,      setQuery]      = useState('')
  const [open,       setOpen]       = useState(false)
  const [highlighted, setHighlighted] = useState(0)

  const matches = useMemo(() => {
    if (!query.trim()) return []
    const q = query.toLowerCase()
    return NSE_SYMBOLS
      .filter(s => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q))
      .slice(0, 10)
  }, [query])

  const select = useCallback((sym) => {
    onChange(sym.symbol)
    setQuery(sym.symbol)
    setOpen(false)
  }, [onChange])

  const handleKey = (e) => {
    if (!open || !matches.length) return
    if (e.key === 'ArrowDown')  { setHighlighted(h => Math.min(h + 1, matches.length - 1)); e.preventDefault() }
    if (e.key === 'ArrowUp')    { setHighlighted(h => Math.max(h - 1, 0)); e.preventDefault() }
    if (e.key === 'Enter')      { select(matches[highlighted]) }
    if (e.key === 'Escape')     { setOpen(false) }
  }

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6,
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-primary)',
                    borderRadius: 2, padding: '4px 8px', width: 200 }}>
        <Search size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
        <input
          value={query || value}
          onChange={e => { setQuery(e.target.value); setOpen(true); setHighlighted(0) }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={handleKey}
          placeholder="Search symbol…"
          style={{
            background: 'transparent', border: 'none', outline: 'none',
            color: 'var(--text-primary)', fontSize: 12, width: '100%',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        />
      </div>
      {open && matches.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, zIndex: 50,
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-primary)',
          borderRadius: 2, width: 280, maxHeight: 260, overflowY: 'auto',
          boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
        }}>
          {matches.map((m, i) => (
            <div
              key={m.symbol}
              onMouseDown={() => select(m)}
              style={{
                padding: '6px 10px', cursor: 'pointer', display: 'flex', gap: 10,
                background: highlighted === i ? 'var(--bg-hover)' : 'transparent',
                borderBottom: '1px solid var(--border-primary)',
              }}
            >
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, fontWeight: 500, color: 'var(--text-primary)', minWidth: 72 }}>
                {m.symbol}
              </span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {m.name}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Quick symbol chips ───────────────────────────────────────────────────────

const HOT_STOCKS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'ZOMATO', 'ADANIENT', 'LT']

// ─── Period / interval selectors ─────────────────────────────────────────────

const PERIODS = [
  { label: '1D', period: '1d',  interval: '5m' },
  { label: '5D', period: '5d',  interval: '15m' },
  { label: '1M', period: '1mo', interval: '1h' },
  { label: '3M', period: '3mo', interval: '1d' },
  { label: '6M', period: '6mo', interval: '1d' },
  { label: '1Y', period: '1y',  interval: '1d' },
  { label: '2Y', period: '2y',  interval: '1wk' },
  { label: '5Y', period: '5y',  interval: '1wk' },
]

// ─── Custom tooltip ───────────────────────────────────────────────────────────

const OhlcvTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)',
      padding: '8px 12px', borderRadius: 2, fontSize: 10,
      fontFamily: 'JetBrains Mono, monospace',
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{String(d.date).slice(0, 10)}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '40px 80px', rowGap: 2 }}>
        <span style={{ color: 'var(--text-muted)' }}>O</span><span>{formatPrice(d.open)}</span>
        <span style={{ color: 'var(--text-muted)' }}>H</span><span className="text-bull">{formatPrice(d.high)}</span>
        <span style={{ color: 'var(--text-muted)' }}>L</span><span className="text-bear">{formatPrice(d.low)}</span>
        <span style={{ color: 'var(--text-muted)' }}>C</span>
        <span style={{ color: d.close >= d.open ? '#26A69A' : '#EF5350' }}>{formatPrice(d.close)}</span>
        <span style={{ color: 'var(--text-muted)' }}>Vol</span><span>{formatVolume(d.volume)}</span>
      </div>
    </div>
  )
}

// ─── RSI tooltip ──────────────────────────────────────────────────────────────

const RsiTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const rsi = payload[0]?.value
  if (rsi == null) return null
  const color = rsi >= 70 ? '#EF5350' : rsi <= 30 ? '#26A69A' : '#F9A825'
  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)',
      padding: '4px 8px', borderRadius: 2, fontSize: 10,
      fontFamily: 'JetBrains Mono, monospace', color,
    }}>
      RSI {rsi?.toFixed(1)}
    </div>
  )
}

// ─── MACD tooltip ─────────────────────────────────────────────────────────────

const MacdTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)',
      padding: '4px 8px', borderRadius: 2, fontSize: 10,
      fontFamily: 'JetBrains Mono, monospace',
    }}>
      <div>MACD <span style={{ color: '#2962FF' }}>{d.macd?.toFixed(3)}</span></div>
      <div>Signal <span style={{ color: '#FF9800' }}>{d.macdSignal?.toFixed(3)}</span></div>
      <div>Hist <span style={{ color: d.histogram >= 0 ? '#26A69A' : '#EF5350' }}>{d.histogram?.toFixed(3)}</span></div>
    </div>
  )
}

// ─── Fundamentals panel ───────────────────────────────────────────────────────

function FundamentalsRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0',
                  borderBottom: '1px solid var(--border-primary)' }}>
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</span>
      <span className="price" style={{ fontSize: 10, color: color || 'var(--text-primary)' }}>{value || '—'}</span>
    </div>
  )
}

// ─── Pattern chip ─────────────────────────────────────────────────────────────

function PatternChip({ pattern, onClick, active }) {
  const isBull = (pattern.direction || pattern.overall_bias || '').toUpperCase() === 'BULLISH'
  const color  = isBull ? '#26A69A' : '#EF5350'
  const conf   = Math.round((pattern.confidence || 0) * 100)
  return (
    <div
      onClick={onClick}
      style={{
        display: 'inline-flex', flexDirection: 'column', gap: 2,
        padding: '4px 8px', borderRadius: 2, cursor: 'pointer',
        border: `1px solid ${active ? color : 'var(--border-primary)'}`,
        background: active ? `${color}14` : 'var(--bg-tertiary)',
        transition: 'all 0.1s', flexShrink: 0,
      }}
    >
      <span style={{ fontSize: 10, fontWeight: 500, color: active ? color : 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
        {(pattern.pattern_type || '').replace(/_/g, ' ')}
      </span>
      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
        <span style={{ fontSize: 8, color }}>
          {isBull ? '▲' : '▼'} {isBull ? 'BULL' : 'BEAR'}
        </span>
        <span style={{ fontSize: 8, color: 'var(--text-muted)' }}>{conf}%</span>
      </div>
    </div>
  )
}

// ─── MAIN ChartIntelligence ───────────────────────────────────────────────────

export default function ChartIntelligence() {
  const [symbol, setSymbol]           = useState('RELIANCE')
  const [selectedPeriod, setSelectedPeriod] = useState(PERIODS[5])  // 1Y default
  const [activePattern, setActivePattern]   = useState(null)
  const [showFundamentals, setShowFundamentals] = useState(true)
  const [showAnalysis, setShowAnalysis]         = useState(false)

  const { ohlcv, fundamentals, quote, liveQuote, isLoading, isError, refetch } =
    useStockChart(symbol, selectedPeriod.period, selectedPeriod.interval)

  const patternQ = usePatternScan(symbol)
  const patterns = patternQ.data?.patterns || []

  // Compute indicators on the full dataset
  const chartData = useMemo(() => {
    if (!ohlcv?.length) return []
    return computeAllIndicators(ohlcv)
  }, [ohlcv])

  // Determine price domain for main chart
  const priceDomain = useMemo(() => {
    if (!chartData.length) return ['auto', 'auto']
    const prices  = chartData.flatMap(d => [d.high, d.low]).filter(Boolean)
    const minP    = Math.min(...prices)
    const maxP    = Math.max(...prices)
    const pad     = (maxP - minP) * 0.05
    return [minP - pad, maxP + pad]
  }, [chartData])

  const livePrice   = liveQuote?.ltp || quote?.ltp
  const changePct   = formatPct(liveQuote?.change_pct || quote?.change_pct)
  const displayConf = Math.round((patternQ.data?.overall_confidence || 0) * 100)

  // Find support / resistance from first active pattern or scan result
  const levels = patternQ.data?.support_resistance || {}

  // Slice data for display (max 300 candles for performance)
  const displayData = chartData.length > 300
    ? chartData.slice(chartData.length - 300)
    : chartData

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Toolbar ────────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '6px 12px', flexShrink: 0,
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-primary)',
        flexWrap: 'wrap',
      }}>
        {/* Search */}
        <StockSearch value={symbol} onChange={sym => { setSymbol(sym); setActivePattern(null) }} />

        {/* Live price badge */}
        {livePrice ? (
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span className="price" style={{ fontSize: 18, fontWeight: 500, color: 'var(--text-primary)' }}>
              {formatPrice(livePrice)}
            </span>
            <span className={`price ${changePct.cls}`} style={{ fontSize: 12 }}>
              {changePct.text}
            </span>
          </div>
        ) : isLoading ? (
          <div className="skeleton" style={{ width: 120, height: 20 }} />
        ) : null}

        {/* Period selector */}
        <div style={{ display: 'flex', gap: 1, marginLeft: 'auto' }}>
          {PERIODS.map(p => (
            <button
              key={p.label}
              onClick={() => setSelectedPeriod(p)}
              style={{
                padding: '3px 9px', fontSize: 10, border: 'none',
                background: selectedPeriod.label === p.label ? 'var(--bg-tertiary)' : 'transparent',
                color: selectedPeriod.label === p.label ? 'var(--text-primary)' : 'var(--text-muted)',
                cursor: 'pointer', borderRadius: 2,
                borderBottom: selectedPeriod.label === p.label ? '2px solid #2962FF' : '2px solid transparent',
              }}
            >
              {p.label}
            </button>
          ))}
        </div>

        <button
          onClick={() => refetch()}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}
          title="Refresh data"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      {/* ── Quick stock chips ─────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 6, padding: '6px 12px', flexShrink: 0,
        borderBottom: '1px solid var(--border-primary)',
        overflowX: 'auto',
      }}>
        {HOT_STOCKS.map(s => (
          <button
            key={s}
            onClick={() => { setSymbol(s); setActivePattern(null) }}
            style={{
              padding: '2px 8px', fontSize: 10, borderRadius: 2, cursor: 'pointer',
              border: `1px solid ${symbol === s ? '#2962FF' : 'var(--border-primary)'}`,
              background: symbol === s ? 'rgba(41,98,255,0.12)' : 'var(--bg-tertiary)',
              color: symbol === s ? '#2962FF' : 'var(--text-muted)',
              fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap',
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {/* ── Main layout: chart + sidebar ─────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Chart column */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {isError && (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
              Chart data unavailable — showing cached / demo data
            </div>
          )}

          {isLoading && !displayData.length ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div className="spinner" />
            </div>
          ) : (
            <>
              {/* Main candlestick chart */}
              <div style={{ flex: 3, minHeight: 0, padding: '4px 0' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={displayData}
                    margin={{ top: 4, right: 64, bottom: 4, left: 4 }}
                  >
                    <CartesianGrid stroke="#2A2E39" strokeDasharray="0" vertical={false} strokeOpacity={0.5} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 9, fill: '#787B86' }}
                      tickFormatter={d => String(d).slice(5, 10)}
                      axisLine={false} tickLine={false}
                      interval={Math.ceil(displayData.length / 8)}
                    />
                    <YAxis
                      domain={priceDomain}
                      tick={{ fontSize: 9, fill: '#787B86' }}
                      tickFormatter={v => `₹${formatIndianNumber(v, 0)}`}
                      axisLine={false} tickLine={false}
                      orientation="right" width={60}
                    />
                    <Tooltip content={<OhlcvTooltip />} />

                    {/* EMA lines */}
                    <Line type="monotone" dataKey="ema20"  stroke="#2962FF" strokeWidth={1}
                          dot={false} isAnimationActive={false} strokeOpacity={0.6} name="EMA20" />
                    <Line type="monotone" dataKey="ema50"  stroke="#FF9800" strokeWidth={1}
                          dot={false} isAnimationActive={false} strokeOpacity={0.6} name="EMA50" />

                    {/* Bollinger bands */}
                    <Line type="monotone" dataKey="bbUpper" stroke="#787B86" strokeWidth={0.5}
                          dot={false} isAnimationActive={false} strokeDasharray="3 3" strokeOpacity={0.5} />
                    <Line type="monotone" dataKey="bbLower" stroke="#787B86" strokeWidth={0.5}
                          dot={false} isAnimationActive={false} strokeDasharray="3 3" strokeOpacity={0.5} />

                    {/* Candlestick bars rendered as scatter via custom shape */}
                    {/* We use a Bar with a custom shape for OHLC rendering */}
                    <Bar dataKey="close" shape={(props) => {
                      const d = props.close !== undefined ? props : null
                      if (!d) return null
                      const item = displayData[props.index]
                      if (!item) return null
                      return (
                        <g key={props.index}>
                          {/* Wick high-low */}
                          <line
                            x1={props.x + props.width / 2}
                            y1={props.yAxis.scale(item.high)}
                            x2={props.x + props.width / 2}
                            y2={props.yAxis.scale(item.low)}
                            stroke="#787B86" strokeWidth={1}
                          />
                          {/* Body */}
                          {(() => {
                            const yO = props.yAxis.scale(item.open)
                            const yC = props.yAxis.scale(item.close)
                            const isBull = item.close >= item.open
                            const top = Math.min(yO, yC)
                            const ht  = Math.max(Math.abs(yC - yO), 1)
                            const col = isBull ? '#26A69A' : '#EF5350'
                            return (
                              <rect
                                x={props.x + 1}
                                y={top}
                                width={Math.max(props.width - 2, 1)}
                                height={ht}
                                fill={col}
                                stroke={col}
                                strokeWidth={0.5}
                              />
                            )
                          })()}
                        </g>
                      )
                    }} isAnimationActive={false} />

                    {/* Support / Resistance lines */}
                    {levels.support && (
                      <ReferenceLine y={levels.support} stroke="#26A69A" strokeDasharray="4 4" strokeWidth={1}
                        label={{ value: `S ₹${formatIndianNumber(levels.support, 0)}`, position: 'right', fontSize: 9, fill: '#26A69A' }} />
                    )}
                    {levels.resistance && (
                      <ReferenceLine y={levels.resistance} stroke="#EF5350" strokeDasharray="4 4" strokeWidth={1}
                        label={{ value: `R ₹${formatIndianNumber(levels.resistance, 0)}`, position: 'right', fontSize: 9, fill: '#EF5350' }} />
                    )}
                    {levels.target && (
                      <ReferenceLine y={levels.target} stroke="#2962FF" strokeDasharray="6 3" strokeWidth={1}
                        label={{ value: `T ₹${formatIndianNumber(levels.target, 0)}`, position: 'right', fontSize: 9, fill: '#2962FF' }} />
                    )}

                    {/* Pattern zone shading for active pattern */}
                    {activePattern && (
                      <ReferenceArea
                        x1={activePattern.key_levels?.start_date || displayData[Math.max(0, displayData.length - 30)]?.date}
                        x2={activePattern.key_levels?.end_date   || displayData[displayData.length - 1]?.date}
                        fill={(activePattern.direction || '').toUpperCase() === 'BULLISH' ? '#26A69A' : '#EF5350'}
                        fillOpacity={0.06}
                        stroke={(activePattern.direction || '').toUpperCase() === 'BULLISH' ? '#26A69A' : '#EF5350'}
                        strokeOpacity={0.3} strokeWidth={1}
                      />
                    )}

                    {/* Live price line */}
                    {livePrice && (
                      <ReferenceLine
                        y={livePrice}
                        stroke="#2962FF"
                        strokeWidth={1.5}
                        label={{
                          value: `▶ ${formatPrice(livePrice)}`,
                          position: 'right', fontSize: 10,
                          fill: '#2962FF', fontWeight: 600,
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* RSI sub-panel */}
              <div style={{ flex: 1, minHeight: 0, borderTop: '1px solid var(--border-primary)', padding: '4px 0' }}>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', padding: '0 12px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>RSI (14)</div>
                <ResponsiveContainer width="100%" height="85%">
                  <LineChart data={displayData} margin={{ top: 2, right: 64, bottom: 2, left: 4 }}>
                    <CartesianGrid stroke="#2A2E39" strokeDasharray="0" vertical={false} strokeOpacity={0.4} />
                    <XAxis dataKey="date" hide />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 8, fill: '#787B86' }} axisLine={false} tickLine={false}
                           orientation="right" width={30} ticks={[30, 50, 70]} />
                    <Tooltip content={<RsiTooltip />} />
                    <ReferenceLine y={70} stroke="#EF5350" strokeDasharray="3 3" strokeOpacity={0.6} />
                    <ReferenceLine y={30} stroke="#26A69A" strokeDasharray="3 3" strokeOpacity={0.6} />
                    <ReferenceLine y={50} stroke="#787B86" strokeOpacity={0.3} />
                    <Line type="monotone" dataKey="rsi" stroke="#F9A825" strokeWidth={1.2}
                          dot={false} isAnimationActive={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* MACD sub-panel */}
              <div style={{ flex: 1, minHeight: 0, borderTop: '1px solid var(--border-primary)', padding: '4px 0' }}>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', padding: '0 12px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>MACD (12, 26, 9)</div>
                <ResponsiveContainer width="100%" height="85%">
                  <ComposedChart data={displayData} margin={{ top: 2, right: 64, bottom: 2, left: 4 }}>
                    <CartesianGrid stroke="#2A2E39" strokeDasharray="0" vertical={false} strokeOpacity={0.4} />
                    <XAxis dataKey="date" hide />
                    <YAxis tick={{ fontSize: 8, fill: '#787B86' }} axisLine={false} tickLine={false}
                           orientation="right" width={30} />
                    <Tooltip content={<MacdTooltip />} />
                    <ReferenceLine y={0} stroke="#787B86" strokeOpacity={0.5} />
                    {/* Histogram */}
                    <Bar dataKey="histogram" isAnimationActive={false} maxBarSize={4}>
                      {displayData.map((d, i) => (
                        <Cell key={i} fill={(d.histogram || 0) >= 0 ? '#26A69A' : '#EF5350'} fillOpacity={0.7} />
                      ))}
                    </Bar>
                    <Line type="monotone" dataKey="macd"       stroke="#2962FF" strokeWidth={1.2} dot={false} isAnimationActive={false} connectNulls />
                    <Line type="monotone" dataKey="macdSignal" stroke="#FF9800" strokeWidth={1.2} dot={false} isAnimationActive={false} connectNulls />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Pattern chips row */}
          {patterns.length > 0 && (
            <div style={{
              display: 'flex', gap: 8, padding: '8px 12px',
              borderTop: '1px solid var(--border-primary)',
              overflowX: 'auto', flexShrink: 0,
              alignItems: 'center',
            }}>
              <span style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>
                Detected Patterns
              </span>
              {patterns.map((p, i) => (
                <PatternChip
                  key={i}
                  pattern={p}
                  active={activePattern === p}
                  onClick={() => setActivePattern(activePattern === p ? null : p)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar: Fundamentals */}
        <div style={{
          width: 220, flexShrink: 0,
          borderLeft: '1px solid var(--border-primary)',
          overflowY: 'auto',
          display: 'flex', flexDirection: 'column',
        }}>
          {/* Fundamentals section */}
          <div>
            <button
              onClick={() => setShowFundamentals(v => !v)}
              style={{
                width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '7px 12px', background: 'var(--bg-secondary)',
                border: 'none', borderBottom: '1px solid var(--border-primary)',
                cursor: 'pointer', color: 'var(--text-muted)',
              }}
            >
              <span className="label">Fundamentals</span>
              {showFundamentals ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
            </button>
            {showFundamentals && (
              <div style={{ padding: '0 12px 8px' }}>
                <FundamentalsRow label="Mkt Cap"     value={formatPrice(fundamentals.market_cap_cr ? fundamentals.market_cap_cr * 1e7 / 1e7 : null) + ' Cr'} />
                <FundamentalsRow label="P/E"         value={fundamentals.pe_ratio?.toFixed(1)} />
                <FundamentalsRow label="P/B"         value={fundamentals.pb_ratio?.toFixed(2)} />
                <FundamentalsRow label="ROE"         value={fundamentals.roe_pct ? `${fundamentals.roe_pct}%` : null} />
                <FundamentalsRow label="Debt/Equity" value={fundamentals.debt_equity?.toFixed(2)} />
                <FundamentalsRow label="Rev Growth"
                  value={fundamentals.revenue_growth ? `${fundamentals.revenue_growth > 0 ? '+' : ''}${fundamentals.revenue_growth}%` : null}
                  color={fundamentals.revenue_growth > 0 ? '#26A69A' : '#EF5350'} />
                <FundamentalsRow label="EPS Growth"
                  value={fundamentals.earnings_growth ? `${fundamentals.earnings_growth > 0 ? '+' : ''}${fundamentals.earnings_growth}%` : null}
                  color={fundamentals.earnings_growth > 0 ? '#26A69A' : '#EF5350'} />
                <FundamentalsRow label="Div Yield"   value={fundamentals.dividend_yield ? `${fundamentals.dividend_yield}%` : null} />
                <FundamentalsRow label="Beta"        value={fundamentals.beta?.toFixed(2)} />
                <FundamentalsRow label="52W High"    value={formatPrice(fundamentals['52w_high'])} color="#26A69A" />
                <FundamentalsRow label="52W Low"     value={formatPrice(fundamentals['52w_low'])}  color="#EF5350" />
                <FundamentalsRow label="Avg Vol"     value={formatVolume(fundamentals.avg_volume)} />
              </div>
            )}
          </div>

          {/* AI Analysis for active pattern */}
          {patterns.length > 0 && (
            <div>
              <button
                onClick={() => setShowAnalysis(v => !v)}
                style={{
                  width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '7px 12px', background: 'var(--bg-secondary)',
                  border: 'none', borderBottom: '1px solid var(--border-primary)',
                  borderTop: '1px solid var(--border-primary)',
                  cursor: 'pointer', color: 'var(--text-muted)',
                }}
              >
                <span className="label">AI Analysis</span>
                {showAnalysis ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
              </button>
              {showAnalysis && (
                <div style={{ padding: '8px 12px', fontSize: 10, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {activePattern
                    ? activePattern.description || activePattern.ai_explanation || 'Select a pattern chip to read AI analysis.'
                    : patternQ.data?.ai_summary || 'Select a detected pattern chip below the chart.'}
                </div>
              )}
            </div>
          )}

          {/* Company description */}
          {fundamentals.description && (
            <div style={{ padding: '8px 12px', fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.5, marginTop: 'auto' }}>
              {fundamentals.description}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
