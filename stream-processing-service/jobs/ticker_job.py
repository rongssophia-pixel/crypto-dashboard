"""
Ticker Job
Validates/cleans ticker data and throttles per symbol for UI consumption.
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from config import settings

logger = logging.getLogger(__name__)


class TickerJob:
    """
    Validates and throttles ticker data per symbol.
    Emits cleaned ticker payloads at configured interval (default 5 seconds).
    """
    
    def __init__(
        self,
        output_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize ticker job
        
        Args:
            output_handler: Async function to call with processed ticker data
        """
        self.output_handler = output_handler
        self._running = False
        self._records_processed = 0
        self._records_emitted = 0
        self._last_emit_ms_by_symbol: dict[str, int] = {}
        
        logger.info("TickerJob initialized")
    
    async def start(self):
        """Start the ticker job"""
        self._running = True
        logger.info("✅ TickerJob started")
    
    async def stop(self):
        """Stop the ticker job"""
        self._running = False
        logger.info(
            f"✅ TickerJob stopped. processed={self._records_processed}, emitted={self._records_emitted}"
        )
    
    async def process(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a ticker message
        
        Args:
            data: Ticker data from enrichment
            
        Returns:
            Cleaned ticker data if emitted, None if throttled
        """
        if not self._running:
            return data
        
        try:
            self._records_processed += 1
            
            # Validate and clean
            cleaned = self._clean(data)
            if not cleaned:
                return None
            
            # Throttle per symbol
            symbol = cleaned.get("symbol")
            if not symbol:
                return None
            
            now_ms = int(time.time() * 1000)
            min_interval_ms = int(settings.ticker_update_interval_seconds * 1000)
            last_ms = self._last_emit_ms_by_symbol.get(symbol)
            
            if last_ms is not None and now_ms - last_ms < min_interval_ms:
                # Throttle: too soon since last emit
                return None
            
            cleaned["processed_at"] = now_ms
            self._last_emit_ms_by_symbol[symbol] = now_ms
            
            self._records_emitted += 1
            
            if self.output_handler:
                await self.output_handler(cleaned)
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error processing ticker: {e}", exc_info=True)
            return None
    
    def _clean(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate and clean ticker data
        
        Args:
            data: Raw ticker data
            
        Returns:
            Cleaned ticker data or None if invalid
        """
        if not isinstance(data, dict):
            return None
        
        if data.get("type") != "ticker":
            return None
        
        symbol = data.get("symbol")
        if not symbol:
            return None
        
        # Extract and validate required fields
        price = data.get("price")
        if price is None or price <= 0:
            return None
        
        ts = data.get("timestamp")
        if ts is None:
            ts = int(datetime.utcnow().timestamp() * 1000)
        
        # Build cleaned ticker with all 24h stats
        cleaned = {
            "type": "ticker",
            "symbol": symbol,
            "exchange": data.get("exchange") or "binance",
            "timestamp": ts,
            "price": float(price),
            "volume": float(data.get("volume", 0)) if data.get("volume") else 0,
            "bid_price": float(data.get("bid_price", 0)) if data.get("bid_price") else None,
            "ask_price": float(data.get("ask_price", 0)) if data.get("ask_price") else None,
            "bid_volume": float(data.get("bid_volume", 0)) if data.get("bid_volume") else None,
            "ask_volume": float(data.get("ask_volume", 0)) if data.get("ask_volume") else None,
        }
        
        # Add 24h statistics
        if "open_24h" in data and data["open_24h"]:
            cleaned["open_24h"] = float(data["open_24h"])
        if "high_24h" in data and data["high_24h"]:
            cleaned["high_24h"] = float(data["high_24h"])
        if "low_24h" in data and data["low_24h"]:
            cleaned["low_24h"] = float(data["low_24h"])
        if "volume_24h" in data and data["volume_24h"]:
            cleaned["volume_24h"] = float(data["volume_24h"])
        if "price_change_24h" in data and data["price_change_24h"] is not None:
            cleaned["price_change_24h"] = float(data["price_change_24h"])
        if "price_change_pct_24h" in data and data["price_change_pct_24h"] is not None:
            cleaned["price_change_pct_24h"] = float(data["price_change_pct_24h"])
        
        # Add enriched fields if present
        if "spread" in data:
            cleaned["spread"] = float(data["spread"])
        if "spread_pct" in data:
            cleaned["spread_pct"] = float(data["spread_pct"])
        if "mid_price" in data:
            cleaned["mid_price"] = float(data["mid_price"])
        
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job statistics"""
        return {
            "job_type": "ticker",
            "processed": self._records_processed,
            "emitted": self._records_emitted,
            "is_running": self._running,
            "symbols_tracked": len(self._last_emit_ms_by_symbol),
        }

