'use client';

/**
 * Analytics Page
 * Symbol Details and Market Data analysis
 */

import { useState, useEffect } from 'react';
import { SymbolSelector } from '@/components/analytics/symbol-selector';
import { PriceTicker } from '@/components/price/price-ticker';
import { InteractiveChart } from '@/components/price/interactive-chart';
import { PriceStats } from '@/components/price/price-stats';
import { MarketDataTable } from '@/components/analytics/market-data-table';
import { Separator } from '@/components/ui/separator';
import { useTicker } from '@/hooks/api/usePriceData';
import { useMarketDataQuery } from '@/hooks/api/useAnalytics';
import { useWatchlist } from '@/hooks/api/useWatchlist';
import { toUTCIso } from '@/lib/time';
import { subDays } from 'date-fns';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Plus } from 'lucide-react';

export default function AnalyticsPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');

  // Fetch watchlist
  const { data: watchlistData, isLoading: isWatchlistLoading } = useWatchlist();
  const watchlistSymbols = watchlistData?.symbols || [];

  // Set initial symbol from watchlist
  useEffect(() => {
    if (watchlistSymbols.length > 0 && !selectedSymbol) {
      setSelectedSymbol(watchlistSymbols[0]);
    }
  }, [watchlistSymbols, selectedSymbol]);

  // Fetch ticker data for selected symbol
  const { data: tickerData, isLoading: isTickerLoading } = useTicker(selectedSymbol);

  // Fetch market data for table
  const { 
    mutate: queryMarketData,
    data: marketDataResponse,
    isPending: marketDataLoading 
  } = useMarketDataQuery();

  // Query market data when symbol changes
  useEffect(() => {
    if (!selectedSymbol) return;
    
    const end = new Date();
    const start = subDays(end, 1);
    
    queryMarketData({
      symbols: [selectedSymbol],
      start_time: toUTCIso(start),
      end_time: toUTCIso(end),
      limit: 50,
      offset: 0,
      order_by: 'timestamp_desc',
    });
  }, [selectedSymbol, queryMarketData]);

  const tableData = marketDataResponse?.data || [];

  // Show empty state if no watchlist symbols
  if (!isWatchlistLoading && watchlistSymbols.length === 0) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Analyze market trends and price movements
          </p>
        </div>

        <div className="flex flex-col items-center justify-center h-[400px] border rounded-lg bg-card/50 border-dashed">
          <div className="text-center space-y-4">
            <h3 className="text-lg font-semibold">No symbols in your watchlist</h3>
            <p className="text-muted-foreground max-w-sm">
              Add symbols to your watchlist from the Dashboard to view analytics.
            </p>
            <Button asChild>
              <Link href="/dashboard">
                <Plus className="w-4 h-4 mr-2" />
                Go to Dashboard
              </Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header with Symbol Selector */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Analyze market trends and price movements
          </p>
        </div>
        <SymbolSelector 
          value={selectedSymbol} 
          onChange={setSelectedSymbol} 
          symbols={watchlistSymbols}
        />
      </div>

      <Separator />

      {/* Main Section: Symbol Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Chart & Ticker */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">{selectedSymbol}</h2>
          </div>
          
          <PriceTicker 
            symbol={selectedSymbol} 
            data={tickerData} 
            isLoading={isTickerLoading} 
          />
          
          <div className="h-[500px] border rounded-lg p-4 bg-card">
            <InteractiveChart symbol={selectedSymbol} />
          </div>
        </div>

        {/* Stats Panel */}
        <div className="space-y-6">
          <h3 className="font-semibold text-lg">Market Stats (24h)</h3>
          <PriceStats 
            data={tickerData} 
            isLoading={isTickerLoading} 
          />
          
          <div className="bg-muted/30 rounded-lg p-4 border border-border/50">
            <h4 className="font-medium mb-2 text-sm">About {selectedSymbol}</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Real-time market data and analytics for {selectedSymbol}. 
              Track price movements, volume, and volatility.
            </p>
          </div>
        </div>
      </div>

      <Separator />

      {/* Bottom Section: Market Data Table */}
      <div id="market-data" className="space-y-4 pt-4">
        <h3 className="text-xl font-semibold">Recent Market Data</h3>
        <MarketDataTable 
          data={tableData}
          isLoading={marketDataLoading}
        />
      </div>
    </div>
  );
}
