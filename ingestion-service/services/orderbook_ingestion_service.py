"""
Orderbook Ingestion Service
Subscription-driven ingestion of Binance partial orderbook snapshots (top N levels).

Control plane:
  - add_interest(symbol): increments refcount and starts a Binance WS stream if needed
  - remove_interest(symbol): decrements refcount and stops stream when count hits zero

Data plane:
  - For each snapshot, publish to Kafka topic crypto.raw.orderbook (key = symbol)
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from config import settings

logger = logging.getLogger(__name__)


class OrderbookIngestionService:
    def __init__(self, kafka_repository, binance_connector):
        self.kafka_repository = kafka_repository
        self.binance_connector = binance_connector

        self._lock = asyncio.Lock()
        self._refcount_by_symbol: dict[str, int] = {}
        self._connection_id_by_symbol: dict[str, str] = {}

        logger.info("OrderbookIngestionService initialized")

    @staticmethod
    def _norm_symbol(symbol: str) -> str:
        return (symbol or "").strip().upper()

    async def add_interest(self, symbol: str) -> dict:
        """
        Add viewer interest for a symbol. Starts Binance stream when first viewer arrives.
        """
        sym = self._norm_symbol(symbol)
        if not sym:
            return {"success": False, "error": "symbol is required"}

        async with self._lock:
            prev = self._refcount_by_symbol.get(sym, 0)
            self._refcount_by_symbol[sym] = prev + 1

            # Already running
            if prev > 0 and sym in self._connection_id_by_symbol:
                return {
                    "success": True,
                    "symbol": sym,
                    "refcount": self._refcount_by_symbol[sym],
                    "started": False,
                }

            # Start stream for first viewer
            async def _handle_snapshot(snapshot: Dict[str, Any]):
                # snapshot is already normalized by BinanceConnector.start_partial_book_stream()
                try:
                    snap_symbol = snapshot.get("symbol") or sym
                    await self.kafka_repository.publish_market_data(
                        symbol=snap_symbol,
                        exchange="binance",
                        data=snapshot,
                        topic=settings.kafka_topic_raw_orderbook,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to publish orderbook snapshot for {sym}: {e}",
                        exc_info=True,
                    )

            connection_id = await self.binance_connector.start_partial_book_stream(
                symbol=sym,
                levels=settings.orderbook_levels,
                speed_ms=settings.orderbook_update_speed_ms,
                callback=_handle_snapshot,
            )
            self._connection_id_by_symbol[sym] = connection_id

            logger.info(
                f"✅ Orderbook stream started for {sym}: connection_id={connection_id}, "
                f"levels={settings.orderbook_levels}, speed_ms={settings.orderbook_update_speed_ms}"
            )

            return {
                "success": True,
                "symbol": sym,
                "refcount": self._refcount_by_symbol[sym],
                "started": True,
                "connection_id": connection_id,
            }

    async def remove_interest(self, symbol: str) -> dict:
        """
        Remove viewer interest for a symbol. Stops Binance stream when last viewer leaves.
        """
        sym = self._norm_symbol(symbol)
        if not sym:
            return {"success": False, "error": "symbol is required"}

        async with self._lock:
            prev = self._refcount_by_symbol.get(sym, 0)
            if prev <= 0:
                return {"success": True, "symbol": sym, "refcount": 0, "stopped": False}

            new = prev - 1
            if new <= 0:
                self._refcount_by_symbol.pop(sym, None)
            else:
                self._refcount_by_symbol[sym] = new

            # Stop stream only when refcount hits zero
            if new > 0:
                return {"success": True, "symbol": sym, "refcount": new, "stopped": False}

            connection_id: Optional[str] = self._connection_id_by_symbol.pop(sym, None)
            if connection_id:
                try:
                    await self.binance_connector.stop_stream(connection_id)
                    logger.info(
                        f"🛑 Orderbook stream stopped for {sym}: connection_id={connection_id}"
                    )
                    return {
                        "success": True,
                        "symbol": sym,
                        "refcount": 0,
                        "stopped": True,
                        "connection_id": connection_id,
                    }
                except Exception as e:
                    logger.error(
                        f"Error stopping orderbook stream for {sym}: {e}", exc_info=True
                    )
                    return {
                        "success": False,
                        "symbol": sym,
                        "refcount": 0,
                        "stopped": False,
                        "error": str(e),
                    }

            return {"success": True, "symbol": sym, "refcount": 0, "stopped": False}

    async def set_interest(self, symbol: str, action: str) -> dict:
        action = (action or "").strip().lower()
        if action == "add":
            return await self.add_interest(symbol)
        if action == "remove":
            return await self.remove_interest(symbol)
        return {"success": False, "error": "action must be 'add' or 'remove'"}

    def get_status(self) -> dict:
        return {
            "topic": settings.kafka_topic_raw_orderbook,
            "levels": settings.orderbook_levels,
            "speed_ms": settings.orderbook_update_speed_ms,
            "active_symbols": sorted(self._connection_id_by_symbol.keys()),
            "refcounts": dict(self._refcount_by_symbol),
            "connections": dict(self._connection_id_by_symbol),
        }


