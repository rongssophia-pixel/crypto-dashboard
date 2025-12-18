"""API Gateway Configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        case_sensitive=False,
        extra="ignore"
    )
    
    service_name: str = "api-gateway"
    service_port: int = 8000
    
    # Service endpoints
    ingestion_service_host: str = "localhost"
    ingestion_service_port: int = 50051
    analytics_service_host: str = "localhost"
    analytics_service_port: int = 50052
    storage_service_host: str = "localhost"
    storage_service_port: int = 50053
    notification_service_host: str = "localhost"
    notification_service_port: int = 50054
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 7
    
    # Email verification
    verification_token_expiration_hours: int = 24
    password_reset_token_expiration_hours: int = 1
    frontend_url: str = "http://localhost:3000"
    
    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "crypto_dashboard"
    postgres_user: str = "crypto_user"
    postgres_password: str
    
    # CORS
    cors_origins: list = ["*"]
    
    # Monitoring
    prometheus_port: int = 9100
    
    # Kafka configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_processed_market_data: str = "crypto.processed.market-data"
    kafka_consumer_group: str = "api-gateway-websocket-group"
    
    # WebSocket configuration
    websocket_heartbeat_interval: int = 30  # seconds
    websocket_max_subscriptions_per_client: int = 50


settings = Settings()

