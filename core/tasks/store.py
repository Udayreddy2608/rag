from src.config.celery_config import celery_app


@celery_app.task(
    bind = True,
    name = "store_document",
    queue = "store",
    max_retries = 3,
    default_retry_delay = 60
)
def store_document(self, data: dict):
    try:
        print(f"Storing document: {data.get('object', 'unknown')}")
        return {"status": "stored", "object": data.get("object")}
    except Exception as exc:
        raise self.retry(exc=exc)


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
