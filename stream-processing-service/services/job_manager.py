"""
Job Manager Service
Coordinates processing jobs and data flow
"""

import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

# Add shared to path for imports
sys.path.insert(0, "/app")

from shared.kafka_utils import KafkaConsumerWrapper
from shared.kafka_utils.producer import KafkaProducerWrapper
from sinks.clickhouse_sink import ClickHouseSink
from jobs.enrichment_job import EnrichmentJob
from jobs.candle_aggregation_job import CandleAggregationJob
from jobs.orderbook_job import OrderbookJob
from jobs.ticker_job import TickerJob
from producers.processed_kafka_producer import ProcessedKafkaProducer

logger = logging.getLogger(__name__)


class JobManager:
    """
    Manages the lifecycle and coordination of processing jobs
    
    Data Flow:
    Kafka Consumer → Enrichment Job → ClickHouse Sink
                   → Candle Aggregation Job → ClickHouse Sink
    """
    
    def __init__(
        self,
        kafka_consumer: KafkaConsumerWrapper,
        clickhouse_sink: ClickHouseSink,
        processed_producer: ProcessedKafkaProducer,
        candle_intervals: List[str],
    ):
        """
        Initialize job manager
        
        Args:
            kafka_consumer: Kafka consumer instance
            clickhouse_sink: ClickHouse sink instance
            candle_intervals: List of candle intervals to aggregate
        """
        self.kafka_consumer = kafka_consumer
        self.clickhouse_sink = clickhouse_sink
        self.processed_producer = processed_producer
        
        # Initialize jobs
        self.enrichment_job = EnrichmentJob(
            output_handler=self._on_enriched_data
        )
        
        self.candle_job = CandleAggregationJob(
            intervals=candle_intervals,
            output_handler=self._on_candle_complete
        )

        self.orderbook_job = OrderbookJob(
            output_handler=self._on_orderbook_processed
        )
        
        self.ticker_job = TickerJob(
            output_handler=self._on_ticker_processed
        )
        
        self._running = False
        self._message_count = 0
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kafka-consumer")
        self._consumer_future: Optional[asyncio.Future] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        logger.info("JobManager initialized")
    
    async def start(self):
        """Start all jobs and begin processing"""
        logger.info("Starting JobManager...")
        
        # Start jobs
        await self.enrichment_job.start()
        await self.candle_job.start()
        await self.orderbook_job.start()
        await self.ticker_job.start()
        
        self._running = True
        self._loop = asyncio.get_event_loop()
        
        # Run Kafka consumer in thread pool (non-blocking)
        self._consumer_future = self._loop.run_in_executor(
            self._executor,
            self._run_consumer_sync
        )
        
        logger.info("✅ JobManager started - processing pipeline active")
    
    async def stop(self):
        """Stop all jobs gracefully"""
        logger.info("Stopping JobManager...")
        
        self._running = False
        
        # Stop consumer (sets _running to False, allows thread to exit)
        self.kafka_consumer.close()
        
        # Wait for consumer thread to finish
        if self._consumer_future:
            try:
                await asyncio.wait_for(self._consumer_future, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Consumer thread did not stop in time")
        
        # Shutdown executor
        self._executor.shutdown(wait=False)
        
        # Stop jobs (they may emit remaining data)
        await self.candle_job.stop()
        await self.orderbook_job.stop()
        await self.ticker_job.stop()
        await self.enrichment_job.stop()
        
        # Final flush of sink
        await self.clickhouse_sink.flush()
        
        logger.info(f"✅ JobManager stopped. Total messages processed: {self._message_count}")
    
    def _run_consumer_sync(self):
        """
        Run the Kafka consumer in a sync context (called from thread pool).
        This is blocking but runs in a separate thread.
        """
        logger.info("Starting Kafka consumer in thread pool...")
        
        try:
            self.kafka_consumer.consume(self._handle_message_sync)
        except Exception as e:
            logger.error(f"Consumer thread error: {e}", exc_info=True)
        
        logger.info("Kafka consumer thread finished")
    
    def _handle_message_sync(self, data: Dict[str, Any]):
        """
        Handle incoming Kafka message (sync context from consumer thread).
        Schedules async processing on the event loop.
        """
        if not self._running or not self._loop:
            return
            
        try:
            self._message_count += 1
            
            # Schedule async processing on the main event loop
            asyncio.run_coroutine_threadsafe(
                self._process_message(data),
                self._loop
            )
            
        except Exception as e:
            logger.error(f"Error scheduling message processing: {e}", exc_info=True)
    
    async def _process_message(self, data: Dict[str, Any]):
        """
        Process a message asynchronously (runs on main event loop).
        Routes data based on type:
        - kline: passthrough to market_candles (no aggregation)
        - ticker: passthrough to market_data (no aggregation)
        - other: aggregate via candle job (backward compatibility)
        """
        try:
            data_type = data.get("type")
            
            if data_type == "kline":
                # Kline data already has OHLCV - pass through directly
                logger.debug(f"Processing kline data: {data.get('symbol')} {data.get('interval')}")
                await self._on_candle_complete(data)
                
            elif data_type == "ticker":
                # Ticker data has 24h stats - enrich then throttle via ticker job
                logger.debug(f"Processing ticker data: {data.get('symbol')}")
                enriched = await self.enrichment_job.process(data)
                # Route through ticker job for throttling and broadcast
                await self.ticker_job.process(enriched)
                
            elif data_type == "orderbook":
                logger.debug(f"Processing orderbook data: {data.get('symbol')}")
                await self.orderbook_job.process(data)
            else:
                # Legacy path: trade/tick data that needs aggregation
                logger.debug(f"Processing legacy data type: {data_type}")
                enriched = await self.enrichment_job.process(data)
                await self.candle_job.process(enriched)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    async def _on_enriched_data(self, data: Dict[str, Any]):
        """
        Callback when data is enriched
        Writes to ClickHouse market_data table
        """
        await self.clickhouse_sink.write_market_data(data)
    
    async def _on_candle_complete(self, candle: Dict[str, Any]):
        """
        Callback when a candle is completed
        Writes to ClickHouse market_candles table
        """
        await self.clickhouse_sink.write_candle(candle)

    async def _on_orderbook_processed(self, book: Dict[str, Any]):
        """
        Callback when an orderbook snapshot is processed.
        Publishes to Kafka crypto.processed.orderbook for API Gateway WS fanout.
        """
        try:
            self.processed_producer.publish_orderbook(book)
        except Exception as e:
            logger.error(f"Failed to publish processed orderbook: {e}", exc_info=True)
    
    async def _on_ticker_processed(self, ticker: Dict[str, Any]):
        """
        Callback when ticker data is processed (throttled).
        Publishes to Kafka crypto.processed.market-data for API Gateway WS fanout.
        """
        try:
            self.processed_producer.publish_market_data(ticker)
        except Exception as e:
            logger.error(f"Failed to publish processed ticker: {e}", exc_info=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive job statistics"""
        return {
            "is_running": self._running,
            "messages_processed": self._message_count,
            "consumer": {
                "is_running": self.kafka_consumer.is_running,
            },
            "enrichment": self.enrichment_job.get_stats(),
            "candle_aggregation": self.candle_job.get_stats(),
            "orderbook": self.orderbook_job.get_stats(),
            "ticker": self.ticker_job.get_stats(),
            "clickhouse_sink": self.clickhouse_sink.get_stats(),
        }
    
    @property
    def is_healthy(self) -> bool:
        """Check if all components are healthy"""
        return (
            self._running
            and self.kafka_consumer.is_running
            and self.enrichment_job._running
            and self.candle_job._running
            and self.clickhouse_sink._running
        )
