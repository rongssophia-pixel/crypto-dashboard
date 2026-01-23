import { ArrowDownIcon, ArrowUpIcon } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { TickerData } from '@/hooks/api/usePriceData';
import { formatDateTime } from '@/lib/time';

interface PriceTickerProps {
  symbol: string;
  data?: TickerData;
  isLoading: boolean;
}

export function PriceTicker({ symbol, data, isLoading }: PriceTickerProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
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
      <div className="flex items-center gap-3">
        {/* Placeholder Icon */}
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
          {symbol.substring(0, 1)}
        </div>
        <div>
          <h1 className="text-2xl font-bold">{symbol}</h1>
          <p className="text-xs text-muted-foreground">Crypto</p>
        </div>
      </div>

      <div className="mt-4 flex items-baseline gap-4">
        <span className="text-4xl font-bold font-mono">
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
      
      <p className="text-xs text-muted-foreground mt-1">
        {formatDateTime(data.timestamp)}
      </p>
    </div>
  );
}

