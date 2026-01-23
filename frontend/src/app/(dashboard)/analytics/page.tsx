'use client';

/**
 * Analytics Page
 * Symbol Details and Market Data analysis
 */

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { SymbolSelector } from '@/components/analytics/symbol-selector';
import { PriceTicker } from '@/components/price/price-ticker';
import { InteractiveChart } from '@/components/price/interactive-chart';
import { PriceStats } from '@/components/price/price-stats';
import { MarketDataTable } from '@/components/analytics/market-data-table';
import { Separator } from '@/components/ui/separator';
import { useTicker } from '@/hooks/api/usePriceData';
import { useWatchlist } from '@/hooks/api/useWatchlist';
import { useMarketDataQuery } from '@/hooks/api/useAnalytics';
import { useRealtimePrice } from '@/hooks/useRealtimePrice';
import { toUTCIso } from '@/lib/time';
import { subDays } from 'date-fns';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Plus } from 'lucide-react';

function AnalyticsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const urlSymbol = searchParams.get('symbol');
  const initializedRef = useRef(false);
  
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');

  // Fetch watchlist
  const { data: watchlistData, isLoading: isWatchlistLoading } = useWatchlist();
  const watchlistSymbols = watchlistData?.symbols || [];

  // Set initial symbol from URL or watchlist (only once)
  useEffect(() => {
    if (initializedRef.current) return;
    
    if (urlSymbol) {
      setSelectedSymbol(urlSymbol.toUpperCase());
      initializedRef.current = true;
    } else if (watchlistSymbols[0]) {
      setSelectedSymbol(watchlistSymbols[0]);
      initializedRef.current = true;
    }
  }, [urlSymbol, watchlistSymbols]);

  // Handle symbol change - update URL to keep it in sync
  const handleSymbolChange = useCallback((newSymbol: string) => {
    setSelectedSymbol(newSymbol);
    // Update URL without full navigation
    router.replace(`/analytics?symbol=${newSymbol}`, { scroll: false });
  }, [router]);

  // Real-time updates
  const { isConnected } = useRealtimePrice(selectedSymbol);

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
      {/* Header with Symbol Selector and Actions */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Analyze market trends and price movements
          </p>
        </div>
        <div className="flex items-center gap-3">
          <SymbolSelector 
            value={selectedSymbol} 
            onChange={handleSymbolChange} 
            symbols={watchlistSymbols}
          />
        </div>
      </div>

      <Separator />

      {/* Main Section: Symbol Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Chart & Ticker */}
        <div className="lg:col-span-2 space-y-6">
          <PriceTicker 
            symbol={selectedSymbol} 
            data={tickerData} 
            isLoading={isTickerLoading} 
            isConnected={isConnected}
          />
          
          <Separator />
          
          <div className="h-[500px]">
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
              {selectedSymbol} is a decentralized digital currency. It is one of the cryptocurrencies tracked by our platform.
            </p>
          </div>
        </div>
      </div>

      <Separator />

      {/* Bottom Section: Real-time Market Data Table */}
      <div id="market-data" className="space-y-4 pt-4">
        <h3 className="text-xl font-semibold">Real-time Market Data</h3>
        <p className="text-sm text-muted-foreground">
          Recent price updates for {selectedSymbol} in the last 24 hours
        </p>
        <MarketDataTable 
          data={tableData}
          isLoading={marketDataLoading}
        />
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <Suspense fallback={
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Analyze market trends and price movements
          </p>
        </div>
        <div className="h-[400px] flex items-center justify-center">
          <div className="animate-pulse text-muted-foreground">Loading...</div>
        </div>
      </div>
    }>
      <AnalyticsContent />
    </Suspense>
  );
}
