/**
 * useMarketData — React Query hooks for market data.
 */
import { useQuery } from '@tanstack/react-query'
import { marketAPI } from '../services/api'

export function useMarketOverview() {
  return useQuery({
    queryKey: ['market', 'overview'],
    queryFn: marketAPI.overview,
    refetchInterval: 60_000, // Refresh every 60 seconds
    staleTime: 30_000,
  })
}

export function useSectors() {
  return useQuery({
    queryKey: ['market', 'sectors'],
    queryFn: marketAPI.sectors,
    staleTime: 5 * 60_000,
  })
}

export function useIPOs() {
  return useQuery({
    queryKey: ['market', 'ipos'],
    queryFn: marketAPI.ipos,
    staleTime: 10 * 60_000,
  })
}

export function useStockFundamentals(symbol) {
  return useQuery({
    queryKey: ['stock', symbol],
    queryFn: () => marketAPI.stock(symbol),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  })
}

export function useStockOHLCV(symbol, period = '1y', interval = '1d') {
  const { chartsAPI } = require('../services/api')
  return useQuery({
    queryKey: ['ohlcv', symbol, period, interval],
    queryFn: () => chartsAPI.ohlcv(symbol, period, interval),
    enabled: !!symbol,
    staleTime: 5 * 60_000,
  })
}
