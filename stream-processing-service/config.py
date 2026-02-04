"""
Stream Processing Service Configuration
Loads configuration from environment variables
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """
    Service configuration settings
    """
    
    model_config = SettingsConfigDict(
        env_file="../.env",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Service info
    service_name: str = "stream-processing-service"
    service_port: int = 50055  # gRPC port
    http_port: int = 8005  # FastAPI HTTP port for monitoring
    
    # Kafka Consumer
    # Local development: localhost:9092
    # Docker deployment: override with KAFKA_BOOTSTRAP_SERVERS=kafka:19092
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "stream-processing-group"
    kafka_topic_raw_market_data: str = "crypto.raw.market-data"
    kafka_topic_processed_market_data: str = "crypto.processed.market-data"
    kafka_topic_raw_orderbook: str = "crypto.raw.orderbook"
    kafka_topic_processed_orderbook: str = "crypto.processed.orderbook"
    kafka_topic_alerts: str = "crypto.alerts"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_sasl_mechanism: Optional[str] = None
    kafka_sasl_username: Optional[str] = None
    kafka_sasl_password: Optional[str] = None
    
    # ClickHouse
    # Local development: localhost
    # Docker deployment: override with CLICKHOUSE_HOST=clickhouse
    # Railway/ClickHouse Cloud: CLICKHOUSE_HOST may include https:// prefix
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_db: str
    clickhouse_user: str = "default"
    clickhouse_password: str
    clickhouse_secure: bool = False
    clickhouse_verify: bool = True
    
    @field_validator('clickhouse_host')
    @classmethod
    def clean_clickhouse_host(cls, v: str) -> str:
        """Strip protocol prefix and port from ClickHouse host URL"""
        if not v:
            return v
        # Remove protocol prefix (https://, http://)
        if '://' in v:
            v = v.split('://', 1)[1]
        # Remove port suffix if present (e.g., host:8443)
        if ':' in v:
            v = v.split(':', 1)[0]
        return v
    
    # Processing configuration
    candle_intervals: str = "1m,5m,15m,1h"  # Comma-separated
    batch_size: int = 100
    flush_interval_seconds: int = 5

    # Orderbook processing
    orderbook_levels: int = 20
    orderbook_max_updates_per_sec: int = 5
    
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


# Global settings instance
settings = Settings()
