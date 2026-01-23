import { ArrowDownIcon, ArrowUpIcon, Bell } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { TickerData } from '@/hooks/api/usePriceData';
import { formatDateTime } from '@/lib/time';

interface PriceTickerProps {
  symbol: string;
  data?: TickerData;
  isLoading: boolean;
  isConnected?: boolean;
  onAlertClick?: () => void;
}

export function PriceTicker({ 
  symbol, 
  data, 
  isLoading, 
  isConnected = false,
  onAlertClick 
}: PriceTickerProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-8 w-8" />
        </div>
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-4 w-32" />
      </div>
    );
  }

  if (!data) return null;

  const isPositive = (data.price_change_pct_24h || 0) >= 0;
  const colorClass = isPositive ? 'text-green-500' : 'text-red-500';

  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          {/* Placeholder Icon */}
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-lg">
            {symbol.substring(0, 1)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{symbol}</h1>
              {/* Live Indicator */}
              <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                isConnected 
                  ? 'bg-green-500/5 text-green-600 border-green-500/20' 
                  : 'bg-yellow-500/5 text-yellow-600 border-yellow-500/20'
              }`}>
                <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
                {isConnected ? 'LIVE' : 'CONNECTING'}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">Crypto • {data.symbol}</p>
          </div>
        </div>

        <Button 
          variant="outline" 
          size="icon" 
          className="h-9 w-9 text-muted-foreground hover:text-foreground transition-colors"
          onClick={onAlertClick}
          title="Set Alert"
        >
          <Bell className="w-4 h-4" />
        </Button>
      </div>

      <div className="mt-6 flex items-baseline gap-4">
        <span className="text-5xl font-bold font-mono tracking-tight">
          ${data.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
        <div className={`flex items-center gap-1 text-lg font-medium ${colorClass}`}>
          {isPositive ? <ArrowUpIcon className="w-5 h-5" /> : <ArrowDownIcon className="w-5 h-5" />}
          <span>
            {isPositive ? '+' : ''}
            {data.price_change_24h?.toLocaleString(undefined, { maximumFractionDigits: 2 })} (
            {data.price_change_pct_24h?.toFixed(2)}%)
          </span>
        </div>
      </div>
      
      <p className="text-xs text-muted-foreground mt-2 font-mono">
        Last updated: {formatDateTime(data.timestamp)}
      </p>
    </div>
  );
}
