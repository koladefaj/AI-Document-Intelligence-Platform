from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import logging

# Get a logger for config-specific warnings
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Centralized configuration management.
    Values are loaded in the following priority:
    1. Initializer arguments (highest)
    2. Environment variables
    3. .env file
    4. Default values (lowest)
    """

    # --- 1. APP BASICS ---
    app_env: str = Field(default="local") # 'local', 'development', 'production'
    app_name: str = Field(default="document-intelligence-backend")

    # --- 2. DATABASE (Postgres) ---
    # Dev Note: In Docker, database_url should point to 'db:5432'
    database_url: str        # Async URL (e.g., postgresql+asyncpg://...)
    database_sync_url: str   # Sync URL for Celery (e.g., postgresql://...)
    database_username: str
    database_password: str
    db_port: int = 5432

    # --- 3. CACHE & BROKER (Redis) ---
    # Dev Note: Used for both Celery tasks and WebSocket Pub/Sub
    redis_url: str           # e.g., redis://redis:6379/0
    redis_port: int = 6379

    # --- 4. AI PROVIDERS ---
    gemini_api: str          # Google AI API Key
    ai_provider: str = "gemini" # Can be 'gemini' or 'ollama'

    # --- 5. TASK QUEUE (Celery) ---
    celery_broker_url: str
    celery_result_backend: str

    # --- 6. FILE STORAGE (MinIO / S3) ---
    # Dev Note: If USE_MINIO=true, these must be valid and reachable
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False
    minio_api_port: int = 9000
    minio_console_port: int = 9001

    # --- 7. SECURITY & JWT ---
    jwt_algorithm: str = "HS256"
    secret_key: str          # Critical: Must be a long, random string in production
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 7

    # --- 8. PYDANTIC CONFIGURATION ---
    model_config = SettingsConfigDict(
        # Look for a file named .env in the root project directory
        env_file=".env",
        env_file_encoding="utf-8",
        # 'allow' lets us pass extra vars that aren't defined above (useful for legacy logs)
        extra="allow",
        # Case insensitive means 'DATABASE_URL' in .env maps to 'database_url' in Python
        case_sensitive=False 
    )

# Singleton instance used by the rest of the application
settings = Settings()