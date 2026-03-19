/**
 * useSignals — React Query hooks for Opportunity Radar.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { radarAPI } from '../services/api'

export function useSignals(filters = {}) {
  return useQuery({
    queryKey: ['signals', filters],
    queryFn: () => radarAPI.signals(filters),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

export function useRefreshSignals() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: radarAPI.refresh,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['signals'] }),
  })
}

export function useInsiderTrades(params = {}) {
  return useQuery({
    queryKey: ['insider', params],
    queryFn: () => radarAPI.insider(params),
    staleTime: 5 * 60_000,
  })
}

export function useBulkDeals() {
  return useQuery({
    queryKey: ['bulkDeals'],
    queryFn: radarAPI.bulkDeals,
    staleTime: 5 * 60_000,
  })
}

export function useFiiDii(days = 30) {
  return useQuery({
    queryKey: ['fiiDii', days],
    queryFn: () => radarAPI.fiiDii(days),
    staleTime: 10 * 60_000,
  })
}

export function useRadarSummary() {
  return useQuery({
    queryKey: ['radarSummary'],
    queryFn: radarAPI.summary,
    staleTime: 30_000,
  })
}
