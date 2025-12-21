'use client';

/**
 * Analytics Page
 * Charts, tables, and metrics for market analysis
 */

import { useState, useEffect } from 'react';
import { SymbolSelector } from '@/components/analytics/symbol-selector';
import { TimeRangePicker, getTimeRangeDates } from '@/components/analytics/time-range-picker';
import { CandlestickChart } from '@/components/analytics/candlestick-chart';
import { MarketDataTable } from '@/components/analytics/market-data-table';
import { MetricsDisplay } from '@/components/analytics/metrics-display';
import { Separator } from '@/components/ui/separator';
import { useCandles, useAggregatedMetrics, useMarketDataQuery } from '@/hooks/api/useAnalytics';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';
import { useInterval } from '@/hooks/useInterval';

export default function AnalyticsPage() {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeRange, setTimeRange] = useState('1h');
  const [interval, setInterval] = useState('1m');
  const [dateRange, setDateRange] = useState(getTimeRangeDates('1h'));

  const { start_time, end_time } = dateRange;

  // Update dates when timeRange changes
  useEffect(() => {
    setDateRange(getTimeRangeDates(timeRange));
  }, [timeRange]);

  // Update dates every minute to keep the window sliding ("now" stays current)
  useInterval(() => {
    setDateRange(getTimeRangeDates(timeRange));
  }, 60000);

  // Fetch candle data
  const { 
    data: candlesResponse, 
    isLoading: candlesLoading,
    error: candlesError 
  } = useCandles({
    symbol,
    interval,
    start_time,
    end_time,
    limit: 1000,
  });

  // Fetch aggregated metrics
  const { 
    data: metricsResponse,
    isLoading: metricsLoading 
  } = useAggregatedMetrics({
    symbol,
    start_time,
    end_time,
  });

  // Market data query mutation for the table
  const { 
    mutate: queryMarketData,
    data: marketDataResponse,
    isPending: marketDataLoading 
  } = useMarketDataQuery();

  // Query market data when symbol or time range changes
  useEffect(() => {
    queryMarketData({
      symbols: [symbol],
      start_time,
      end_time,
      limit: 50,
      offset: 0,
      order_by: 'timestamp_desc',
    });
  }, [symbol, start_time, end_time, queryMarketData]);

  // Transform candles data
  const candleData = candlesResponse?.candles || [];

  // Transform metrics data
  const metricsData = (() => {
    const metrics = metricsResponse?.metrics;
    if (!metrics || metrics.length === 0) {
      return {
        averagePrice: 0,
        priceVolatility: 0,
        totalVolume: 0,
        high: 0,
        low: 0,
        tradeCount: 0,
      };
    }
    
    // Convert array of metrics to object
    const metricsMap = metrics.reduce((acc, metric) => {
      acc[metric.metric_type] = metric.value;
      return acc;
    }, {} as Record<string, number>);
    
    return {
      averagePrice: metricsMap['avg_price'] || 0,
      priceVolatility: metricsMap['volatility'] || 0,
      totalVolume: metricsMap['total_volume'] || 0,
      high: metricsMap['max_price'] || 0,
      low: metricsMap['min_price'] || 0,
      tradeCount: metricsMap['trade_count'] || 0,
    };
  })();

  // Transform market data for table
  const tableData = marketDataResponse?.data || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Historical data and market analysis
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <SymbolSelector value={symbol} onChange={setSymbol} />
        <TimeRangePicker value={timeRange} onChange={setTimeRange} />
      </div>

      <Separator />

      {/* Error State */}
      {candlesError && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Error Loading Data
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {candlesError.message || 'Failed to load analytics data. Please try again.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Charts */}
      <CandlestickChart
        data={candleData}
        interval={interval}
        onIntervalChange={setInterval}
        isLoading={candlesLoading}
      />

      {/* Metrics */}
      <MetricsDisplay 
        data={metricsData} 
        symbol={symbol}
        isLoading={metricsLoading}
      />

      <Separator />

      {/* Table */}
      <MarketDataTable 
        data={tableData}
        isLoading={marketDataLoading}
      />
    </div>
  );
}
