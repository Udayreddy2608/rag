import logging
from pathlib import Path
import json


from src.config.celery_config import celery_app
from src.db.models.document_models import Document
from core.layers.chunker import chunk
from core.layers.embedder import embed
from core.layers.extraction import ExtractionResult
from core.layers.entity_generation import extract_entities
from src.db.clients import get_minio_client
from minio.error import S3Error
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(
    bind = True,
    name = "transform_document",
    queue = "transform",
    max_retries = 3,
    default_retry_delay = 60
)
def transform_document(self, data: dict):
    object_key = data.get("object")
    logger.info(f"Starting transformation for: {object_key}")
    try:
        if "extracted_text" in data and data.get("extracted_text"):
            extraction_result = ExtractionResult(
                text=data["extracted_text"],
                metadata=data.get("extracted_metadata", {}),
            )
        elif "extracted_minio_object" in data:
            minio_client = get_minio_client()
            bucket = data.get("bucket")
            object_name = data["extracted_minio_object"]
            try:
                response = minio_client.get_object(bucket, object_name)
                raw = response.read()
                try:
                    text = raw.decode("utf-8")
                except Exception:
                    text = raw.decode("utf-8", errors="replace")
                extraction_result = ExtractionResult(
                    text=text,
                    metadata=data.get("extracted_metadata", {}),
                )
            except S3Error as e:
                logger.error(f"Failed to download extracted text from MinIO: {e}")
                raise self.retry(exc=e)
        else:
            tmp_path = data.get("tmp_path")
            if tmp_path:
                from core.layers.extraction import extract

                extraction_result = extract(Path(tmp_path))
            else:
                raise ValueError("No extracted text or MinIO pointer available in task data")
        logger.info(f"Chunking extracted text for: {object_key}")
        chunks = chunk(extraction_result, strategy='recursive')
        logger.info(f"Created {len(chunks)} chunks for: {object_key}")

        embedded_chunks = embed(chunks, provider_name="openai")
        logger.info(f"Embedded {len(embedded_chunks)} chunks for: {object_key}")

        entities = extract_entities(chunks, extractor_name="spacy")
        logger.info(f"Extracted entities for: {object_key}")

        file_hash = data.get("hash")
        embedded_object_name = f"embedded/{file_hash}.json"

        payload = json.dumps([
            {
                "text": ec.text,
                "embedding": ec.embedding,
                "metadata": ec.metadata,
                "entities": entities[i].to_dict() if i < len(entities) else {}
            }
            for i, ec in enumerate(embedded_chunks)
        ]).encode("utf-8")

        minio_client = get_minio_client()
        minio_client.put_object(
            bucket_name=data["bucket"],
            object_name=embedded_object_name,
            data=io.BytesIO(payload),
            length=len(payload),
            content_type="application/json",
        )
        logger.info(f"Uploaded {len(embedded_chunks)} embedded chunks to MinIO: {embedded_object_name}")

        return {
            **data,
            "embedded_minio_object": embedded_object_name,  # just a path, tiny
        }

    except Exception as exc:
        logger.error(f"Transformation failed for {object_key}: {exc}")
        raise self.retry(exc=exc)


if __name__ == "__main__":
    sample_document = Document(
        id="doc123",
        title="Sample Document",
        content="This is the content of the sample document.",
        metadata={
            "source": "user_upload",
            "minio_path": "documents/sample_document.pdf",
            "filehash": "abc123def456",
            "uploaded_at": "2024-06-01T12:00:00Z"
        }
    )
    transform_document(sample_document)
        