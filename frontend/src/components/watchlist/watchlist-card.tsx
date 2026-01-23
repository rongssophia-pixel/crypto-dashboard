'use client';

/**
 * Watchlist Card Component
 * Displays symbol info, price, and sparkline
 */

import { useMemo } from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { SparklineChart } from './sparkline-chart';
import { useCandles, useLatestPrices } from '@/hooks/api/useAnalytics';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowDownIcon, ArrowUpIcon, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRemoveFromWatchlist } from '@/hooks/api/useWatchlist';
import { toast } from 'sonner';
import { subDays } from 'date-fns';
import { toUTCIso } from '@/lib/time';
import { cn } from '@/lib/utils';

interface WatchlistCardProps {
  symbol: string;
  onClick?: (symbol: string) => void;
  isSelected?: boolean;
}

export function WatchlistCard({ symbol, onClick, isSelected }: WatchlistCardProps) {
  const removeMutation = useRemoveFromWatchlist();

  // Fetch latest price
  const { data: priceData, isLoading: isPriceLoading } = useLatestPrices({
    symbols: [symbol],
  });

  // Fetch 24h history for sparkline
  const timeRange = useMemo(() => {
    const end = new Date();
    const start = subDays(end, 1);
    return {
      start: toUTCIso(start),
      end: toUTCIso(end),
    };
  }, []);

  const { data: candleData, isLoading: isCandleLoading } = useCandles({
    symbol,
    interval: '1h',
    start_time: timeRange.start,
    end_time: timeRange.end,
  });

  const handleRemove = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    removeMutation.mutate(symbol, {
      onSuccess: () => {
        toast.success(`Removed ${symbol} from watchlist`);
      },
      onError: () => {
        toast.error(`Failed to remove ${symbol}`);
      },
    });
  };

  if (isPriceLoading || isCandleLoading) {
    return <Skeleton className="h-[140px] w-full rounded-xl" />;
  }

  const price = priceData?.prices[0];
  const candles = candleData?.candles || [];
  
  // Transform candle data for sparkline
  const sparklineData = candles.map(c => ({
    timestamp: c.timestamp,
    value: c.close,
  }));

  const isPositive = (price?.change_24h || 0) >= 0;
  const color = isPositive ? '#22c55e' : '#ef4444';

  const CardContentWrapper = ({ children }: { children: React.ReactNode }) => {
    const card = (
      <Card 
        className={cn(
          "hover:bg-accent/50 transition-colors relative group overflow-hidden cursor-pointer",
          isSelected && "border-primary bg-accent/20"
        )}
        onClick={onClick ? () => onClick(symbol) : undefined}
      >
        <CardContent className="p-4">
          {children}
        </CardContent>
      </Card>
    );

    if (onClick) {
      return card;
    }

    return (
      <Link href={`/analytics?symbol=${symbol}`}>
        {card}
      </Link>
    );
  };

  return (
    <CardContentWrapper>
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-bold text-lg">{symbol}</h3>
          <p className="text-sm text-muted-foreground">
            ${price?.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className={`flex items-center text-sm font-medium ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
          {isPositive ? <ArrowUpIcon className="w-3 h-3 mr-1" /> : <ArrowDownIcon className="w-3 h-3 mr-1" />}
          {Math.abs(price?.change_24h || 0).toFixed(2)}%
        </div>
      </div>
      
      <div className="h-[60px] mt-2">
        <SparklineChart data={sparklineData} color={color} height={60} />
      </div>

      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8"
        onClick={handleRemove}
      >
        <X className="w-4 h-4 text-muted-foreground hover:text-foreground" />
      </Button>
    </CardContentWrapper>
  );
}
