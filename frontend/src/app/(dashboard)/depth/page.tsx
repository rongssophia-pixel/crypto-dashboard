'use client';

/**
 * Depth Page
 * Live orderbook depth chart driven by /ws/orderbook.
 */

import { useState } from 'react';
import { DepthChart } from '@/components/orderbook/depth-chart';
import { ConnectionStatus } from '@/components/realtime/connection-status';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { useRealtimeOrderbook } from '@/hooks/useRealtimeOrderbook';
import { formatNumber } from '@/lib/utils';
import { toast } from 'sonner';

const DEFAULT_SYMBOL = 'BTCUSDT';

export default function DepthPage() {
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [draft, setDraft] = useState(DEFAULT_SYMBOL);

  const { book, status, isConnected, error } = useRealtimeOrderbook(symbol);

  const applySymbol = () => {
    const next = draft.trim().toUpperCase();
    if (!next) {
      toast.error('Please enter a symbol');
      return;
    }
    setSymbol(next);
    toast.success(`Viewing depth for ${next}`);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Depth</h1>
        <p className="text-muted-foreground">Live orderbook depth snapshots (top 20 levels)</p>
      </div>

      <ConnectionStatus
        status={status}
        subscriptions={[symbol]}
        onReconnect={() => {
          // The hook will reconnect automatically when disconnected; keep UI simple.
          toast.message('Reconnecting…');
        }}
      />

      <Card>
        <CardHeader>
          <CardTitle>Symbol</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col sm:flex-row gap-3 items-end">
          <div className="flex-1 w-full">
            <Label htmlFor="symbol">Symbol</Label>
            <Input
              id="symbol"
              value={draft}
              onChange={(e) => setDraft(e.target.value.toUpperCase())}
              placeholder="e.g., ETHUSDT"
              disabled={!isConnected && status !== 'disconnected'}
            />
          </div>
          <Button onClick={applySymbol} disabled={!draft.trim()}>
            Apply
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Feed</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <div className="flex flex-wrap gap-x-6 gap-y-1">
            <div>
              Status: <span className="text-foreground">{status}</span>
            </div>
            <div>
              Last snapshot:{' '}
              <span className="font-mono text-foreground">
                {book?.timestamp ?? '—'}
              </span>
            </div>
            <div>
              Levels:{' '}
              <span className="text-foreground">
                bids={book?.bids?.length ?? 0}, asks={book?.asks?.length ?? 0}
              </span>
            </div>
            {book?.mid_price != null && (
              <div>
                Mid: <span className="font-mono text-foreground">{formatNumber(book.mid_price)}</span>
              </div>
            )}
          </div>
          {error && <div className="text-red-600 dark:text-red-400">Error: {error}</div>}
        </CardContent>
      </Card>

      <DepthChart symbol={symbol} book={book} />
    </div>
  );
}


