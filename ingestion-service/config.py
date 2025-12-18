"""
Ingestion Service Configuration
Loads configuration from environment variables
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
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
    service_name: str = "ingestion-service"
    service_port: int = 50051  # gRPC port
    http_port: int = 8001  # FastAPI HTTP port for monitoring
    
    # Kafka configuration
    # Local development: localhost:9092
    # Docker deployment: override with KAFKA_BOOTSTRAP_SERVERS=kafka:19092
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_raw_market_data: str = "crypto.raw.market-data"
    kafka_topic_processed_market_data: str = "crypto.processed.market-data"
    
    # PostgreSQL configuration
    # Local development: localhost
    # Docker deployment: override with POSTGRES_HOST=postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str
    
    # Binance API configuration
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    binance_websocket_url: str = "wss://stream.binance.com:9443"
    
    # JWT configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    prometheus_port: int = 9100


# Global settings instance
settings = Settings()

