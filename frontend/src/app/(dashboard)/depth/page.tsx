'use client';

/**
 * Depth Page
 * Live orderbook depth chart driven by /ws/orderbook.
 */

import { useState } from 'react';
import { ConnectionStatus } from '@/components/realtime/connection-status';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { useRealtimeOrderbook } from '@/hooks/useRealtimeOrderbook';
import { OrderbookPanel } from '@/components/orderbook/orderbook-panel';
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

      <details className="rounded-xl border bg-background">
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium">
          Connection
          <span className="ml-2 text-xs text-muted-foreground">(click to expand)</span>
        </summary>
        <div className="px-4 pb-4">
          <ConnectionStatus
            status={status}
            subscriptions={[symbol]}
            onReconnect={() => {
              toast.message('Reconnecting…');
            }}
          />
          {error && <div className="mt-3 text-sm text-red-600 dark:text-red-400">Error: {error}</div>}
        </div>
      </details>

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

      <OrderbookPanel symbol={symbol} book={book} levels={20} />
    </div>
  );
}


