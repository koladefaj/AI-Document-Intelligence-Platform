from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    app_env: str = Field(default="local")
    app_name: str = Field(default="document-intelligence-backend")

    database_url: str
    database_sync_url: str
    database_username: str
    database_password: str
    db_port: int


    redis_url: str
    redis_port: int

    celery_broker_url: str
    celery_result_backend: str

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool = False
    minio_api_port: int
    minio_console_port: int

    jwt_algorithm: str = "HS256"
    secret_key: str
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings()