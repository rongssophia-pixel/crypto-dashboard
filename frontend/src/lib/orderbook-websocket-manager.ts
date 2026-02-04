/**
 * Orderbook WebSocket Manager
 * Dedicated singleton for /ws/orderbook (one symbol per tab).
 */

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

type MessageHandler = (data: any) => void;
type ErrorHandler = (error: Error) => void;
type StatusHandler = (status: ConnectionStatus) => void;

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export class OrderbookWebSocketManager {
  private static instance: OrderbookWebSocketManager;
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private errorHandlers: Set<ErrorHandler> = new Set();
  private statusHandlers: Set<StatusHandler> = new Set();
  private status: ConnectionStatus = 'disconnected';
  private accessToken: string | null = null;
  private symbol: string | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  private constructor() {}

  static getInstance(): OrderbookWebSocketManager {
    if (!OrderbookWebSocketManager.instance) {
      OrderbookWebSocketManager.instance = new OrderbookWebSocketManager();
    }
    return OrderbookWebSocketManager.instance;
  }

  connect(accessToken: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    this.accessToken = accessToken;
    this.setStatus('connecting');

    const wsUrl = `${WS_URL}/ws/orderbook?token=${accessToken}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setStatus('connected');
      this.startHeartbeat();

      // Resubscribe to current symbol
      if (this.symbol) {
        this.send({ action: 'subscribe', symbols: [this.symbol] });
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse orderbook WebSocket message:', error);
      }
    };

    this.ws.onerror = () => {
      this.errorHandlers.forEach((handler) => handler(new Error('WebSocket error')));
    };

    this.ws.onclose = () => {
      this.setStatus('disconnected');
      this.stopHeartbeat();
      this.attemptReconnect();
    };
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('disconnected');
  }

  subscribe(symbol: string): void {
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;

    this.symbol = sym;

    if (this.isConnected()) {
      this.send({ action: 'subscribe', symbols: [sym] });
    }
  }

  unsubscribe(): void {
    if (!this.symbol) return;
    const sym = this.symbol;
    this.symbol = null;

    if (this.isConnected()) {
      this.send({ action: 'unsubscribe', symbols: [sym] });
    }
  }

  on(eventType: string, handler: MessageHandler): void {
    if (!this.messageHandlers.has(eventType)) {
      this.messageHandlers.set(eventType, new Set());
    }
    this.messageHandlers.get(eventType)!.add(handler);
  }

  off(eventType: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(eventType);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  onError(handler: ErrorHandler): void {
    this.errorHandlers.add(handler);
  }

  offError(handler: ErrorHandler): void {
    this.errorHandlers.delete(handler);
  }

  onStatusChange(handler: StatusHandler): void {
    this.statusHandlers.add(handler);
    handler(this.status);
  }

  offStatusChange(handler: StatusHandler): void {
    this.statusHandlers.delete(handler);
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  getSymbol(): string | null {
    return this.symbol;
  }

  private isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  private send(data: any): void {
    if (!this.isConnected()) return;
    this.ws!.send(JSON.stringify(data));
  }

  private handleMessage(message: WebSocketMessage): void {
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) handlers.forEach((h) => h(message));

    const wildcardHandlers = this.messageHandlers.get('*');
    if (wildcardHandlers) wildcardHandlers.forEach((h) => h(message));
  }

  private setStatus(status: ConnectionStatus): void {
    this.status = status;
    this.statusHandlers.forEach((handler) => handler(status));
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    this.reconnectAttempts++;
    this.setStatus('reconnecting');

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    setTimeout(() => {
      if (this.accessToken) {
        this.connect(this.accessToken);
      }
    }, delay);
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({ action: 'ping' });
      }
    }, 30000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

export const orderbookWsManager = OrderbookWebSocketManager.getInstance();


