"""Notification Service Configuration"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    service_name: str = "notification-service"
    service_port: int = 50054
    
    # PostgreSQL
    postgres_host: str
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

