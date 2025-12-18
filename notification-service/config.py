"""Notification Service Configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        case_sensitive=False,
        extra="ignore"
    )
    
    service_name: str = "notification-service"
    service_port: int = 50054
    
    # PostgreSQL
    # Local development: localhost
    # Docker deployment: override with POSTGRES_HOST=postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: str
    
    # Email provider
    email_provider: str = "sendgrid"  # sendgrid, mailgun, ses
    email_api_key: Optional[str] = None
    email_from_address: str
    email_from_name: str = "Crypto Analytics"
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    prometheus_port: int = 9104
    
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_alerts: str = "crypto.alerts"
    kafka_consumer_group: str = "notification-service-group"
    
    # Retry logic
    max_retry_attempts: int = 3
    retry_interval_seconds: int = 60


settings = Settings()

