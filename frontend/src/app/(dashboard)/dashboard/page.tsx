'use client';

/**
 * Dashboard Page
 * Main overview page with stats, latest prices, and quick actions
 */

import { useMemo } from 'react';
import { StatsCards } from '@/components/dashboard/stats-cards';
import { LatestPrices } from '@/components/dashboard/latest-prices';
import { QuickActions } from '@/components/dashboard/quick-actions';
import { useLatestPrices } from '@/hooks/api/useAnalytics';
import { useStreams } from '@/hooks/api/useStreams';

const DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];

export default function DashboardPage() {
  // Fetch latest prices for default symbols
  const { data: pricesResponse, isLoading: pricesLoading, error: pricesError } = useLatestPrices({
    symbols: DEFAULT_SYMBOLS,
  });

  // Fetch active streams for stats
  const { data: streamsResponse, isLoading: streamsLoading } = useStreams();

  // Calculate stats from real data
  const stats = useMemo(() => {
    const streams = streamsResponse?.streams || [];
    const activeStreams = streams.filter((s: any) => s.status === 'running').length;
    
    // Get unique symbols from all streams
    const uniqueSymbols = new Set<string>();
    streams.forEach((stream: any) => {
      if (stream.symbols && Array.isArray(stream.symbols)) {
        stream.symbols.forEach((symbol: string) => uniqueSymbols.add(symbol));
      }
    });

    // Calculate total 24h volume from prices
    const prices = pricesResponse?.prices || [];
    const totalVolume = prices.reduce((sum: number, price: any) => 
      sum + (price.volume_24h || 0), 0
    );

    // Get latest update time
    const latestUpdate = prices.length > 0 
      ? prices[0].timestamp 
      : new Date().toISOString();

    return {
      symbolsCount: uniqueSymbols.size || 0,
      activeStreams,
      lastUpdate: latestUpdate,
      volume24h: totalVolume > 0 ? `$${(totalVolume / 1e9).toFixed(2)}B` : 'N/A',
    };
  }, [pricesResponse, streamsResponse]);

  // Transform prices data for LatestPrices component
  const latestPrices = useMemo(() => {
    return pricesResponse?.prices || [];
  }, [pricesResponse]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your crypto analytics platform
        </p>
      </div>

      <StatsCards
        symbolsCount={stats.symbolsCount}
        activeStreams={stats.activeStreams}
        lastUpdate={stats.lastUpdate}
        volume24h={stats.volume24h}
        isLoading={streamsLoading}
      />

      <div className="grid gap-6 md:grid-cols-2">
        <LatestPrices 
          data={latestPrices} 
          isLoading={pricesLoading}
          error={pricesError?.message}
        />
        <QuickActions />
      </div>
    </div>
  );
}
