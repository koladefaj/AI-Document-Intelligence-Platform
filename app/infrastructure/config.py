import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # --- 1. APP BASICS ---
    app_env: str = Field(default="local")
    app_name: str = Field(default="document-intelligence-backend")

    # --- 2. DATABASE & REDIS ---
    database_url: str
    database_sync_url: str
    db_port: int
    redis_url: str
    redis_port: int
    celery_broker_url: str
    celery_result_backend: str
    minio_endpoint: str
    minio_bucket: str
    minio_access_key: str
    minio_secret_key: str
    minio_api_port: int
    minio_console_port: int
    minio_secure: bool
    storage_type: str

    # --- R2 S3 --- #

    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str | None = None
    s3_region: str = "auto"

    # --- 3. AI & SECURITY ---
    gemini_api: str
    ai_provider: str 
    ollama_model: str
    secret_key: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    jwt_algorithm: str
    
    def __init__(self, **values):
        super().__init__(**values)
        
        # 1. Check for Railway FIRST. If we are on Railway, DO NOT touch the strings.
        # Railway injects its own internal URLs which should be used as-is.
        is_railway = os.environ.get('RAILWAY_ENVIRONMENT_ID') is not None
        
        # 2. Check for Docker (Local Compose)
        is_docker = os.path.exists('/.dockerenv')
        
        if is_railway:
            logger.info("Railway environment detected. Using Dashboard variables as provided.")
        elif is_docker:
            logger.info("Local Docker detected. Routing traffic to service names (db, redis, minio).")
            # Replace localhost with the service names defined in your docker-compose.yml
            # Ensure your DB service in docker-compose is named 'db' or 'postgres_db'
            target_db = "postgres_db" # Change to "db" if that's your service name
            
            self.database_url = self.database_url.replace("localhost", target_db).replace("127.0.0.1", target_db)
            self.database_sync_url = self.database_sync_url.replace("localhost", target_db).replace("127.0.0.1", target_db)
            
            self.redis_url = self.redis_url.replace("localhost", "redis").replace("127.0.0.1", "redis")
            self.celery_broker_url = self.celery_broker_url.replace("localhost", "redis").replace("127.0.0.1", "redis")
            self.celery_result_backend = self.celery_result_backend.replace("localhost", "redis").replace("127.0.0.1", "redis")
            
            self.minio_endpoint = self.minio_endpoint.replace("localhost", "minio").replace("127.0.0.1", "minio")
        else:
            logger.info("Local Windows/OS detected. Using localhost connections.")

    @field_validator("gemini_api", mode="after")
    @classmethod
    def clean_api_key(cls, v: str) -> str:
        return v.strip().strip('"').strip("'")

    model_config = SettingsConfigDict(
        # This order is important: System Environment Variables (Railway) always 
        # override the .env file (Local).
        env_file=".env" if os.path.exists(".env") else None,
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=False 
    )

settings = Settings()