"""
Analytics Service Configuration
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration settings"""
    
    model_config = SettingsConfigDict(
        env_file="../.env",
        case_sensitive=False,
        extra="ignore"
    )
    
    service_name: str = "analytics-service"
    service_port: int = 50052  # gRPC port
    http_port: int = 8002  # FastAPI HTTP port
    
    # ClickHouse configuration
    # Local development: localhost
    # Docker deployment: override with CLICKHOUSE_HOST=clickhouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_db: str = "crypto_analytics"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_secure: bool = False
    clickhouse_verify: bool = True
    
    # JWT configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    prometheus_port: int = 9102
    
    # Query defaults
    default_query_limit: int = 1000
    max_query_limit: int = 10000
    default_candle_limit: int = 500
    max_candle_limit: int = 5000
    
    # Cache configuration
    cache_enabled: bool = True
    cache_ttl_seconds: int = 60


settings = Settings()
