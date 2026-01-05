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
        
        # Better Docker detection - check multiple indicators
        is_docker = (
            os.path.exists('/.dockerenv') or 
            os.path.exists('/proc/1/cgroup') and 
            any('docker' in line for line in open('/proc/1/cgroup', 'r').readlines())
        ) if os.name != 'nt' else False  # Never true on Windows (nt)
        
        # OR: Use an explicit environment variable instead
        # is_docker = os.getenv('RUNNING_IN_DOCKER', 'false').lower() == 'true'
        
        if is_docker:
            logger.info("Docker environment detected. Routing traffic to service names.")
            self.database_url = self.database_url.replace("localhost", "db").replace("127.0.0.1", "db")
            self.database_sync_url = self.database_sync_url.replace("localhost", "db").replace("127.0.0.1", "db")
            self.redis_url = self.redis_url.replace("localhost", "redis").replace("127.0.0.1", "redis")
            self.celery_broker_url = self.celery_broker_url.replace("localhost", "redis").replace("127.0.0.1", "redis")
            self.celery_result_backend = self.celery_result_backend.replace("localhost", "redis").replace("127.0.0.1", "redis")
            self.minio_endpoint = self.minio_endpoint.replace("localhost", "minio").replace("127.0.0.1", "minio")
        else:
            logger.info("Local environment detected. Using localhost for services.")

    @field_validator("gemini_api", mode="after")
    @classmethod
    def clean_api_key(cls, v: str) -> str:
        return v.strip().strip('"').strip("'")

    model_config = SettingsConfigDict(
        env_file=".env" if os.path.exists(".env") else None,
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=False 
    )

settings = Settings()