/**
 * ChartIntelligence — Full-width chart analysis tool.
 * Candlestick chart with RSI + MACD sub-panels, pattern chips, drawer analysis.
 * TradingView/Kite visual language.
 */
import { useState, useMemo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell,
} from 'recharts'
import { Search, ChevronDown } from 'lucide-react'
import { chartsAPI } from '../services/api'
import LoadingSpinner from '../components/common/LoadingSpinner'

const QUICK_STOCKS = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 'ADANIENT.NS']
const PERIODS = ['1W', '1M', '3M', '6M', '1Y']

/* ── Custom candlestick bar ──────────────────────────────────────────── */
const CandleBar = (props) => {
  const { x, y, width, height, open, close, high, low, index } = props
  if (open == null || close == null) return null
  const isBull = close >= open
  const fill = isBull ? '#26A69A' : '#EF5350'
  const bodyH = Math.max(1, Math.abs(height))
  const bodyY = isBull ? y : y + height
  const wickX = x + width / 2

  return (
    <g key={index}>
      {/* Wick */}
      <line x1={wickX} y1={props.highY ?? y} x2={wickX} y2={props.lowY ?? y + bodyH} stroke="#787B86" strokeWidth={0.5} />
      {/* Body */}
      <rect x={x + 1} y={bodyY} width={Math.max(1, width - 2)} height={bodyH} fill={fill} rx={0} />
    </g>
  )
}

/* ── OHLCV tooltip ───────────────────────────────────────────────────── */
function OHLCVTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload || {}
  return (
    <div style={{
      background: '#1E222D', border: '1px solid #2A2E39', borderRadius: '4px',
      padding: '8px 12px', fontSize: '11px', fontFamily: "'JetBrains Mono', monospace",
    }}>
      <div style={{ color: '#787B86', marginBottom: '4px' }}>{label}</div>
      {[['O', d.open], ['H', d.high], ['L', d.low], ['C', d.close]].map(([k, v]) => (
        <div key={k} style={{ color: '#D1D4DC' }}>{k}: ₹{(v||0).toFixed(2)}</div>
      ))}
      {d.volume && <div style={{ color: '#4C525E', marginTop: '4px' }}>Vol: {(d.volume/1e5).toFixed(1)}L</div>}
    </div>
  )
}

/* ── RSI tooltip ─────────────────────────────────────────────────────── */
function RSITooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1E222D', border: '1px solid #2A2E39', borderRadius: '4px',
      padding: '4px 8px', fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: '#2962FF',
    }}>
      RSI: {(payload[0]?.value || 0).toFixed(1)}
    </div>
  )
}

