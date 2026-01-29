'use client';

/**
 * Trade Feed Component
 * Scrolling list of recent trades
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { formatDateTime } from '@/lib/time';
import { formatPrice, formatNumber } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';

interface Trade {
  symbol: string;
  price: number;
  volume?: number;
  timestamp: string;
  side?: 'buy' | 'sell';
}

interface TradeFeedProps {
  trades: Trade[];
  maxTrades?: number;
}

export function TradeFeed({ trades, maxTrades = 100 }: TradeFeedProps) {
  const [autoScroll, setAutoScroll] = useState(true);
  const [displayTrades, setDisplayTrades] = useState<Trade[]>([]);

  useEffect(() => {
    setDisplayTrades((prev) => {
      const newTrades = [...trades, ...prev].slice(0, maxTrades);
      return newTrades;
    });
  }, [trades, maxTrades]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Trade Feed</CardTitle>
            <CardDescription>
              Recent market trades • {displayTrades.length} trades
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              id="auto-scroll"
              checked={autoScroll}
              onCheckedChange={setAutoScroll}
            />
            <Label htmlFor="auto-scroll" className="text-sm">
              Auto-scroll
            </Label>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          {displayTrades.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No trades yet. Waiting for market data...
            </p>
          ) : (
            <div className="space-y-2">
              {displayTrades.map((trade, index) => (
                <div
                  key={`${trade.symbol}-${trade.timestamp}-${index}`}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={
                        trade.side === 'buy'
                          ? 'default'
                          : trade.side === 'sell'
                          ? 'destructive'
                          : 'secondary'
                      }
                      className="w-16 justify-center"
                    >
                      {trade.side || 'TRADE'}
                    </Badge>
                    <div>
                      <p className="font-medium">{trade.symbol}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(trade.timestamp, 'HH:mm:ss')}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono font-semibold">
                      {formatPrice(trade.price)}
                    </p>
                    {trade.volume && (
                      <p className="text-xs text-muted-foreground">
                        Vol: {formatNumber(trade.volume / 1000)}K
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}



