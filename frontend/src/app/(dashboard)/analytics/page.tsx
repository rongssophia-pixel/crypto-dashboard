'use client';

/**
 * Analytics Page
 * Symbol Details and Market Data analysis
 * Unified Dashboard Layout
 */

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { SymbolSelector } from '@/components/analytics/symbol-selector';
import { InteractiveChart } from '@/components/price/interactive-chart';
import { MarketDataTable } from '@/components/analytics/market-data-table';
import { Separator } from '@/components/ui/separator';
import { useTicker } from '@/hooks/api/usePriceData';
import { useWatchlist } from '@/hooks/api/useWatchlist';
import { useMarketDataQuery } from '@/hooks/api/useAnalytics';
import { useRealtimePrice } from '@/hooks/useRealtimePrice';
import { useRealtimeOrderbook } from '@/hooks/useRealtimeOrderbook';
import { OrderbookPanel } from '@/components/orderbook/orderbook-panel';
import { DepthChartPlot } from '@/components/orderbook/depth-chart';
import { toUTCIso } from '@/lib/time';
import { subDays } from 'date-fns';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { Plus, ArrowUp, ArrowDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

import { OverviewStats } from '@/components/analytics/overview-stats';
import { RollingNumber } from '@/components/ui/rolling-number';

function AnalyticsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const urlSymbol = searchParams.get('symbol');
  const urlTab = searchParams.get('tab') || 'overview'; // 'overview' or 'depth'
  const initializedRef = useRef(false);
  
  const [selectedSymbol, setSelectedSymbol] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>(urlTab);

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

  // Keep tab state in sync with URL
  useEffect(() => {
    setActiveTab(urlTab);
  }, [urlTab]);

  // Handle symbol change
  const handleSymbolChange = useCallback((newSymbol: string) => {
    setSelectedSymbol(newSymbol);
    router.replace(`/analytics?symbol=${newSymbol}&tab=${activeTab}`, { scroll: false });
  }, [router, activeTab]);

  // Handle tab change
  const handleTabChange = useCallback((tab: string) => {
    setActiveTab(tab);
    if (selectedSymbol) {
      router.replace(`/analytics?symbol=${selectedSymbol}&tab=${tab}`, { scroll: false });
    }
  }, [router, selectedSymbol]);

  // Real-time updates
  const { isConnected: isPriceConnected } = useRealtimePrice(selectedSymbol);

  // Orderbook (Always subscribe in this dashboard view)
  const { book: orderbookBook, error: orderbookError } =
    useRealtimeOrderbook(selectedSymbol);

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

  // Transform data for table
  const tableData = (marketDataResponse?.data || []).map((item: any) => ({
    ...item,
    bid: item.bid_price,
    ask: item.ask_price,
    spread: item.bid_price && item.ask_price 
      ? ((item.ask_price - item.bid_price) / item.bid_price) * 100 
      : undefined,
  }));

  // Empty state
  if (!isWatchlistLoading && watchlistSymbols.length === 0) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">Analyze market trends and price movements</p>
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

  const getCoinInfo = (symbol: string) => {
    const s = symbol.replace('USDT', '').replace('USD', '').toUpperCase();
    const map: Record<string, { name: string; color: string }> = {
      BTC: { name: 'Bitcoin', color: '#F7931A' },
      ETH: { name: 'Ethereum', color: '#627EEA' },
      SOL: { name: 'Solana', color: '#14F195' },
      BNB: { name: 'BNB', color: '#F3BA2F' },
      DOGE: { name: 'Dogecoin', color: '#C2A633' },
      XRP: { name: 'XRP', color: '#23292F' },
      ADA: { name: 'Cardano', color: '#0033AD' },
      AVAX: { name: 'Avalanche', color: '#E84142' },
      DOT: { name: 'Polkadot', color: '#E6007A' },
      MATIC: { name: 'Polygon', color: '#8247E5' },
      LTC: { name: 'Litecoin', color: '#345D9D' },
      UNI: { name: 'Uniswap', color: '#FF007A' },
      LINK: { name: 'Chainlink', color: '#2A5ADA' },
    };
    return map[s] || { name: s, color: '#64748b' };
  };

  const isPositive = (tickerData?.price_change_pct_24h || 0) >= 0;
  const showLiveValues = isPriceConnected && !!tickerData;

  const coinInfo = getCoinInfo(selectedSymbol);

  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Header Section */}
      <div className="flex flex-col gap-6">
        {/* Row 1: Identity & Search */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
           {/* Left: Identity */}
           <div className="flex items-center gap-4">
              <div 
                className="w-12 h-12 rounded-xl flex items-center justify-center text-white text-2xl font-bold shadow-lg"
                style={{ backgroundColor: coinInfo.color }}
              >
                 {/* Icon based on symbol */}
                 {selectedSymbol.substring(0,1)}
              </div>
              <div>
                 <h1 className="text-3xl font-bold leading-none tracking-tight">
                    {coinInfo.name} USD
                 </h1>
                 <div className="text-sm text-muted-foreground font-medium mt-1.5 flex items-center gap-2">
                    <span>{selectedSymbol}</span>
                    <span className="w-1 h-1 rounded-full bg-slate-600" />
                    <span>CRYPTO</span>
                    {isPriceConnected && (
                      <Badge variant="outline" className="text-emerald-500 border-emerald-500/20 bg-emerald-500/10 text-[10px] px-1.5 py-0 ml-1">
                        LIVE
                      </Badge>
                    )}
                 </div>
              </div>
           </div>

           {/* Right: Search */}
           <div className="w-full md:w-[280px]">
              <SymbolSelector 
                value={selectedSymbol} 
                onChange={handleSymbolChange} 
                symbols={watchlistSymbols}
              />
           </div>
        </div>

        {/* Row 2: Page Navigation Tabs */}
        <div className="flex items-center gap-8 border-b border-slate-800">
            <button 
              onClick={() => handleTabChange('overview')}
              className={cn(
                "pb-3 border-b-2 px-1 transition-colors font-medium",
                activeTab === 'overview' 
                  ? "border-emerald-500 text-foreground" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              Overview
            </button>
            <button 
              onClick={() => handleTabChange('depth')}
              className={cn(
                "pb-3 border-b-2 px-1 transition-colors font-medium",
                activeTab === 'depth' 
                  ? "border-emerald-500 text-foreground" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              Depth
            </button>
        </div>
      </div>

      {/* Main Workspace Content */}
      {activeTab === 'overview' ? (
        // Overview Tab Content
        <div className="space-y-6">
           {/* Big Price Display */}
           <div className="flex items-baseline gap-3 px-1">
             <span className="text-4xl font-mono font-bold tracking-tight text-foreground">
               {showLiveValues ? (
                 <>
                   $<RollingNumber value={tickerData?.price || 0} decimals={2} />
                 </>
               ) : (
                 '--'
               )}
             </span>
             {showLiveValues ? (
               <div className={cn("flex items-center text-lg font-medium", isPositive ? "text-emerald-500" : "text-rose-500")}>
                  <span className="font-mono">
                    {tickerData && (tickerData.price_change_24h || 0) > 0 ? '+' : ''}
                    <RollingNumber value={tickerData?.price_change_24h || 0} prefix="$" decimals={2} />
                  </span>
                  <span className="ml-2 flex items-center">
                    {isPositive ? <ArrowUp className="w-5 h-5 mr-1" /> : <ArrowDown className="w-5 h-5 mr-1" />}
                    <RollingNumber value={Math.abs(tickerData?.price_change_pct_24h || 0)} suffix="%" decimals={2} />
                  </span>
               </div>
             ) : (
               <span className="text-sm text-muted-foreground">WebSocket disconnected</span>
             )}
             <span className="text-xs text-slate-500 ml-auto font-mono">
               {new Date().toUTCString()}
             </span>
           </div>

           {/* Full Width Chart */}
           <div className="flex flex-col border border-slate-800 rounded-xl bg-slate-950 overflow-hidden shadow-sm h-[500px]">
              <div className="flex-1 p-1">
                 <InteractiveChart symbol={selectedSymbol} />
              </div>
           </div>

           {/* Stats Grid */}
           <OverviewStats data={tickerData} isLoading={isTickerLoading} isConnected={isPriceConnected} />

           <Separator />

           {/* Market Trades */}
           <div className="space-y-4">
             <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">Market Trades</h3>
                  <p className="text-sm text-muted-foreground">Recent transactions</p>
                </div>
             </div>
             <MarketDataTable 
               data={tableData}
               isLoading={marketDataLoading}
             />
           </div>
        </div>
      ) : (
        // Depth Tab Content
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[650px]">
           {/* Depth Chart (Main Area) */}
           <div className="lg:col-span-3 flex flex-col border border-slate-800 rounded-xl bg-slate-950 overflow-hidden shadow-sm p-4 relative">
              <div className="absolute top-4 left-4 z-10 bg-slate-900/80 backdrop-blur px-3 py-1 rounded text-xs font-mono text-slate-400 border border-slate-800">
                 Depth Chart
              </div>
              <div className="flex-1 min-h-0">
                 <DepthChartPlot book={orderbookBook} height="100%" theme="dark" />
              </div>
              {orderbookError && (
                <div className="text-center text-xs text-red-400 mt-2">
                  Error: {orderbookError}
                </div>
              )}
           </div>

           {/* Orderbook Sidebar */}
           <div className="lg:col-span-1 h-full flex flex-col gap-4 min-h-[400px]">
              <OrderbookPanel 
                symbol={selectedSymbol} 
                book={orderbookBook} 
                levels={20} 
                showChart={false} // Only ladder & stats
              />
           </div>
        </div>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <Suspense fallback={
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        </div>
        <div className="h-[400px] flex items-center justify-center">
          <div className="animate-pulse text-muted-foreground">Loading dashboard...</div>
        </div>
      </div>
    }>
      <AnalyticsContent />
    </Suspense>
  );
}
