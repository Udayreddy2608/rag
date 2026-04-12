from src.config.celery_config import celery_app
from src.db.models.document_models import Document

@celery_app.task(
    bind = True,
    name = "tasks.transform.transform_document",
    queue = "transform",
    max_retries = 3,
    default_retry_delay = 60
)
def transform_document(self, document: Document):
    try:
        print(f"Starting transformation for document: {document.id}")
    except Exception as exc:
        print(f"Error occurred while transforming document {document.id}: {exc}")


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
        