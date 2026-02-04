import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { TimeRangePreset, getTimeRangeFromPreset, getIntervalForTimeRange, toUTCIso } from '@/lib/time';

export interface TickerData {
  symbol: string;
  timestamp: string;
  price: number;
  volume: number;
  bid_price: number;
  ask_price: number;
  open_24h?: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  price_change_24h: number;
  price_change_pct_24h: number;
  trade_count: number;
}

export interface CandleData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  trade_count: number;
}

export function useTicker(symbol: string) {
  return useQuery<TickerData>({
    queryKey: ['ticker', symbol],
    queryFn: async () => {
      return apiClient.get<TickerData>(`/api/v1/analytics/ticker/${symbol}`);
    },
    refetchInterval: 10000, // Fallback polling every 10s
    enabled: !!symbol,
  });
}

export function usePriceCandles(
  symbol: string,
  timeRange: TimeRangePreset
) {
  const interval = getIntervalForTimeRange(timeRange);
  
  return useQuery<{ candles: CandleData[] }>({
    queryKey: ['candles', symbol, timeRange],
    queryFn: async () => {
      // For simplified endpoint, we just pass interval and limit
      // But we can also use the robust endpoint if we want precise time ranges
      // The simplified endpoint `get_candles_by_interval` in backend calculates start time based on limit * interval.
      // But here we want a specific time range (e.g. 1D). 
      // So we should use the robust /candles/query or calculate limit manually.
      // Or we can use the GET /candles endpoint which takes start/end time.
      
      const { start, end } = getTimeRangeFromPreset(timeRange);
      
      // Use the GET /candles endpoint in API Gateway which proxies to analytics-service GET /candles (robust one)
      // Wait, I implemented `get_candles_simple` as GET /candles/{symbol} which takes limit and interval.
      // But API Gateway also has GET /candles which takes start_time/end_time.
      // Let's use the robust one for precise ranges.
      
      const queryParams = new URLSearchParams({
        symbol: symbol,
        interval: interval,
        start_time: toUTCIso(start),
        end_time: toUTCIso(end),
        limit: '1000' // Ensure we get enough points
      });

      return apiClient.get<{ candles: CandleData[] }>(`/api/v1/analytics/candles?${queryParams}`);
    },
    enabled: !!symbol,
  });
}





