import React, { useState, useEffect, useMemo } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { useChartData } from '../hooks/useChartData'
import { STOCK_LIST, getStockData } from '../data/mockChartData'
import { getPatterns } from '../data/mockPatterns'
import {
  computeEMA, computeRSI, computeMACD,
  computeBollingerBands, computeVolumeMA,
} from '../utils/indicators'

const C = {
  bgPage:      '#131722',
  bgCard:      '#1E222D',
  bgElevated:  '#2A2E39',
  bgHover:     '#363A45',
  border:      '#2A2E39',
  borderStrong:'#363A45',
  textPrimary: '#D1D4DC',
  textSecond:  '#787B86',
  textMuted:   '#4C525E',
  bull:        '#26A69A',
  bear:        '#EF5350',
  accent:      '#2962FF',
  accentSubtle:'#1E2B4D',
  ema20:       '#F59E0B',
  ema50:       '#2962FF',
  ema200:      '#8B5CF6',
  bbColor:     '#4C525E',
  et:          '#F26522',
}
const MONO = "'JetBrains Mono', 'Courier New', monospace"

const PERIOD_MAP = {
  '1W': '5d',
  '1M': '1mo',
  '3M': '3mo',
  '6M': '6mo',
  '1Y': '1y',
  '2Y': '2y',
  '5Y': '5y',
}

