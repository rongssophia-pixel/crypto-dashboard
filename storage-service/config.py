"""Storage Service Configuration"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "storage-service"
    service_port: int = 50053
    
    # AWS/LocalStack
    aws_endpoint_url: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    
    # Monitoring
    prometheus_port: int = 9103
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

