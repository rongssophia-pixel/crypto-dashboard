"""
Ingestion Service Configuration
Loads configuration from environment variables
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


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
    http_port: int = 8001  # FastAPI HTTP port for monitoring
    
    # Kafka configuration
    # Local development: localhost:9092
    # Docker deployment: override with KAFKA_BOOTSTRAP_SERVERS=kafka:19092
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_raw_market_data: str = "crypto.raw.market-data"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_sasl_mechanism: Optional[str] = None
    kafka_sasl_username: Optional[str] = None
    kafka_sasl_password: Optional[str] = None
    
    # Binance API configuration
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    binance_websocket_url: str = "wss://stream.binance.us:9443"
    binance_rest_api_url: str = "https://api.binance.us"
    
    # Auto-ingestion configuration
    auto_start_ingestion: bool = True
    kline_intervals: str = "1m,5m,15m,1h,4h,1d"  # Comma-separated intervals
    enable_ticker_streams: bool = True
    enable_trade_streams: bool = False
    symbol_filter_quote_currency: str = "USDT"
    max_symbols_per_connection: int = 50  # Reduced to avoid HTTP 414 (URI too long)
    symbol_refresh_interval_hours: int = 24
    
    # JWT configuration (kept for compatibility)
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    prometheus_port: int = 9100
    
    @property
    def kline_interval_list(self) -> List[str]:
        """Parse comma-separated kline intervals into a list"""
        return [interval.strip() for interval in self.kline_intervals.split(",")]


# Global settings instance
settings = Settings()

