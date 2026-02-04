'use client';

/**
 * Real-Time Orderbook Hook
 * Subscribes to /ws/orderbook for a single symbol.
 */

import { useEffect, useState } from 'react';
import { orderbookWsManager, ConnectionStatus } from '@/lib/orderbook-websocket-manager';
import { useAuth } from './useAuth';

export type OrderbookLevel = [number, number];

export interface OrderbookSnapshot {
  symbol: string;
  exchange?: string;
  timestamp: number | string;
  levels?: number;
  bids: OrderbookLevel[];
  asks: OrderbookLevel[];
  mid_price?: number;
  spread?: number;
  spread_pct?: number;
  processed_at?: number;
  last_update_id?: number;
}

export function useRealtimeOrderbook(symbol: string) {
  const { isAuthenticated } = useAuth();
  const [book, setBook] = useState<OrderbookSnapshot | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sym = symbol.trim().toUpperCase();
    if (!isAuthenticated || !sym) {
      return;
    }

    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      setError('No access token available');
      return;
    }

    if (orderbookWsManager.getStatus() === 'disconnected') {
      orderbookWsManager.connect(accessToken);
    }

    orderbookWsManager.subscribe(sym);

    const handleOrderbook = (message: any) => {
      if (message.type === 'orderbook' && message.symbol) {
        setBook(message as OrderbookSnapshot);
      } else if (message.type === 'warning' && message.message) {
        setError(String(message.message));
      }
    };

    const handleStatusChange = (s: ConnectionStatus) => setStatus(s);
    const handleError = (err: Error) => setError(err.message);

    orderbookWsManager.on('orderbook', handleOrderbook);
    orderbookWsManager.on('*', handleOrderbook);
    orderbookWsManager.onStatusChange(handleStatusChange);
    orderbookWsManager.onError(handleError);

    return () => {
      orderbookWsManager.unsubscribe();
      orderbookWsManager.off('orderbook', handleOrderbook);
      orderbookWsManager.off('*', handleOrderbook);
      orderbookWsManager.offStatusChange(handleStatusChange);
      orderbookWsManager.offError(handleError);
    };
  }, [isAuthenticated, symbol]);

  return {
    book,
    status,
    error,
    isConnected: status === 'connected',
  };
}


