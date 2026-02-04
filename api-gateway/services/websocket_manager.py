"""
WebSocket Connection Manager
Manages WebSocket connections and symbol subscriptions
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

from fastapi import WebSocket
from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)


# Prometheus metrics
WS_CONNECTIONS = Gauge(
    "websocket_active_connections",
    "Number of active WebSocket connections"
)

WS_SUBSCRIPTIONS = Gauge(
    "websocket_active_subscriptions",
    "Number of active symbol subscriptions",
    ["symbol"]
)

WS_MESSAGES_SENT = Counter(
    "websocket_messages_sent_total",
    "Total WebSocket messages sent",
    ["symbol"]
)

WS_ERRORS = Counter(
    "websocket_errors_total",
    "Total WebSocket errors",
    ["error_type"]
)


class WebSocketConnection:
    """Represents a single WebSocket connection"""
    
    def __init__(self, connection_id: str, websocket: WebSocket, user_id: str):
        self.connection_id = connection_id
        self.websocket = websocket
        self.user_id = user_id
        self.subscriptions: Set[str] = set()
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()


class ConnectionManager:
    """
    Manages WebSocket connections and symbol subscriptions
    Singleton pattern - use get_instance() to access
    """
    
    _instance = None
    
    def __init__(self):
        # Map: connection_id -> WebSocketConnection
        self.active_connections: Dict[str, WebSocketConnection] = {}
        
        # Map: symbol -> Set[connection_id]
        self.symbol_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info("ConnectionManager initialized")
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """
        Register a new WebSocket connection
        
        Args:
            websocket: FastAPI WebSocket instance
            user_id: Authenticated user ID
            
        Returns:
            connection_id: Unique identifier for this connection
        """
        connection_id = str(uuid.uuid4())
        
        async with self._lock:
            connection = WebSocketConnection(connection_id, websocket, user_id)
            self.active_connections[connection_id] = connection
            WS_CONNECTIONS.set(len(self.active_connections))
            
        logger.info(
            f"WebSocket connected: {connection_id} (user: {user_id}, "
            f"total: {len(self.active_connections)})"
        )
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        Unregister a WebSocket connection and clean up subscriptions
        
        Args:
            connection_id: Connection identifier
        """
        async with self._lock:
            connection = self.active_connections.get(connection_id)
            if not connection:
                return
            
            # Remove all subscriptions for this connection
            for symbol in connection.subscriptions.copy():
                await self._unsubscribe_unsafe(connection_id, symbol)
            
            # Remove connection
            del self.active_connections[connection_id]
            WS_CONNECTIONS.set(len(self.active_connections))
        
        logger.info(
            f"WebSocket disconnected: {connection_id} "
            f"(total: {len(self.active_connections)})"
        )
    
    async def subscribe(self, connection_id: str, symbols: List[str]) -> List[str]:
        """
        Subscribe a connection to one or more symbols
        
        Args:
            connection_id: Connection identifier
            symbols: List of symbols to subscribe to
            
        Returns:
            List of successfully subscribed symbols
        """
        async with self._lock:
            connection = self.active_connections.get(connection_id)
            if not connection:
                logger.warning(f"Subscribe failed: connection {connection_id} not found")
                return []
            
            subscribed = []
            for symbol in symbols:
                # Check max subscriptions limit
                if len(connection.subscriptions) >= 50:  # Max from config
                    logger.warning(
                        f"Max subscriptions reached for connection {connection_id}"
                    )
                    break
                
                # Add subscription
                connection.subscriptions.add(symbol)
                self.symbol_subscriptions[symbol].add(connection_id)
                subscribed.append(symbol)
                
                # Update metrics
                WS_SUBSCRIPTIONS.labels(symbol=symbol).set(
                    len(self.symbol_subscriptions[symbol])
                )
            
            connection.update_activity()
        
        logger.info(
            f"Connection {connection_id} subscribed to {len(subscribed)} symbols: "
            f"{subscribed[:5]}{'...' if len(subscribed) > 5 else ''}"
        )
        
        return subscribed
    
    async def _unsubscribe_unsafe(self, connection_id: str, symbol: str):
        """
        Internal method to unsubscribe (assumes lock is held)
        """
        # Remove from symbol subscriptions
        if symbol in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol].discard(connection_id)
            
            # Clean up empty symbol sets
            if not self.symbol_subscriptions[symbol]:
                del self.symbol_subscriptions[symbol]
                WS_SUBSCRIPTIONS.labels(symbol=symbol).set(0)
            else:
                WS_SUBSCRIPTIONS.labels(symbol=symbol).set(
                    len(self.symbol_subscriptions[symbol])
                )
        
        # Remove from connection subscriptions
        connection = self.active_connections.get(connection_id)
        if connection:
            connection.subscriptions.discard(symbol)
    
    async def unsubscribe(self, connection_id: str, symbols: List[str]) -> List[str]:
        """
        Unsubscribe a connection from one or more symbols
        
        Args:
            connection_id: Connection identifier
            symbols: List of symbols to unsubscribe from
            
        Returns:
            List of successfully unsubscribed symbols
        """
        async with self._lock:
            connection = self.active_connections.get(connection_id)
            if not connection:
                logger.warning(
                    f"Unsubscribe failed: connection {connection_id} not found"
                )
                return []
            
            unsubscribed = []
            for symbol in symbols:
                if symbol in connection.subscriptions:
                    await self._unsubscribe_unsafe(connection_id, symbol)
                    unsubscribed.append(symbol)
            
            connection.update_activity()
        
        logger.info(
            f"Connection {connection_id} unsubscribed from {len(unsubscribed)} symbols"
        )
        
        return unsubscribed
    
    async def get_subscriptions(self, connection_id: str) -> List[str]:
        """
        Get list of symbols a connection is subscribed to
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            List of subscribed symbols
        """
        connection = self.active_connections.get(connection_id)
        if not connection:
            return []
        
        return list(connection.subscriptions)
    
    async def broadcast_to_symbol(self, symbol: str, message: dict):
        """
        Broadcast a message to all connections subscribed to a symbol
        
        Args:
            symbol: Symbol identifier
            message: Message to broadcast (will be JSON serialized)
        """
        # Get subscribers for this symbol
        subscriber_ids = self.symbol_subscriptions.get(symbol, set()).copy()
        
        if not subscriber_ids:
            return
        
        # Broadcast to all subscribers
        failed_connections = []
        
        for connection_id in subscriber_ids:
            connection = self.active_connections.get(connection_id)
            if not connection:
                failed_connections.append(connection_id)
                continue
            
            try:
                await connection.websocket.send_json(message)
                connection.update_activity()
                WS_MESSAGES_SENT.labels(symbol=symbol).inc()
            except Exception as e:
                logger.error(
                    f"Failed to send message to {connection_id}: {e}"
                )
                WS_ERRORS.labels(error_type="send_failed").inc()
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
    
    async def send_to_connection(self, connection_id: str, message: dict):
        """
        Send a message to a specific connection
        
        Args:
            connection_id: Connection identifier
            message: Message to send (will be JSON serialized)
        """
        connection = self.active_connections.get(connection_id)
        if not connection:
            logger.warning(f"Send failed: connection {connection_id} not found")
            return
        
        try:
            await connection.websocket.send_json(message)
            connection.update_activity()
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            WS_ERRORS.labels(error_type="send_failed").inc()
            await self.disconnect(connection_id)
    
    def get_stats(self) -> dict:
        """
        Get connection manager statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_connections": len(self.active_connections),
            "total_symbols_subscribed": len(self.symbol_subscriptions),
            "connections": [
                {
                    "connection_id": conn.connection_id,
                    "user_id": conn.user_id,
                    "subscriptions": len(conn.subscriptions),
                    "connected_at": conn.connected_at.isoformat(),
                    "last_activity": conn.last_activity.isoformat(),
                }
                for conn in self.active_connections.values()
            ],
            "symbol_stats": {
                symbol: len(subscribers)
                for symbol, subscribers in self.symbol_subscriptions.items()
            }
        }






