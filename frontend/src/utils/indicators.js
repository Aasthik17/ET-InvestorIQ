/**
 * ET InvestorIQ — Technical Indicators
 * Client-side computation of RSI, MACD, EMA, Bollinger Bands.
 * All functions operate on plain arrays of closing prices (numbers).
 * No external dependencies required.
 */

// ─────────────────────────────────────────────────────────────────────────────
// EMA — Exponential Moving Average
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Compute EMA for an array of prices.
 * Returns array of same length; leading values filled with null until period is met.
 * @param {number[]} closes
 * @param {number}   period
 * @returns {(number|null)[]}
 */
export function computeEMA(closes, period) {
  if (!closes || closes.length < period) return closes.map(() => null)
  const k      = 2 / (period + 1)
  const result = new Array(closes.length).fill(null)

  // Seed with SMA of first `period` values
  const seed = closes.slice(0, period).reduce((a, b) => a + b, 0) / period
  result[period - 1] = seed

  for (let i = period; i < closes.length; i++) {
    result[i] = closes[i] * k + result[i - 1] * (1 - k)
  }
  return result
}

// ─────────────────────────────────────────────────────────────────────────────
// RSI — Relative Strength Index (Wilder's smoothing)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Compute RSI (14-period default) using Wilder's smoothed average.
 * Returns array of same length; first `period` values are null.
 * @param {number[]} closes
 * @param {number}   period  (default 14)
 * @returns {(number|null)[]}
 */
export function computeRSI(closes, period = 14) {
  if (!closes || closes.length <= period) return closes.map(() => null)
  const result = new Array(closes.length).fill(null)

  // First RSI: average of first `period` gains and losses
  let avgGain = 0
  let avgLoss = 0
  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1]
    if (diff > 0) avgGain += diff
    else           avgLoss += Math.abs(diff)
  }
  avgGain /= period
  avgLoss /= period

  const rs0      = avgLoss === 0 ? 100 : avgGain / avgLoss
  result[period] = 100 - 100 / (1 + rs0)

  // Wilder smoothing for remaining bars
  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1]
    const gain = diff > 0 ? diff : 0
    const loss = diff < 0 ? Math.abs(diff) : 0
    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period
    const rs    = avgLoss === 0 ? 100 : avgGain / avgLoss
    result[i]   = parseFloat((100 - 100 / (1 + rs)).toFixed(2))
  }
  return result
}

// ─────────────────────────────────────────────────────────────────────────────
// MACD — Moving Average Convergence / Divergence
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Compute MACD line, Signal line, and Histogram.
 * @param {number[]} closes
 * @param {number}   fast    EMA period (default 12)
 * @param {number}   slow    EMA period (default 26)
 * @param {number}   signal  EMA of MACD (default 9)
 * @returns {{ macd: number[], signal: number[], histogram: number[] }}
 *          All arrays same length as closes; leading entries null.
 */
export function computeMACD(closes, fast = 12, slow = 26, signal = 9) {
  const emaFast = computeEMA(closes, fast)
  const emaSlow = computeEMA(closes, slow)
  const n       = closes.length

  // MACD line = EMA(fast) - EMA(slow)
  const macdLine = closes.map((_, i) => {
    if (emaFast[i] === null || emaSlow[i] === null) return null
    return parseFloat((emaFast[i] - emaSlow[i]).toFixed(4))
  })

  // Signal line = EMA(9) of MACD line — only over valid values
  const validMacd    = macdLine.filter(v => v !== null)
  const macdStartIdx = macdLine.findIndex(v => v !== null)

  const signalSmall  = computeEMA(validMacd, signal)
  const signalLine   = new Array(n).fill(null)
  for (let i = 0; i < signalSmall.length; i++) {
    signalLine[macdStartIdx + i] = signalSmall[i] === null
      ? null
      : parseFloat(signalSmall[i].toFixed(4))
  }

  // Histogram = MACD - Signal
  const histogram = closes.map((_, i) => {
    if (macdLine[i] === null || signalLine[i] === null) return null
    return parseFloat((macdLine[i] - signalLine[i]).toFixed(4))
  })

  return { macd: macdLine, signal: signalLine, histogram }
}

