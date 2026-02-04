"""
Orderbook Job
Validates/cleans orderbook snapshots and throttles per symbol for UI consumption.
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from config import settings

logger = logging.getLogger(__name__)


class OrderbookJob:
    def __init__(
        self,
        output_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.output_handler = output_handler
        self._running = False
        self._records_processed = 0
        self._records_emitted = 0
        self._last_emit_ms_by_symbol: dict[str, int] = {}

        logger.info("OrderbookJob initialized")

    async def start(self):
        self._running = True
        logger.info("✅ OrderbookJob started")

    async def stop(self):
        self._running = False
        logger.info(
            f"✅ OrderbookJob stopped. processed={self._records_processed}, emitted={self._records_emitted}"
        )

    async def process(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._running:
            return data

        try:
            self._records_processed += 1

            cleaned = self._clean(data)
            if not cleaned:
                return None

            # Throttle per symbol
            symbol = cleaned.get("symbol")
            if not symbol:
                return None

            now_ms = int(time.time() * 1000)
            min_interval_ms = int(1000 / max(settings.orderbook_max_updates_per_sec, 1))
            last_ms = self._last_emit_ms_by_symbol.get(symbol)
            if last_ms is not None and now_ms - last_ms < min_interval_ms:
                return None

            cleaned["processed_at"] = now_ms
            self._last_emit_ms_by_symbol[symbol] = now_ms

            # Derived fields for UI
            self._add_derived_fields(cleaned)

            self._records_emitted += 1

            if self.output_handler:
                await self.output_handler(cleaned)

            return cleaned

        except Exception as e:
            logger.error(f"Error processing orderbook: {e}", exc_info=True)
            return None

    def _clean(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(data, dict):
            return None

        if data.get("type") != "orderbook":
            return None

        symbol = data.get("symbol")
        if not symbol:
            return None

        bids = self._parse_levels(data.get("bids") or [])
        asks = self._parse_levels(data.get("asks") or [])

        # Drop empty snapshots
        if not bids and not asks:
            return None

        # Cap levels (keep best N)
        bids.sort(key=lambda x: x[0], reverse=True)
        asks.sort(key=lambda x: x[0])

        bids = bids[: settings.orderbook_levels]
        asks = asks[: settings.orderbook_levels]

        ts = data.get("timestamp")
        if ts is None:
            ts = int(datetime.utcnow().timestamp() * 1000)

        return {
            "type": "orderbook",
            "symbol": symbol,
            "exchange": data.get("exchange") or "binance",
            "timestamp": ts,
            "levels": int(data.get("levels") or settings.orderbook_levels),
            "bids": bids,
            "asks": asks,
            "last_update_id": data.get("last_update_id"),
        }

    @staticmethod
    def _parse_levels(levels: Any) -> list[list[float]]:
        out: list[list[float]] = []
        if not isinstance(levels, list):
            return out
        for lvl in levels:
            if not isinstance(lvl, (list, tuple)) or len(lvl) < 2:
                continue
            try:
                price = float(lvl[0])
                size = float(lvl[1])
            except Exception:
                continue
            if price <= 0 or size <= 0:
                continue
            out.append([price, size])
        return out

    @staticmethod
    def _add_derived_fields(book: Dict[str, Any]) -> None:
        bids = book.get("bids") or []
        asks = book.get("asks") or []
        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None

        if best_bid is not None and best_ask is not None:
            spread = best_ask - best_bid
            book["spread"] = spread
            book["mid_price"] = (best_bid + best_ask) / 2
            book["spread_pct"] = (spread / best_bid) * 100 if best_bid else 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "job_type": "orderbook",
            "processed": self._records_processed,
            "emitted": self._records_emitted,
            "is_running": self._running,
            "symbols_tracked": len(self._last_emit_ms_by_symbol),
        }


