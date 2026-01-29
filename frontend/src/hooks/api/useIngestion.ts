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
 * This fetches the list of symbols currently being ingested
 */
export function useAvailableSymbols() {
  const { data, isLoading, error } = useIngestionStatus();
  
  return {
    symbols: data?.symbols || [],
    isLoading,
    error,
  };
}

