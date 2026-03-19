/**
 * ChartIntelligence — Pattern detection and OHLCV charting page.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Search, TrendingUp, TrendingDown, BarChart2, Target } from 'lucide-react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine
} from 'recharts'
import { chartsAPI } from '../services/api'
import LoadingSpinner from '../components/common/LoadingSpinner'

const NSE_SYMBOLS = [
  'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
  'KOTAKBANK.NS', 'BAJFINANCE.NS', 'SBIN.NS', 'HINDUNILVR.NS', 'ITC.NS',
  'AXISBANK.NS', 'TITAN.NS', 'SUNPHARMA.NS', 'TATASTEEL.NS', 'MARUTI.NS',
]

const DIRECTION_COLOR = { BULLISH: 'text-bull', BEARISH: 'text-bear', NEUTRAL: 'text-muted' }
const DIRECTION_BADGE = { BULLISH: 'badge-bull', BEARISH: 'badge-bear', NEUTRAL: 'badge-neutral' }

function PatternBadge({ pattern }) {
  const dir = pattern.direction || 'NEUTRAL'
  const conf = Math.round(pattern.confidence * 100)
  return (
    <div className={`card border ${dir === 'BULLISH' ? 'border-bull/30' : dir === 'BEARISH' ? 'border-bear/30' : 'border-border'} p-3`}>
      <div className="flex items-start justify-between mb-1">
        <span className="text-sm font-semibold text-text-base line-clamp-2 flex-1 mr-2">
          {pattern.pattern_label || pattern.pattern_type}
        </span>
        <span className={`badge ${DIRECTION_BADGE[dir]} flex-shrink-0`}>{dir}</span>
      </div>
      <div className="flex items-center gap-3 mt-2">
        <div>
          <div className="text-xs text-muted">Confidence</div>
          <div className={`font-bold text-sm ${DIRECTION_COLOR[dir]}`}>{conf}%</div>
        </div>
        {pattern.key_levels?.target && (
          <div>
            <div className="text-xs text-muted">Target</div>
            <div className="font-bold text-sm text-text-base">₹{pattern.key_levels.target}</div>
          </div>
        )}
        {pattern.key_levels?.stop_loss && (
          <div>
            <div className="text-xs text-muted">Stop Loss</div>
            <div className="font-bold text-sm text-bear">₹{pattern.key_levels.stop_loss}</div>
          </div>
        )}
      </div>
      {pattern.backtest_stats?.win_rate && (
        <div className="mt-2 pt-2 border-t border-border text-xs text-muted">
          Win Rate: <span className="font-semibold text-text-base">{pattern.backtest_stats.win_rate}%</span>
          &nbsp;·&nbsp;Avg Return: <span className="font-semibold text-bull">{pattern.backtest_stats.avg_return_pct}%</span>
          &nbsp;·&nbsp;{pattern.backtest_stats.sample_size} trades
        </div>
      )}
    </div>
  )
}

function CandleChart({ data, levels }) {
  if (!data || !data.data || data.data.length === 0) return null
  const chartData = data.data.slice(-60).map(d => ({
    date: d.date.slice(5),
    close: d.close,
    volume: d.volume,
    price: d.close,
  }))

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="section-title mb-0">Price Chart (Last 60 Days)</div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted">Current: </span>
          <span className="font-bold text-text-base">₹{data.current_price?.toLocaleString('en-IN')}</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={chartData}>
          <CartesianGrid stroke="#21262D" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#8B949E' }} interval={9} />
          <YAxis tick={{ fontSize: 9, fill: '#8B949E' }} domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{ background: '#161B22', border: '1px solid #21262D', borderRadius: 8, fontSize: 11 }}
            formatter={(v) => [`₹${v.toFixed(2)}`, 'Price']}
          />
          {levels?.support_zones?.slice(0, 2).map((s, i) => (
            <ReferenceLine key={`s${i}`} y={s} stroke="#00C896" strokeDasharray="4 4" strokeOpacity={0.5} />
          ))}
          {levels?.resistance_zones?.slice(0, 2).map((r, i) => (
            <ReferenceLine key={`r${i}`} y={r} stroke="#FF4757" strokeDasharray="4 4" strokeOpacity={0.5} />
          ))}
          <Line type="monotone" dataKey="price" stroke="#0066FF" dot={false} strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 text-xs text-muted">
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-bull opacity-50" /> Support</span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-bear opacity-50" /> Resistance</span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-accent" /> Close</span>
      </div>
    </div>
  )
}

function LevelsCard({ levels }) {
  if (!levels) return null
  return (
    <div className="card">
      <div className="section-title flex items-center gap-2">
        <Target size={14} className="text-accent" /> Key Levels
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <div className="text-muted text-xs mb-1">52W High</div>
          <div className="font-bold text-bear">₹{levels.week_52_high?.toLocaleString('en-IN')}</div>
        </div>
        <div>
          <div className="text-muted text-xs mb-1">52W Low</div>
          <div className="font-bold text-bull">₹{levels.week_52_low?.toLocaleString('en-IN')}</div>
        </div>
        <div>
          <div className="text-muted text-xs mb-1">Pivot</div>
          <div className="font-bold text-text-base">₹{levels.pivot_point?.toLocaleString('en-IN')}</div>
        </div>
        <div>
          <div className="text-muted text-xs mb-1">Current</div>
          <div className="font-bold text-accent">₹{levels.current_price?.toLocaleString('en-IN')}</div>
        </div>
      </div>
      {levels.support_zones?.length > 0 && (
        <div className="mt-3">
          <div className="text-xs text-muted mb-1">Support Zones</div>
          <div className="flex flex-wrap gap-1">
            {levels.support_zones.map((s, i) => (
              <span key={i} className="badge badge-bull">₹{s}</span>
            ))}
          </div>
        </div>
      )}
      {levels.resistance_zones?.length > 0 && (
        <div className="mt-2">
          <div className="text-xs text-muted mb-1">Resistance Zones</div>
          <div className="flex flex-wrap gap-1">
            {levels.resistance_zones.map((r, i) => (
              <span key={i} className="badge badge-bear">₹{r}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ChartIntelligence() {
  const [symbol, setSymbol] = useState('RELIANCE.NS')
  const [inputSymbol, setInputSymbol] = useState('RELIANCE.NS')
  const [period, setPeriod] = useState('1y')

  const { data: scanResult, isLoading: scanLoading } = useQuery({
    queryKey: ['chart-scan', symbol],
    queryFn: () => chartsAPI.scan(symbol),
    staleTime: 15 * 60_000,
  })

  const { data: levels } = useQuery({
    queryKey: ['chart-levels', symbol],
    queryFn: () => chartsAPI.levels(symbol),
    staleTime: 15 * 60_000,
  })

  const { data: ohlcv, isLoading: ohlcvLoading } = useQuery({
    queryKey: ['chart-ohlcv', symbol, period],
    queryFn: () => chartsAPI.ohlcv(symbol, period),
    staleTime: 5 * 60_000,
  })

  const handleSearch = (e) => {
    e.preventDefault()
    const sym = inputSymbol.trim().toUpperCase()
    setSymbol(sym.includes('.') ? sym : sym + '.NS')
  }

  const patterns = scanResult?.patterns || []
  const bullPatterns = patterns.filter(p => p.direction === 'BULLISH').length
  const bearPatterns = patterns.filter(p => p.direction === 'BEARISH').length

  return (
    <div className="p-4 lg:p-6 space-y-5 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-base">Chart Intelligence</h1>
        <p className="text-muted text-sm mt-0.5">AI-powered technical pattern detection</p>
      </div>

      {/* Search + Quick select */}
      <div className="flex flex-col sm:flex-row gap-3">
        <form onSubmit={handleSearch} className="flex gap-2 flex-1">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={inputSymbol}
              onChange={e => setInputSymbol(e.target.value)}
              placeholder="e.g. RELIANCE.NS"
              className="input-dark w-full pl-9 text-sm"
            />
          </div>
          <button type="submit" className="btn-primary">Analyze</button>
        </form>
        <div className="flex gap-1.5 flex-wrap">
          {['1mo', '3mo', '6mo', '1y'].map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors
                ${period === p ? 'bg-accent text-white' : 'bg-card border border-border text-muted hover:text-text-base'}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Quick stock buttons */}
      <div className="flex flex-wrap gap-1.5">
        {NSE_SYMBOLS.slice(0, 10).map(sym => (
          <button
            key={sym}
            onClick={() => { setSymbol(sym); setInputSymbol(sym) }}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors
              ${symbol === sym ? 'bg-accent/20 text-accent border border-accent/40' : 'bg-card border border-border text-muted hover:text-text-base'}`}
          >
            {sym.replace('.NS', '')}
          </button>
        ))}
      </div>

      {/* Loading state */}
      {scanLoading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner text={`Scanning ${symbol} for patterns...`} />
        </div>
      )}

      {/* Results */}
      {!scanLoading && scanResult && (
        <div className="space-y-5">
          {/* Summary bar */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="card">
              <div className="stat-label mb-1">Symbol</div>
              <div className="text-xl font-bold text-text-base">{symbol.replace('.NS', '')}</div>
            </div>
            <div className="card">
              <div className="stat-label mb-1">Price</div>
              <div className="text-xl font-bold text-text-base">₹{scanResult.current_price?.toLocaleString('en-IN')}</div>
              <div className={`text-sm font-semibold mt-0.5 ${scanResult.price_change_1d_pct >= 0 ? 'text-bull' : 'text-bear'}`}>
                {scanResult.price_change_1d_pct >= 0 ? '+' : ''}{scanResult.price_change_1d_pct?.toFixed(2)}%
              </div>
            </div>
            <div className="card">
              <div className="stat-label mb-1">RSI</div>
              <div className={`text-xl font-bold ${scanResult.rsi > 70 ? 'text-bear' : scanResult.rsi < 30 ? 'text-bull' : 'text-text-base'}`}>
                {scanResult.rsi?.toFixed(1)}
              </div>
              <div className="text-xs text-muted mt-0.5">
                {scanResult.rsi > 70 ? 'Overbought' : scanResult.rsi < 30 ? 'Oversold' : 'Neutral'}
              </div>
            </div>
            <div className="card">
              <div className="stat-label mb-1">Bias</div>
              <div className={`text-xl font-bold ${DIRECTION_COLOR[scanResult.overall_bias] || 'text-muted'}`}>
                {scanResult.overall_bias}
              </div>
              <div className="text-xs text-muted">{bullPatterns}▲ {bearPatterns}▼ patterns</div>
            </div>
          </div>

          {/* Chart + Levels */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              {ohlcvLoading ? <div className="card flex items-center justify-center h-64"><LoadingSpinner /></div>
                : <CandleChart data={ohlcv} levels={levels} />}
            </div>
            <LevelsCard levels={levels} />
          </div>

          {/* Detected patterns */}
          <div>
            <h2 className="section-title">
              Detected Patterns ({patterns.length})
            </h2>
            {patterns.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {patterns.map((p, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <PatternBadge pattern={p} />
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="card text-center py-8 text-muted">
                No patterns detected for {symbol} at this time.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
