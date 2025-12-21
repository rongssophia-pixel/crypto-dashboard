'use client';

/**
 * Real-Time Data Page
 * Live WebSocket streaming of market data
 */

import { useState } from 'react';
import { useRealtimeData } from '@/hooks/useRealtimeData';
import { wsManager } from '@/lib/websocket-manager';
import { ConnectionStatus } from '@/components/realtime/connection-status';
import { LiveTicker } from '@/components/realtime/live-ticker';
import { TradeFeed } from '@/components/realtime/trade-feed';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];

export default function RealtimePage() {
  const [subscribedSymbols, setSubscribedSymbols] = useState<string[]>(DEFAULT_SYMBOLS);
  const [newSymbol, setNewSymbol] = useState('');
  const { data, status, isConnected } = useRealtimeData(subscribedSymbols);

  const handleAddSymbol = () => {
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) {
      toast.error('Please enter a symbol');
      return;
    }
    if (subscribedSymbols.includes(symbol)) {
      toast.error('Symbol already subscribed');
      return;
    }
    if (subscribedSymbols.length >= 50) {
      toast.error('Maximum 50 symbols allowed');
      return;
    }

    setSubscribedSymbols([...subscribedSymbols, symbol]);
    setNewSymbol('');
    toast.success(`Subscribed to ${symbol}`);
  };

  const handleReconnect = () => {
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
      wsManager.connect(accessToken);
    } else {
      toast.error('No access token available');
    }
  };

  // Transform data for ticker
  console.log('🎯 [RealtimePage] Raw data from hook:', data.length, 'items');
  const tickerData = data.map((item) => {
    console.log('🔄 [RealtimePage] Transforming item:', item.symbol, {
      price: item.price,
      price_change_pct_24h: item.price_change_pct_24h,
      change_24h: item.change_24h
    });
    return {
      symbol: item.symbol,
      price: item.price,
      // Backend sends price_change_pct_24h, not change_24h
      change: item.price_change_pct_24h || item.change_24h,
    };
  });
  console.log('📊 [RealtimePage] Ticker data:', tickerData.length, 'items:', tickerData);

  // Transform data for trade feed
  const trades = data.map((item) => ({
    symbol: item.symbol,
    price: item.price,
    volume: item.volume,
    timestamp: item.timestamp,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Real-Time Data</h1>
        <p className="text-muted-foreground">
          Live market data streaming via WebSocket
        </p>
      </div>

      {/* Connection Status */}
      <ConnectionStatus
        status={status}
        subscriptions={subscribedSymbols}
        onReconnect={handleReconnect}
      />

      {/* Add Symbol */}
      <div className="flex gap-2">
        <div className="flex-1">
          <Label htmlFor="symbol">Add Symbol</Label>
          <div className="flex gap-2 mt-2">
            <Input
              id="symbol"
              placeholder="e.g., DOGEUSDT"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              onKeyPress={(e) => e.key === 'Enter' && handleAddSymbol()}
              disabled={!isConnected}
            />
            <Button
              onClick={handleAddSymbol}
              disabled={!isConnected}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add
            </Button>
          </div>
        </div>
      </div>

      {/* Live Ticker */}
      <LiveTicker data={tickerData} isConnected={isConnected} />

      {/* Trade Feed */}
      <TradeFeed trades={trades} />
    </div>
  );
}
