"""Stream Processing Service Configuration"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "stream-processing-service"
    service_port: int = 50055
    
    # Kafka
    kafka_bootstrap_servers: str
    kafka_topic_raw_market_data: str = "crypto.raw.market-data"
    kafka_topic_processed_market_data: str = "crypto.processed.market-data"
    kafka_topic_alerts: str = "crypto.alerts"
    
    # ClickHouse
    clickhouse_host: str
    clickhouse_port: int = 9000
    clickhouse_db: str
    
    # Flink
    flink_endpoint: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    prometheus_port: int = 9105
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

