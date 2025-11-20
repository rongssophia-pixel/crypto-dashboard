"""
Ingestion Service Configuration
Loads configuration from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Service configuration settings
    """
    
    # Service info
    service_name: str = "ingestion-service"
    service_port: int = 50051
    
    # Kafka configuration
    kafka_bootstrap_servers: str
    kafka_topic_raw_market_data: str = "crypto.raw.market-data"
    kafka_topic_processed_market_data: str = "crypto.processed.market-data"
    
    # PostgreSQL configuration
    postgres_host: str
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

