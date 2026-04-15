# Database Clients
from redis import Redis
from qdrant_client import AsyncQdrantClient
from minio import Minio
from src.config.config import (
    MinioConfig,
    QdrantConfig,
    RedisConfig,
    load_minio_config,
    load_qdrant_config,
    load_redis_config,
)


def get_redis_client(config: RedisConfig | None = None) -> Redis:
    config = config or load_redis_config()
    return Redis(
        host=config.redis_host,
        port=config.redis_port,
        password=config.redis_password,
        decode_responses=True
    )

def get_async_qdrant_client(config: QdrantConfig | None = None) -> AsyncQdrantClient:
    config = config or load_qdrant_config()
    url = f"http://{config.qdrant_host}:{config.qdrant_api_port}"
    return AsyncQdrantClient(
        url=url,
        api_key=config.qdrant_api_key,
    )

def get_minio_client(config: MinioConfig | None = None) -> Minio:
    config = config or load_minio_config()
    return Minio(
        endpoint=f"{config.minio_host}:{config.minio_api_port}",
        access_key=config.minio_root_user,
        secret_key=config.minio_root_password,
        secure=False
    )


if __name__ == "__main__":
    redis_client = get_redis_client()
    qdrant_client = get_async_qdrant_client()
    minio_client = get_minio_client()

    print("Redis Client:", redis_client)
    print("Qdrant Client:", qdrant_client)
    print("MinIO Client:", minio_client)