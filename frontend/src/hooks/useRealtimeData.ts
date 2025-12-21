'use client';

/**
 * Real-Time Data Hook
 * React hook for subscribing to WebSocket market data
 */

import { useEffect, useState } from 'react';
import { wsManager, ConnectionStatus } from '@/lib/websocket-manager';
import { useAuth } from './useAuth';

interface MarketData {
  symbol: string;
  price: number;
  volume?: number;
  timestamp: string;
  [key: string]: any;
}

export function useRealtimeData(symbols: string[]) {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState<Map<string, MarketData>>(new Map());
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated || symbols.length === 0) {
      return;
    }

    // Get access token from localStorage
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      setError('No access token available');
      return;
    }

    console.log('🎬 [useRealtimeData] Effect running, symbols:', symbols);
    console.log('🎬 [useRealtimeData] Current WS status:', wsManager.getStatus());

    // Connect WebSocket if disconnected
    const currentStatus = wsManager.getStatus();
    if (currentStatus === 'disconnected') {
      console.log('🎬 [useRealtimeData] Connecting WebSocket...');
      wsManager.connect(accessToken);
      
      // Wait for connection to be established before subscribing
      // The WebSocketManager will auto-subscribe on connection
    }

    // Subscribe to symbols (will be queued if not connected yet)
    console.log('🎬 [useRealtimeData] Calling subscribe with symbols:', symbols);
    
    // If already connected, subscribe immediately
    // If connecting, the subscribe will be queued and sent when connection opens
    wsManager.subscribe(symbols);
    
    // Add a small delay to ensure subscription is sent after connection state updates
    const subscribeTimer = setTimeout(() => {
      const status = wsManager.getStatus();
      console.log('🔄 [useRealtimeData] Double-checking subscription, status:', status);
      if (status === 'connected') {
        console.log('🔄 [useRealtimeData] Re-subscribing to ensure symbols are registered');
        wsManager.subscribe(symbols);
      }
    }, 1000);

    // Handle market data messages
    const handleMarketData = (message: any) => {
      console.log('🔵 [useRealtimeData] Received message:', message);
      if (message.type === 'market_data' && message.symbol) {
        console.log('✅ [useRealtimeData] Processing market_data for symbol:', message.symbol, 'price:', message.price);
        setData((prevData) => {
          const newData = new Map(prevData);
          // Backend sends data at root level, not nested in message.data
          newData.set(message.symbol, message);
          console.log('📊 [useRealtimeData] Updated data map, size:', newData.size, 'symbols:', Array.from(newData.keys()));
          return newData;
        });
      } else {
        console.log('⚠️ [useRealtimeData] Skipping message - type:', message.type, 'has symbol:', !!message.symbol);
      }
    };

    // Handle status changes
    const handleStatusChange = (newStatus: ConnectionStatus) => {
      setStatus(newStatus);
    };

    // Handle errors
    const handleError = (err: Error) => {
      setError(err.message);
    };

    // Register handlers
    wsManager.on('market_data', handleMarketData);
    wsManager.on('*', handleMarketData); // Catch-all
    wsManager.onStatusChange(handleStatusChange);
    wsManager.onError(handleError);

    // Cleanup
    return () => {
      clearTimeout(subscribeTimer);
      wsManager.unsubscribe(symbols);
      wsManager.off('market_data', handleMarketData);
      wsManager.off('*', handleMarketData);
      wsManager.offStatusChange(handleStatusChange);
      wsManager.offError(handleError);
    };
  }, [isAuthenticated, symbols.join(',')]);

  const dataArray = Array.from(data.values());
  console.log('📤 [useRealtimeData] Returning data array, length:', dataArray.length, 'status:', status);
  
  return {
    data: dataArray,
    status,
    error,
    isConnected: status === 'connected',
  };
}
