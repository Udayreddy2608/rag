from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

class MinioConfig(BaseSettings):
    minio_root_user: str = Field(..., description="MinIO root username")
    minio_root_password: str = Field(..., description="MinIO root password")
    minio_host: str = Field(..., description="MinIO host address")
    minio_api_port: int = Field(..., description="MinIO API port")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

class QdrantConfig(BaseSettings):
    qdrant_host: str = Field(..., description="Qdrant host address")
    qdrant_api_port: int = Field(
        ..., validation_alias="QDRANT_HTTP_PORT", description="Qdrant API port"
    )
    qdrant_log_level: str = Field(..., description="Qdrant log level (INFO, DEBUG, etc.)")
    qdrant_api_key: str = Field(..., description="Qdrant API key")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

class RedisConfig(BaseSettings):
    redis_host: str = Field(..., description="Redis host address")
    redis_port: int = Field(..., description="Redis port")
    redis_password: str = Field(..., description="Redis password")
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )


def load_minio_config() -> MinioConfig:
    return MinioConfig()  # type: ignore[call-arg]


def load_qdrant_config() -> QdrantConfig:
    return QdrantConfig()  # type: ignore[call-arg]


def load_redis_config() -> RedisConfig:
    return RedisConfig()  # type: ignore[call-arg]

if __name__ == "__main__":
    minio_config = load_minio_config()
    qdrant_config = load_qdrant_config()
    redis_config = load_redis_config()

    print("MinIO Configuration:")
    print(f"Root User: {minio_config.minio_root_user}")
    print(f"Root Password: {minio_config.minio_root_password}")
    print(f"Host: {minio_config.minio_host}")
    print(f"API Port: {minio_config.minio_api_port}")

    print("\nQdrant Configuration:")
    print(f"Host: {qdrant_config.qdrant_host}")
    print(f"API Port: {qdrant_config.qdrant_api_port}")
    print(f"Log Level: {qdrant_config.qdrant_log_level}")

    print("\nRedis Configuration:")
    print(f"Host: {redis_config.redis_host}")
    print(f"Port: {redis_config.redis_port}")
    print(f"Password: {redis_config.redis_password}")
