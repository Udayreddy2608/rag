from src.config.celery_config import celery_app
from src.config.config import load_minio_config, load_qdrant_config
from src.db.clients import get_async_qdrant_client, get_minio_client, get_redis_client
from src.db.models.document_models import DocumentMetadata

@celery_app.task(name="ingest_data",
                 bind = True,
                 queue = "ingest",
                 default_retry_delay = 60)
def ingest_data(self, data: dict):
    try:
        print(f"Starting ingestion for data: {data.get('file_name', 'unknown')}")
    except Exception as exc:
        print(f"Error occurred while ingesting data: {exc}")


if __name__ == "__main__":
    sample_data = {
        "file_name": "example_document.pdf",
        "content": "This is the content of the example document.",
        "metadata": {
            "source": "user_upload",
            "minio_path": "documents/example_document.pdf",
            "filehash": "abc123def456",
            "uploaded_at": "2024-06-01T12:00:00Z"
        }
    }
    ingest_data(sample_data)