export default function ChartIntelligence() {

  // State
  const [symbol,    setSymbol]    = useState('RELIANCE')
  const [timeframe, setTimeframe] = useState('1Y')
  const [search,    setSearch]    = useState('')
  const [showDrop,  setShowDrop]  = useState(false)
  const [showEMA,   setShowEMA]   = useState(true)
  const [showBB,    setShowBB]    = useState(false)
  const [showVol,   setShowVol]   = useState(true)
  const [showRSI,   setShowRSI]   = useState(true)
  const [showMACD,  setShowMACD]  = useState(false)

  // Data
  const period = PERIOD_MAP[timeframe] ?? '1y'
  const { ohlcv, quote, fundamentals, status, error, dataSource }
    = useChartData(symbol, period)

  // If real fetch failed, use mock as explicit fallback
  const displayData = useMemo(() => {
    if (status === 'success' && ohlcv.length > 0) return ohlcv
    if (status === 'error' || status === 'idle') {
      return getStockData(symbol) ?? []
    }
    return ohlcv
  }, [ohlcv, status, symbol])

  // Indicator computation
  const chartData = useMemo(() => {
    if (!displayData.length) return []
    const closes  = displayData.map(d => d.close)
    const volumes = displayData.map(d => d.volume)

    let ema20 = [], ema50 = [], ema200 = [], bb = [],
        rsi = [], macd = [], volMA = []
    try {
      ema20  = computeEMA(closes, 20)
      ema50  = computeEMA(closes, 50)
      ema200 = computeEMA(closes, 200)
      bb     = computeBollingerBands(closes)
      rsi    = computeRSI(closes)
      macd   = computeMACD(closes)
      volMA  = computeVolumeMA(volumes)
    } catch (e) {
      console.warn('indicators.js error:', e.message)
    }

    return displayData.map((candle, i) => ({
      ...candle,
      ema20:    ema20[i]  ?? null,
      ema50:    ema50[i]  ?? null,
      ema200:   ema200[i] ?? null,
      bbUpper:  bb[i]?.upper  ?? null,
      bbMiddle: bb[i]?.middle ?? null,
      bbLower:  bb[i]?.lower  ?? null,
      rsi:      rsi[i]  ?? null,
      macdLine: macd[i]?.macd      ?? null,
      macdSig:  macd[i]?.signal    ?? null,
      macdHist: macd[i]?.histogram ?? null,
      volMA:    volMA[i] ?? null,
    }))
  }, [displayData])

  // Quote display values
  const displayQuote = useMemo(() => {
    if (quote && status === 'success') return quote
    if (!displayData.length) return null
    const last = displayData[displayData.length - 1]
    const prev = displayData[displayData.length - 2] ?? last
    return {
      ltp:        last.close,
      open:       last.open,
      high:       last.high,
      low:        last.low,
      close:      last.close,
      volume:     last.volume,
      change:     parseFloat((last.close - prev.close).toFixed(2)),
      change_pct: parseFloat(
        (((last.close - prev.close) / prev.close) * 100).toFixed(2)
      ),
    }
  }, [quote, displayData, status])

  // Patterns
  const patterns = getPatterns(symbol) ?? []

  // Search filter
  const searchResults = useMemo(() => {
    if (!search) return STOCK_LIST.slice(0, 8)
    const q = search.toUpperCase()
    return STOCK_LIST.filter(s =>
      s.symbol.includes(q) || s.name.toUpperCase().includes(q)
    ).slice(0, 8)
  }, [search])

  // Helpers
  function fmtPrice(v) {
    if (v == null) return '—'
    return Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })
  }
  function fmtVol(v) {
    if (!v) return '—'
    if (v >= 1e7) return `${(v/1e7).toFixed(2)}Cr`
    if (v >= 1e5) return `${(v/1e5).toFixed(2)}L`
    return `${(v/1e3).toFixed(1)}K`
  }

  // Candlestick custom shape
  const CandlestickBar = (props) => {
    const { x, width, payload } = props
    if (!payload || !props.yAxis?.scale) return null
    const { open, high, low, close } = payload
    const scale  = props.yAxis.scale
    const isBull = close >= open
    const color  = isBull ? C.bull : C.bear
    const yO = scale(open),  yC = scale(close)
    const yH = scale(high),  yL = scale(low)
    const top = Math.min(yO, yC)
    const bot = Math.max(yO, yC)
    const cx  = x + width / 2
    return (
      <g>
        <line x1={cx} y1={yH} x2={cx} y2={top}
              stroke={C.textSecond} strokeWidth={1}/>
        <line x1={cx} y1={bot} x2={cx} y2={yL}
              stroke={C.textSecond} strokeWidth={1}/>
        <rect x={x+1} y={top} width={Math.max(width-2,1)}
              height={Math.max(bot-top,1)}
              fill={color} stroke={color} strokeWidth={0.5}/>
      </g>
    )
  }

  // Custom Tooltip
  const ChartTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0]?.payload
    if (!d) return null
    const isBull = d.close >= d.open
    return (
      <div style={{
        background: C.bgElevated, border: `1px solid ${C.borderStrong}`,
        borderRadius: 4, padding: '10px 14px', fontSize: 12,
        color: C.textSecond, pointerEvents: 'none', minWidth: 160,
      }}>
        <div style={{ color: C.textPrimary, marginBottom: 6,
                      fontSize: 11, fontWeight: 500 }}>{d.date}</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
                      gap: '3px 12px', fontFamily: MONO }}>
          <span>O: <b style={{ color: C.textPrimary }}>{fmtPrice(d.open)}</b></span>
          <span>H: <b style={{ color: C.bull }}>{fmtPrice(d.high)}</b></span>
          <span>L: <b style={{ color: C.bear }}>{fmtPrice(d.low)}</b></span>
          <span>C: <b style={{ color: isBull ? C.bull : C.bear }}>
            {fmtPrice(d.close)}</b></span>
        </div>
        <div style={{ marginTop: 5, fontFamily: MONO, color: C.textMuted }}>
          Vol: {fmtVol(d.volume)}
        </div>
      </div>
    )
  }

  // Subchart label
  const SubLabel = ({ text }) => (
    <div style={{
      fontSize: 10, fontWeight: 500, letterSpacing: '0.07em',
      textTransform: 'uppercase', color: C.textMuted,
      padding: '4px 8px 0',
    }}>{text}</div>
  )

  // Y domain
  const yMin = chartData.length
    ? Math.min(...chartData.map(d => d.low))   * 0.995 : 0
  const yMax = chartData.length
    ? Math.max(...chartData.map(d => d.high))  * 1.005 : 100
  const xInterval = Math.max(1, Math.floor(chartData.length / 8))

  return (
    <div style={{ display: 'flex', height: '100%',
                  background: C.bgPage, color: C.textPrimary }}>

      {/* MAIN AREA */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex',
                    flexDirection: 'column', overflow: 'hidden' }}>

        {/* TOOLBAR */}
        <div style={{
          height: 48, flexShrink: 0,
          background: C.bgCard,
          borderBottom: `1px solid ${C.border}`,
          display: 'flex', alignItems: 'center',
          padding: '0 12px', gap: 10,
        }}>

          {/* Search */}
          <div style={{ position: 'relative' }}>
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); setShowDrop(true) }}
              onFocus={() => setShowDrop(true)}
              onBlur={() => setTimeout(() => setShowDrop(false), 150)}
              placeholder="Search symbol… e.g. RELIANCE"
              style={{
                width: 220, height: 32,
                background: C.bgElevated,
                border: `1px solid ${C.borderStrong}`,
                borderRadius: 4, padding: '0 10px',
                fontSize: 13, color: C.textPrimary,
                outline: 'none',
              }}
            />
            {showDrop && searchResults.length > 0 && (
              <div style={{
                position: 'absolute', top: 36, left: 0, zIndex: 100,
                width: 260, background: C.bgCard,
                border: `1px solid ${C.border}`,
                borderRadius: 4, overflow: 'hidden',
                maxHeight: 240, overflowY: 'auto',
              }}>
                {searchResults.map(s => (
                  <div key={s.symbol}
                    onMouseDown={() => {
                      setSymbol(s.symbol)
                      setSearch('')
                      setShowDrop(false)
                    }}
                    style={{
                      padding: '7px 12px', cursor: 'pointer',
                      borderBottom: `1px solid ${C.border}`,
                    }}
                    onMouseEnter={e =>
                      e.currentTarget.style.background = C.bgHover}
                    onMouseLeave={e =>
                      e.currentTarget.style.background = 'transparent'}
                  >
                    <span style={{ fontFamily: MONO, fontSize: 12,
                                   color: C.textPrimary, fontWeight: 500 }}>
                      {s.symbol}
                    </span>
                    <span style={{ fontSize: 11, color: C.textSecond,
                                   marginLeft: 8 }}>
                      {s.name}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Timeframe buttons */}
          <div style={{
            display: 'flex', border: `1px solid ${C.border}`,
            borderRadius: 4, overflow: 'hidden',
          }}>
            {Object.keys(PERIOD_MAP).map((tf, i, arr) => (
              <button key={tf}
                onClick={() => setTimeframe(tf)}
                style={{
                  height: 30, padding: '0 11px',
                  background: timeframe === tf ? C.accentSubtle : 'transparent',
                  color: timeframe === tf ? C.accent : C.textSecond,
                  border: 'none',
                  borderRight: i < arr.length - 1
                    ? `1px solid ${C.border}` : 'none',
                  fontSize: 12, cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >{tf}</button>
            ))}
          </div>

          {/* Indicator toggles */}
          {[
            ['EMA',  showEMA,  setShowEMA],
            ['BB',   showBB,   setShowBB],
            ['VOL',  showVol,  setShowVol],
            ['RSI',  showRSI,  setShowRSI],
            ['MACD', showMACD, setShowMACD],
          ].map(([label, active, setter]) => (
            <button key={label}
              onClick={() => setter(v => !v)}
              style={{
                height: 28, padding: '0 10px',
                background: active ? C.accentSubtle : 'transparent',
                color: active ? C.accent : C.textSecond,
                border: `1px solid ${active
                  ? C.accent + '44' : C.border}`,
                borderRadius: 3, fontSize: 11, cursor: 'pointer',
                fontFamily: 'inherit', letterSpacing: '0.04em',
              }}
            >{label}</button>
          ))}

          {/* Data source badge */}
          <div style={{ marginLeft: 'auto', display: 'flex',
                        alignItems: 'center', gap: 5 }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: dataSource === 'live' ? C.bull : '#F59E0B',
              flexShrink: 0,
            }}/>
            <span style={{ fontSize: 10, color: C.textMuted }}>
              {dataSource === 'live' ? 'Live EOD' : 'Demo Data'}
            </span>
          </div>
        </div>

        {/* DEBUG / ERROR PANEL */}
        {(status === 'error' || status === 'loading') && (
          <div style={{
            background: status === 'error' ? '#2D1A1A' : C.bgCard,
            borderBottom: `1px solid ${
              status === 'error' ? '#5C2828' : C.border}`,
            padding: '6px 16px', fontSize: 11,
            color: C.textSecond,
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            {status === 'loading' && (
              <>
                <div style={{
                  width: 10, height: 10, borderRadius: '50%',
                  border: `2px solid ${C.border}`,
                  borderTopColor: C.accent,
                  animation: 'spin 0.8s linear infinite',
                  flexShrink: 0,
                }}/>
                <span>Fetching {symbol} data from Yahoo Finance…</span>
              </>
            )}
            {status === 'error' && (
              <>
                <span style={{ color: C.bear, fontWeight: 600 }}>
                  API Error:
                </span>
                <span style={{ color: '#F87171' }}>{error}</span>
                <span style={{ color: C.textMuted }}>
                  — showing demo data
                </span>
                <button
                  onClick={() => {
                    const s = symbol
                    setSymbol('')
                    setTimeout(() => setSymbol(s), 50)
                  }}
                  style={{
                    marginLeft: 'auto', fontSize: 11,
                    color: C.accent, background: 'none',
                    border: `1px solid ${C.accent}44`,
                    borderRadius: 3, padding: '2px 10px',
                    cursor: 'pointer',
                  }}
                >Retry</button>
              </>
            )}
          </div>
        )}

        {/* QUOTE BAR */}
        {displayQuote && (
          <div style={{
            height: 40, flexShrink: 0,
            background: C.bgPage,
            borderBottom: `1px solid ${C.border}`,
            display: 'flex', alignItems: 'center',
            padding: '0 16px', gap: 16,
            fontFamily: MONO, fontSize: 12,
          }}>
            <span style={{ fontSize: 14, fontWeight: 600,
                           color: C.textPrimary }}>{symbol}</span>
            <span style={{ fontSize: 11, color: C.textSecond,
                           fontFamily: 'inherit' }}>
              {fundamentals?.company_name ??
               STOCK_LIST.find(s => s.symbol === symbol)?.name ?? ''}
            </span>
            <span style={{ fontSize: 18, color: C.textPrimary,
                           marginLeft: 4 }}>
              ₹{fmtPrice(displayQuote.ltp)}
            </span>
            <span style={{
              color: displayQuote.change_pct >= 0 ? C.bull : C.bear,
            }}>
              {displayQuote.change_pct >= 0 ? '+' : ''}
              {fmtPrice(displayQuote.change)} (
              {displayQuote.change_pct >= 0 ? '+' : ''}
              {displayQuote.change_pct?.toFixed(2)}%)
            </span>
            {[
              ['O', displayQuote.open],
              ['H', displayQuote.high],
              ['L', displayQuote.low],
              ['C', displayQuote.close],
            ].map(([label, val]) => (
              <span key={label} style={{ color: C.textSecond }}>
                {label}:{' '}
                <span style={{ color: C.textPrimary }}>
                  ₹{fmtPrice(val)}
                </span>
              </span>
            ))}
            <span style={{ color: C.textSecond }}>
              Vol:{' '}
              <span style={{ color: C.textPrimary }}>
                {fmtVol(displayQuote.volume)}
              </span>
            </span>
            {fundamentals?.['52w_high'] && (
              <>
                <span style={{ color: C.textSecond }}>
                  52W H:{' '}
                  <span style={{ color: C.bull }}>
                    ₹{fmtPrice(fundamentals['52w_high'])}
                  </span>
                </span>
                <span style={{ color: C.textSecond }}>
                  52W L:{' '}
                  <span style={{ color: C.bear }}>
                    ₹{fmtPrice(fundamentals['52w_low'])}
                  </span>
                </span>
              </>
            )}
          </div>
        )}

        {/* CHARTS */}
        <div style={{ flex: 1, overflow: 'auto', padding: '0 0 16px' }}>

          {/* Loading skeleton */}
          {status === 'loading' && !chartData.length && (
            <div style={{ padding: 16 }}>
              {[400, 80, 80, 80].map((h, i) => (
                <div key={i} style={{
                  height: h, background: C.bgCard,
                  borderRadius: 4, marginBottom: 8,
                  animation: 'pulse 1.4s ease-in-out infinite',
                  animationDelay: `${i * 0.1}s`,
                }}/>
              ))}
            </div>
          )}

          {chartData.length > 0 && (
            <>
              {/* Price chart */}
              <SubLabel text={`PRICE — ${symbol} (${timeframe})`} />
              <ResponsiveContainer width="100%" height={380}>
                <ComposedChart data={chartData}
                  margin={{ top: 8, right: 60, bottom: 0, left: 0 }}>
                  <CartesianGrid vertical={false}
                    stroke={C.bgCard} strokeDasharray="0"/>
                  <XAxis dataKey="date"
                    tick={{ fill: C.textMuted, fontSize: 10 }}
                    tickLine={false} axisLine={false}
                    interval={xInterval}
                    tickFormatter={d => {
                      const dt = new Date(d)
                      return dt.toLocaleDateString('en-IN',
                        { day: '2-digit', month: 'short' })
                    }}
                  />
                  <YAxis orientation="right"
                    domain={[yMin, yMax]}
                    tick={{ fill: C.textMuted, fontSize: 10 }}
                    tickLine={false} axisLine={false}
                    tickFormatter={v =>
                      `₹${v.toLocaleString('en-IN',
                        { maximumFractionDigits: 0 })}`}
                    width={72}
                  />
                  <Tooltip content={<ChartTooltip />}
                    cursor={{ stroke: C.borderStrong, strokeWidth: 1 }}/>
                  <Bar dataKey="close" shape={<CandlestickBar />}
                    isAnimationActive={false}/>
                  {showEMA && <>
                    <Line type="monotone" dataKey="ema20"
                      stroke={C.ema20} strokeWidth={1}
                      dot={false} isAnimationActive={false}
                      connectNulls name="EMA 20"/>
                    <Line type="monotone" dataKey="ema50"
                      stroke={C.ema50} strokeWidth={1.5}
                      dot={false} isAnimationActive={false}
                      connectNulls name="EMA 50"/>
                    <Line type="monotone" dataKey="ema200"
                      stroke={C.ema200} strokeWidth={1.5}
                      dot={false} isAnimationActive={false}
                      connectNulls name="EMA 200"/>
                  </>}
                  {showBB && <>
                    <Line type="monotone" dataKey="bbUpper"
                      stroke={C.bbColor} strokeWidth={0.5}
                      strokeDasharray="3 3"
                      dot={false} isAnimationActive={false}
                      connectNulls/>
                    <Line type="monotone" dataKey="bbMiddle"
                      stroke={C.bbColor} strokeWidth={0.5}
                      dot={false} isAnimationActive={false}
                      connectNulls/>
                    <Line type="monotone" dataKey="bbLower"
                      stroke={C.bbColor} strokeWidth={0.5}
                      strokeDasharray="3 3"
                      dot={false} isAnimationActive={false}
                      connectNulls/>
                  </>}
                </ComposedChart>
              </ResponsiveContainer>

              {/* Volume chart */}
              {showVol && <>
                <SubLabel text="VOLUME" />
                <ResponsiveContainer width="100%" height={72}>
                  <ComposedChart data={chartData}
                    margin={{ top: 0, right: 60, bottom: 0, left: 0 }}>
                    <CartesianGrid vertical={false} stroke={C.bgCard}/>
                    <YAxis orientation="right" width={72}
                      tick={{ fill: C.textMuted, fontSize: 9 }}
                      tickLine={false} axisLine={false}
                      tickFormatter={v => fmtVol(v)}/>
                    <Bar dataKey="volume" isAnimationActive={false}
                      fill={C.bull + '33'}
                      stroke={C.bull} strokeWidth={0.5}/>
                    <Line type="monotone" dataKey="volMA"
                      stroke={C.textSecond} strokeWidth={1}
                      dot={false} isAnimationActive={false}
                      connectNulls/>
                  </ComposedChart>
                </ResponsiveContainer>
              </>}

              {/* RSI chart */}
              {showRSI && <>
                <SubLabel text="RSI (14)" />
                <ResponsiveContainer width="100%" height={72}>
                  <ComposedChart data={chartData}
                    margin={{ top: 0, right: 60, bottom: 0, left: 0 }}>
                    <CartesianGrid vertical={false} stroke={C.bgCard}/>
                    <YAxis orientation="right" domain={[0, 100]}
                      width={72} ticks={[30, 50, 70]}
                      tick={{ fill: C.textMuted, fontSize: 9 }}
                      tickLine={false} axisLine={false}/>
                    <ReferenceLine y={70}
                      stroke={C.bear + '55'} strokeDasharray="3 3"/>
                    <ReferenceLine y={30}
                      stroke={C.bull + '55'} strokeDasharray="3 3"/>
                    <ReferenceLine y={50} stroke={C.border}/>
                    <Line type="monotone" dataKey="rsi"
                      stroke={C.accent} strokeWidth={1.2}
                      dot={false} isAnimationActive={false}
                      connectNulls/>
                  </ComposedChart>
                </ResponsiveContainer>
              </>}

              {/* MACD chart */}
              {showMACD && <>
                <SubLabel text="MACD (12, 26, 9)" />
                <ResponsiveContainer width="100%" height={72}>
                  <ComposedChart data={chartData}
                    margin={{ top: 0, right: 60, bottom: 0, left: 0 }}>
                    <CartesianGrid vertical={false} stroke={C.bgCard}/>
                    <YAxis orientation="right" width={72}
                      tick={{ fill: C.textMuted, fontSize: 9 }}
                      tickLine={false} axisLine={false}
                      tickFormatter={v => v.toFixed(1)}/>
                    <ReferenceLine y={0} stroke={C.borderStrong}/>
                    <Bar dataKey="macdHist" isAnimationActive={false}
                      fill={C.bull + '55'}/>
                    <Line type="monotone" dataKey="macdLine"
                      stroke={C.accent} strokeWidth={1.2}
                      dot={false} isAnimationActive={false}
                      connectNulls/>
                    <Line type="monotone" dataKey="macdSig"
                      stroke={C.ema20} strokeWidth={1}
                      dot={false} isAnimationActive={false}
                      connectNulls/>
                  </ComposedChart>
                </ResponsiveContainer>
              </>}
            </>
          )}
        </div>
      </div>

      {/* PATTERN PANEL */}
      <div style={{
        width: 272, flexShrink: 0,
        background: C.bgCard,
        borderLeft: `1px solid ${C.border}`,
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '10px 12px 8px',
          borderBottom: `1px solid ${C.border}`,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ fontSize: 10, fontWeight: 500,
                         letterSpacing: '0.07em',
                         textTransform: 'uppercase',
                         color: C.textMuted }}>
            PATTERNS DETECTED
          </span>
          <span style={{
            background: C.accentSubtle, color: C.accent,
            borderRadius: 3, fontSize: 10,
            padding: '1px 6px', fontWeight: 500,
          }}>{patterns.length}</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {patterns.length === 0 ? (
            <div style={{ padding: 16, fontSize: 12,
                          color: C.textMuted, textAlign: 'center' }}>
              No patterns detected for {symbol}
            </div>
          ) : patterns.map(p => {
            const isBull = p.direction === 'BULLISH'
            const conf   = Math.round((p.confidence ?? 0) * 100)
            const confColor = conf >= 70 ? C.bull
                            : conf >= 50 ? '#F59E0B' : C.bear
            return (
              <div key={p.id} style={{
                borderLeft: `2px solid ${isBull ? C.bull : C.bear}`,
                borderBottom: `1px solid ${C.border}`,
                padding: '10px 12px',
              }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center', marginBottom: 6,
                }}>
                  <span style={{ fontSize: 12, fontWeight: 600,
                                 color: C.textPrimary }}>
                    {p.pattern_type.replace(/_/g, ' ')}
                  </span>
                  <span style={{
                    fontSize: 10, padding: '1px 6px', borderRadius: 3,
                    background: (isBull ? C.bull : C.bear) + '1A',
                    color: isBull ? C.bull : C.bear,
                  }}>
                    {isBull ? '▲' : '▼'} {p.direction}
                  </span>
                </div>
                <div style={{ marginBottom: 4 }}>
                  <div style={{ height: 3, background: C.bgElevated,
                                borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', width: `${conf}%`,
                      background: confColor,
                    }}/>
                  </div>
                  <div style={{ fontSize: 10, color: C.textMuted,
                                fontFamily: MONO, marginTop: 2 }}>
                    {conf}% confidence
                  </div>
                </div>
                <div style={{ fontSize: 11, color: C.textSecond,
                              marginBottom: 6, lineHeight: 1.5,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden' }}>
                  {p.description}
                </div>
                {p.backtest && (
                  <div style={{ fontSize: 10, color: C.textMuted,
                                fontFamily: MONO }}>
                    Win rate:{' '}
                    <span style={{ color: C.bull }}>
                      {Math.round(p.backtest.win_rate * 100)}%
                    </span>
                    {' · '}Avg:{' '}
                    <span style={{ color: C.bull }}>
                      +{p.backtest.avg_return_pct}%
                    </span>
                    {' · '}{p.backtest.sample_size} trades
                  </div>
                )}
                {p.key_levels && (
                  <div style={{ marginTop: 6, fontSize: 10,
                                display: 'flex', gap: 8,
                                flexWrap: 'wrap', fontFamily: MONO }}>
                    <span style={{ color: C.bull }}>
                      S: ₹{fmtPrice(p.key_levels.support)}
                    </span>
                    <span style={{ color: C.bear }}>
                      R: ₹{fmtPrice(p.key_levels.resistance)}
                    </span>
                    <span style={{ color: C.accent }}>
                      T: ₹{fmtPrice(p.key_levels.target)}
                    </span>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {fundamentals && (
          <div style={{
            borderTop: `1px solid ${C.border}`,
            padding: '10px 12px',
          }}>
            <div style={{ fontSize: 10, fontWeight: 500,
                          letterSpacing: '0.07em',
                          textTransform: 'uppercase',
                          color: C.textMuted, marginBottom: 8 }}>
              FUNDAMENTALS
            </div>
            {[
              ['P/E Ratio',  fundamentals.pe_ratio?.toFixed(1)],
              ['P/B Ratio',  fundamentals.pb_ratio?.toFixed(2)],
              ['Mkt Cap',    fundamentals.market_cap_cr
                ? `₹${(fundamentals.market_cap_cr/100).toFixed(0)}K Cr`
                : null],
              ['Beta',       fundamentals.beta?.toFixed(2)],
            ].filter(([, v]) => v != null).map(([label, val]) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between',
                fontSize: 11, marginBottom: 4,
              }}>
                <span style={{ color: C.textSecond }}>{label}</span>
                <span style={{ fontFamily: MONO,
                               color: C.textPrimary }}>{val}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
