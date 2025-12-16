"""
Kafka Alert Consumer
Consumes alert events from crypto.alerts topic and triggers notifications
"""

import asyncio
import json
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

logger = logging.getLogger(__name__)


class AlertConsumer:
    """
    Async Kafka consumer for alert events
    Routes alerts to notification business service
    """
    
    def __init__(
        self,
        business_service,
        kafka_servers: str,
        topic: str = "crypto.alerts",
        group_id: str = "notification-service-group"
    ):
        """
        Initialize alert consumer
        
        Args:
            business_service: NotificationBusinessService instance
            kafka_servers: Kafka bootstrap servers
            topic: Topic to consume from
            group_id: Consumer group ID
        """
        self.business_service = business_service
        self.kafka_servers = kafka_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False
        logger.info(
            f"AlertConsumer initialized: topic={topic}, group={group_id}, "
            f"servers={kafka_servers}"
        )
    
    async def start(self):
        """Start consuming messages from Kafka"""
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.kafka_servers,
            group_id=self.group_id,
            auto_offset_reset='earliest',
            enable_auto_commit=False,  # Manual commit after processing
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        try:
            await self.consumer.start()
            logger.info(f"Kafka consumer started for topic: {self.topic}")
            self.running = True
            
            # Start consuming messages
            await self.consume_messages()
            
        except KafkaError as e:
            logger.error(f"Kafka error during consumer start: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting consumer: {e}")
            raise
    
    async def consume_messages(self):
        """Main consumption loop"""
        try:
            async for message in self.consumer:
                if not self.running:
                    logger.info("Consumer stopped, breaking message loop")
                    break
                
                try:
                    alert = message.value
                    logger.info(
                        f"Received alert: topic={message.topic}, "
                        f"partition={message.partition}, offset={message.offset}"
                    )
                    logger.debug(f"Alert data: {alert}")
                    
                    # Process the alert
                    result = await self.process_alert(alert)
                    
                    if result.get("success"):
                        logger.info(
                            f"Alert processed successfully: "
                            f"notification_id={result.get('notification_id')}"
                        )
                    else:
                        logger.error(
                            f"Alert processing failed: {result.get('error')}"
                        )
                    
                    # Commit offset after successful processing
                    await self.consumer.commit()
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode alert message: {e}")
                    # Still commit to avoid getting stuck on bad message
                    await self.consumer.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing alert message: {e}")
                    # Commit to avoid reprocessing same message indefinitely
                    await self.consumer.commit()
                    
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in consume_messages: {e}")
            raise
    
    async def process_alert(self, alert: dict) -> dict:
        """
        Process a single alert event
        
        Args:
            alert: Alert event data
            
        Returns:
            Processing result
        """
        try:
            # Delegate to business service
            result = await self.business_service.process_alert(alert)
            return result
        except Exception as e:
            logger.error(f"Error in process_alert: {e}")
            return {"success": False, "error": str(e)}
    
    async def stop(self):
        """Stop consuming and cleanup"""
        logger.info("Stopping alert consumer...")
        self.running = False
        
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}")
    
    def is_running(self) -> bool:
        """Check if consumer is running"""
        return self.running and self.consumer is not None
