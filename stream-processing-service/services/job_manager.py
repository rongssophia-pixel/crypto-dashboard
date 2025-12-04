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
from sinks.clickhouse_sink import ClickHouseSink
from jobs.enrichment_job import EnrichmentJob
from jobs.candle_aggregation_job import CandleAggregationJob

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
        
        # Initialize jobs
        self.enrichment_job = EnrichmentJob(
            output_handler=self._on_enriched_data
        )
        
        self.candle_job = CandleAggregationJob(
            intervals=candle_intervals,
            output_handler=self._on_candle_complete
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
        """
        try:
            # Process through enrichment job
            enriched = await self.enrichment_job.process(data)
            
            # Process through candle aggregation
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
