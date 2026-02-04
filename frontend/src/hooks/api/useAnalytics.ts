/**
 * Analytics API Hooks
 * React Query hooks for analytics endpoints
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// Types
interface LatestPriceParams {
  symbols?: string[];
}

interface PriceData {
  symbol: string;
  price: number;
  timestamp: string;
  volume_24h?: number;
  change_24h?: number;
}

interface LatestPricesResponse {
  prices: PriceData[];
}

interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlesResponse {
  candles: Candle[];
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

interface AggregatedMetric {
  metric_type: string;
  value: number;
  timestamp?: string;
}

interface MetricsResponse {
  metrics: AggregatedMetric[];
}

interface WatchlistItem {
  symbol: string;
  added_at: string;
}

interface WatchlistResponse {
  watchlist: WatchlistItem[];
}

/**
 * Get latest prices for symbols
 */
export function useLatestPrices(params?: LatestPriceParams) {
  return useQuery<LatestPricesResponse>({
    queryKey: ['latest-prices', params?.symbols],
    queryFn: async () => {
      const queryParams = params?.symbols
        ? `?symbols=${params.symbols.join(',')}`
        : '';
      return apiClient.get<LatestPricesResponse>(`/api/v1/analytics/market-data/latest${queryParams}`);
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}

/**
 * Get OHLCV candles
 */
export function useCandles(params: CandleParams) {
  return useQuery<CandlesResponse>({
    queryKey: ['candles', params],
    queryFn: async () => {
      const queryParams = new URLSearchParams({
        symbol: params.symbol,
        interval: params.interval,
        start_time: params.start_time,
        end_time: params.end_time,
        ...(params.limit && { limit: params.limit.toString() }),
      });
      return apiClient.get<CandlesResponse>(`/api/v1/analytics/candles?${queryParams}`);
    },
    enabled: !!params.symbol,
  });
}

/**
 * Query market data
 */
export function useMarketDataQuery() {
  return useMutation<any, Error, any>({
    mutationFn: async (params: any) => {
      return apiClient.post<any>('/api/v1/analytics/market-data/query', params);
    },
  });
}

/**
 * Get aggregated metrics
 */
export function useAggregatedMetrics(params: MetricsParams) {
  return useQuery<MetricsResponse>({
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
      
      return apiClient.get<MetricsResponse>(`/api/v1/analytics/metrics/aggregated?${queryParams}`);
    },
    enabled: !!params.symbol,
  });
}

/**
 * Get user watchlist
 */
export function useWatchlist() {
  return useQuery<WatchlistResponse>({
    queryKey: ['watchlist'],
    queryFn: async () => {
      return apiClient.get<WatchlistResponse>('/api/v1/analytics/watchlist');
    },
  });
}






