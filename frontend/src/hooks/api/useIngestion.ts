/**
 * Ingestion Service API Hooks
 * React Query hooks for ingestion service endpoints
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface IngestionStatusResponse {
  active_connections: number;
  symbols_count: number;
  symbols: string[];
  is_running: boolean;
}

interface AvailableSymbolsResponse {
  symbols: string[];
  count: number;
}

/**
 * Get ingestion service status including all available symbols
 */
export function useIngestionStatus() {
  return useQuery<IngestionStatusResponse>({
    queryKey: ['ingestion-status'],
    queryFn: async () => {
      return apiClient.get<IngestionStatusResponse>('/api/v1/ingestion/status');
    },
    refetchInterval: 60000, // Refetch every 60 seconds
    staleTime: 30000, // Consider data fresh for 30 seconds
  });
}

/**
 * Get available symbols for watchlist selection
 * Fetches distinct symbols from ClickHouse database
 */
export function useAvailableSymbols() {
  return useQuery<AvailableSymbolsResponse>({
    queryKey: ['available-symbols'],
    queryFn: async () => {
      return apiClient.get<AvailableSymbolsResponse>('/api/v1/analytics/symbols/available');
    },
    refetchInterval: 300000, // Refetch every 5 minutes
    staleTime: 60000, // Consider data fresh for 1 minute
    select: (data) => ({
      symbols: data.symbols,
      count: data.count,
      isLoading: false,
      error: null,
    }),
  });
}

