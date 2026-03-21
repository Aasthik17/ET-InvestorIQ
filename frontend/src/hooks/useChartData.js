import { useState, useEffect, useRef } from 'react'

/**
 * Fetches real EOD OHLCV data from the backend.
 *
 * Returns:
 *   ohlcv        — array of {date, open, high, low, close, volume}
 *   quote        — {ltp, change, change_pct, open, high, low, volume}
 *   fundamentals — {company_name, pe_ratio, 52w_high, 52w_low, ...}
 *   status       — 'idle' | 'loading' | 'success' | 'error'
 *   error        — error message string if status === 'error'
 *   dataSource   — 'live' | 'mock'
 */
export function useChartData(symbol, period = '1y') {
  const [ohlcv,        setOhlcv]        = useState([])
  const [quote,        setQuote]        = useState(null)
  const [fundamentals, setFundamentals] = useState(null)
  const [status,       setStatus]       = useState('idle')
  const [error,        setError]        = useState(null)
  const [dataSource,   setDataSource]   = useState('mock')
  const abortRef = useRef(null)

  // Simple in-memory cache — avoids re-fetching on re-renders
  const cacheRef = useRef({})

  useEffect(() => {
    if (!symbol) return

    const cacheKey = `${symbol}__${period}`

    // If cached, apply immediately without loading state
    if (cacheRef.current[cacheKey]) {
      const c = cacheRef.current[cacheKey]
      setOhlcv(c.ohlcv)
      setQuote(c.quote)
      setFundamentals(c.fundamentals)
      setStatus('success')
      setDataSource('live')
      setError(null)
      return
    }

    // Cancel any in-flight fetch
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    setStatus('loading')
    setError(null)

    const url = `/api/chart-data/${encodeURIComponent(symbol)}?period=${period}`

    fetch(url, { signal: abortRef.current.signal })
      .then(async (res) => {
        if (!res.ok) {
          let detail = `HTTP ${res.status}`
          try {
            const body = await res.json()
            detail = body.detail || detail
          } catch {}
          throw new Error(detail)
        }
        return res.json()
      })
      .then((data) => {
        if (!data.ohlcv || data.ohlcv.length === 0) {
          throw new Error('API returned empty OHLCV array')
        }

        const result = {
          ohlcv:        data.ohlcv,
          quote:        data.quote,
          fundamentals: data.fundamentals,
        }

        // Cache it
        cacheRef.current[cacheKey] = result

        setOhlcv(result.ohlcv)
        setQuote(result.quote)
        setFundamentals(result.fundamentals)
        setStatus('success')
        setDataSource('live')
        setError(null)
      })
      .catch((err) => {
        if (err.name === 'AbortError') return

        // Surface the real error — do NOT silently use mock data
        console.error(`[useChartData] Failed to fetch ${symbol}:`, err.message)
        setStatus('error')
        setError(err.message)
        setDataSource('mock')
      })

    return () => abortRef.current?.abort()
  }, [symbol, period])

  return { ohlcv, quote, fundamentals, status, error, dataSource }
}
