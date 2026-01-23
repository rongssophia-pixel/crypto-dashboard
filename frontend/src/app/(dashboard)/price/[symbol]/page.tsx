'use client';

import { use } from 'react';
import { notFound } from 'next/navigation';
import { PriceTicker } from '@/components/price/price-ticker';
import { InteractiveChart } from '@/components/price/interactive-chart';
import { PriceStats } from '@/components/price/price-stats';
import { useTicker } from '@/hooks/api/usePriceData';
import { useRealtimePrice } from '@/hooks/useRealtimePrice';
import { Button } from '@/components/ui/button';
import { Bell, Star } from 'lucide-react';
import { Separator } from '@/components/ui/separator';

interface PricePageProps {
  params: Promise<{ symbol: string }>;
}

export default function PricePage({ params }: PricePageProps) {
  // Unwrap params using React.use()
  const { symbol: rawSymbol } = use(params);
  const symbol = rawSymbol.toUpperCase();
  
  // Real-time updates
  const { isConnected } = useRealtimePrice(symbol);
  
  // Initial data fetch (and polling fallback)
  const { data: tickerData, isLoading: isTickerLoading, error: tickerError } = useTicker(symbol);

  if (tickerError) {
    // Basic error handling
    return (
      <div className="flex items-center justify-center h-full">
         <div className="text-center">
            <h2 className="text-lg font-bold">Error loading symbol</h2>
            <p className="text-muted-foreground">{symbol} not found or service unavailable</p>
         </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Actions */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
           <span>Markets</span>
           <span>/</span>
           <span className="text-foreground font-medium">{symbol}</span>
        </div>
        <div className="flex items-center gap-2">
           <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${isConnected ? 'bg-green-500/10 text-green-600' : 'bg-yellow-500/10 text-yellow-600'}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
              {isConnected ? 'Live' : 'Connecting...'}
           </div>
           <Button variant="outline" size="sm" className="gap-2">
              <Star className="w-4 h-4" />
              Watch
           </Button>
           <Button variant="outline" size="sm" className="gap-2">
              <Bell className="w-4 h-4" />
              Alerts
           </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Chart Area */}
        <div className="lg:col-span-2 space-y-6">
          <PriceTicker 
            symbol={symbol} 
            data={tickerData} 
            isLoading={isTickerLoading} 
          />
          
          <Separator />
          
          <div className="h-[500px]">
             <InteractiveChart symbol={symbol} />
          </div>
        </div>

        {/* Side Panel */}
        <div className="space-y-6">
          <h3 className="font-semibold text-lg">Market Stats (24h)</h3>
          <PriceStats 
            data={tickerData} 
            isLoading={isTickerLoading} 
          />
          
          {/* Additional panels like Order Book or Recent Trades could go here */}
          <div className="bg-muted/30 rounded-lg p-4 border border-border/50">
             <h4 className="font-medium mb-2 text-sm">About {symbol}</h4>
             <p className="text-xs text-muted-foreground leading-relaxed">
                {symbol} is a decentralized digital currency. It is one of the cryptocurrencies tracked by our platform.
             </p>
          </div>
        </div>
      </div>
    </div>
  );
}
