'use client';

/**
 * Live Price Ticker Component
 * Scrolling ticker with real-time price updates
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn, formatPrice, formatNumber } from '@/lib/utils';

interface TickerData {
  symbol: string;
  price: number;
  change?: number;
}

interface LiveTickerProps {
  data: TickerData[];
  isConnected: boolean;
}

export function LiveTicker({ data, isConnected }: LiveTickerProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Live Price Ticker</CardTitle>
          <CardDescription>Real-time price updates</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {isConnected
              ? 'Waiting for market data...'
              : 'Connect to see live prices'}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live Price Ticker</CardTitle>
        <CardDescription>
          Real-time price updates • {data.length} symbols
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((item) => {
            const isPositive = (item.change || 0) >= 0;
            return (
              <div
                key={item.symbol}
                className={cn(
                  'p-4 rounded-lg border transition-colors',
                  'hover:bg-muted/50 cursor-pointer'
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm">{item.symbol}</span>
                  {item.change !== undefined && (
                    <Badge
                      variant={isPositive ? 'default' : 'destructive'}
                      className="gap-1 text-xs"
                    >
                      {isPositive ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {formatNumber(Math.abs(item.change))}%
                    </Badge>
                  )}
                </div>
                <div className="text-2xl font-bold font-mono">
                  {formatPrice(item.price)}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}



