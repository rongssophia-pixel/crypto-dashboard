import { useEffect, useState, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { TickerData } from './api/usePriceData';

// WebSocket message types
interface WSMessage {
  type: string;
  symbol?: string;
  price?: number;
  volume?: number;
  // Add other fields as needed
}

export function useRealtimePrice(symbol: string) {
  const queryClient = useQueryClient();
  const { token } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
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
              price: data.price,
              volume: data.volume, // Accumulate? Or is it total?
              // Update other fields if available in WS message
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
  }, [symbol, token, queryClient]);

  return { isConnected };
}

