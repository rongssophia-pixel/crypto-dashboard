/**
 * Analytics API Hooks
 * React Query hooks for analytics endpoints
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// Types
interface LatestPriceParams {
  symbols?: string[];
}

interface CandleParams {
  symbol: string;
  interval: string;
  start_time: string;
  end_time: string;
  limit?: number;
}

interface MetricsParams {
  symbol: string;
  start_time: string;
  end_time: string;
  metric_types?: string[];
}

/**
 * Get latest prices for symbols
 */
export function useLatestPrices(params?: LatestPriceParams) {
  return useQuery({
    queryKey: ['latest-prices', params?.symbols],
    queryFn: async () => {
      const queryParams = params?.symbols
        ? `?symbols=${params.symbols.join(',')}`
        : '';
      return apiClient.get(`/api/v1/analytics/market-data/latest${queryParams}`);
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}

/**
 * Get OHLCV candles
 */
export function useCandles(params: CandleParams) {
  return useQuery({
    queryKey: ['candles', params],
    queryFn: async () => {
      const queryParams = new URLSearchParams({
        symbol: params.symbol,
        interval: params.interval,
        start_time: params.start_time,
        end_time: params.end_time,
        ...(params.limit && { limit: params.limit.toString() }),
      });
      return apiClient.get(`/api/v1/analytics/candles?${queryParams}`);
    },
    enabled: !!params.symbol,
  });
}

/**
 * Query market data
 */
export function useMarketDataQuery() {
  return useMutation({
    mutationFn: async (params: any) => {
      return apiClient.post('/api/v1/analytics/market-data/query', params);
    },
  });
}

/**
 * Get aggregated metrics
 */
export function useAggregatedMetrics(params: MetricsParams) {
  return useQuery({
    queryKey: ['metrics', params],
    queryFn: async () => {
      const queryParams = new URLSearchParams({
        symbol: params.symbol,
        start_time: params.start_time,
        end_time: params.end_time,
      });
      
      // Add metric types if specified
      const metricTypes = params.metric_types || [
        'avg_price',
        'total_volume',
        'volatility',
        'min_price',
        'max_price',
        'trade_count',
      ];
      
      metricTypes.forEach(type => {
        queryParams.append('metric_types', type);
      });
      
      return apiClient.get(`/api/v1/analytics/metrics/aggregated?${queryParams}`);
    },
    enabled: !!params.symbol,
  });
}

/**
 * Get user watchlist
 */
export function useWatchlist() {
  return useQuery({
    queryKey: ['watchlist'],
    queryFn: async () => {
      return apiClient.get('/api/v1/analytics/watchlist');
    },
  });
}
