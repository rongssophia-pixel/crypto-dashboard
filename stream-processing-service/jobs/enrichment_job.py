"""
Market Data Enrichment Job
Enriches raw market data with calculated fields
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class EnrichmentJob:
    """
    Enriches raw market data with additional calculated fields:
    - Spread (ask - bid)
    - Spread percentage
    - Mid price
    - Processing timestamp
    """
    
    def __init__(
        self,
        output_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize enrichment job
        
        Args:
            output_handler: Async function to call with enriched data
        """
        self.output_handler = output_handler
        self._records_processed = 0
        self._running = False
        
        logger.info("EnrichmentJob initialized")
    
    async def start(self):
        """Start the enrichment job"""
        self._running = True
        logger.info("✅ EnrichmentJob started")
    
    async def stop(self):
        """Stop the enrichment job"""
        self._running = False
        logger.info(f"✅ EnrichmentJob stopped. Processed {self._records_processed} records")
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and enrich a single market data record
        
        Args:
            data: Raw market data from Kafka
            
        Returns:
            Enriched market data
        """
        if not self._running:
            return data
            
        try:
            enriched = self._enrich(data)
            self._records_processed += 1
            
            # Call output handler if set
            if self.output_handler:
                await self.output_handler(enriched)
                
            return enriched
            
        except Exception as e:
            logger.error(f"Error enriching data: {e}", exc_info=True)
            return data
    
    def _enrich(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add calculated fields to market data
        
        Args:
            data: Raw market data
            
        Returns:
            Enriched data with additional fields
        """
        enriched = data.copy()
        
        # Extract prices
        bid_price = float(data.get("bid_price", 0))
        ask_price = float(data.get("ask_price", 0))
        price = float(data.get("price", 0))
        
        # Calculate spread
        spread = ask_price - bid_price if ask_price and bid_price else 0
        enriched["spread"] = spread
        
        # Calculate spread percentage
        if bid_price > 0:
            spread_pct = (spread / bid_price) * 100
        else:
            spread_pct = 0
        enriched["spread_pct"] = round(spread_pct, 6)
        
        # Calculate mid price
        if bid_price and ask_price:
            mid_price = (bid_price + ask_price) / 2
        else:
            mid_price = price
        enriched["mid_price"] = mid_price
        
        # Add processing timestamp
        enriched["processed_at"] = int(datetime.utcnow().timestamp() * 1000)
        
        # Add source marker
        enriched["enriched"] = True
        
        return enriched
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job statistics"""
        return {
            "job_type": "enrichment",
            "records_processed": self._records_processed,
            "is_running": self._running,
        }

