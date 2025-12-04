"""
Stream Processing Service Configuration
Loads configuration from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Service configuration settings
    """
    
    # Service info
    service_name: str = "stream-processing-service"
    service_port: int = 50055  # gRPC port
    http_port: int = 8005  # FastAPI HTTP port for monitoring
    
    # Kafka Consumer
    kafka_bootstrap_servers: str
    kafka_consumer_group: str = "stream-processing-group"
    kafka_topic_raw_market_data: str = "crypto.raw.market-data"
    kafka_topic_processed_market_data: str = "crypto.processed.market-data"
    kafka_topic_alerts: str = "crypto.alerts"
    
    # ClickHouse
    clickhouse_host: str
    clickhouse_port: int = 9000
    clickhouse_db: str
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    
    # Processing configuration
    candle_intervals: str = "1m,5m,15m,1h"  # Comma-separated
    batch_size: int = 100
    flush_interval_seconds: int = 5
    
    # PostgreSQL (for alert subscriptions - optional)
    postgres_host: Optional[str] = None
    postgres_port: int = 5432
    postgres_db: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    
    # JWT configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    prometheus_port: int = 9105
    
    @property
    def candle_interval_list(self) -> list:
        """Get candle intervals as a list"""
        return [i.strip() for i in self.candle_intervals.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
