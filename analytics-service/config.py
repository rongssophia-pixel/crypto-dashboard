"""
Analytics Service Configuration
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration settings"""
    
    service_name: str = "analytics-service"
    service_port: int = 50052
    
    # ClickHouse configuration
    clickhouse_host: str
    clickhouse_port: int = 9000
    clickhouse_db: str
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    
    # JWT configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    prometheus_port: int = 9102
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

