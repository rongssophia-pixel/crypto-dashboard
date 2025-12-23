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
    # Local development: http://localhost:4566
    # Docker deployment: override with AWS_ENDPOINT_URL=http://localstack:4566
    aws_endpoint_url: str = "http://localhost:4566"
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    athena_output_bucket: str = "crypto-athena-results"
    athena_database: str = "crypto_archive"
    athena_workgroup: str = "primary"

    # ClickHouse (used for exporting hot data to cold storage)
    # Railway/ClickHouse Cloud: CLICKHOUSE_HOST may include https:// prefix
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


settings = Settings()
