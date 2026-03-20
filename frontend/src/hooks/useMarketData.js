import { useQuery }     from '@tanstack/react-query'
import { useWebSocket }  from './useWebSocket'
import { useState, useEffect } from 'react'
import api from '../services/api'

// ─────────────────────────────────────────────────────────────────────────────
// DASHBOARD
// Live index prices via WebSocket (4s), supplemented by REST snapshot (5 min)
// ─────────────────────────────────────────────────────────────────────────────

export function useDashboardData() {
  const { data: wsData, status: wsStatus } = useWebSocket('/ws/prices')

  const overview = useQuery({
    queryKey:        ['market_overview'],
    queryFn:         () => api.get('/market/overview').then(r => r.data),
    staleTime:       60_000,
    refetchInterval: 300_000,  // every 5 minutes
    retry:           2,
  })

  const [indices, setIndices] = useState(null)
  const [movers,  setMovers]  = useState(null)

  useEffect(() => {
    if (wsData?.type === 'index_update') {
      setIndices(wsData.indices)
      if (wsData.movers) setMovers(wsData.movers)
    }
  }, [wsData])

  return {
    // Live prices overlay WS data on top of REST snapshot default
    indices:     indices  || overview.data?.indices,
    movers: {
      gainers:   movers?.gainers || overview.data?.top_gainers  || [],
      losers:    movers?.losers  || overview.data?.top_losers   || [],
    },
    fiiDii:      overview.data?.fii_dii_7d         || [],
    sectors:     overview.data?.sector_performance || [],
    ipos:        overview.data?.ipo_pipeline       || { current: [], upcoming: [], listed: [] },
    breadth:     overview.data?.breadth            || { advances: 0, declines: 0, unchanged: 0 },
    marketStatus: overview.data?.market_status     || { is_open: false, status_text: 'Unknown' },
    wsStatus,
    isLoading:   overview.isLoading && !indices,
    isError:     overview.isError,
    lastUpdated: overview.dataUpdatedAt,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// OPPORTUNITY RADAR
// REST polling every 5 minutes — signals don't need sub-second freshness
// ─────────────────────────────────────────────────────────────────────────────

export function useRadarData(filters = {}) {
  const params = new URLSearchParams(
    Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== null && v !== undefined && v !== ''))
  ).toString()

  return useQuery({
    queryKey:        ['radar_signals', filters],
    queryFn:         () => api.get(`/radar/signals${params ? '?' + params : ''}`).then(r => r.data),
    staleTime:       120_000,
    refetchInterval: 300_000,
    refetchOnWindowFocus: false,
    retry:           2,
  })
}

export function useInsiderTrades() {
  return useQuery({
    queryKey:        ['insider_trades'],
    queryFn:         () => api.get('/radar/insider').then(r => r.data),
    staleTime:       300_000,
    refetchInterval: 600_000,
    retry:           2,
  })
}

export function useBulkDeals() {
  return useQuery({
    queryKey:        ['bulk_deals'],
    queryFn:         () => api.get('/radar/bulk-deals').then(r => r.data),
    staleTime:       300_000,
    refetchInterval: 600_000,
    retry:           2,
  })
}

export function useFilings() {
  return useQuery({
    queryKey:        ['filings'],
    queryFn:         () => api.get('/radar/filings').then(r => r.data),
    staleTime:       300_000,
    refetchInterval: 900_000,
    retry:           2,
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// CHART INTELLIGENCE
// OHLCV fetched once per symbol/period (1h cache), live price via WebSocket
// ─────────────────────────────────────────────────────────────────────────────

export function useStockChart(symbol, period = '1y', interval = '1d') {
  const ohlcvQuery = useQuery({
    queryKey:        ['ohlcv', symbol, period, interval],
    queryFn:         () =>
      api.get(`/charts/ohlcv/${symbol}?period=${period}&interval=${interval}`)
         .then(r => r.data),
    enabled:          !!symbol,
    staleTime:        3_600_000,   // 1 hour
    keepPreviousData: true,
    retry:            2,
  })

  const { data: wsData } = useWebSocket(symbol ? `/ws/stock/${symbol}` : null)
  const [liveQuote, setLiveQuote] = useState(null)

  useEffect(() => {
    if (wsData?.type === 'stock_update') {
      setLiveQuote(wsData.quote)
    }
  }, [wsData])

  // Reset live quote when symbol changes
  useEffect(() => {
    setLiveQuote(null)
  }, [symbol])

  return {
    ...ohlcvQuery,
    liveQuote,
    ohlcv:        ohlcvQuery.data?.ohlcv        || [],
    fundamentals: ohlcvQuery.data?.fundamentals || {},
    quote:        liveQuote || ohlcvQuery.data?.quote || {},
  }
}

export function usePatternScan(symbol) {
  return useQuery({
    queryKey:    ['patterns', symbol],
    queryFn:     () => api.get(`/charts/scan/${symbol}`).then(r => r.data),
    enabled:     !!symbol,
    staleTime:   1_800_000,
    retry:       2,
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// MARKET STATUS (standalone — used by Navbar/Sidebar)
// ─────────────────────────────────────────────────────────────────────────────

export function useMarketStatus() {
  return useQuery({
    queryKey:        ['market_status'],
    queryFn:         () => api.get('/market/overview').then(r => r.data?.market_status),
    staleTime:       60_000,
    refetchInterval: 120_000,
    retry:           1,
  })
}

// ─────────────────────────────────────────────────────────────────────────────
// SECTOR PERFORMANCE (standalone — sidebar widget / sector allocation chart)
// ─────────────────────────────────────────────────────────────────────────────

export function useSectorPerformance() {
  return useQuery({
    queryKey:        ['sectors'],
    queryFn:         () => api.get('/market/sectors').then(r => r.data),
    staleTime:       3_600_000,
    refetchInterval: 3_600_000,
    retry:           1,
  })
}
