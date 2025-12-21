/**
 * WebSocket Manager
 * Singleton class for managing WebSocket connection to market data stream
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

export class WebSocketManager {
  private static instance: WebSocketManager;
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private errorHandlers: Set<ErrorHandler> = new Set();
  private statusHandlers: Set<StatusHandler> = new Set();
  private status: ConnectionStatus = 'disconnected';
  private accessToken: string | null = null;
  private subscriptions: Set<string> = new Set();
  private heartbeatInterval: NodeJS.Timeout | null = null;

  private constructor() {}

  static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager();
    }
    return WebSocketManager.instance;
  }

  connect(accessToken: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    this.accessToken = accessToken;
    this.setStatus('connecting');

    const wsUrl = `${WS_URL}/ws/market-data?token=${accessToken}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('🟢 [WebSocketManager] WebSocket connected');
      console.log('🟢 [WebSocketManager] Subscriptions in Set:', this.subscriptions.size, Array.from(this.subscriptions));
      this.reconnectAttempts = 0;
      this.setStatus('connected');
      this.startHeartbeat();
      
      // Resubscribe to previous subscriptions
      if (this.subscriptions.size > 0) {
        const symbolsArray = Array.from(this.subscriptions);
        console.log('🟢 [WebSocketManager] Resubscribing to symbols:', symbolsArray);
        this.send({
          action: 'subscribe',
          symbols: symbolsArray,
        });
      } else {
        console.log('⚠️ [WebSocketManager] No subscriptions to resubscribe');
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        console.log('🌐 [WebSocketManager] Received message:', message);
        this.handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.errorHandlers.forEach((handler) => handler(new Error('WebSocket error')));
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed');
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

  subscribe(symbols: string[]): void {
    symbols.forEach((symbol) => this.subscriptions.add(symbol));
    
    console.log(`📝 [WebSocketManager] Subscribe called for ${symbols.length} symbols:`, symbols);
    console.log(`📝 [WebSocketManager] Current status:`, this.status, 'isConnected:', this.isConnected());
    console.log(`📝 [WebSocketManager] Total subscriptions in Set:`, this.subscriptions.size);
    
    if (this.isConnected()) {
      console.log(`✅ [WebSocketManager] Sending subscribe message for:`, symbols);
      this.send({
        action: 'subscribe',
        symbols,
      });
    } else {
      console.log(`⚠️ [WebSocketManager] Not connected yet, will subscribe on connection. Symbols queued:`, Array.from(this.subscriptions));
    }
  }

  unsubscribe(symbols: string[]): void {
    symbols.forEach((symbol) => this.subscriptions.delete(symbol));
    
    if (this.isConnected()) {
      this.send({
        action: 'unsubscribe',
        symbols,
      });
    }
  }

  listSubscriptions(): void {
    if (this.isConnected()) {
      this.send({ action: 'list' });
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
    // Immediately call with current status
    handler(this.status);
  }

  offStatusChange(handler: StatusHandler): void {
    this.statusHandlers.delete(handler);
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  getSubscriptions(): string[] {
    return Array.from(this.subscriptions);
  }

  private isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  private send(data: any): void {
    if (this.isConnected()) {
      const message = JSON.stringify(data);
      console.log('📤 [WebSocketManager] Sending message:', message);
      this.ws!.send(message);
    } else {
      console.warn('⚠️ [WebSocketManager] WebSocket not connected, cannot send message:', data);
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      handlers.forEach((handler) => handler(message));
    }

    // Also trigger wildcard handlers
    const wildcardHandlers = this.messageHandlers.get('*');
    if (wildcardHandlers) {
      wildcardHandlers.forEach((handler) => handler(message));
    }
  }

  private setStatus(status: ConnectionStatus): void {
    this.status = status;
    this.statusHandlers.forEach((handler) => handler(status));
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    this.setStatus('reconnecting');

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

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
    }, 30000); // 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

export const wsManager = WebSocketManager.getInstance();
