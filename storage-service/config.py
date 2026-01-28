"""Storage Service Configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        case_sensitive=False,
        extra="ignore"
    )
    
    service_name: str = "storage-service"
    service_port: int = 50053
    http_port: int = 8003

    # AWS/LocalStack
    # Local development: set AWS_ENDPOINT_URL=http://localhost:4566
    # Production (Railway): leave unset to use real AWS
    aws_endpoint_url: str | None = None
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-2"
    s3_bucket_name: str
    athena_output_bucket: str = "crypto-athena-results-2026"
    athena_database: str = "crypto_archive"
    athena_workgroup: str = "primary"

    # ClickHouse (used for exporting hot data to cold storage)
    # Railway/ClickHouse Cloud: CLICKHOUSE_HOST may include https:// prefix
    # Local: localhost:9000, ClickHouse Cloud: use port 9440 with secure=true
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_db: str = "crypto_analytics"
    clickhouse_user: str = "default"
    clickhouse_password: str
    clickhouse_secure: bool = False
    clickhouse_verify: bool = True
    
    @field_validator('clickhouse_host')
    @classmethod
    def clean_clickhouse_host(cls, v: str) -> str:
        """Strip protocol prefix and port from ClickHouse host URL"""
        if not v:
            return v
        # Remove protocol prefix (https://, http://)
        if '://' in v:
            v = v.split('://', 1)[1]
        # Remove port suffix if present (e.g., host:8443)
        if ':' in v:
            v = v.split(':', 1)[0]
        return v

    # Postgres (for job tracking)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "crypto_analytics"
    postgres_user: str = "postgres"
    postgres_password: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    # Monitoring
    prometheus_port: int = 9103

    # Archival TTL Configuration (data older than TTL will be archived to S3 then deleted)
    # Use hours for finer granularity (e.g., 24 = 1 day, 6 = 6 hours)
    market_data_ttl_hours: int = 2  # Default: 24 hours (1 day)
    market_candles_ttl_hours: int = 120  # Default: 120 hours (5 days)

    # Archival Scheduler Configuration
    archival_enabled: bool = True
    archival_check_interval_hours: int = 1  # How often to check for data to archive (deprecated, use cron)
    
    # Archival Cron Schedules (cron expressions: minute hour day month day_of_week)
    # Format: "minute hour day month day_of_week"
    # Examples: "0 * * * *" = every hour, "30 7 * * *" = daily at 7:30 AM UTC
    archival_market_data_cron: str = "0 * * * *"      # Every hour at minute 0
    archival_market_candles_cron: str = "30 7 * * *"  # Daily at 7:30 AM UTC (11:30 PM PST)


settings = Settings()
