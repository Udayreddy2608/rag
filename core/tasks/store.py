import asyncio
import logging
from pathlib import Path

from src.config.celery_config import celery_app
from core.layers.embedders.base import EmbeddedChunk
from core.layers.qdrant_upload import upload_to_qdrant
from src.config.config import load_qdrant_config

qdrant_config =  load_qdrant_config()
QDRANT_COLLECTION_NAME = qdrant_config.qdrant_collection_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery_app.task(
    bind = True,
    name = "store_document",
    queue = "store",
    max_retries = 3,
    default_retry_delay = 60
)
def store_document(self, data: dict):
    object_key = data.get("object", "unknown")
    tmp_path = data.get("tmp_path")
    embedded_chunks_raw = data.get("embedded_chunks", [])
    try:
        logger.info(f"Storing document: {data.get('object', 'unknown')}")
        embedded_chunks = [
            EmbeddedChunk(
                text=chunk["text"],
                embedding=chunk["embedding"],
                metadata=chunk["metadata"]
            )
            for chunk in embedded_chunks_raw
        ]
        logger.info(f"Uploading {len(embedded_chunks)} chunks to Qdrant for: {object_key}")
        asyncio.run(upload_to_qdrant(collection_name=QDRANT_COLLECTION_NAME, embedded_chunks=embedded_chunks))
        logger.info(f"Successfully stored document: {object_key}")
        return {"status": "success", "object": object_key}
    
    except Exception as exc:
        logger.error(f"Failed to store document {object_key}: {exc}")
        raise self.retry(exc=exc)
    
    finally:
        if tmp_path and Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
                logger.info(f"Temporary file removed: {tmp_path}")
            except Exception as exc:
                logger.error(f"Failed to remove temporary file {tmp_path}: {exc}")

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
