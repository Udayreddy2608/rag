from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

class MinioConfig(BaseSettings):
    minio_root_user: str = Field(..., description="MinIO root username")
    minio_root_password: str = Field(..., description="MinIO root password")
    minio_host: str = Field(..., description="MinIO host address")
    minio_api_port: int = Field(..., description="MinIO API port")
    minio_bucket_name: str = Field(..., description="MinIO bucket name")

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
    qdrant_collection_name: str = Field(..., description="Qdrant collection name")

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

class EmbeddingConfig(BaseSettings):
    embedding_model_name: str = Field(..., description="Embedding model name")
    embedding_api_key: str = Field(..., description="Embedding API key")
    embedding_batch_size: int = Field(100, description="Batch size for embedding requests")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )


def load_minio_config() -> MinioConfig:
    return MinioConfig()  # type: ignore[call-arg]


def load_qdrant_config() -> QdrantConfig:
    return QdrantConfig()  # type: ignore[call-arg]


def load_redis_config() -> RedisConfig:
    return RedisConfig()  # type: ignore[call-arg]

def load_embedding_config() -> EmbeddingConfig:
    return EmbeddingConfig()  # type: ignore[call-arg]

if __name__ == "__main__":
    minio_config = load_minio_config()
    qdrant_config = load_qdrant_config()
    redis_config = load_redis_config()
    embedding_config = load_embedding_config()

    print("MinIO Configuration:")
    print(f"Root User: {minio_config.minio_root_user}")
    print(f"Root Password: {minio_config.minio_root_password}")
    print(f"Host: {minio_config.minio_host}")
    print(f"API Port: {minio_config.minio_api_port}")
    print(f"Bucket Name: {minio_config.minio_bucket_name}")

    print("\nQdrant Configuration:")
    print(f"Host: {qdrant_config.qdrant_host}")
    print(f"API Port: {qdrant_config.qdrant_api_port}")
    print(f"Log Level: {qdrant_config.qdrant_log_level}")
    print(f"API Key: {qdrant_config.qdrant_api_key}")
    print(f"Collection Name: {qdrant_config.qdrant_collection_name}")

    print("\nRedis Configuration:")
    print(f"Host: {redis_config.redis_host}")
    print(f"Port: {redis_config.redis_port}")
    print(f"Password: {redis_config.redis_password}")

    print("\nEmbedding Configuration:")
    print(f"Model Name: {embedding_config.embedding_model_name}")
    print(f"API Key: {embedding_config.embedding_api_key}")
    print(f"Batch Size: {embedding_config.embedding_batch_size}")