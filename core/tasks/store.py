import asyncio
import logging
from pathlib import Path
import json
import uuid

from src.config.celery_config import celery_app
from core.layers.embedders.base import EmbeddedChunk
from core.layers.qdrant_upload import upload_to_qdrant
from src.config.config import load_qdrant_config
from src.db.clients import get_minio_client, get_sync_qdrant_client
from qdrant_client import models as qdrant_models

qdrant_config =  load_qdrant_config()
QDRANT_COLLECTION_NAME = qdrant_config.qdrant_collection_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _upload_sync(collection_name: str, embedded_chunks: list):
    client = get_sync_qdrant_client()
    
    try:
        client.get_collection(collection_name)
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=len(embedded_chunks[0].embedding),
                distance=qdrant_models.Distance.COSINE,
            ),
        )

    points = []
    for i, ec in enumerate(embedded_chunks):
        file_hash = ec.metadata.get("file_hash") if isinstance(ec.metadata, dict) else None
        if file_hash:
            external_id = f"{file_hash}_{i}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, external_id))
        else:
            point_id = str(uuid.uuid4())

        payload = {
            "text": ec.text,
            **(ec.metadata if isinstance(ec.metadata, dict) else {})
        }

        payload.pop("embedding", None)

        points.append(qdrant_models.PointStruct(
            id=point_id,
            vector=ec.embedding,
            payload=payload, 
        ))


    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)

@celery_app.task(
    bind = True,
    name = "store_document",
    queue = "store",
    max_retries = 3,
    default_retry_delay = 60
)
def store_document(self, data: dict):
    object_key = data.get("object")
    tmp_path = data.get("tmp_path")

    try:
        minio_client = get_minio_client()
        embedded_object_name = data["embedded_minio_object"]
        
        logger.info(f"Downloading embedded chunks from MinIO: {embedded_object_name}")
        response = minio_client.get_object(data["bucket"], embedded_object_name)
        embedded_chunks_raw = json.loads(response.read().decode("utf-8"))
        logger.info(f"Downloaded {len(embedded_chunks_raw)} embedded chunks")

        embedded_chunks = [
            EmbeddedChunk(
                text=ec["text"],
                embedding=ec["embedding"],
                metadata={**ec["metadata"], "entities": ec.get("entities", {})},
            )
 
            for ec in embedded_chunks_raw
        ]

        logger.info(f"Storing {len(embedded_chunks)} chunks for {object_key}")
        _upload_sync(QDRANT_COLLECTION_NAME, embedded_chunks)
        logger.info(f"Successfully stored {len(embedded_chunks)} chunks for {object_key}")

        return {
            "status": "success",
            "object": object_key,
            "chunks_stored": len(embedded_chunks),
        }

    except Exception as exc:
        logger.error(f"Store failed for {object_key}: {exc}")
        raise self.retry(exc=exc)

    finally:
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink()
            logger.debug(f"Cleaned up temp file {tmp_path}")

if __name__ == "__main__":
    sample_document = {
        "id": "doc123",
        "title": "Sample Document",
        "content": "This is the content of the sample document.",
        "metadata": {
            "source": "user_upload",
            "minio_path": "documents/sample_document.pdf",
            "filehash": "abc123def456",
            "uploaded_at": "2024-06-01T12:00:00Z"
        }
    }
    store_document(sample_document)