// ─────────────────────────────────────────────────────────────────────────────
// BOLLINGER BANDS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Compute Bollinger Bands.
 * @param {number[]} closes
 * @param {number}   period  (default 20)
 * @param {number}   stdDev  (default 2)
 * @returns {{ upper: number[], middle: number[], lower: number[] }}
 */
export function computeBollingerBands(closes, period = 20, stdDev = 2) {
  const n      = closes.length
  const upper  = new Array(n).fill(null)
  const middle = new Array(n).fill(null)
  const lower  = new Array(n).fill(null)

  for (let i = period - 1; i < n; i++) {
    const slice = closes.slice(i - period + 1, i + 1)
    const mean  = slice.reduce((a, b) => a + b, 0) / period
    const variance = slice.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / period
    const sd    = Math.sqrt(variance)

    middle[i] = parseFloat(mean.toFixed(2))
    upper[i]  = parseFloat((mean + stdDev * sd).toFixed(2))
    lower[i]  = parseFloat((mean - stdDev * sd).toFixed(2))
  }

  return { upper, middle, lower }
}

// ─────────────────────────────────────────────────────────────────────────────
// SMA — Simple Moving Average
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Compute SMA.
 * @param {number[]} closes
 * @param {number}   period
 * @returns {(number|null)[]}
 */
export function computeSMA(closes, period) {
  return closes.map((_, i) => {
    if (i < period - 1) return null
    const sum = closes.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
    return parseFloat((sum / period).toFixed(2))
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// ATR — Average True Range
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Compute ATR with Wilder's smoothing.
 * @param {Array<{high:number,low:number,close:number}>} candles
 * @param {number} period  (default 14)
 * @returns {(number|null)[]}
 */
export function computeATR(candles, period = 14) {
  if (!candles || candles.length <= period) return candles.map(() => null)
  const n   = candles.length
  const tr  = new Array(n).fill(null)
  const atr = new Array(n).fill(null)

  for (let i = 1; i < n; i++) {
    const h = candles[i].high
    const l = candles[i].low
    const c = candles[i - 1].close
    tr[i] = Math.max(h - l, Math.abs(h - c), Math.abs(l - c))
  }

  // First ATR = SMA(TR, period)
  const firstSlice = tr.slice(1, period + 1).filter(v => v !== null)
  if (firstSlice.length < period) return atr
  atr[period] = firstSlice.reduce((a, b) => a + b, 0) / period

  for (let i = period + 1; i < n; i++) {
    if (tr[i] === null) continue
    atr[i] = parseFloat(((atr[i - 1] * (period - 1) + tr[i]) / period).toFixed(2))
  }
  return atr
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper: extract close prices from OHLCV data array
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Extract close prices from OHLCV rows returned by the API.
 * @param {Array<{close:number}>} ohlcv
 * @returns {number[]}
 */
export function extractCloses(ohlcv) {
  return (ohlcv || []).map(d => d.close)
}

/**
 * Compute all indicators for a given OHLCV dataset.
 * Returns an object mapping indicator name → array aligned to ohlcv.
 */
export function computeAllIndicators(ohlcv) {
  const closes = extractCloses(ohlcv)
  if (!closes.length) return {}

  const rsi               = computeRSI(closes, 14)
  const { macd, signal: macdSignal, histogram } = computeMACD(closes)
  const ema20             = computeEMA(closes, 20)
  const ema50             = computeEMA(closes, 50)
  const ema200            = computeEMA(closes, 200)
  const { upper, middle, lower } = computeBollingerBands(closes, 20)

  // Merge into per-bar objects for Recharts
  return ohlcv.map((bar, i) => ({
    ...bar,
    rsi:         rsi[i],
    macd:        macd[i],
    macdSignal:  macdSignal[i],
    histogram:   histogram[i],
    ema20:       ema20[i],
    ema50:       ema50[i],
    ema200:      ema200[i],
    bbUpper:     upper[i],
    bbMiddle:    middle[i],
    bbLower:     lower[i],
  }))
}
