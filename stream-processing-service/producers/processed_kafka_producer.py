"""
Processed Kafka Producer
Publishes UI-ready processed messages to Kafka topics.
"""

import logging
from typing import Any, Dict, Optional

from config import settings
from shared.kafka_utils.producer import KafkaProducerWrapper

logger = logging.getLogger(__name__)


class ProcessedKafkaProducer:
    def __init__(self, producer: KafkaProducerWrapper):
        self.producer = producer
        logger.info("ProcessedKafkaProducer initialized")

    def publish_orderbook(self, data: Dict[str, Any], topic: Optional[str] = None):
        symbol = data.get("symbol")
        if not symbol:
            logger.warning("Skipping processed orderbook publish: missing symbol")
            return

        self.producer.send(
            topic=topic or settings.kafka_topic_processed_orderbook,
            value=data,
            key=symbol,
        )
    
    def publish_market_data(self, data: Dict[str, Any], topic: Optional[str] = None):
        """
        Publish processed market data (ticker) to Kafka
        
        Args:
            data: Processed ticker data
            topic: Optional override topic
        """
        symbol = data.get("symbol")
        if not symbol:
            logger.warning("Skipping processed market data publish: missing symbol")
            return
        
        self.producer.send(
            topic=topic or settings.kafka_topic_processed_market_data,
            value=data,
            key=symbol,
        )


