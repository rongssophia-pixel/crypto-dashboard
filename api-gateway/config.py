"""API Gateway Configuration"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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
    jwt_expiration_minutes: int = 60
    
    # CORS
    cors_origins: list = ["*"]
    
    # Monitoring
    prometheus_port: int = 9100
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

