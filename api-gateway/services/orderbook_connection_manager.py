"""
Orderbook WebSocket Connection Manager
Dedicated manager for /ws/orderbook with max 1 symbol per connection.

Also integrates with ingestion-service interest control:
- When first subscriber arrives for a symbol: action=add
- When last subscriber leaves: action=remove
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

from fastapi import WebSocket
from prometheus_client import Counter, Gauge

from services.ingestion_interest_client import IngestionInterestClient

logger = logging.getLogger(__name__)


# Prometheus metrics (separate namespace)
OB_WS_CONNECTIONS = Gauge(
    "orderbook_websocket_active_connections",
    "Number of active orderbook WebSocket connections",
)

OB_WS_SUBSCRIPTIONS = Gauge(
    "orderbook_websocket_active_subscriptions",
    "Number of active orderbook subscriptions",
    ["symbol"],
)

OB_WS_MESSAGES_SENT = Counter(
    "orderbook_websocket_messages_sent_total",
    "Total orderbook WebSocket messages sent",
    ["symbol"],
)

OB_WS_ERRORS = Counter(
    "orderbook_websocket_errors_total",
    "Total orderbook WebSocket errors",
    ["error_type"],
)


class OrderbookWebSocketConnection:
    def __init__(self, connection_id: str, websocket: WebSocket, user_id: str):
        self.connection_id = connection_id
        self.websocket = websocket
        self.user_id = user_id
        self.subscriptions: Set[str] = set()  # max size 1
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

    def update_activity(self):
        self.last_activity = datetime.utcnow()


class OrderbookConnectionManager:
    def __init__(self, interest_client: Optional[IngestionInterestClient] = None):
        self.active_connections: Dict[str, OrderbookWebSocketConnection] = {}
        self.symbol_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # symbol -> conn_ids
        self._lock = asyncio.Lock()
        self.interest_client = interest_client or IngestionInterestClient()

        logger.info("OrderbookConnectionManager initialized")

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        connection_id = str(uuid.uuid4())
        async with self._lock:
            self.active_connections[connection_id] = OrderbookWebSocketConnection(
                connection_id, websocket, user_id
            )
            OB_WS_CONNECTIONS.set(len(self.active_connections))
        return connection_id

    async def disconnect(self, connection_id: str):
        interest_removes: list[str] = []
        async with self._lock:
            connection = self.active_connections.get(connection_id)
            if not connection:
                return

            for symbol in list(connection.subscriptions):
                became_empty = await self._unsubscribe_unsafe(connection_id, symbol)
                if became_empty:
                    interest_removes.append(symbol)

            del self.active_connections[connection_id]
            OB_WS_CONNECTIONS.set(len(self.active_connections))

        for sym in interest_removes:
            await self._interest_remove(sym)

    async def subscribe(self, connection_id: str, symbols: List[str]) -> List[str]:
        """
        Subscribe connection to exactly one symbol.
        If connection already subscribed to a different symbol, replace it.
        """
        if not symbols:
            return []

        target = (symbols[0] or "").strip().upper()
        if not target:
            return []

        interest_adds: list[str] = []
        interest_removes: list[str] = []

        async with self._lock:
            connection = self.active_connections.get(connection_id)
            if not connection:
                return []

            current = next(iter(connection.subscriptions), None)
            if current == target:
                return [target]

            # Replace existing subscription (max 1)
            if current:
                became_empty = await self._unsubscribe_unsafe(connection_id, current)
                if became_empty:
                    interest_removes.append(current)

            # Subscribe to new symbol
            was_empty = len(self.symbol_subscriptions[target]) == 0
            connection.subscriptions = {target}
            self.symbol_subscriptions[target].add(connection_id)
            OB_WS_SUBSCRIPTIONS.labels(symbol=target).set(len(self.symbol_subscriptions[target]))

            if was_empty:
                interest_adds.append(target)

            connection.update_activity()

        # Call control plane outside lock
        for sym in interest_removes:
            ok = await self._interest_remove(sym)
            if not ok:
                await self.send_to_connection(
                    connection_id,
                    {
                        "type": "warning",
                        "message": f"Failed to stop upstream ingestion for {sym} (ingestion-service unreachable?)",
                    },
                )
        for sym in interest_adds:
            ok = await self._interest_add(sym)
            if not ok:
                await self.send_to_connection(
                    connection_id,
                    {
                        "type": "warning",
                        "message": f"Failed to start upstream ingestion for {sym} (ingestion-service unreachable?)",
                    },
                )

        return [target]

    async def unsubscribe(self, connection_id: str, symbols: List[str]) -> List[str]:
        if not symbols:
            return []

        symbols_norm = [(s or "").strip().upper() for s in symbols if (s or "").strip()]
        interest_removes: list[str] = []
        unsubscribed: list[str] = []

        async with self._lock:
            connection = self.active_connections.get(connection_id)
            if not connection:
                return []

            for sym in symbols_norm:
                if sym in connection.subscriptions:
                    became_empty = await self._unsubscribe_unsafe(connection_id, sym)
                    unsubscribed.append(sym)
                    if became_empty:
                        interest_removes.append(sym)

            connection.update_activity()

        for sym in interest_removes:
            ok = await self._interest_remove(sym)
            if not ok:
                await self.send_to_connection(
                    connection_id,
                    {
                        "type": "warning",
                        "message": f"Failed to stop upstream ingestion for {sym} (ingestion-service unreachable?)",
                    },
                )

        return unsubscribed

    async def _unsubscribe_unsafe(self, connection_id: str, symbol: str) -> bool:
        """
        Assumes lock held.
        Returns True if symbol subscription set became empty.
        """
        # Remove from symbol map
        if symbol in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol].discard(connection_id)
            if not self.symbol_subscriptions[symbol]:
                del self.symbol_subscriptions[symbol]
                OB_WS_SUBSCRIPTIONS.labels(symbol=symbol).set(0)
                became_empty = True
            else:
                OB_WS_SUBSCRIPTIONS.labels(symbol=symbol).set(len(self.symbol_subscriptions[symbol]))
                became_empty = False
        else:
            became_empty = True

        # Remove from connection
        conn = self.active_connections.get(connection_id)
        if conn:
            conn.subscriptions.discard(symbol)

        return became_empty

    async def get_subscriptions(self, connection_id: str) -> List[str]:
        conn = self.active_connections.get(connection_id)
        if not conn:
            return []
        return list(conn.subscriptions)

    async def broadcast_to_symbol(self, symbol: str, message: dict):
        subscriber_ids = self.symbol_subscriptions.get(symbol, set()).copy()
        if not subscriber_ids:
            return

        failed: list[str] = []
        for connection_id in subscriber_ids:
            conn = self.active_connections.get(connection_id)
            if not conn:
                failed.append(connection_id)
                continue
            try:
                await conn.websocket.send_json(message)
                conn.update_activity()
                OB_WS_MESSAGES_SENT.labels(symbol=symbol).inc()
            except Exception as e:
                logger.error(f"Failed to send orderbook message to {connection_id}: {e}")
                OB_WS_ERRORS.labels(error_type="send_failed").inc()
                failed.append(connection_id)

        for cid in failed:
            await self.disconnect(cid)

    async def send_to_connection(self, connection_id: str, message: dict):
        conn = self.active_connections.get(connection_id)
        if not conn:
            return
        try:
            await conn.websocket.send_json(message)
            conn.update_activity()
        except Exception as e:
            logger.error(f"Failed to send to connection {connection_id}: {e}")
            OB_WS_ERRORS.labels(error_type="send_failed").inc()
            await self.disconnect(connection_id)

    def get_stats(self) -> dict:
        return {
            "total_connections": len(self.active_connections),
            "symbols": {sym: len(ids) for sym, ids in self.symbol_subscriptions.items()},
        }

    async def _interest_add(self, symbol: str) -> bool:
        ok = await self.interest_client.add(symbol)
        if not ok:
            OB_WS_ERRORS.labels(error_type="interest_add_failed").inc()
        return ok

    async def _interest_remove(self, symbol: str) -> bool:
        ok = await self.interest_client.remove(symbol)
        if not ok:
            OB_WS_ERRORS.labels(error_type="interest_remove_failed").inc()
        return ok


