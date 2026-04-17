import logging
import tempfile
from pathlib import Path
import io

from src.config.celery_config import celery_app
from src.db.clients import get_minio_client
from core.layers.extraction import extract

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="ingest_data",
    queue="ingest",
    max_retries=3,
    default_retry_delay=60,
)
def ingest_data(self, metadata: dict) -> dict:
    object_key = metadata["object"]
    bucket = metadata["bucket"]
    file_hash = metadata["hash"]
    ext = Path(object_key).suffix.lower()
    tmp_path = Path(tempfile.gettempdir()) / f"{file_hash}{ext}"

    try:
        logger.info(f"Downloading {object_key} from bucket {bucket}")
        minio_client = get_minio_client()
        minio_client.fget_object(bucket, object_key, str(tmp_path))
        logger.info(f"Downloaded to {tmp_path}")

        extraction_result = extract(tmp_path)
        logger.info(f"Extracted {extraction_result.metadata.get('char_count', '?')} chars")

        # Upload extracted text to MinIO instead of returning it in the Celery result
        minio_client = get_minio_client()
        extracted_object_name = f"extracted/{file_hash}.txt"
        text_bytes = extraction_result.text.encode("utf-8")
        text_stream = io.BytesIO(text_bytes)
        try:
            minio_client.put_object(
                bucket_name=bucket,
                object_name=extracted_object_name,
                data=text_stream,
                length=len(text_bytes),
                content_type="text/plain; charset=utf-8",
            )
            logger.info(f"Uploaded extracted text to MinIO: {extracted_object_name}")
        except Exception as e:
            logger.error(f"Failed to upload extracted text to MinIO: {e}")

        # Return metadata and a pointer to the MinIO object; do NOT include the raw extracted text
        return {
            **metadata,
            "tmp_path": str(tmp_path),
            "extracted_minio_object": extracted_object_name,
            "extracted_metadata": extraction_result.metadata,
        }

    except Exception as exc:
        logger.error(f"Ingest failed for {object_key}: {exc}")
        raise self.retry(exc=exc)