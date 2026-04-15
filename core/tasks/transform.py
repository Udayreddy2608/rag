import logging


from src.config.celery_config import celery_app
from src.db.models.document_models import Document
from core.layers.chunker import chunk
from core.layers.embedder import embed
from core.layers.extraction import ExtractionResult

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
        extraction_result = ExtractionResult(
            text=data["extracted_text"],
            metadata=data["extracted_metadata"]
        )
        logger.info(f"Chunking extracted text for: {object_key}")
        chunks = chunk(extraction_result, strategy='recursive')
        logger.info(f"Created {len(chunks)} chunks for: {object_key}")
        embedded_chunks = embed(chunks, provider_name="openai")
        logger.info(f"Embedded {len(embedded_chunks)} chunks for: {object_key}")
        return {
            **data,
            "embedded_chunks": [
                {
                    "text": ec.text,
                    "embedding": ec.embedding,
                    "metadata": ec.metadata,
                }
                for ec in embedded_chunks
            ],
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
        