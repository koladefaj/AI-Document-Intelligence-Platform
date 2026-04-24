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
    database_url: str | None = None
    database_sync_url: str | None = None
    db_port: int | None = None
    redis_url: str | None = None
    redis_port: int | None = None
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    minio_endpoint: str | None = None
    minio_bucket: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_api_port: int | None = None
    minio_console_port: int | None = None
    minio_secure: bool | None = None
    storage_type: str | None = None

    # --- R2 S3 --- #

    s3_endpoint: str = Field(default="http://localhost:9000")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="document-bucket")
    s3_region: str = Field(default="us-east-1")

    # --- 3. AI & SECURITY ---
    gemini_api: str | None = None
    ai_provider: str = Field(default="ollama")
    ollama_model: str = Field(default="llama3")
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_embedding_model: str = Field(default="nomic-embed-text")
    gemini_model: str = Field(default="gemini-2.0-flash")
    gemini_embedding_model: str = Field(default="models/embedding-001")
    allowed_origins: str = Field(default="http://localhost:8000,http://localhost:3000")
    secret_key: str | None = None
    access_token_expire_minutes: int | None = None
    refresh_token_expire_days: int | None = None
    jwt_algorithm: str | None = None
    
    def __init__(self, **values):
        super().__init__(**values)
        
        # 1. Check for Railway FIRST. If on Railway, DO NOT touch the strings.
        # Railway injects its own internal URLs which should be used as-is.
        is_railway = os.environ.get('RAILWAY_ENVIRONMENT_ID') is not None
        
        # 2. Check for Docker (Local Compose)
        is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
        
        if is_railway:
            logger.info("Railway environment detected. Using Dashboard variables as provided.")
        elif is_docker:
            logger.info("Local Docker detected. Using internal network routing.")
        else:
            logger.info("Local Windows/OS detected. Using localhost connections.")

    @field_validator("gemini_api", mode="after")
    @classmethod
    def clean_api_key(cls, v: str | None) -> str:
        if v is None:
            return ""
        return v.strip().strip('"').strip("'")

    model_config = SettingsConfigDict(
        # System Environment Variables (Railway) always 
        # override the .env file (Local).
        env_file=".env" if os.path.exists(".env") else None,
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=False 
    )

settings = Settings()
