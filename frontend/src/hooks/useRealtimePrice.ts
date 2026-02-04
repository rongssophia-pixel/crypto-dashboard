import { useEffect, useState, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { TickerData } from './api/usePriceData';

export function useRealtimePrice(symbol: string) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const { accessToken: token } = apiClient.getTokens();
    if (!symbol || !token) return;

    // Connect to WebSocket
    // Use the API Gateway WebSocket endpoint
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/market-data?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket Connected');
      setIsConnected(true);
      
      // Subscribe to symbol
      ws.send(JSON.stringify({
        action: 'subscribe',
        symbols: [symbol]
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle market data updates
        if (data.type === 'market_data' && data.symbol === symbol) {
          // Update React Query cache for ticker
          queryClient.setQueryData<TickerData>(['ticker', symbol], (oldData) => {
            if (!oldData) return undefined;
            
            // Merge update with existing data
            return {
              ...oldData,
              price: data.price ?? oldData.price,
              volume: data.volume ?? oldData.volume,
              open_24h: data.open_24h ?? oldData.open_24h,
              high_24h: data.high_24h ?? oldData.high_24h,
              low_24h: data.low_24h ?? oldData.low_24h,
              volume_24h: data.volume_24h ?? oldData.volume_24h,
              price_change_24h: data.price_change_24h ?? oldData.price_change_24h,
              price_change_pct_24h: data.price_change_pct_24h ?? oldData.price_change_pct_24h,
              bid_price: data.bid_price ?? oldData.bid_price,
              ask_price: data.ask_price ?? oldData.ask_price,
              timestamp: new Date().toISOString()
            };
          });
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket Disconnected');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          action: 'unsubscribe',
          symbols: [symbol]
        }));
        ws.close();
      }
    };
  }, [symbol, queryClient]);

  return { isConnected };
}