export default function ChartIntelligence() {
  const [symbol, setSymbol] = useState('RELIANCE.NS')
  const [searchInput, setSearchInput] = useState('')
  const [period, setPeriod] = useState('3M')
  const [activeChip, setActiveChip] = useState(null)

  const { data: ohlcv, isLoading: chartLoading } = useQuery({
    queryKey: ['ohlcv', symbol, period],
    queryFn: () => chartsAPI.ohlcv(symbol, period.toLowerCase(), '1d'),
    staleTime: 5 * 60_000,
    enabled: !!symbol,
  })

  const { data: scan } = useQuery({
    queryKey: ['chart-scan', symbol],
    queryFn: () => chartsAPI.scan(symbol),
    staleTime: 5 * 60_000,
    enabled: !!symbol,
  })

  const { data: sr } = useQuery({
    queryKey: ['sr', symbol],
    queryFn: () => chartsAPI.supportResistance(symbol),
    staleTime: 10 * 60_000,
    enabled: !!symbol,
  })

  // Process OHLCV data for charts
  const chartData = useMemo(() => {
    const rows = ohlcv?.data || ohlcv || []
    if (!Array.isArray(rows)) return []
    return rows.map(r => ({
      date: r.date ? new Date(r.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '',
      open: r.open, high: r.high, low: r.low, close: r.close, volume: r.volume,
      rsi: r.rsi,
      macd: r.macd, macd_signal: r.macd_signal,
      macd_hist: r.macd_histogram ?? ((r.macd || 0) - (r.macd_signal || 0)),
    }))
  }, [ohlcv])

  const priceRange = useMemo(() => {
    if (!chartData.length) return { min: 0, max: 100 }
    const highs = chartData.map(d => d.high || 0)
    const lows  = chartData.map(d => d.low  || Infinity)
    const mn = Math.min(...lows)
    const mx = Math.max(...highs)
    const pad = (mx - mn) * 0.05
    return { min: mn - pad, max: mx + pad }
  }, [chartData])

  const patterns = scan?.patterns || []
  const latestRSI = chartData.length ? chartData[chartData.length - 1]?.rsi : null
  const latestPrice = chartData.length ? chartData[chartData.length - 1]?.close : null

  const handleSearch = (e) => {
    e.preventDefault()
    const sym = searchInput.trim().toUpperCase()
    if (sym) { setSymbol(sym.includes('.') ? sym : sym + '.NS'); setSearchInput('') }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: '#131722' }}>

      {/* ── Toolbar ────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        height: '48px', padding: '0 16px',
        background: '#1E222D', borderBottom: '1px solid #2A2E39', flexShrink: 0,
      }}>
        {/* Search */}
        <form onSubmit={handleSearch} style={{ position: 'relative', width: '260px', flexShrink: 0 }}>
          <Search size={13} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: '#4C525E' }} />
          <input
            className="input price"
            placeholder="Search symbol... e.g. RELIANCE"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            style={{ paddingLeft: '30px', fontSize: '12px' }}
          />
        </form>

        {/* Quick select */}
        <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
          {QUICK_STOCKS.map(s => {
            const clean = s.replace('.NS', '')
            const active = symbol === s
            return (
              <button key={s} onClick={() => setSymbol(s)} style={{
                height: '26px', padding: '0 8px', fontSize: '11px',
                background: active ? '#1E2B4D' : 'transparent',
                color: active ? '#2962FF' : '#787B86',
                border: active ? '1px solid #2962FF30' : '1px solid #2A2E39',
                borderRadius: '3px', cursor: 'pointer',
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {clean}
              </button>
            )
          })}
        </div>

        <div className="divider-v" />

        {/* Timeframe buttons */}
        <div className="toggle-group" style={{ flexShrink: 0 }}>
          {PERIODS.map(p => (
            <button key={p} className={`toggle-btn${period === p ? ' active' : ''}`}
              onClick={() => setPeriod(p)} style={{ padding: '0 10px', fontSize: '11px' }}>
              {p}
            </button>
          ))}
        </div>

        <div style={{ marginLeft: 'auto' }}>
          <button className="btn-primary" style={{ height: '28px', fontSize: '12px' }}>
            Scan Universe
          </button>
        </div>
      </div>

      {/* ── Current stock header ──────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '20px',
        padding: '8px 16px', background: '#131722', borderBottom: '1px solid #2A2E39', flexShrink: 0,
      }}>
        <span className="price" style={{ fontSize: '16px', fontWeight: 600, color: '#D1D4DC' }}>
          {symbol.replace('.NS', '')}
        </span>
        {latestPrice && (
          <span className="price" style={{ fontSize: '20px', color: '#D1D4DC' }}>
            ₹{latestPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        )}
        {latestRSI && (
          <span className="text-xs" style={{ color: '#787B86' }}>
            RSI <span className={`price ${latestRSI > 70 ? 'bear' : latestRSI < 30 ? 'bull' : ''}`}
              style={{ color: latestRSI > 70 ? '#EF5350' : latestRSI < 30 ? '#26A69A' : '#D1D4DC' }}>
              {latestRSI.toFixed(1)}
            </span>
          </span>
        )}
        {sr?.pivot && (
          <span className="text-xs" style={{ color: '#787B86' }}>
            Pivot <span className="price" style={{ color: '#D1D4DC' }}>₹{sr.pivot.toFixed(2)}</span>
          </span>
        )}
        {sr?.resistance?.length > 0 && (
          <span className="text-xs" style={{ color: '#787B86' }}>
            R1 <span className="price bear">₹{sr.resistance[0].toFixed(2)}</span>
          </span>
        )}
        {sr?.support?.length > 0 && (
          <span className="text-xs" style={{ color: '#787B86' }}>
            S1 <span className="price bull">₹{sr.support[0].toFixed(2)}</span>
          </span>
        )}
      </div>

      {/* ── Charts area ──────────────────────────────────────────────── */}
      {chartLoading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <LoadingSpinner size={20} text="Loading chart..." />
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}>

          {/* Main candlestick chart — 65% */}
          <div style={{ flex: 65, minHeight: 0, borderBottom: '1px solid #2A2E39' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 60, bottom: 0, left: 0 }}>
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: '#4C525E' }}
                  tickLine={false}
                  axisLine={false}
                  interval={Math.max(1, Math.floor(chartData.length / 8))}
                />
                <YAxis
                  domain={[priceRange.min, priceRange.max]}
                  orientation="right"
                  tick={{ fontSize: 10, fill: '#4C525E', fontFamily: "'JetBrains Mono', monospace" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={v => `₹${v >= 1000 ? (v/1000).toFixed(1)+'k' : v.toFixed(0)}`}
                  width={56}
                />
                <Tooltip content={OHLCVTooltip} />
                {/* Support */}
                {sr?.support?.slice(0, 2).map((v, i) => (
                  <ReferenceLine key={`s${i}`} y={v} stroke="#26A69A" strokeDasharray="4 4" strokeWidth={0.75}
                    label={{ value: `S${i+1}`, position: 'right', fill: '#26A69A', fontSize: 9 }} />
                ))}
                {/* Resistance */}
                {sr?.resistance?.slice(0, 2).map((v, i) => (
                  <ReferenceLine key={`r${i}`} y={v} stroke="#EF5350" strokeDasharray="4 4" strokeWidth={0.75}
                    label={{ value: `R${i+1}`, position: 'right', fill: '#EF5350', fontSize: 9 }} />
                ))}
                {/* Volume bars (bottom portion, faded) */}
                <Bar dataKey="volume" yAxisId="vol" opacity={0.15} isAnimationActive={false}>
                  {chartData.map((d, i) => (
                    <Cell key={i} fill={d.close >= d.open ? '#26A69A' : '#EF5350'} />
                  ))}
                </Bar>
                {/* Price line (fallback if no OHLCV) */}
                <Line type="monotone" dataKey="close" dot={false} strokeWidth={1.5}
                  stroke="#2962FF" isAnimationActive={false}
                  hide={chartData.some(d => d.open != null)}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* RSI sub-chart — 17.5% */}
          <div style={{ flex: 17, minHeight: 0, borderBottom: '1px solid #2A2E39', padding: '0' }}>
            <div style={{ display: 'flex', alignItems: 'center', height: '18px', padding: '0 8px' }}>
              <span className="label">RSI (14)</span>
            </div>
            <div style={{ height: 'calc(100% - 18px)' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 0, right: 60, bottom: 0, left: 0 }}>
                  <XAxis dataKey="date" hide />
                  <YAxis domain={[0, 100]} orientation="right" tick={{ fontSize: 9, fill: '#4C525E' }} tickLine={false} axisLine={false} width={56} ticks={[30, 50, 70]} />
                  <Tooltip content={RSITooltip} />
                  <ReferenceLine y={70} stroke="#EF5350" strokeDasharray="4 4" strokeWidth={0.5} />
                  <ReferenceLine y={30} stroke="#26A69A" strokeDasharray="4 4" strokeWidth={0.5} />
                  <ReferenceLine y={50} stroke="#2A2E39" strokeWidth={0.5} />
                  <Line type="monotone" dataKey="rsi" dot={false} strokeWidth={1.5} stroke="#2962FF" isAnimationActive={false} connectNulls />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* MACD sub-chart — 17.5% */}
          <div style={{ flex: 18, minHeight: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', height: '18px', padding: '0 8px' }}>
              <span className="label">MACD (12, 26, 9)</span>
            </div>
            <div style={{ height: 'calc(100% - 18px)' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 0, right: 60, bottom: 4, left: 0 }}>
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#4C525E' }} tickLine={false} axisLine={false} interval={Math.max(1, Math.floor(chartData.length / 8))} />
                  <YAxis orientation="right" tick={{ fontSize: 9, fill: '#4C525E' }} tickLine={false} axisLine={false} width={56} />
                  <Tooltip contentStyle={{ background: '#1E222D', border: '1px solid #2A2E39', fontSize: '11px' }} />
                  <ReferenceLine y={0} stroke="#2A2E39" />
                  <Bar dataKey="macd_hist" isAnimationActive={false} radius={[1,1,0,0]}>
                    {chartData.map((d, i) => (
                      <Cell key={i} fill={(d.macd_hist ?? 0) >= 0 ? '#26A69A' : '#EF5350'} />
                    ))}
                  </Bar>
                  <Line type="monotone" dataKey="macd" dot={false} stroke="#2962FF" strokeWidth={1} isAnimationActive={false} connectNulls />
                  <Line type="monotone" dataKey="macd_signal" dot={false} stroke="#F59E0B" strokeWidth={1} isAnimationActive={false} connectNulls />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── Pattern chips row ─────────────────────────────────────────── */}
      {patterns.length > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          padding: '6px 16px', background: '#1E222D', borderTop: '1px solid #2A2E39',
          overflow: 'auto', flexShrink: 0,
        }}>
          <span className="label" style={{ flexShrink: 0 }}>Patterns:</span>
          {patterns.map((p, i) => {
            const isBull = (p.direction || '').toUpperCase().includes('BULL')
            const isActive = activeChip === i
            return (
              <button key={i} onClick={() => setActiveChip(isActive ? null : i)} style={{
                display: 'inline-flex', alignItems: 'center', gap: '4px',
                height: '22px', padding: '0 8px', flexShrink: 0,
                background: isActive ? '#1E2B4D' : 'transparent',
                border: isActive ? '1px solid #2962FF' : '1px solid #2A2E39',
                borderRadius: '3px', cursor: 'pointer', fontSize: '11px',
                color: isActive ? '#2962FF' : '#787B86',
              }}>
                <span className={isBull ? 'bull' : 'bear'}>{isBull ? '▲' : '▼'}</span>
                {p.pattern_name?.replace(/_/g, ' ')}
                {p.confidence && <span className="price" style={{ color: '#4C525E' }}>{Math.round(p.confidence * 100)}%</span>}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
